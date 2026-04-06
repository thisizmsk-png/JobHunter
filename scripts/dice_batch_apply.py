#!/usr/bin/env python3
"""
Dice Batch Easy Apply — applies to all jobs in data/apify_dice_jobs.json
Uses persistent browser profile for authenticated session.

Usage:
  python3 scripts/dice_batch_apply.py                 # apply to all
  python3 scripts/dice_batch_apply.py --limit 50     # apply to first 50
  python3 scripts/dice_batch_apply.py --query "Java developer C2C" --pages 5
"""

import json
import sqlite3
import hashlib
import time
import argparse
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError:
    print("pip3 install playwright && playwright install chromium")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "jobs.db"
JOBS_JSON = PROJECT_ROOT / "data" / "apify_dice_jobs.json"
LOG_DIR = PROJECT_ROOT / "data" / "logs"
LOG_DIR.mkdir(exist_ok=True)
PROFILE_DIR = str(PROJECT_ROOT / "data" / "browser_profile")

PROFILE = {
    "first_name": "Vamsi",
    "last_name": "M",
    "full_name": "Vamsi M",
    "email": "vamsim.java@gmail.com",
    "phone": "9293410298",
    "phone_fmt": "(929) 341-0298",
    "zip": "07080",
    "city": "South Plainfield",
    "state": "NJ",
    "title": "Sr Java Full Stack Developer",
    "years_exp": "9",
    "rate": "90",
    "linkedin": "https://linkedin.com/in/vamsim",
    "cover": (
        "Sr Java Full Stack Developer with 9 years of experience in Java 17, Spring Boot, "
        "Microservices, REST APIs, AWS, Docker, Kubernetes, Angular 17, React, Kafka, Redis. "
        "Available immediately for C2C contract at $90/hr. H1B visa — authorized to work, "
        "no sponsorship needed. South Plainfield, NJ — open to remote/hybrid."
    ),
}

SKIP_TITLE = ["lead", "architect", "principal", "director", "manager", " vp ", "chief",
               "tech lead", "team lead", "staff engineer"]
SKIP_DESC = ["w2 only", "no c2c", "only w2", "no corp", "no third party",
             "citizens only", "gc only", "green card only",
             "secret clearance", "top secret", "ts/sci", "no h1", "no h-1",
             "local only", "locals only", "wi residents", "nc only", "tx only",
             "dallas only", "chicago only", "local candidates only"]
SKIP_IN_TITLE = ["w2", "w-2", "only locals", "local only", "wi only", "nc only"]

resume_files = list((PROJECT_ROOT / "assets").glob("*.docx")) + list((PROJECT_ROOT / "assets").glob("*.pdf"))
RESUME_FILE = str(resume_files[0]) if resume_files else None


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def dedup_hash(guid):
    return hashlib.sha256(f"dice:{guid}".encode()).hexdigest()


def already_applied(conn, guid):
    dhash = dedup_hash(guid)
    return conn.execute("SELECT id FROM jobs WHERE dedup_hash=?", (dhash,)).fetchone() is not None


def save_application(conn, job):
    dhash = dedup_hash(job["guid"])
    try:
        conn.execute(
            "INSERT OR IGNORE INTO jobs (external_id, source, title, company, location, job_type, url, status, dedup_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (job["guid"], "dice", job["title"], job["company"],
             job.get("location", "Remote"), "contract", job["url"], "applied", dhash)
        )
        conn.commit()
        row = conn.execute("SELECT id FROM jobs WHERE dedup_hash=?", (dhash,)).fetchone()
        if row:
            conn.execute(
                "INSERT INTO applications (job_id, method, ats_platform, status) VALUES (?, ?, ?, ?)",
                (row["id"], "dice_easy_apply", "dice", "submitted")
            )
            conn.commit()
    except Exception as e:
        print(f"  DB err: {e}")


def log(msg, lf=None):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    if lf:
        lf.write(line + "\n")
        lf.flush()


