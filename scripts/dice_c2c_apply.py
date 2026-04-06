#!/usr/bin/env python3
"""
Dice C2C Job Applier — Targeted script for Vamsi M.
Searches multiple Dice URLs, filters for C2C eligibility, and applies via Easy Apply / wizard.

Usage:
    python3 scripts/dice_c2c_apply.py
    python3 scripts/dice_c2c_apply.py --dry-run
    python3 scripts/dice_c2c_apply.py --target 20
"""
import argparse
import asyncio
import hashlib
import json
import logging
import os
import random
import signal
import sqlite3
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "jobs.db"
LOG_DIR = PROJECT_ROOT / "data" / "logs"
PROFILE_DIR = PROJECT_ROOT / "data" / "browser_profile"

sys.path.insert(0, str(PROJECT_ROOT))

from playwright.async_api import async_playwright, TimeoutError as PwTimeout

LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"dice_c2c_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file),
    ],
)
logger = logging.getLogger("dice_c2c")

# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
PROFILE = {
    "first_name": "Vamsi",
    "last_name": "M",
    "email": "vamsim.java@gmail.com",
    "phone": "(929) 341-0298",
    "location": "South Plainfield, NJ 07080",
    "title": "Sr Java Full Stack Developer",
    "experience": "9",
    "visa": "H1B",
    "rate": "$90/hr C2C",
    "pitch": "Sr Java Full Stack Developer with 9 years experience. Available for C2C contract at $90/hr.",
}

# ---------------------------------------------------------------------------
# Search URLs
# ---------------------------------------------------------------------------
SEARCH_URLS = [
    "https://www.dice.com/jobs?q=Java+Developer+C2C&datePosted=ONE_WEEK&employmentType=CONTRACTS",
    "https://www.dice.com/jobs?q=Java+Spring+Boot+contract&datePosted=ONE_WEEK&employmentType=CONTRACTS&location=Remote",
    "https://www.dice.com/jobs?q=Java+Full+Stack+C2C&datePosted=ONE_WEEK&employmentType=CONTRACTS",
    "https://www.dice.com/jobs?q=Java+Microservices+C2C+contract&datePosted=ONE_WEEK&employmentType=CONTRACTS",
]

# ---------------------------------------------------------------------------
# Filter rules
# ---------------------------------------------------------------------------
TITLE_EXCLUDE = [
    "lead", "architect", "principal", "director", "manager", "vp", "chief",
    "staff engineer", "distinguished", "head of",
    ".net", "python", "okta", "kdb", "security clearance",
]

C2C_EXCLUSION_PHRASES = [
    "w2 only", "no c2c", "citizens only", "gc only", "no third party",
    "us citizens only", "green card only", "no corp to corp",
    "w-2 only", "no corp-to-corp", "citizen only", "only w2",
]

_shutdown = False

def _handle_signal(sig, frame):
    global _shutdown
    if _shutdown:
        sys.exit(1)
    logger.warning("Shutdown requested. Finishing current job...")
    _shutdown = True

signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn

def dedup_hash(source, ext_id):
    return hashlib.sha256(f"{source}:{ext_id}".encode()).hexdigest()

def was_applied(conn, dhash):
    row = conn.execute(
        """SELECT a.id FROM applications a JOIN jobs j ON j.id = a.job_id
           WHERE j.dedup_hash = ? AND a.status IN ('submitted','success')""",
        (dhash,),
    ).fetchone()
    return row is not None

def insert_job(conn, **kw):
    dhash = kw.get("dedup_hash") or dedup_hash(kw["source"], kw["external_id"])
    kw["dedup_hash"] = dhash
    cols = ", ".join(kw.keys())
    ph = ", ".join(["?"] * len(kw))
    try:
        cur = conn.execute(f"INSERT OR IGNORE INTO jobs ({cols}) VALUES ({ph})", list(kw.values()))
        conn.commit()
        if cur.lastrowid:
            return cur.lastrowid
        row = conn.execute("SELECT id FROM jobs WHERE dedup_hash = ?", (dhash,)).fetchone()
        return row["id"] if row else 0
    except Exception as e:
        logger.error(f"DB insert error: {e}")
        return 0

