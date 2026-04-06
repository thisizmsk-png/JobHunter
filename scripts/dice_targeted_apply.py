#!/usr/bin/env python3
"""
Dice Targeted Apply — Applies to a specific list of Dice job URLs via CDP.
Connects to existing Chrome instance with remote debugging on port 9333.

Usage:
    python3 scripts/dice_targeted_apply.py
"""
import asyncio
import hashlib
import json
import logging
import random
import sqlite3
import sys
import traceback
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "jobs.db"
LOG_DIR = PROJECT_ROOT / "data" / "logs"

sys.path.insert(0, str(PROJECT_ROOT))

from playwright.async_api import async_playwright, TimeoutError as PwTimeout

LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"dice_targeted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file),
    ],
)
logger = logging.getLogger("dice_targeted")

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
    "rate": "90",
    "pitch": "Sr Java Full Stack Developer with 9 years experience. Available immediately for C2C contract at $90/hr.",
}

# ---------------------------------------------------------------------------
# Target jobs
# ---------------------------------------------------------------------------
TARGET_JOBS = [
    {
        "url": "https://www.dice.com/job-detail/6dc37f6b-a34b-42d5-b397-b8dd2106534a",
        "title": "Java Full Stack Developer",
        "company": "4 Consulting Inc",
    },
    {
        "url": "https://www.dice.com/job-detail/94f1c5c8-32c5-4340-ac16-0381ab2b6fca",
        "title": "Sr Java Developer (Trading)",
        "company": "PamTen Inc",
    },
    {
        "url": "https://www.dice.com/job-detail/03814ca1-7675-4ec6-b97e-2d4887430a4d",
        "title": "Java Developer IV",
        "company": "V-Soft Consulting",
    },
    {
        "url": "https://www.dice.com/job-detail/6abcd4ec-094a-4d32-b2cd-a6064f391f5f",
        "title": "Java Mulesoft Developer",
        "company": "Hexacorp",
    },
    {
        "url": "https://www.dice.com/job-detail/fe963adb-dd2c-45c4-ba86-12ef78d83566",
        "title": "Java/API Developer",
        "company": "Lares IT Solutions",
    },
    {
        "url": "https://www.dice.com/job-detail/6d059d23-6b80-427d-8e0f-00e7b0cd7e76",
        "title": "Need Java Developer - Visa Independent",
        "company": "Radiantze",
    },
    {
        "url": "https://www.dice.com/job-detail/b369074c-bd65-44f2-b2d6-68e379d64860",
        "title": "Amazon Connect Voice Engineer (Java)",
        "company": "Accion Labs",
    },
]

C2C_EXCLUSION_PHRASES = [
    "w2 only", "no c2c", "citizens only", "gc only", "no third party",
    "us citizens only", "green card only", "no corp to corp",
    "w-2 only", "no corp-to-corp", "citizen only", "only w2",
]

CDP_PORT = 9333

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

def has_c2c_exclusion(text):
    t = text.lower()
    return any(phrase in t for phrase in C2C_EXCLUSION_PHRASES)

def uuid_from_url(url):
    if "/job-detail/" in url:
        return url.split("/job-detail/")[-1].split("?")[0]
    return ""

# ---------------------------------------------------------------------------
# Form filling
# ---------------------------------------------------------------------------

async def _fill_form_fields(page):
    """Fill form fields on wizard pages with profile data."""
    inputs = await page.query_selector_all(
        'input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"]):not([type="file"])'
    )
    for inp in inputs:
        try:
            if not await inp.is_visible():
                continue
            val = (await inp.get_attribute("value") or "").strip()
            if val:
                continue

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
            elif any(k in field_id for k in ["rate", "salary", "compensation", "pay"]):
                await inp.fill(PROFILE["rate"])
        except Exception:
            continue

    # Fill textareas
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

    # Handle select dropdowns
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
                for opt_text in ["yes", "authorized", "h1b"]:
                    if any(opt_text in ot for ot in option_texts):
                        await sel.select_option(label=next(ot for ot in option_texts if opt_text in ot))
                        break
            elif any(k in field_id for k in ["sponsor"]):
                for opt_text in ["no"]:
                    if any(opt_text in ot for ot in option_texts):
                        await sel.select_option(label=next(ot for ot in option_texts if opt_text in ot))
                        break
        except Exception:
            continue

# ---------------------------------------------------------------------------
# Apply logic
# ---------------------------------------------------------------------------