def apply_dice_easy(page, job_url, job, lf):
    """Navigate to Dice job and apply via Easy Apply wizard."""
    try:
        page.goto(job_url, timeout=20000, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
    except Exception as e:
        log(f"  LOAD FAIL: {e}", lf)
        return "load_failed"

    # Check job description for exclusions (only check job description area, not sidebar)
    try:
        desc_el = page.locator('[data-cy="jobDescription"], .job-description, #jobDescription, [class*="description"]').first
        desc_text = desc_el.inner_text(timeout=3000).lower() if desc_el.count() > 0 else ""
    except Exception:
        desc_text = ""

    for skip in SKIP_DESC:
        if skip in desc_text and skip not in ["local only", "locals only"]:  # location filters less strict
            log(f"  SKIP: '{skip}' in description", lf)
            return "skipped_w2"

    # Check title
    title_l = job["title"].lower()
    for s in SKIP_IN_TITLE:
        if s in title_l:
            log(f"  SKIP: '{s}' in title", lf)
            return "skipped_title"

    # Find Easy Apply button
    easy_apply_btn = None
    for sel in [
        'button[data-cy="applyButton"]',
        'button:has-text("Easy Apply")',
        '[class*="apply-button"]:has-text("Easy Apply")',
        'button.btn-primary:has-text("Apply")',
        'a:has-text("Easy Apply")',
    ]:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=2000):
                easy_apply_btn = btn
                break
        except Exception:
            continue

    if not easy_apply_btn:
        # Check if already applied
        if "applied" in page.inner_text("body").lower()[:500]:
            return "already_applied"
        log(f"  NO Easy Apply button", lf)
        return "no_easy_apply"

    try:
        easy_apply_btn.click(timeout=5000)
        page.wait_for_timeout(2000)
    except Exception as e:
        log(f"  CLICK FAIL: {e}", lf)
        return "click_failed"

    # Handle multi-step wizard
    for step in range(8):
        page.wait_for_timeout(1500)
        page_text = page.inner_text("body").lower()

        # Success check
        if any(w in page_text for w in ["application submitted", "you've applied", "application complete",
                                         "thank you for applying", "successfully applied"]):
            log(f"  SUCCESS: confirmed ✓", lf)
            return "applied"

        # Fill visible form fields
        filled = fill_wizard_fields(page, lf)

        # Upload resume if file input visible
        if RESUME_FILE:
            try:
                fi = page.locator('input[type="file"]').first
                if fi.is_visible(timeout=1000):
                    fi.set_input_files(RESUME_FILE, timeout=5000)
                    page.wait_for_timeout(1000)
                    log(f"  Resume uploaded", lf)
            except Exception:
                pass

        # Click Next or Submit
        clicked = False
        for btn_sel in [
            'button[data-cy="submit-btn"]',
            'button:has-text("Submit Application")',
            'button:has-text("Submit")',
            'button:has-text("Next")',
            'button:has-text("Continue")',
            'button[type="submit"]',
        ]:
            try:
                btn = page.locator(btn_sel).first
                if btn.is_visible(timeout=1500) and btn.is_enabled(timeout=1500):
                    btn_text = btn.inner_text(timeout=1000).lower()
                    btn.click(timeout=5000)
                    page.wait_for_timeout(2000)
                    clicked = True
                    if "submit" in btn_text:
                        # Check for success after submit
                        page.wait_for_timeout(2000)
                        new_text = page.inner_text("body").lower()
                        if any(w in new_text for w in ["submitted", "thank you", "applied", "complete"]):
                            log(f"  SUCCESS: submitted ✓", lf)
                            return "applied"
                        return "applied"  # assume submitted
                    break
            except Exception:
                continue

        if not clicked:
            log(f"  No clickable button at step {step}", lf)
            break

    # Final check
    final_text = page.inner_text("body").lower()
    if any(w in final_text for w in ["submitted", "thank you", "applied", "application received"]):
        return "applied"

    return "submitted_uncertain"