def record_application(conn, job_id, method, status, error_msg=None):
    conn.execute(
        "INSERT INTO applications (job_id, method, ats_platform, status, error_message) VALUES (?, ?, ?, ?, ?)",
        (job_id, method, method, status, error_msg),
    )
    conn.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
    conn.commit()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def human_delay(lo=1.0, hi=3.0):
    await asyncio.sleep(random.uniform(lo, hi))

async def page_text(page):
    try:
        return await page.inner_text("body")
    except Exception:
        return ""

def should_skip_title(title):
    t = title.lower()
    return any(exc in t for exc in TITLE_EXCLUDE)

def has_c2c_exclusion(text):
    t = text.lower()
    return any(phrase in t for phrase in C2C_EXCLUSION_PHRASES)

# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

async def extract_jobs_from_page(page):
    """Extract job links from a Dice search results page."""
    jobs = []
    try:
        await page.wait_for_selector(
            'a[href*="/job-detail/"], a[id^="job-title-"], .card-title-link',
            timeout=15000,
        )
    except PwTimeout:
        logger.warning("No job cards found on page")
        return jobs

    # Use JS extraction as specified in the task
    results = await page.evaluate("""
        (() => {
            const seen = new Set();
            const results = [];
            document.querySelectorAll('a[href*="/job-detail/"]').forEach(l => {
                const href = l.href.split('?')[0];
                if (seen.has(href)) return;
                const title = l.textContent.trim();
                if (title && !['Apply Now','Applied','Easy Apply','Save','Saved'].includes(title)) {
                    seen.add(href);
                    results.push({url: href, title: title});
                }
            });
            return results;
        })()
    """)

    for r in results:
        url = r["url"]
        title = r["title"]
        uuid = ""
        if "/job-detail/" in url:
            uuid = url.split("/job-detail/")[-1].split("?")[0]
        if uuid and title:
            jobs.append({"uuid": uuid, "title": title, "url": url})

    return jobs


async def collect_all_jobs(page):
    """Navigate all search URLs and collect unique job listings."""
    all_jobs = {}
    for search_url in SEARCH_URLS:
        if _shutdown:
            break
        logger.info(f"Loading: {search_url}")
        await page.goto(search_url, wait_until="domcontentloaded")
        await human_delay(3, 5)

        jobs = await extract_jobs_from_page(page)
        new_count = 0
        for j in jobs:
            if j["uuid"] not in all_jobs:
                all_jobs[j["uuid"]] = j
                new_count += 1
        logger.info(f"  Found {len(jobs)} jobs, {new_count} new (total unique: {len(all_jobs)})")

        # Also check page 2 if many results
        if len(jobs) >= 18:
            page2_url = search_url + ("&" if "?" in search_url else "?") + "page=2"
            logger.info(f"Loading page 2: {page2_url}")
            await page.goto(page2_url, wait_until="domcontentloaded")
            await human_delay(3, 5)
            jobs2 = await extract_jobs_from_page(page)
            new2 = 0
            for j in jobs2:
                if j["uuid"] not in all_jobs:
                    all_jobs[j["uuid"]] = j
                    new2 += 1
            logger.info(f"  Page 2: {len(jobs2)} jobs, {new2} new (total unique: {len(all_jobs)})")

    return list(all_jobs.values())


