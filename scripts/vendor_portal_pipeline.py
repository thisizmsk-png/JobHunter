#!/usr/bin/env python3
"""
Vendor Portal Job Scraper + Applier
Visits 444 public vendor job portals, finds Java contract listings, applies.

Usage:
  python3 scripts/vendor_portal_pipeline.py           # run all vendors
  python3 scripts/vendor_portal_pipeline.py --batch 0 # run batch 0 (first 50)
  python3 scripts/vendor_portal_pipeline.py --limit 20 # stop after 20 applications
"""

import json
import sqlite3
import hashlib
import time
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError:
    print("ERROR: playwright not installed. Run: pip3 install playwright && playwright install chromium")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "jobs.db"
VENDOR_JSON = PROJECT_ROOT / "data" / "vendor_urls.json"
LOG_DIR = PROJECT_ROOT / "data" / "logs"
LOG_DIR.mkdir(exist_ok=True)

PROFILE = {
    "first_name": "Vamsi",
    "last_name": "M",
    "full_name": "Vamsi M",
    "email": "vamsim.java@gmail.com",
    "phone": "(929) 341-0298",
    "phone_raw": "9293410298",
    "location": "South Plainfield, NJ 07080",
    "city": "South Plainfield",
    "state": "NJ",
    "zip": "07080",
    "title": "Sr Java Full Stack Developer",
    "experience": "9",
    "linkedin": "https://linkedin.com/in/vamsim",
    "visa": "H1B",
    "rate": "90",
}

RESUME_PATH = PROJECT_ROOT / "assets"
# Find resume file
resume_files = list(RESUME_PATH.glob("*.docx")) + list(RESUME_PATH.glob("*.pdf"))
RESUME_FILE = str(resume_files[0]) if resume_files else None

COVER_MSG = (
    "I am a Sr Java Full Stack Developer with 9 years of experience in Java, Spring Boot, "
    "Microservices, REST APIs, AWS, Docker, Kubernetes, Angular, and React. "
    "I am available for C2C contract at $90/hr. H1B visa, no sponsorship needed. "
    "South Plainfield, NJ - open to remote and hybrid roles."
)

JAVA_KEYWORDS = ["java", "spring", "j2ee", "microservices", "full stack java", "fullstack java",
                  "spring boot", "jvm", "hibernate", "kafka", "aws java"]
SKIP_TITLE = ["lead", "architect", "principal", "director", "manager", "vp ", "vice president",
               "chief", " sr. lead", "staff engineer", ".net developer", "python developer",
               "data engineer", "devops", "security engineer", "okta", "salesforce"]
SKIP_DESC = ["w2 only", "no c2c", "no corp", "only w2", "citizens only", "gc only",
             "green card only", "us citizens", "secret clearance", "ts/sci", "no third party"]

LOGIN_SKIP = ["jobdiva.com", "portal", "career-portal", "login", "register",
              "signin", "sign-in", "aviontego", "topechelon", "procomservices.com/jobs",
              "reactionsearch.com/candidate"]

BATCH_SIZE = 50
MAX_JOBS_PER_VENDOR = 5
REQUEST_DELAY = 1.5  # seconds between vendors


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def dedup_hash(title, company, url):
    key = f"{title.lower().strip()}:{company.lower().strip()}:{urlparse(url).netloc}"
    return hashlib.sha256(key.encode()).hexdigest()


def is_java_job(title, desc=""):
    text = (title + " " + desc[:300]).lower()
    return any(kw in text for kw in JAVA_KEYWORDS)


def should_skip_title(title):
    t = title.lower()
    return any(ex in t for ex in SKIP_TITLE)


def should_skip_desc(desc):
    d = desc.lower()
    return any(ex in d for ex in SKIP_DESC)


def load_vendors():
    with open(VENDOR_JSON) as f:
        vendors = json.load(f)
    # Filter out login-required
    public = []
    for v in vendors:
        url = v.get("url", "").lower()
        if any(skip in url for skip in LOGIN_SKIP):
            continue
        public.append(v)
    return public


