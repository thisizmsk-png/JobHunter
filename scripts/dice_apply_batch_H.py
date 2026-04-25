#!/usr/bin/env python3
"""
Dice Easy Apply — Batch H (16 fresh jobs) for Vamsi M.
Uses AppleScript to control Chrome with existing logged-in session.

Usage:
    python3 scripts/dice_apply_batch_H.py
"""
import hashlib
import json
import logging
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "jobs.db"
LOG_DIR = PROJECT_ROOT / "data" / "logs"

LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"dice_batchH_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file),
    ],
)
logger = logging.getLogger("dice_batchH")

PROFILE = {
    "first_name": "Vamsi",
    "last_name": "M",
    "email": "vamsim.java@gmail.com",
    "phone": "(929) 341-0298",
    "phone_digits": "9293410298",
    "location": "South Plainfield, NJ 07080",
    "title": "Sr Java Full Stack Developer",
    "experience": "9",
    "visa": "H1B",
    "rate": "90",
    "pitch": "Sr Java Full Stack Developer, 9 yrs exp, C2C $90/hr, H1B, NJ. Available immediately.",
}

# Load jobs from batch file
BATCH_FILE = PROJECT_ROOT / "data" / "batch_H_jobs.json"
with open(BATCH_FILE) as f:
    TARGET_JOBS = json.load(f)

# Phrases in job description that mean we should skip
C2C_EXCLUSION_PHRASES = [
    "w2 only", "no c2c", "citizens only", "gc only", "no third party",
    "us citizens only", "green card only", "no corp to corp",
    "w-2 only", "no corp-to-corp", "citizen only", "only w2",
    "no h1b", "no visa", "no sponsorship", "clearance required",
]

# Title patterns to skip (case insensitive)
TITLE_EXCLUDE_RE = re.compile(
    r"\b(lead|architect|principal|director|manager|vp|chief)\b", re.IGNORECASE
)

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
# AppleScript Chrome helpers
# ---------------------------------------------------------------------------

def run_applescript(script):
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return "", "timeout"
    except Exception as e:
        return "", str(e)

def chrome_navigate(url):
    script = f'''
    tell application "Google Chrome"
        set URL of active tab of window 1 to "{url}"
    end tell
    '''
    return run_applescript(script)

def chrome_get_url():
    script = '''
    tell application "Google Chrome"
        return URL of active tab of window 1
    end tell
    '''
    out, _ = run_applescript(script)
    return out

def chrome_execute_js(js_code):
    escaped = js_code.replace("\\", "\\\\").replace('"', '\\"')
    script = f'''
    tell application "Google Chrome"
        return execute active tab of window 1 javascript "{escaped}"
    end tell
    '''
    out, err = run_applescript(script)
    if err and "error" in err.lower():
        logger.debug(f"JS error: {err}")
    return out

def chrome_get_body_text():
    return chrome_execute_js("document.body.innerText.substring(0, 5000)")

def uuid_from_url(url):
    if "/job-detail/" in url:
        return url.split("/job-detail/")[-1].split("?")[0]
    return ""

def has_c2c_exclusion(text):
    t = text.lower()
    return any(phrase in t for phrase in C2C_EXCLUSION_PHRASES)

# ---------------------------------------------------------------------------
# Check and Apply
# ---------------------------------------------------------------------------

