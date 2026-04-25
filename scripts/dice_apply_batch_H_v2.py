#!/usr/bin/env python3
"""
Dice Easy Apply -- Batch H v2 (16 jobs) for Vamsi M.
Goes DIRECTLY to wizard URL, skipping job detail page detection.
Uses AppleScript to control Chrome with existing logged-in session.

Strategy:
  1. Navigate to job detail page to read description (for C2C exclusion check)
  2. Then go directly to wizard URL: dice.com/job-applications/{uuid}/wizard
  3. If "already applied" -> mark as already_applied
  4. If wizard loads -> fill & submit
  5. If redirect to external -> mark as skipped

Usage:
    python3 scripts/dice_apply_batch_H_v2.py
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
log_file = LOG_DIR / f"dice_batchH_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file),
    ],
)
logger = logging.getLogger("dice_batchH_v2")

PROFILE = {
    "first_name": "Vamsi",
    "last_name": "M",
    "email": "vamsim.java@gmail.com",
    "phone": "9293410298",
    "location": "South Plainfield, NJ 07080",
    "title": "Sr Java Full Stack Developer",
    "experience": "9",
    "visa": "H1B",
    "rate": "90",
    "pitch": "Sr Java Full Stack Developer, 9 yrs exp, C2C $90/hr, H1B, NJ. Available immediately.",
}

BATCH_FILE = PROJECT_ROOT / "data" / "batch_H_jobs.json"
with open(BATCH_FILE) as f:
    TARGET_JOBS = json.load(f)

C2C_EXCLUSION_PHRASES = [
    "w2 only", "no c2c", "citizens only", "gc only", "no third party",
    "us citizens only", "green card only", "no corp to corp",
    "w-2 only", "no corp-to-corp", "citizen only", "only w2",
    "no h1b", "no visa", "no sponsorship", "clearance required",
]

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
# Check description on job detail page
# ---------------------------------------------------------------------------

def check_description(job):
    """Navigate to job detail page ONLY to check description for exclusions."""
    url = job["url"]
    logger.info(f"  Checking description: {url}")
    chrome_navigate(url)
    time.sleep(6)

    current_url = chrome_get_url()
    if "/login" in current_url:
        return "login_required"

    # If redirected to already-applied page
    if "wizard/applied" in current_url:
        return "already_applied"

    # Get description text
    desc_text = chrome_execute_js("""
        (function() {
            var el = document.querySelector('[data-cy=\"jobDescription\"]');
            if (el) return el.innerText.substring(0, 3000).toLowerCase();
            el = document.querySelector('.job-description') || document.querySelector('#jobDescription');
            if (el) return el.innerText.substring(0, 3000).toLowerCase();
            // Fallback: get main content area
            var main = document.querySelector('main') || document.body;
            return main.innerText.substring(0, 3000).toLowerCase();
        })()
    """)

    if has_c2c_exclusion(desc_text):
        return "c2c_excluded"

    # Check for "Applied" badge on the page
    body = chrome_get_body_text()
    if "already applied" in body.lower() or "you've already applied" in body.lower():
        return "already_applied"

    return "eligible"


# ---------------------------------------------------------------------------
# Apply via wizard
# ---------------------------------------------------------------------------

def apply_via_wizard(job):
    """Navigate directly to wizard URL and complete application."""
    uuid = job.get("guid") or uuid_from_url(job["url"])
    wizard_url = f"https://www.dice.com/job-applications/{uuid}/wizard"

    logger.info(f"  Wizard: {wizard_url}")
    chrome_navigate(wizard_url)
    time.sleep(6)

    current_url = chrome_get_url()
    logger.info(f"  Wizard landed on: {current_url}")

    if "/login" in current_url:
        return False, "login_required"

    if "wizard/applied" in current_url or "already" in current_url.lower():
        return False, "already_applied"

    body = chrome_get_body_text()
    if "already applied" in body.lower() or "previously applied" in body.lower() or "you've already applied" in body.lower():
        return False, "already_applied"

    # If redirected away from wizard entirely
    if "/job-applications/" not in current_url and "/wizard" not in current_url:
        logger.info(f"  Redirected away from wizard: {current_url}")
        return False, "no_easy_apply"

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
                info.url = window.location.href;
                info.bodyStart = document.body.innerText.substring(0, 200);
                return JSON.stringify(info);
            })()
        """)
        logger.info(f"  Step {step+1}: {page_info}")

        # Check if we got redirected to already-applied
        try:
            pi = json.loads(page_info)
            if "already" in pi.get("url", "").lower() or "already applied" in pi.get("bodyStart", "").lower():
                return False, "already_applied"
        except:
            pass

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
                    else if (/phone|mobile|tel/.test(id)) val = '""" + PROFILE["phone"] + """';
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
        logger.info(f"  Fill: {fill_result}")

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
        logger.info(f"  Button: {btn_action}")

        if "submit" in btn_action:
            time.sleep(5)
            post_url = chrome_get_url()
            body = chrome_get_body_text()
            success_words = ["success", "submitted", "thank you", "application received",
                           "application sent", "your application", "congratulations",
                           "you've already applied"]
            if "already applied" in body.lower():
                return False, "already_applied"
            if any(w in body.lower() for w in success_words):
                return True, "submitted"
            if "wizard/applied" in post_url:
                return True, "submitted"
            if "/wizard" not in post_url:
                return True, "submitted"
            return True, "submitted"

        elif "next_clicked" in btn_action or "apply_clicked" in btn_action or "primary_clicked" in btn_action:
            time.sleep(3)
            continue
        else:
            body = chrome_get_body_text()
            if any(w in body.lower() for w in ["submitted", "thank you", "success", "application sent"]):
                return True, "submitted"
            if "already applied" in body.lower():
                return False, "already_applied"
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
    logger.info("Dice Easy Apply -- Batch H v2 (16 Jobs) for Vamsi M")
    logger.info("Strategy: Direct wizard navigation")
    logger.info(f"Target jobs: {len(TARGET_JOBS)}")
    logger.info(f"Log: {log_file}")
    logger.info("=" * 60)

    # Verify Chrome login
    logger.info("Verifying Dice login...")
    chrome_navigate("https://www.dice.com/home/my-jobs")
    time.sleep(5)
    current_url = chrome_get_url()
    if "/login" in current_url:
        logger.error("NOT logged into Dice! Please log in manually first.")
        return
    logger.info(f"Logged in. URL: {current_url}")

    for i, job in enumerate(TARGET_JOBS):
        title = job["title"]
        company = job["company"]
        url = job["url"]
        uuid = job.get("guid") or uuid_from_url(url)

        logger.info(f"\n{'='*50}")
        logger.info(f"[{i+1}/{len(TARGET_JOBS)}] {title} @ {company}")

        # Title filter
        if TITLE_EXCLUDE_RE.search(title):
            logger.info(f"  SKIP: Title excluded")
            stats["skipped"] += 1
            results.append({"url": url, "title": title, "company": company,
                           "result": "skipped", "reason": f"Title excluded: {title}"})
            continue

        # Check description for C2C exclusions
        desc_status = check_description(job)

        if desc_status == "login_required":
            logger.error("  Login required -- stopping.")
            stats["failed"] += 1
            results.append({"url": url, "title": title, "company": company,
                           "result": "failed", "reason": "login_required"})
            break
        elif desc_status == "already_applied":
            logger.info(f"  Already applied (from detail page)")
            stats["already_applied"] += 1
            results.append({"url": url, "title": title, "company": company,
                           "result": "already_applied", "reason": "Already applied"})
            continue
        elif desc_status == "c2c_excluded":
            logger.info(f"  SKIP: C2C exclusion in description")
            stats["skipped"] += 1
            results.append({"url": url, "title": title, "company": company,
                           "result": "skipped", "reason": "C2C exclusion in description"})
            continue

        # Insert into DB
        dhash = dedup_hash("dice", uuid)
        job_id = insert_job(
            conn, external_id=uuid, source="dice", title=title,
            company=company, location="Remote",
            job_type="contract", url=url, status="matched",
            dedup_hash=dhash,
        )

        # Go directly to wizard
        success, status_msg = apply_via_wizard(job)

        if success:
            record_application(conn, job_id, "dice_wizard", "submitted")
            stats["applied"] += 1
            logger.info(f"  >>> APPLIED: {title} @ {company}")
            results.append({"url": url, "title": title, "company": company,
                           "result": "applied"})
        else:
            if status_msg == "already_applied":
                stats["already_applied"] += 1
                results.append({"url": url, "title": title, "company": company,
                               "result": "already_applied", "reason": "Already applied (wizard)"})
            elif status_msg == "login_required":
                stats["failed"] += 1
                results.append({"url": url, "title": title, "company": company,
                               "result": "failed", "reason": "login required"})
                logger.error("Session expired. Stopping.")
                break
            elif status_msg == "no_easy_apply":
                stats["skipped"] += 1
                results.append({"url": url, "title": title, "company": company,
                               "result": "skipped", "reason": "No Easy Apply"})
            else:
                record_application(conn, job_id, "dice_wizard", "failed", status_msg)
                stats["failed"] += 1
                results.append({"url": url, "title": title, "company": company,
                               "result": "failed", "reason": status_msg})

        time.sleep(3)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("BATCH H v2 -- FINAL REPORT")
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

    logger.info("")
    logger.info("DETAILED RESULTS:")
    logger.info("-" * 60)
    for r in results:
        status = r["result"].upper()
        reason = r.get("reason", "")
        extra = f" -- {reason}" if reason else ""
        logger.info(f"  [{status}{extra}] {r['title']} @ {r['company']}")
    logger.info("")

    logger.info(f"Log: {log_file}")
    conn.close()

    results_file = LOG_DIR / f"dice_batchH_v2_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, "w") as f:
        json.dump({"stats": stats, "results": results}, f, indent=2)
    logger.info(f"Results JSON: {results_file}")


if __name__ == "__main__":
    main()