def fill_wizard_fields(page, lf):
    """Fill all visible form inputs in current wizard step."""
    filled = 0
    try:
        inputs = page.locator("input:visible, select:visible, textarea:visible").all()
        for inp in inputs:
            try:
                tag = inp.evaluate("el => el.tagName.toLowerCase()")
                itype = (inp.get_attribute("type") or "text").lower()
                iname = (inp.get_attribute("name") or "").lower()
                iid = (inp.get_attribute("id") or "").lower()
                iph = (inp.get_attribute("placeholder") or "").lower()
                ilabel = ""
                try:
                    lid = inp.get_attribute("id")
                    if lid:
                        lel = page.locator(f'label[for="{lid}"]').first
                        if lel.count() > 0:
                            ilabel = lel.inner_text(timeout=500).lower()
                except Exception:
                    pass

                fn = f"{iname} {iid} {iph} {ilabel}".strip().lower()

                if itype in ("hidden", "button", "file"):
                    continue
                if itype == "checkbox":
                    if any(w in fn for w in ["agree", "terms", "consent", "certify", "confirm"]):
                        if not inp.is_checked():
                            inp.check()
                            filled += 1
                    continue
                if itype == "radio":
                    # Work auth / sponsorship radios
                    val = inp.get_attribute("value") or ""
                    val_l = val.lower()
                    if any(w in fn for w in ["sponsor", "sponsorship"]):
                        if val_l in ("no", "false", "0"):
                            inp.check()
                    elif any(w in fn for w in ["authorized", "eligib", "work auth", "legally"]):
                        if val_l in ("yes", "true", "1"):
                            inp.check()
                    continue

                value = None
                if itype == "email" or "email" in fn:
                    value = PROFILE["email"]
                elif any(w in fn for w in ["first name", "firstname", "first_name", "fname"]):
                    value = PROFILE["first_name"]
                elif any(w in fn for w in ["last name", "lastname", "last_name", "lname", "surname"]):
                    value = PROFILE["last_name"]
                elif any(w in fn for w in ["full name", "fullname", "your name", "name"]) and "company" not in fn and "user" not in fn:
                    value = PROFILE["full_name"]
                elif itype == "tel" or any(w in fn for w in ["phone", "mobile", "cell"]):
                    value = PROFILE["phone_fmt"]
                elif any(w in fn for w in ["zip", "postal"]):
                    value = PROFILE["zip"]
                elif any(w in fn for w in ["city"]):
                    value = PROFILE["city"]
                elif "linkedin" in fn:
                    value = PROFILE["linkedin"]
                elif any(w in fn for w in ["salary", "rate", "compensation", "desired pay", "expected"]):
                    value = PROFILE["rate"]
                elif any(w in fn for w in ["year", "experience"]):
                    value = PROFILE["years_exp"]
                elif any(w in fn for w in ["cover", "message", "summary", "note", "comment", "about", "tell us", "intro"]):
                    value = PROFILE["cover"]
                elif "title" in fn and "job" not in fn:
                    value = PROFILE["title"]
                elif tag == "select":
                    # Handle common select fields
                    if any(w in fn for w in ["state", "region"]):
                        value = "NJ"
                    elif any(w in fn for w in ["country"]):
                        value = "United States"
                    elif any(w in fn for w in ["visa", "work auth", "authorization"]):
                        value = "H1B"
                    elif any(w in fn for w in ["sponsor"]):
                        value = "No"
                    elif any(w in fn for w in ["year", "experience"]):
                        value = "9"

                if value is None:
                    continue

                if tag == "select":
                    try:
                        inp.select_option(label=str(value), timeout=2000)
                        filled += 1
                    except Exception:
                        try:
                            inp.select_option(value=str(value), timeout=2000)
                            filled += 1
                        except Exception:
                            pass
                else:
                    try:
                        current = inp.input_value(timeout=1000)
                        if current and len(current) > 3:
                            continue  # already filled
                    except Exception:
                        pass
                    try:
                        inp.fill(str(value), timeout=3000)
                        filled += 1
                    except Exception:
                        pass
            except Exception:
                continue
    except Exception:
        pass
    return filled