def log(msg, logfile=None):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    if logfile:
        logfile.write(line + "\n")
        logfile.flush()


def smart_search_jobs(page, vendor_url, timeout=8000):
    """Try to find Java jobs on vendor page via search or listing scan."""
    jobs_found = []

    # Strategy 1: Look for a search input and search "Java"
    search_sels = [
        'input[name*="search" i]', 'input[placeholder*="search" i]',
        'input[placeholder*="keyword" i]', 'input[id*="keyword" i]',
        'input[name*="keyword" i]', 'input[type="search"]',
        'input[placeholder*="job title" i]', 'input[id*="search" i]',
        '#keywords', '#search-keyword', '.search-input',
    ]
    searched = False
    for sel in search_sels:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                el.fill("Java")
                page.keyboard.press("Enter")
                page.wait_for_timeout(2500)
                searched = True
                break
        except Exception:
            continue

    # Strategy 2: Parse job listings from current page
    page.wait_for_timeout(1500)

    # Common job title selectors
    title_sels = [
        "h2 a", "h3 a", "h4 a",
        ".job-title a", ".jobtitle a", ".position-title a",
        '[class*="job-title"]', '[class*="jobtitle"]', '[class*="position-title"]',
        '[class*="job-name"]', '[class*="job_title"]',
        'a[href*="job"]', 'a[href*="career"]', 'a[href*="position"]',
        'td a', 'li a[href*="job"]',
        '.card-title a', '.listing-title a',
    ]

    seen_urls = set()
    for sel in title_sels:
        try:
            links = page.locator(sel).all()
            for link in links[:30]:
                try:
                    title = link.inner_text(timeout=2000).strip()
                    href = link.get_attribute("href") or ""
                    if not title or len(title) < 5 or len(title) > 200:
                        continue
                    if not is_java_job(title):
                        continue
                    if should_skip_title(title):
                        continue
                    if href in seen_urls:
                        continue
                    seen_urls.add(href)
                    # Make absolute URL
                    if href.startswith("/"):
                        parsed = urlparse(vendor_url)
                        href = f"{parsed.scheme}://{parsed.netloc}{href}"
                    elif not href.startswith("http"):
                        href = vendor_url.rstrip("/") + "/" + href.lstrip("/")
                    jobs_found.append({"title": title, "url": href})
                    if len(jobs_found) >= MAX_JOBS_PER_VENDOR:
                        break
                except Exception:
                    continue
            if jobs_found:
                break
        except Exception:
            continue

    return jobs_found


def try_apply(page, job_url, job_title, company, logfile):
    """Navigate to job page and attempt to fill + submit application form."""
    try:
        page.goto(job_url, timeout=15000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
    except Exception as e:
        log(f"    LOAD ERR: {e}", logfile)
        return "failed"

    page_text = page.inner_text("body")
    page_lower = page_text.lower()

    # Check for C2C exclusions in job description
    if should_skip_desc(page_lower):
        log(f"    SKIP: W2/no-C2C in description", logfile)
        return "skipped_w2"

    # Look for Apply button
    apply_sels = [
        'a:has-text("Apply Now")', 'a:has-text("Apply")',
        'button:has-text("Apply Now")', 'button:has-text("Apply")',
        'input[value*="Apply" i]',
        '[class*="apply-btn"]', '[id*="apply-btn"]',
        'a[href*="apply"]',
    ]
    clicked_apply = False
    for sel in apply_sels:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=2000):
                btn.click(timeout=5000)
                page.wait_for_timeout(2000)
                clicked_apply = True
                break
        except Exception:
            continue

    # Now try to fill the form (on current page, or after clicking apply)
    result = fill_and_submit_form(page, job_title, company, logfile)
    return result