async def check_job_detail(page, job):
    """Navigate to job detail, check for C2C exclusions."""
    url = job["url"]
    logger.info(f"  Loading job page: {url}")
    await page.goto(url, wait_until="domcontentloaded")
    await human_delay(2, 4)

    body = await page_text(page)

    # Check C2C exclusions
    if has_c2c_exclusion(body):
        return {"eligible": False, "reason": "C2C exclusion in description (W2 only / no C2C)"}

    # Check if already applied
    applied_el = await page.query_selector(
        '[data-testid="applied-badge"], .applied-badge, button:has-text("Applied")'
    )
    if applied_el:
        return {"eligible": False, "reason": "Already applied (badge visible)"}

    if "applied" in body[:800].lower():
        badge = await page.query_selector('text="Applied"')
        if badge:
            return {"eligible": False, "reason": "Already applied (text badge)"}

    # Check for Easy Apply button
    easy_apply = await page.query_selector(
        'button:has-text("Easy Apply"), apply-button-wc, a:has-text("Easy Apply")'
    )
    if not easy_apply:
        company_apply = await page.query_selector('text="Apply on company site"')
        if company_apply:
            return {"eligible": False, "reason": "External apply (company site)"}
        apply_btn = await page.query_selector('button:has-text("Apply")')
        if not apply_btn:
            return {"eligible": False, "reason": "No apply button found"}

    return {"eligible": True}