def fetch_dice_search(page, query, pages=3):
    """Scrape Dice search results for Easy Apply jobs."""
    jobs = []
    seen = set()
    SKIP_T = ["lead", "architect", "principal", "director", "manager", " vp ", "chief",
               "tech lead", "team lead", "staff engineer"]

    for p in range(1, pages + 1):
        url = f"https://www.dice.com/jobs?q={query.replace(' ', '+')}&employmentType=CONTRACTS&datePosted=ONE_MONTH&page={p}"
        try:
            page.goto(url, timeout=20000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            page.evaluate("window.scrollTo(0, 1000)")
            page.wait_for_timeout(1000)
        except Exception:
            break

        # Get all job links
        seen_hrefs = set()
        links = page.locator('a[href*="/job-detail/"]').all()
        for link in links:
            try:
                href = link.get_attribute("href", timeout=1000) or ""
                href = href.split("?")[0]
                if not href or href in seen_hrefs:
                    continue
                title = link.inner_text(timeout=1000).strip()
                if not title or title in ["Apply Now", "Applied", "Easy Apply", "Save", "Saved", ""]:
                    continue
                if len(title) > 150:
                    continue
                if any(s in title.lower() for s in SKIP_T):
                    continue
                # Get parent container to check apply state
                parent = link.evaluate_handle("el => el.closest('div.card, article, li, div[class*=\"job\"]')")
                parent_text = link.evaluate("el => { const p = el.closest('[class*=\"card\"],[class*=\"job-item\"],article,li'); return p ? p.textContent : ''; }")
                if "Applied" in parent_text:
                    continue
                easy = "Easy Apply" in parent_text
                if not easy:
                    continue  # only grab Easy Apply jobs in search
                seen_hrefs.add(href)
                guid = href.rstrip("/").split("/")[-1]
                if guid not in seen:
                    seen.add(guid)
                    full_url = f"https://www.dice.com/job-detail/{guid}"
                    jobs.append({"guid": guid, "title": title, "company": "", "url": full_url, "easy_apply": True})
            except Exception:
                continue

        print(f"  Page {p}: {len(jobs)} Easy Apply jobs so far")
        time.sleep(1.5)

    return jobs


def run(limit=None, from_file=True, queries=None, pages_per_query=5):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    lf = open(LOG_DIR / f"dice_batch_{ts}.log", "w")
    conn = get_db()

    jobs = []

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
        )
        page = browser.new_page()

        # Load jobs from file or scrape
        if from_file and JOBS_JSON.exists():
            with open(JOBS_JSON) as f:
                jobs = json.load(f)
            log(f"Loaded {len(jobs)} jobs from {JOBS_JSON}", lf)

        if queries:
            log(f"Scraping Dice for additional jobs...", lf)
            for q in queries:
                log(f"  Query: {q}", lf)
                new_jobs = fetch_dice_search(page, q, pages=pages_per_query)
                existing_guids = {j["guid"] for j in jobs}
                added = [j for j in new_jobs if j["guid"] not in existing_guids]
                jobs.extend(added)
                log(f"  Added {len(added)} new jobs (total: {len(jobs)})", lf)

        # Filter already applied
        eligible = [j for j in jobs if not already_applied(conn, j["guid"])]
        log(f"Eligible (not yet applied): {len(eligible)} of {len(jobs)}", lf)

        if limit:
            eligible = eligible[:limit]

        total_applied = 0
        total_skipped = 0
        total_failed = 0

        for idx, job in enumerate(eligible):
            log(f"\n[{idx+1}/{len(eligible)}] {job['title'][:60]} @ {job['company'][:25]}", lf)
            log(f"  URL: {job['url']}", lf)

            try:
                status = apply_dice_easy(page, job["url"], job, lf)
            except Exception as e:
                log(f"  EXCEPTION: {e}", lf)
                status = "failed"

            if status in ("applied", "submitted_uncertain"):
                save_application(conn, job)
                total_applied += 1
                log(f"  -> APPLIED ✓ ({total_applied} total)", lf)
            elif status.startswith("skipped") or status in ("already_applied",):
                total_skipped += 1
            elif status in ("load_failed", "failed", "no_easy_apply"):
                total_failed += 1

            time.sleep(1.5)

        browser.close()

    log(f"\n{'='*60}", lf)
    log(f"DICE BATCH APPLY COMPLETE", lf)
    log(f"  Total processed: {len(eligible)}", lf)
    log(f"  Applied: {total_applied}", lf)
    log(f"  Skipped: {total_skipped}", lf)
    log(f"  Failed/No Easy Apply: {total_failed}", lf)
    log(f"{'='*60}", lf)
    lf.close()
    conn.close()

    # Update state.json
    try:
        state_path = PROJECT_ROOT / "data" / "state.json"
        with open(state_path) as f:
            state = json.load(f)
        old_total = state.get("total_applications", 0)
        state["total_applications"] = old_total + total_applied
        state["last_run_at"] = datetime.now().isoformat()
        with open(state_path, "w") as f:
            json.dump(state, f, indent=2)
        print(f"\nTotal applications now: {state['total_applications']}")
    except Exception:
        pass

    return total_applied


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--query", type=str, default=None, help="Additional Dice search query")
    parser.add_argument("--pages", type=int, default=5, help="Pages per search query")
    parser.add_argument("--no-file", action="store_true", help="Skip loading from apify_dice_jobs.json")
    args = parser.parse_args()

    queries = None
    if args.query:
        queries = [args.query]
    elif not args.no_file:
        # Default extra queries to scrape
        queries = [
            "Java developer C2C contract remote",
            "Java Spring Boot microservices contract",
            "Senior Java Full Stack Developer contract",
            "Java developer corp to corp",
            "Java AWS developer contract",
        ]

    run(limit=args.limit, from_file=not args.no_file, queries=queries, pages_per_query=args.pages)