async def check_job_detail(page, job):
    """Navigate to job detail, check for C2C exclusions, return eligibility info."""
    url = job["url"]
    logger.info(f"  Checking: {job['title'][:60]}")
    await page.goto(url, wait_until="domcontentloaded")
    await human_delay(2, 3)

    body = await page_text(page)

    # Check C2C exclusions in description
    if has_c2c_exclusion(body):
        return {"eligible": False, "reason": "C2C exclusion in description"}

    # Check if already applied
    if "applied" in body.lower()[:500]:
        # Check for Applied badge near the apply button area
        applied_el = await page.query_selector('text="Applied"')
        if applied_el:
            return {"eligible": False, "reason": "Already applied"}

    # Check for Easy Apply button
    easy_apply = await page.query_selector(
        'button:has-text("Easy Apply"), apply-button-wc, a:has-text("Easy Apply")'
    )
    if not easy_apply:
        # Check for "Apply on company site" — skip those
        company_apply = await page.query_selector('text="Apply on company site"')
        if company_apply:
            return {"eligible": False, "reason": "Apply on company site (external)"}
        # May be a different button text
        apply_btn = await page.query_selector('button:has-text("Apply")')
        if not apply_btn:
            return {"eligible": False, "reason": "No apply button found"}

    # Get company name from detail page
    company = ""
    try:
        company_el = await page.query_selector('[data-testid="employer-name"], .employer-name, a[data-cy="companyNameLink"]')
        if company_el:
            company = (await company_el.inner_text()).strip()
    except Exception:
        pass

    return {"eligible": True, "company": company}


async def apply_via_wizard(page, job):
    """Apply using Dice's wizard flow (navigates to /job-applications/{uuid}/wizard)."""
    uuid = job["uuid"]
    wizard_url = f"https://www.dice.com/job-applications/{uuid}/wizard"
    logger.info(f"  Opening wizard: {wizard_url}")

    try:
        await page.goto(wizard_url, wait_until="domcontentloaded")
        await human_delay(2, 3)

        current_url = page.url
        # Check login redirect
        if "/dashboard/login" in current_url or "/login" in current_url:
            logger.error("  Redirected to login -- need to be signed in to Dice")
            return False, "login_required"

        body = await page_text(page)
        if "already applied" in body.lower() or "previously applied" in body.lower():
            logger.info("  Already applied (wizard says so)")
            return False, "already_applied"

        # Step through wizard
        for step in range(6):
            if _shutdown:
                return False, "shutdown"

            await human_delay(1, 2)

            # Fill any visible text fields that are empty
            await _fill_form_fields(page)

            # Check for submit button (final step)
            submit_btn = await page.query_selector(
                'button[type="submit"]:has-text("Submit"), '
                'button:has-text("Submit Application"), '
                'button:has-text("Submit")'
            )
            if submit_btn and await submit_btn.is_visible():
                logger.info(f"  Step {step+1}: Clicking Submit")
                await submit_btn.scroll_into_view_if_needed()
                await human_delay(0.5, 1)
                await submit_btn.click()
                await human_delay(2, 4)

                body = await page_text(page)
                success_words = ["success", "submitted", "thank you", "application received", "application sent"]
                if any(w in body.lower() for w in success_words):
                    return True, "submitted"
                # If URL changed away from wizard, likely success
                if "job-applications" not in page.url:
                    return True, "submitted"
                return True, "submitted"

            # Check for Next button
            next_btn = await page.query_selector(
                'button:has-text("Next"), button:has-text("Continue"), button[data-testid="next-button"]'
            )
            if next_btn and await next_btn.is_visible():
                logger.info(f"  Step {step+1}: Clicking Next")
                await next_btn.scroll_into_view_if_needed()
                await human_delay(0.5, 1)
                await next_btn.click()
                await human_delay(1.5, 2.5)
                continue

            # Check for Easy Apply / Apply button
            apply_btn = await page.query_selector(
                'button:has-text("Easy Apply"), button:has-text("Apply")'
            )
            if apply_btn and await apply_btn.is_visible():
                logger.info(f"  Step {step+1}: Clicking Apply")
                await apply_btn.scroll_into_view_if_needed()
                await human_delay(0.5, 1)
                await apply_btn.click()
                await human_delay(1.5, 2.5)
                continue

            logger.warning(f"  No actionable button at step {step+1}")
            break

        return False, "wizard_incomplete"

    except PwTimeout:
        return False, "timeout"
    except Exception as e:
        logger.error(f"  Wizard error: {e}")
        return False, str(e)[:100]