async def apply_via_wizard(page, job):
    """Apply using Dice Easy Apply wizard."""
    uuid = uuid_from_url(job["url"])

    try:
        # First try clicking Easy Apply on the detail page
        easy_apply = await page.query_selector(
            'button:has-text("Easy Apply"), apply-button-wc'
        )
        if easy_apply:
            logger.info("  Clicking Easy Apply button...")
            await easy_apply.click()
            await human_delay(2, 4)
        else:
            wizard_url = f"https://www.dice.com/job-applications/{uuid}/wizard"
            logger.info(f"  Navigating to wizard: {wizard_url}")
            await page.goto(wizard_url, wait_until="domcontentloaded")
            await human_delay(2, 3)

        current_url = page.url
        if "/dashboard/login" in current_url or "/login" in current_url:
            logger.error("  Redirected to login -- session expired")
            return False, "login_required"

        body = await page_text(page)
        if "already applied" in body.lower() or "previously applied" in body.lower():
            logger.info("  Already applied (wizard confirmation)")
            return False, "already_applied"

        # Step through wizard (up to 6 steps)
        for step in range(6):
            await human_delay(1, 2)
            await _fill_form_fields(page)

            # Check for submit button (final step)
            submit_btn = await page.query_selector(
                'button[type="submit"]:has-text("Submit"), '
                'button:has-text("Submit Application"), '
                'button:has-text("Submit")'
            )
            if submit_btn and await submit_btn.is_visible():
                btn_text = (await submit_btn.inner_text()).strip()
                if "submit" in btn_text.lower():
                    logger.info(f"  Step {step+1}: Clicking Submit")
                    await submit_btn.scroll_into_view_if_needed()
                    await human_delay(0.5, 1)
                    await submit_btn.click()
                    await human_delay(3, 5)

                    body = await page_text(page)
                    success_words = ["success", "submitted", "thank you", "application received", "application sent"]
                    if any(w in body.lower() for w in success_words):
                        return True, "submitted"
                    if "job-applications" not in page.url:
                        return True, "submitted"
                    return True, "submitted"

            # Check for Next/Continue button
            next_btn = await page.query_selector(
                'button:has-text("Next"), button:has-text("Continue"), button[data-testid="next-button"]'
            )
            if next_btn and await next_btn.is_visible():
                logger.info(f"  Step {step+1}: Clicking Next")
                await next_btn.scroll_into_view_if_needed()
                await human_delay(0.5, 1)
                await next_btn.click()
                await human_delay(2, 3)
                continue

            # Check for Easy Apply button within wizard
            apply_btn = await page.query_selector(
                'button:has-text("Easy Apply"), button:has-text("Apply")'
            )
            if apply_btn and await apply_btn.is_visible():
                logger.info(f"  Step {step+1}: Clicking Apply")
                await apply_btn.scroll_into_view_if_needed()
                await human_delay(0.5, 1)
                await apply_btn.click()
                await human_delay(2, 3)
                continue

            logger.warning(f"  No actionable button at step {step+1}")
            try:
                ss_path = LOG_DIR / f"wizard_stuck_{uuid[:8]}_{step}.png"
                await page.screenshot(path=str(ss_path))
                logger.info(f"  Screenshot: {ss_path}")
            except Exception:
                pass
            break

        return False, "wizard_incomplete"

    except PwTimeout:
        return False, "timeout"
    except Exception as e:
        logger.error(f"  Wizard error: {e}")
        return False, str(e)[:100]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    conn = get_db()
    results = []
    stats = {"total": len(TARGET_JOBS), "applied": 0, "skipped": 0, "failed": 0}

    logger.info("=" * 60)
    logger.info("Dice Targeted Apply for Vamsi M")
    logger.info(f"Target jobs: {len(TARGET_JOBS)}")
    logger.info(f"Log: {log_file}")
    logger.info("=" * 60)

    # Connect to already-running Chrome with CDP on port 9333
    async with async_playwright() as p:
        try:
            logger.info(f"Connecting to Chrome via CDP on port {CDP_PORT}...")
            browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP_PORT}")
            logger.info("Connected to Chrome!")

            contexts = browser.contexts
            if contexts:
                context = contexts[0]
                page = context.pages[0] if context.pages else await context.new_page()
            else:
                context = await browser.new_context()
                page = await context.new_page()

            # Verify login
            logger.info("Verifying Dice login...")
            await page.goto("https://www.dice.com/dashboard", wait_until="domcontentloaded")
            await human_delay(3, 5)

            if "/login" in page.url:
                logger.error("NOT logged into Dice! Please log in manually in the browser.")
                logger.info("Waiting 120 seconds for manual login...")
                for i in range(60):
                    await asyncio.sleep(2)
                    if "/login" not in page.url:
                        logger.info("Login detected!")
                        break
                    if i % 10 == 0 and i > 0:
                        logger.info(f"  Waiting... ({i*2}s)")
                else:
                    logger.error("Login timeout. Exiting.")
                    return
            else:
                logger.info("Logged into Dice!")

            # Process each target job
            for i, job in enumerate(TARGET_JOBS):
                title = job["title"]
                company = job["company"]
                url = job["url"]
                uuid = uuid_from_url(url)

                logger.info(f"\n{'='*50}")
                logger.info(f"[{i+1}/{len(TARGET_JOBS)}] {title} @ {company}")
                logger.info(f"  URL: {url}")

                # Check job detail page
                detail = await check_job_detail(page, job)
                if not detail["eligible"]:
                    reason = detail["reason"]
                    logger.info(f"  SKIP: {reason}")
                    stats["skipped"] += 1
                    results.append({
                        "url": url, "title": title, "company": company,
                        "result": "skipped", "reason": reason
                    })
                    continue

                # Insert into DB
                dhash = dedup_hash("dice", uuid)
                job_id = insert_job(
                    conn, external_id=uuid, source="dice", title=title,
                    company=company, location="Remote",
                    job_type="contract", url=url, status="matched",
                    dedup_hash=dhash,
                )

                # Apply
                success, status_msg = await apply_via_wizard(page, job)

                if success:
                    record_application(conn, job_id, "dice_wizard", "submitted")
                    stats["applied"] += 1
                    logger.info(f"  >>> APPLIED: {title} @ {company}")
                    results.append({
                        "url": url, "title": title, "company": company,
                        "result": "applied"
                    })
                    try:
                        ss_path = LOG_DIR / f"applied_{uuid[:8]}.png"
                        await page.screenshot(path=str(ss_path))
                        logger.info(f"  Screenshot: {ss_path}")
                    except Exception:
                        pass
                else:
                    if status_msg == "already_applied":
                        stats["skipped"] += 1
                        results.append({
                            "url": url, "title": title, "company": company,
                            "result": "skipped", "reason": "already applied"
                        })
                    elif status_msg == "login_required":
                        stats["failed"] += 1
                        results.append({
                            "url": url, "title": title, "company": company,
                            "result": "failed", "reason": "login required - session expired"
                        })
                        logger.error("Session expired. Stopping.")
                        break
                    else:
                        record_application(conn, job_id, "dice_wizard", "failed", status_msg)
                        stats["failed"] += 1
                        results.append({
                            "url": url, "title": title, "company": company,
                            "result": "failed", "reason": status_msg
                        })

                await human_delay(2, 4)

        except Exception as e:
            logger.error(f"Fatal error: {e}")
            logger.error(traceback.format_exc())
        finally:
            try:
                await browser.close()
            except Exception:
                pass

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("FINAL REPORT")
    logger.info("=" * 60)
    logger.info(f"Total jobs:  {stats['total']}")
    logger.info(f"Applied:     {stats['applied']}")
    logger.info(f"Skipped:     {stats['skipped']}")
    logger.info(f"Failed:      {stats['failed']}")
    logger.info("")

    logger.info("DETAILED RESULTS:")
    logger.info("-" * 60)
    for r in results:
        status = r["result"].upper()
        reason = r.get("reason", "")
        extra = f" -- {reason}" if reason else ""
        logger.info(f"  [{status}{extra}]")
        logger.info(f"    {r['title']} @ {r['company']}")
        logger.info(f"    {r['url']}")
    logger.info("")

    logger.info(f"Log: {log_file}")
    conn.close()

    # Save results JSON
    results_file = LOG_DIR / f"dice_targeted_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, "w") as f:
        json.dump({"stats": stats, "results": results}, f, indent=2)
    logger.info(f"Results JSON: {results_file}")


if __name__ == "__main__":
    asyncio.run(main())