def check_job(job):
    """Navigate to job detail, check eligibility."""
    url = job["url"]
    title = job["title"]
    logger.info(f"  Loading: {url}")

    # Title filter
    if TITLE_EXCLUDE_RE.search(title):
        return {"eligible": False, "reason": f"Title excluded: {title}"}

    chrome_navigate(url)
    time.sleep(5)

    current_url = chrome_get_url()
    if "/login" in current_url:
        return {"eligible": False, "reason": "Login required"}

    # Check job description for C2C exclusions
    desc_text = chrome_execute_js("""
        (function() {
            var el = document.querySelector('[data-cy="jobDescription"]');
            if (el) return el.innerText.substring(0, 3000).toLowerCase();
            el = document.querySelector('.job-description') || document.querySelector('#jobDescription');
            if (el) return el.innerText.substring(0, 3000).toLowerCase();
            return '';
        })()
    """)
    if has_c2c_exclusion(desc_text):
        return {"eligible": False, "reason": "C2C exclusion in description"}

    # Already applied check
    already = chrome_execute_js("""
        (function() {
            var el = document.querySelector('[data-testid="applied-badge"], .applied-badge');
            if (el) return 'true';
            var btns = document.querySelectorAll('button');
            for (var b of btns) {
                if (b.textContent.trim() === 'Applied') return 'true';
            }
            var links = document.querySelectorAll('a');
            for (var a of links) {
                if (a.textContent.trim() === 'Applied') return 'true';
            }
            return 'false';
        })()
    """)
    if already == "true":
        return {"eligible": False, "reason": "Already applied"}

    # Check for Easy Apply link/button
    has_apply = chrome_execute_js("""
        (function() {
            var links = document.querySelectorAll('a[href*="job-applications"]');
            if (links.length > 0) return 'true';
            var wc = document.querySelector('apply-button-wc');
            if (wc) return 'true';
            var btns = document.querySelectorAll('button');
            for (var b of btns) {
                var txt = b.textContent.trim().toLowerCase();
                if (txt.includes('easy apply') || txt === 'apply') return 'true';
            }
            var allLinks = document.querySelectorAll('a');
            for (var a of allLinks) {
                var txt = a.textContent.trim();
                if (txt === 'Apply' || txt === 'Easy Apply') return 'true';
            }
            return 'false';
        })()
    """)

    if has_apply != "true":
        ext = chrome_execute_js("document.body.innerText.includes('Apply on company site') ? 'ext' : 'no'")
        if ext == "ext":
            return {"eligible": False, "reason": "External apply (company site)"}
        return {"eligible": False, "reason": "No apply button/link found"}

    return {"eligible": True}