def fill_and_submit_form(page, job_title, company, logfile):
    """Smart form filler for vendor apply forms."""
    page.wait_for_timeout(1500)

    # Detect if there's actually a form
    forms = page.locator("form").all()
    inputs = page.locator("input:visible, textarea:visible, select:visible").all()
    if not inputs and not forms:
        log(f"    NO FORM found", logfile)
        return "no_form"

    filled = 0
    field_map = []

    # Gather all visible inputs
    for inp in inputs:
        try:
            tag = inp.evaluate("el => el.tagName.toLowerCase()")
            inp_type = inp.get_attribute("type") or "text"
            inp_name = (inp.get_attribute("name") or "").lower()
            inp_id = (inp.get_attribute("id") or "").lower()
            inp_ph = (inp.get_attribute("placeholder") or "").lower()
            inp_label = ""
            # Try to get associated label
            try:
                label_id = inp.get_attribute("id")
                if label_id:
                    label_el = page.locator(f'label[for="{label_id}"]').first
                    inp_label = label_el.inner_text(timeout=1000).lower()
            except Exception:
                pass

            fn = f"{inp_name} {inp_id} {inp_ph} {inp_label}".strip()

            if inp_type in ("hidden", "submit", "button", "checkbox", "radio", "file"):
                # Handle checkboxes for consent
                if inp_type == "checkbox":
                    try:
                        if any(w in fn for w in ["agree", "consent", "terms", "accept"]):
                            inp.check()
                    except Exception:
                        pass
                continue

            if tag == "select":
                field_map.append((inp, fn, "select"))
            else:
                field_map.append((inp, fn, inp_type))
        except Exception:
            continue

    for inp, fn, ftype in field_map:
        value = None

        # Determine value based on field name/placeholder
        if ftype == "email" or "email" in fn:
            value = PROFILE["email"]
        elif any(w in fn for w in ["first", "fname", "first_name"]) and "last" not in fn:
            value = PROFILE["first_name"]
        elif any(w in fn for w in ["last", "lname", "last_name", "surname"]):
            value = PROFILE["last_name"]
        elif any(w in fn for w in ["full name", "your name", "fullname", "candidate name"]):
            value = PROFILE["full_name"]
        elif "name" in fn and not any(w in fn for w in ["company", "employer", "user", "last", "first"]):
            value = PROFILE["full_name"]
        elif any(w in fn for w in ["phone", "mobile", "tel", "cell"]):
            value = PROFILE["phone"]
        elif any(w in fn for w in ["zip", "postal"]):
            value = PROFILE["zip"]
        elif any(w in fn for w in ["city"]):
            value = PROFILE["city"]
        elif any(w in fn for w in ["state"]):
            if ftype == "select":
                value = "NJ"
            else:
                value = PROFILE["state"]
        elif any(w in fn for w in ["linkedin"]):
            value = PROFILE["linkedin"]
        elif any(w in fn for w in ["title", "position", "job title", "desired"]):
            value = PROFILE["title"]
        elif any(w in fn for w in ["experience", "years"]):
            value = PROFILE["experience"]
        elif any(w in fn for w in ["rate", "salary", "compensation", "pay"]):
            value = PROFILE["rate"]
        elif any(w in fn for w in ["message", "comment", "cover", "letter", "note", "summary",
                                    "body", "inquiry", "about", "introduction", "tell us"]):
            value = COVER_MSG
        elif any(w in fn for w in ["location", "address"]):
            value = PROFILE["location"]
        elif any(w in fn for w in ["company", "employer", "current employer"]):
            value = "Independent Contractor"
        elif any(w in fn for w in ["visa", "work auth", "authorization"]):
            if ftype == "select":
                value = "H1B"
            else:
                value = "H1B - Authorized to Work"

        if value is None:
            continue

        try:
            if ftype == "select":
                # Try select by value or label
                try:
                    inp.select_option(label=value, timeout=2000)
                except Exception:
                    try:
                        inp.select_option(value=value, timeout=2000)
                    except Exception:
                        pass
            else:
                inp.fill(str(value), timeout=3000)
            filled += 1
        except Exception:
            continue

    if filled == 0:
        log(f"    NO FIELDS filled", logfile)
        return "no_fields"

    log(f"    Filled {filled} fields", logfile)

    # Handle file upload if resume is available
    if RESUME_FILE:
        try:
            file_inputs = page.locator('input[type="file"]:visible').all()
            if not file_inputs:
                # Try hidden file input with JS
                file_inputs = page.locator('input[type="file"]').all()
            for fi in file_inputs[:1]:
                try:
                    fi.set_input_files(RESUME_FILE, timeout=5000)
                    log(f"    Resume uploaded", logfile)
                    page.wait_for_timeout(1000)
                    break
                except Exception:
                    pass
        except Exception:
            pass

    # Find and click submit button
    submit_sels = [
        'button[type="submit"]', 'input[type="submit"]',
        'button:has-text("Submit")', 'button:has-text("Apply")',
        'button:has-text("Send")', 'button:has-text("Apply Now")',
        '[class*="submit"]', '[id*="submit"]',
    ]
    for sel in submit_sels:
        try:
            btns = page.locator(sel).all()
            for btn in btns:
                try:
                    if not btn.is_visible(timeout=1000):
                        continue
                    btn_text = btn.inner_text(timeout=1000).lower()
                    if any(w in btn_text for w in ["search", "subscribe", "newsletter", "reset"]):
                        continue
                    btn.click(timeout=8000)
                    page.wait_for_timeout(2500)
                    # Check for success
                    new_text = page.inner_text("body").lower()
                    if any(w in new_text for w in ["thank you", "thank-you", "success",
                                                    "received", "submitted", "application sent",
                                                    "we'll be in touch"]):
                        log(f"    SUCCESS: submission confirmed", logfile)
                        return "applied"
                    log(f"    SUBMITTED (no explicit confirm)", logfile)
                    return "applied"
                except Exception:
                    continue
        except Exception:
            continue

    # JS fallback
    try:
        page.evaluate("""() => {
            const btns = [...document.querySelectorAll('button[type=submit],input[type=submit]')];
            const valid = btns.filter(b => {
                const t = (b.value||b.textContent||'').toLowerCase();
                return !['search','subscribe','newsletter'].some(w => t.includes(w));
            });
            if (valid.length) valid[0].click();
        }""")
        page.wait_for_timeout(2500)
        new_text = page.inner_text("body").lower()
        if any(w in new_text for w in ["thank you", "success", "received", "submitted"]):
            return "applied"
    except Exception:
        pass

    return "submitted_uncertain"