async def _fill_form_fields(page):
    """Fill form fields on wizard pages with profile data."""
    # Fill text inputs
    inputs = await page.query_selector_all('input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"]):not([type="file"])')
    for inp in inputs:
        try:
            if not await inp.is_visible():
                continue
            val = (await inp.get_attribute("value") or "").strip()
            if val:
                continue  # Already filled

            name = (await inp.get_attribute("name") or "").lower()
            placeholder = (await inp.get_attribute("placeholder") or "").lower()
            label = (await inp.get_attribute("aria-label") or "").lower()
            field_id = name + placeholder + label

            if any(k in field_id for k in ["first", "fname"]):
                await inp.fill(PROFILE["first_name"])
            elif any(k in field_id for k in ["last", "lname", "surname"]):
                await inp.fill(PROFILE["last_name"])
            elif any(k in field_id for k in ["email", "e-mail"]):
                await inp.fill(PROFILE["email"])
            elif any(k in field_id for k in ["phone", "mobile", "tel"]):
                await inp.fill(PROFILE["phone"])
            elif any(k in field_id for k in ["city", "location"]):
                await inp.fill("South Plainfield, NJ")
            elif any(k in field_id for k in ["year", "experience"]):
                await inp.fill(PROFILE["experience"])
        except Exception:
            continue

    # Fill textareas (cover letter, additional info)
    textareas = await page.query_selector_all("textarea")
    for ta in textareas:
        try:
            if not await ta.is_visible():
                continue
            val = (await ta.input_value()).strip()
            if not val:
                await ta.fill(PROFILE["pitch"])
        except Exception:
            continue

    # Handle select dropdowns (work authorization, sponsorship)
    selects = await page.query_selector_all("select")
    for sel in selects:
        try:
            if not await sel.is_visible():
                continue
            name = (await sel.get_attribute("name") or "").lower()
            label = (await sel.get_attribute("aria-label") or "").lower()
            field_id = name + label

            options = await sel.query_selector_all("option")
            option_texts = []
            for opt in options:
                option_texts.append((await opt.inner_text()).strip().lower())

            if any(k in field_id for k in ["auth", "eligible", "legally", "right to work"]):
                # Select Yes for work authorization
                for opt_text in ["yes", "authorized", "h1b"]:
                    if any(opt_text in ot for ot in option_texts):
                        await sel.select_option(label=next(ot for ot in option_texts if opt_text in ot))
                        break
            elif any(k in field_id for k in ["sponsor"]):
                # Select No for sponsorship
                for opt_text in ["no"]:
                    if any(opt_text in ot for ot in option_texts):
                        await sel.select_option(label=next(ot for ot in option_texts if opt_text in ot))
                        break
        except Exception:
            continue


async def apply_via_easy_apply_button(page, job):
    """Try clicking Easy Apply on the job detail page, then fill the form."""
    try:
        # Click Easy Apply button
        easy_apply = await page.query_selector(
            'button:has-text("Easy Apply"), apply-button-wc'
        )
        if easy_apply:
            await easy_apply.click()
            await human_delay(2, 3)

        # Check if a modal/form appeared or if we were redirected to wizard
        if "/job-applications/" in page.url and "/wizard" in page.url:
            # Redirected to wizard
            return await _continue_wizard(page, job)

        # Maybe a modal popped up — try filling it
        await _fill_form_fields(page)
        await human_delay(1, 2)

        # Try submit
        submit_btn = await page.query_selector(
            'button[type="submit"]:has-text("Submit"), button:has-text("Submit Application")'
        )
        if submit_btn and await submit_btn.is_visible():
            await submit_btn.click()
            await human_delay(2, 3)
            body = await page_text(page)
            if any(w in body.lower() for w in ["success", "submitted", "thank you"]):
                return True, "submitted"
            return True, "submitted"

        # Fall back to wizard approach
        return await apply_via_wizard(page, job)

    except Exception as e:
        logger.error(f"  Easy apply error: {e}")
        return False, str(e)[:100]