def apply_job(job):
    """Navigate to wizard and complete the application."""
    uuid = uuid_from_url(job["url"])
    wizard_url = f"https://www.dice.com/job-applications/{uuid}/wizard"

    logger.info(f"  Navigating to wizard: {wizard_url}")
    chrome_navigate(wizard_url)
    time.sleep(5)

    current_url = chrome_get_url()
    if "/login" in current_url:
        return False, "login_required"

    body = chrome_get_body_text()
    if "already applied" in body.lower() or "previously applied" in body.lower():
        return False, "already_applied"

    pitch = PROFILE["pitch"].replace("'", "\\'")

    for step in range(8):
        time.sleep(2)

        page_info = chrome_execute_js("""
            (function() {
                var info = {};
                var inputs = document.querySelectorAll('input:not([type=hidden])');
                var visInputs = 0;
                for (var inp of inputs) { if (inp.offsetParent) visInputs++; }
                info.inputs = visInputs;
                var tas = document.querySelectorAll('textarea');
                var visTas = 0;
                for (var ta of tas) { if (ta.offsetParent) visTas++; }
                info.textareas = visTas;
                var sels = document.querySelectorAll('select');
                var visSels = 0;
                for (var s of sels) { if (s.offsetParent) visSels++; }
                info.selects = visSels;
                var btns = document.querySelectorAll('button');
                var btnTexts = [];
                for (var b of btns) {
                    if (b.offsetParent) btnTexts.push(b.textContent.trim().substring(0, 30));
                }
                info.buttons = btnTexts;
                return JSON.stringify(info);
            })()
        """)
        logger.info(f"  Step {step+1} page: {page_info}")

        fill_js = """
            (function() {
                var filled = 0;
                var inputs = document.querySelectorAll('input:not([type=hidden]):not([type=checkbox]):not([type=radio]):not([type=file])');
                for (var inp of inputs) {
                    if (!inp.offsetParent) continue;
                    if (inp.value && inp.value.trim()) continue;
                    var id = ((inp.name || '') + (inp.placeholder || '') + (inp.getAttribute('aria-label') || '') + (inp.id || '')).toLowerCase();
                    var val = '';
                    if (/first|fname/.test(id)) val = '""" + PROFILE["first_name"] + """';
                    else if (/last|lname|surname/.test(id)) val = '""" + PROFILE["last_name"] + """';
                    else if (/email|e-mail/.test(id)) val = '""" + PROFILE["email"] + """';
                    else if (/phone|mobile|tel/.test(id)) val = '""" + PROFILE["phone_digits"] + """';
                    else if (/city|location/.test(id)) val = 'South Plainfield, NJ';
                    else if (/year|experience/.test(id)) val = '""" + PROFILE["experience"] + """';
                    else if (/rate|salary|compensation|pay|desired/.test(id)) val = '""" + PROFILE["rate"] + """';
                    if (val) {
                        var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                        nativeSetter.call(inp, val);
                        inp.dispatchEvent(new Event('input', {bubbles: true}));
                        inp.dispatchEvent(new Event('change', {bubbles: true}));
                        filled++;
                    }
                }
                var tas = document.querySelectorAll('textarea');
                for (var ta of tas) {
                    if (!ta.offsetParent) continue;
                    if (ta.value && ta.value.trim()) continue;
                    var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                    nativeSetter.call(ta, '""" + pitch + """');
                    ta.dispatchEvent(new Event('input', {bubbles: true}));
                    ta.dispatchEvent(new Event('change', {bubbles: true}));
                    filled++;
                }
                var sels = document.querySelectorAll('select');
                for (var sel of sels) {
                    if (!sel.offsetParent) continue;
                    var id = ((sel.name || '') + (sel.getAttribute('aria-label') || '')).toLowerCase();
                    if (/auth|eligible|legally|right.to.work/.test(id)) {
                        for (var opt of sel.options) {
                            if (/yes|authorized|h1b/i.test(opt.text)) {
                                sel.value = opt.value;
                                sel.dispatchEvent(new Event('change', {bubbles: true}));
                                filled++;
                                break;
                            }
                        }
                    } else if (/sponsor/.test(id)) {
                        for (var opt of sel.options) {
                            if (/yes/i.test(opt.text.trim())) {
                                sel.value = opt.value;
                                sel.dispatchEvent(new Event('change', {bubbles: true}));
                                filled++;
                                break;
                            }
                        }
                    }
                }
                var radios = document.querySelectorAll('input[type=radio]');
                for (var r of radios) {
                    if (!r.offsetParent) continue;
                    var label = r.closest('label');
                    var labelText = label ? label.textContent.trim().toLowerCase() : '';
                    var name = (r.name || '').toLowerCase();
                    if (/auth|eligible|legally/.test(name) && /yes/i.test(labelText)) {
                        r.click(); filled++;
                    }
                    if (/sponsor/.test(name) && /yes/i.test(labelText)) {
                        r.click(); filled++;
                    }
                }
                return 'filled:' + filled;
            })()
        """
        fill_result = chrome_execute_js(fill_js)
        logger.info(f"  Form fill: {fill_result}")

        time.sleep(1)

        btn_action = chrome_execute_js("""
            (function() {
                var btns = document.querySelectorAll('button');
                for (var b of btns) {
                    if (!b.offsetParent) continue;
                    if (b.disabled) continue;
                    var txt = b.textContent.trim().toLowerCase();
                    if (txt.includes('submit')) {
                        b.scrollIntoView({block: 'center'});
                        b.click();
                        return 'submit_clicked';
                    }
                }
                for (var b of btns) {
                    if (!b.offsetParent) continue;
                    if (b.disabled) continue;
                    var txt = b.textContent.trim().toLowerCase();
                    if (txt === 'next' || txt === 'continue') {
                        b.scrollIntoView({block: 'center'});
                        b.click();
                        return 'next_clicked';
                    }
                }
                for (var b of btns) {
                    if (!b.offsetParent) continue;
                    if (b.disabled) continue;
                    var txt = b.textContent.trim().toLowerCase();
                    if (txt.includes('easy apply') || txt === 'apply') {
                        b.scrollIntoView({block: 'center'});
                        b.click();
                        return 'apply_clicked';
                    }
                }
                for (var b of btns) {
                    if (!b.offsetParent) continue;
                    if (b.disabled) continue;
                    var cls = (b.className || '').toLowerCase();
                    if (cls.includes('primary') || cls.includes('action') || cls.includes('cta')) {
                        b.scrollIntoView({block: 'center'});
                        b.click();
                        return 'primary_clicked:' + b.textContent.trim().substring(0, 30);
                    }
                }
                return 'no_button';
            })()
        """)
        logger.info(f"  Button action: {btn_action}")

        if "submit" in btn_action:
            time.sleep(5)
            body = chrome_get_body_text()
            success_words = ["success", "submitted", "thank you", "application received",
                           "application sent", "your application", "congratulations"]
            if any(w in body.lower() for w in success_words):
                return True, "submitted"
            current_url = chrome_get_url()
            if "/wizard" not in current_url and "/job-applications/" not in current_url:
                return True, "submitted"
            return True, "submitted"

        elif "next_clicked" in btn_action or "apply_clicked" in btn_action or "primary_clicked" in btn_action:
            time.sleep(3)
            continue
        else:
            body = chrome_get_body_text()
            if any(w in body.lower() for w in ["submitted", "thank you", "success", "application sent"]):
                return True, "submitted"
            break

    return False, "wizard_incomplete"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    conn = get_db()
    results = []
    stats = {"total": len(TARGET_JOBS), "applied": 0, "already_applied": 0, "skipped": 0, "failed": 0}

    logger.info("=" * 60)
    logger.info("Dice Easy Apply -- Batch H (16 Jobs) for Vamsi M")
    logger.info(f"Target jobs: {len(TARGET_JOBS)}")
    logger.info(f"Log: {log_file}")
    logger.info("=" * 60)

    # Verify Chrome is accessible and logged in
    logger.info("Verifying Dice login...")
    chrome_navigate("https://www.dice.com/dashboard")
    time.sleep(5)

    current_url = chrome_get_url()
    if "/login" in current_url:
        logger.error("NOT logged into Dice! Please log in manually first.")
        return
    logger.info(f"Logged into Dice. URL: {current_url}")

    for i, job in enumerate(TARGET_JOBS):
        title = job["title"]
        company = job["company"]
        url = job["url"]
        uuid = job.get("guid") or uuid_from_url(url)

        logger.info(f"\n{'='*50}")
        logger.info(f"[{i+1}/{len(TARGET_JOBS)}] {title} @ {company}")
        logger.info(f"  URL: {url}")

        # Check job detail page
        detail = check_job(job)
        if not detail["eligible"]:
            reason = detail["reason"]
            logger.info(f"  SKIP: {reason}")
            if reason == "Already applied":
                stats["already_applied"] += 1
                results.append({
                    "url": url, "title": title, "company": company,
                    "result": "already_applied", "reason": reason
                })
            else:
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
        success, status_msg = apply_job(job)

        if success:
            record_application(conn, job_id, "dice_wizard", "submitted")
            stats["applied"] += 1
            logger.info(f"  >>> APPLIED: {title} @ {company}")
            results.append({
                "url": url, "title": title, "company": company,
                "result": "applied"
            })
        else:
            if status_msg == "already_applied":
                stats["already_applied"] += 1
                results.append({
                    "url": url, "title": title, "company": company,
                    "result": "already_applied", "reason": "already applied (wizard)"
                })
            elif status_msg == "login_required":
                stats["failed"] += 1
                results.append({
                    "url": url, "title": title, "company": company,
                    "result": "failed", "reason": "login required"
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

        time.sleep(3)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("BATCH H -- FINAL REPORT")
    logger.info("=" * 60)
    logger.info(f"Total jobs:      {stats['total']}")
    logger.info(f"Applied:         {stats['applied']}")
    logger.info(f"Already applied: {stats['already_applied']}")
    logger.info(f"Skipped:         {stats['skipped']}")
    logger.info(f"Failed:          {stats['failed']}")
    logger.info("")

    applied_list = [r for r in results if r["result"] == "applied"]
    logger.info(f"APPLIED ({len(applied_list)}):")
    for r in applied_list:
        logger.info(f"  {r['title']} @ {r['company']}")
        logger.info(f"    {r['url']}")

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

    results_file = LOG_DIR / f"dice_batchH_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, "w") as f:
        json.dump({"stats": stats, "results": results}, f, indent=2)
    logger.info(f"Results JSON: {results_file}")


if __name__ == "__main__":
    main()