def save_application(conn, vendor_name, job_title, job_url, status, method="vendor_portal"):
    dhash = dedup_hash(job_title, vendor_name, job_url)
    # Insert job
    try:
        conn.execute(
            "INSERT OR IGNORE INTO jobs (external_id, source, title, company, location, job_type, url, status, dedup_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (dhash[:20], "vendor_portal", job_title, vendor_name, "Remote/Hybrid", "contract",
             job_url, "applied", dhash)
        )
        conn.commit()
        job_row = conn.execute("SELECT id FROM jobs WHERE dedup_hash=?", (dhash,)).fetchone()
        if job_row:
            conn.execute(
                "INSERT INTO applications (job_id, method, ats_platform, status) VALUES (?, ?, ?, ?)",
                (job_row["id"], method, "vendor_custom", status)
            )
            conn.commit()
            return True
    except Exception as e:
        pass
    return False


def already_applied(conn, job_title, vendor_name, job_url):
    dhash = dedup_hash(job_title, vendor_name, job_url)
    row = conn.execute("SELECT id FROM jobs WHERE dedup_hash=?", (dhash,)).fetchone()
    return row is not None


def run_pipeline(batch_num=None, limit=None):
    vendors = load_vendors()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logfile_path = LOG_DIR / f"vendor_portal_{timestamp}.log"
    logfile = open(logfile_path, "w")

    if batch_num is not None:
        start = batch_num * BATCH_SIZE
        vendors = vendors[start:start + BATCH_SIZE]
        log(f"Running batch {batch_num}: vendors {start}-{start+len(vendors)}", logfile)
    else:
        log(f"Running ALL {len(vendors)} public vendors", logfile)

    conn = get_db()
    total_applied = 0
    total_skipped = 0
    total_failed = 0
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = ctx.new_page()
        page.set_default_timeout(12000)

        for idx, vendor in enumerate(vendors):
            if limit and total_applied >= limit:
                log(f"\nReached limit of {limit} applications. Stopping.", logfile)
                break

            vendor_name = vendor.get("name", "Unknown")
            vendor_url = vendor.get("url", "")
            if not vendor_url:
                continue

            log(f"\n[{idx+1}/{len(vendors)}] {vendor_name} — {vendor_url}", logfile)

            # Navigate to vendor job page
            try:
                page.goto(vendor_url, timeout=15000, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
            except Exception as e:
                log(f"  LOAD FAILED: {e}", logfile)
                total_failed += 1
                results.append({"vendor": vendor_name, "url": vendor_url, "status": "load_failed", "jobs": []})
                time.sleep(REQUEST_DELAY)
                continue

            # Search for Java jobs
            jobs = smart_search_jobs(page, vendor_url)

            if not jobs:
                log(f"  No Java jobs found", logfile)
                total_skipped += 1
                results.append({"vendor": vendor_name, "url": vendor_url, "status": "no_jobs", "jobs": []})
                time.sleep(REQUEST_DELAY)
                continue

            log(f"  Found {len(jobs)} Java jobs", logfile)
            vendor_results = []

            for job in jobs[:MAX_JOBS_PER_VENDOR]:
                if limit and total_applied >= limit:
                    break

                job_title = job["title"]
                job_url_full = job["url"]

                if already_applied(conn, job_title, vendor_name, job_url_full):
                    log(f"  [SKIP-DUP] {job_title}", logfile)
                    continue

                log(f"  [APPLY] {job_title[:60]}", logfile)

                try:
                    status = try_apply(page, job_url_full, job_title, vendor_name, logfile)
                except Exception as e:
                    log(f"    EXCEPTION: {e}", logfile)
                    status = "failed"

                if status in ("applied", "submitted_uncertain"):
                    save_application(conn, vendor_name, job_title, job_url_full, "submitted")
                    total_applied += 1
                    log(f"    -> APPLIED ({total_applied} total)", logfile)
                elif status.startswith("skipped"):
                    total_skipped += 1

                vendor_results.append({"title": job_title, "url": job_url_full, "status": status})
                time.sleep(REQUEST_DELAY)

            results.append({"vendor": vendor_name, "url": vendor_url, "status": "processed", "jobs": vendor_results})
            time.sleep(REQUEST_DELAY)

        browser.close()

    # Final summary
    log(f"\n{'='*60}", logfile)
    log(f"VENDOR PORTAL PIPELINE COMPLETE", logfile)
    log(f"  Vendors processed: {len(vendors)}", logfile)
    log(f"  Applications submitted: {total_applied}", logfile)
    log(f"  Skipped (no jobs/W2): {total_skipped}", logfile)
    log(f"  Failed (load error): {total_failed}", logfile)
    log(f"{'='*60}", logfile)

    # Save results JSON
    results_path = LOG_DIR / f"vendor_portal_results_{timestamp}.json"
    with open(results_path, "w") as f:
        json.dump({"summary": {"applied": total_applied, "skipped": total_skipped, "failed": total_failed},
                   "results": results}, f, indent=2)

    logfile.close()
    conn.close()

    return {"applied": total_applied, "skipped": total_skipped, "failed": total_failed}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, default=None, help="Batch number (0-based, 50 vendors each)")
    parser.add_argument("--limit", type=int, default=None, help="Max applications to submit")
    args = parser.parse_args()
    run_pipeline(batch_num=args.batch, limit=args.limit)