async def _continue_wizard(page, job):
    """Continue through wizard after being redirected from Easy Apply."""
    for step in range(6):
        await human_delay(1, 2)
        await _fill_form_fields(page)

        submit_btn = await page.query_selector('button:has-text("Submit")')
        if submit_btn and await submit_btn.is_visible():
            await submit_btn.click()
            await human_delay(2, 3)
            return True, "submitted"

        next_btn = await page.query_selector('button:has-text("Next"), button:has-text("Continue")')
        if next_btn and await next_btn.is_visible():
            await next_btn.click()
            await human_delay(1.5, 2.5)
            continue

        break
    return False, "wizard_incomplete"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    parser = argparse.ArgumentParser(description="Dice C2C Job Applier for Vamsi M")
    parser.add_argument("--dry-run", action="store_true", help="Scan only, don't apply")
    parser.add_argument("--target", type=int, default=20, help="Target number of applications")
    args = parser.parse_args()

    conn = get_db()
    results = []  # Track all results
    stats = {"found": 0, "applied": 0, "skipped": 0, "failed": 0, "already": 0}

    logger.info("=" * 60)
    logger.info("Dice C2C Applier for Vamsi M")
    logger.info(f"Target: {args.target} applications | Dry run: {args.dry_run}")
    logger.info(f"Log: {log_file}")
    logger.info("=" * 60)

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1400, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.pages[0] if context.pages else await context.new_page()

        try:
            # Step 0: Ensure logged in to Dice
            logger.info("\n--- STEP 0: Checking Dice login ---")
            await page.goto("https://www.dice.com/dashboard", wait_until="domcontentloaded")
            await human_delay(3, 5)

            current_url = page.url
            if "/dashboard/login" in current_url or "/login" in current_url:
                logger.info("Not logged in to Dice. Navigating to login page...")
                logger.info("============================================")
                logger.info("  PLEASE LOG IN TO DICE IN THE BROWSER WINDOW")
                logger.info("============================================")
                logger.info("Waiting up to 180 seconds for login...")

                # Wait for redirect away from login page
                logged_in = False
                for wait_i in range(90):
                    await asyncio.sleep(2)
                    cur = page.url
                    if "/login" not in cur and "/dashboard/login" not in cur:
                        logger.info(f"Login detected! Current URL: {cur}")
                        logged_in = True
                        break
                    if wait_i % 10 == 0 and wait_i > 0:
                        logger.info(f"  Still waiting for login... ({wait_i * 2}s)")

                if not logged_in:
                    logger.error("Login timeout after 180 seconds. Exiting.")
                    await context.close()
                    conn.close()
                    return

                await human_delay(2, 3)
            else:
                logger.info("Already logged in to Dice!")

            # Step 1: Collect jobs from all search URLs
            logger.info("\n--- STEP 1: Collecting jobs ---")
            all_jobs = await collect_all_jobs(page)
            stats["found"] = len(all_jobs)
            logger.info(f"Total unique jobs found: {len(all_jobs)}")

            # Step 2: Filter and apply
            logger.info("\n--- STEP 2: Filtering and applying ---")
            applied_count = 0

            for i, job in enumerate(all_jobs):
                if _shutdown or applied_count >= args.target:
                    break

                title = job["title"]
                uuid = job["uuid"]
                url = job["url"]

                logger.info(f"\n[{i+1}/{len(all_jobs)}] {title[:70]}")

                # Title filter
                if should_skip_title(title):
                    logger.info(f"  SKIP: excluded title keyword")
                    stats["skipped"] += 1
                    results.append({"title": title, "url": url, "result": "skipped", "reason": "excluded title"})
                    continue

                # Check DB for already applied
                dhash = dedup_hash("dice", uuid)
                if was_applied(conn, dhash):
                    logger.info(f"  SKIP: already in DB")
                    stats["already"] += 1
                    results.append({"title": title, "url": url, "result": "skipped", "reason": "already applied (DB)"})
                    continue

                # Check job detail page
                detail = await check_job_detail(page, job)
                if not detail["eligible"]:
                    reason = detail["reason"]
                    logger.info(f"  SKIP: {reason}")
                    stats["skipped"] += 1
                    results.append({"title": title, "url": url, "result": "skipped", "reason": reason})
                    continue

                company = detail.get("company", "Unknown")

                if args.dry_run:
                    logger.info(f"  DRY-RUN: Would apply -- {title[:60]} @ {company}")
                    results.append({"title": title, "company": company, "url": url, "result": "dry_run"})
                    continue

                # Insert job into DB
                job_id = insert_job(
                    conn, external_id=uuid, source="dice", title=title,
                    company=company, location=job.get("location", ""),
                    job_type="contract", url=url, status="matched",
                )

                # Apply via wizard
                success, status_msg = await apply_via_wizard(page, job)

                if success:
                    record_application(conn, job_id, "dice_wizard", "submitted")
                    stats["applied"] += 1
                    applied_count += 1
                    logger.info(f"  APPLIED ({applied_count}/{args.target}): {title[:60]} @ {company}")
                    results.append({"title": title, "company": company, "url": url, "result": "applied"})
                else:
                    if status_msg == "already_applied":
                        stats["already"] += 1
                        results.append({"title": title, "company": company, "url": url, "result": "skipped", "reason": "already applied"})
                    elif status_msg == "login_required":
                        logger.error("LOGIN REQUIRED -- Session expired mid-run")
                        results.append({"title": title, "company": company, "url": url, "result": "failed", "reason": "login required"})
                        stats["failed"] += 1
                        # Try to re-login
                        logger.info("Attempting to navigate back to login...")
                        await page.goto("https://www.dice.com/dashboard/login", wait_until="domcontentloaded")
                        logger.info("Please log in again. Waiting 120s...")
                        relogged = False
                        for wait_i in range(60):
                            await asyncio.sleep(2)
                            if "/login" not in page.url:
                                relogged = True
                                logger.info("Re-login successful!")
                                break
                        if not relogged:
                            logger.error("Re-login timeout. Stopping.")
                            break
                    else:
                        record_application(conn, job_id, "dice_wizard", "failed", status_msg)
                        stats["failed"] += 1
                        results.append({"title": title, "company": company, "url": url, "result": "failed", "reason": status_msg})

                await human_delay(2, 4)

        except Exception as e:
            logger.error(f"Fatal error: {e}")
            logger.error(traceback.format_exc())
        finally:
            await context.close()

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("FINAL SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Jobs found:     {stats['found']}")
    logger.info(f"Applied:        {stats['applied']}")
    logger.info(f"Skipped:        {stats['skipped']}")
    logger.info(f"Already applied:{stats['already']}")
    logger.info(f"Failed:         {stats['failed']}")
    logger.info("")

    # Detailed results
    logger.info("DETAILED RESULTS:")
    for r in results:
        status = r["result"]
        reason = r.get("reason", "")
        title = r.get("title", "?")[:60]
        company = r.get("company", "")
        extra = f" ({reason})" if reason else ""
        logger.info(f"  [{status.upper()}{extra}] {title} @ {company}")

    logger.info(f"\nLog saved to: {log_file}")
    conn.close()

    # Save results to JSON too
    results_file = LOG_DIR / f"dice_c2c_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, "w") as f:
        json.dump({"stats": stats, "results": results}, f, indent=2)
    logger.info(f"Results JSON: {results_file}")


if __name__ == "__main__":
    asyncio.run(main())
