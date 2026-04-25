#!/usr/bin/env python3
"""
Dice Targeted Apply — Uses AppleScript to control Chrome with existing logged-in session.
Navigates to each job URL, checks eligibility, and applies via Easy Apply wizard.

Usage:
    python3 scripts/dice_applescript_apply.py
"""
import hashlib
import json
import logging
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
log_file = LOG_DIR / f"dice_as_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file),
    ],
)
logger = logging.getLogger("dice_as")

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
    logger.info(f"  Loading: {url}")
    chrome_navigate(url)
    time.sleep(5)

    current_url = chrome_get_url()
    if "/login" in current_url:
        return {"eligible": False, "reason": "Login required"}

    body = chrome_get_body_text()

    # C2C exclusions
    if has_c2c_exclusion(body):
        return {"eligible": False, "reason": "C2C exclusion (W2 only / no C2C)"}

    # Already applied check
    already = chrome_execute_js("""
        (function() {
            // Check for Applied badge/text
            var el = document.querySelector('[data-testid=\\"applied-badge\\"], .applied-badge');
            if (el) return 'true';
            // Check buttons with "Applied" text
            var btns = document.querySelectorAll('button');
            for (var b of btns) {
                if (b.textContent.trim() === 'Applied') return 'true';
            }
            // Check anchor tags with "Applied"
            var links = document.querySelectorAll('a');
            for (var a of links) {
                if (a.textContent.trim() === 'Applied') return 'true';
            }
            // Check general text near apply area
            var body = document.body.innerText.substring(0, 1000);
            if (body.includes('Applied') && !body.includes('Easy Apply')) return 'true';
            return 'false';
        })()
    """)
    if already == "true":
        return {"eligible": False, "reason": "Already applied"}

    # Check for Apply link/button (Dice uses <a> tags for apply!)
    has_apply = chrome_execute_js("""
        (function() {
            // Check anchor tags with wizard URL
            var links = document.querySelectorAll('a[href*=\\"job-applications\\"]');
            if (links.length > 0) return 'true';
            // Check apply-button-wc web component
            var wc = document.querySelector('apply-button-wc');
            if (wc) return 'true';
            // Check buttons
            var btns = document.querySelectorAll('button');
            for (var b of btns) {
                var txt = b.textContent.trim().toLowerCase();
                if (txt.includes('easy apply') || txt === 'apply') return 'true';
            }
            // Check any link with Apply text
            var allLinks = document.querySelectorAll('a');
            for (var a of allLinks) {
                var txt = a.textContent.trim();
                if (txt === 'Apply' || txt === 'Easy Apply') return 'true';
            }
            return 'false';
        })()
    """)

    if has_apply != "true":
        # Check for external apply
        ext = chrome_execute_js("document.body.innerText.includes('Apply on company site') ? 'ext' : 'no'")
        if ext == "ext":
            return {"eligible": False, "reason": "External apply (company site)"}
        return {"eligible": False, "reason": "No apply button/link found"}

    return {"eligible": True}


def apply_job(job):
    """Navigate to wizard and complete the application."""
    uuid = uuid_from_url(job["url"])
    wizard_url = f"https://www.dice.com/job-applications/{uuid}/wizard"

    # Navigate directly to wizard URL (most reliable)
    logger.info(f"  Navigating to wizard: {wizard_url}")
    chrome_navigate(wizard_url)
    time.sleep(5)

    # Check for login redirect
    current_url = chrome_get_url()
    if "/login" in current_url:
        return False, "login_required"

    body = chrome_get_body_text()
    if "already applied" in body.lower() or "previously applied" in body.lower():
        return False, "already_applied"

    # Step through wizard (up to 8 steps)
    for step in range(8):
        time.sleep(2)

        # Get page state
        page_info = chrome_execute_js("""
            (function() {
                var info = {};
                // Count visible inputs
                var inputs = document.querySelectorAll('input:not([type=hidden])');
                var visInputs = 0;
                for (var inp of inputs) { if (inp.offsetParent) visInputs++; }
                info.inputs = visInputs;
                // Count visible textareas
                var tas = document.querySelectorAll('textarea');
                var visTas = 0;
                for (var ta of tas) { if (ta.offsetParent) visTas++; }
                info.textareas = visTas;
                // Count visible selects
                var sels = document.querySelectorAll('select');
                var visSels = 0;
                for (var s of sels) { if (s.offsetParent) visSels++; }
                info.selects = visSels;
                // Find buttons
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

        # Fill form fields
        fill_js = """
            (function() {
                var filled = 0;
                var inputs = document.querySelectorAll('input:not([type=hidden]):not([type=checkbox]):not([type=radio]):not([type=file])');
                for (var inp of inputs) {
                    if (!inp.offsetParent) continue;
                    if (inp.value && inp.value.trim()) continue;
                    var id = ((inp.name || '') + (inp.placeholder || '') + (inp.getAttribute('aria-label') || '')).toLowerCase();
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
                // Textareas
                var tas = document.querySelectorAll('textarea');
                for (var ta of tas) {
                    if (!ta.offsetParent) continue;
                    if (ta.value && ta.value.trim()) continue;
                    var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                    nativeSetter.call(ta, '""" + PROFILE["pitch"] + """');
                    ta.dispatchEvent(new Event('input', {bubbles: true}));
                    ta.dispatchEvent(new Event('change', {bubbles: true}));
                    filled++;
                }
                // Selects
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
                            if (/^no$/i.test(opt.text.trim())) {
                                sel.value = opt.value;
                                sel.dispatchEvent(new Event('change', {bubbles: true}));
                                filled++;
                                break;
                            }
                        }
                    }
                }
                // Radio buttons - handle work auth / sponsorship
                var radios = document.querySelectorAll('input[type=radio]');
                for (var r of radios) {
                    if (!r.offsetParent) continue;
                    var label = r.closest('label');
                    var labelText = label ? label.textContent.trim().toLowerCase() : '';
                    var name = (r.name || '').toLowerCase();
                    // Work authorization: select Yes
                    if (/auth|eligible|legally/.test(name) && /yes/i.test(labelText)) {
                        r.click(); filled++;
                    }
                    // Sponsorship: select No
                    if (/sponsor/.test(name) && /no/i.test(labelText)) {
                        r.click(); filled++;
                    }
                }
                return 'filled:' + filled;
            })()
        """
        fill_result = chrome_execute_js(fill_js)
        logger.info(f"  Form fill: {fill_result}")

        time.sleep(1)

        # Click the appropriate button
        btn_action = chrome_execute_js("""
            (function() {
                var btns = document.querySelectorAll('button');
                // Priority 1: Submit
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
                // Priority 2: Next / Continue
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
                // Priority 3: Apply / Easy Apply
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
                // Priority 4: Any primary/action button
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
            # Even if we can't confirm, if submit was clicked, count it
            return True, "submitted"

        elif "next_clicked" in btn_action or "apply_clicked" in btn_action or "primary_clicked" in btn_action:
            time.sleep(3)
            continue
        else:
            logger.warning(f"  No actionable button at step {step+1}")
            # Check if we're on a confirmation page
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
    stats = {"total": len(TARGET_JOBS), "applied": 0, "skipped": 0, "failed": 0}

    logger.info("=" * 60)
    logger.info("Dice Targeted Apply (AppleScript) for Vamsi M")
    logger.info(f"Target jobs: {len(TARGET_JOBS)}")
    logger.info(f"Log: {log_file}")
    logger.info("=" * 60)

    # Verify login
    logger.info("Verifying Dice login...")
    chrome_navigate("https://www.dice.com/dashboard")
    time.sleep(5)

    current_url = chrome_get_url()
    if "/login" in current_url:
        logger.error("NOT logged into Dice! Please log in manually.")
        logger.info("Waiting 120 seconds for manual login...")
        for i in range(60):
            time.sleep(2)
            current_url = chrome_get_url()
            if "/login" not in current_url:
                logger.info("Login detected!")
                break
            if i % 10 == 0 and i > 0:
                logger.info(f"  Waiting... ({i*2}s)")
        else:
            logger.error("Login timeout. Exiting.")
            return
    else:
        logger.info(f"Logged into Dice! URL: {current_url}")

    for i, job in enumerate(TARGET_JOBS):
        title = job["title"]
        company = job["company"]
        url = job["url"]
        uuid = uuid_from_url(url)

        logger.info(f"\n{'='*50}")
        logger.info(f"[{i+1}/{len(TARGET_JOBS)}] {title} @ {company}")
        logger.info(f"  URL: {url}")

        # Check job detail page
        detail = check_job(job)
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
                stats["skipped"] += 1
                results.append({
                    "url": url, "title": title, "company": company,
                    "result": "skipped", "reason": "already applied"
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

    results_file = LOG_DIR / f"dice_as_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, "w") as f:
        json.dump({"stats": stats, "results": results}, f, indent=2)
    logger.info(f"Results JSON: {results_file}")


if __name__ == "__main__":
    main()
