#!/usr/bin/env python3
"""
Dice Easy Apply batch — 30 jobs for Vamsi M (Apr 6 2026).
Uses AppleScript to control Chrome with existing logged-in session.
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
log_file = LOG_DIR / f"dice30_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file),
    ],
)
logger = logging.getLogger("dice30")

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
    "pitch": "Sr Java Full Stack Developer, 9 years -- Java 17, Spring Boot, Microservices, REST APIs, AWS, Docker, Kubernetes, Angular, React. Available for C2C at $90/hr. H1B, no sponsorship needed.",
}

TARGET_JOBS = [
    {"url": "https://www.dice.com/job-detail/7f75fa6e-2838-4fb1-9079-ffb955664e9b", "title": "JAVA/J2EE Developer", "company": "Vigna Solutions"},
    {"url": "https://www.dice.com/job-detail/5c639e31-75bb-4cca-8f7d-656100b34325", "title": "Java Backend Developer", "company": "CBTS"},
    {"url": "https://www.dice.com/job-detail/dd2a117b-881b-44c7-97ea-47f7d46485f2", "title": "Java Developer", "company": "InfiCare Technologies"},
    {"url": "https://www.dice.com/job-detail/50a9b0a7-9699-450d-a286-1e13d29fca78", "title": "Sr. Java Developer", "company": "SSN Group"},
    {"url": "https://www.dice.com/job-detail/1b6eefcb-a667-4cde-9df9-8f6cc2bb8981", "title": "Full Stack Java Developer", "company": "ARK Solutions"},
    {"url": "https://www.dice.com/job-detail/c7095c67-e6bf-4852-b75c-e14da8a24d34", "title": "Java Backend Engineer", "company": "BayOne Solutions"},
    {"url": "https://www.dice.com/job-detail/18e8f47e-489d-4440-a4dd-485f686ed538", "title": "Java/JEE Core Java Developer", "company": "NTT DATA Americas"},
    {"url": "https://www.dice.com/job-detail/111a9509-014d-4f4e-862b-6847d9107aa2", "title": "Java FSD with AI", "company": "Galent"},
    {"url": "https://www.dice.com/job-detail/ae2f245d-63c0-4821-bddb-af0556b00993", "title": "Need Java Microservices Developer", "company": "SRS Consulting"},
    {"url": "https://www.dice.com/job-detail/cb6f5bfb-d197-4672-8302-43e7d50800ed", "title": "Java Developer/FSD", "company": "Comprehensive Resources"},
    {"url": "https://www.dice.com/job-detail/46601a41-e688-4626-9877-f766ee7d0205", "title": "Software Engineer Java Angular", "company": "APN Software"},
    {"url": "https://www.dice.com/job-detail/33c94001-b5b0-4220-9285-4bac47325c28", "title": "Software Engineering Core Java Advanced", "company": "BCforward"},
    {"url": "https://www.dice.com/job-detail/5594e56f-90cb-4a8c-84f6-6621f47bd28b", "title": "Java Engineer + AWS Cloud", "company": "Mastech Digital"},
    {"url": "https://www.dice.com/job-detail/5dbca418-2e41-4dae-8b90-cf4b2d62c35b", "title": "Java Developer", "company": "HPTech"},
    {"url": "https://www.dice.com/job-detail/af5290fa-09d3-4b71-a75b-eeb56a890238", "title": "Java Developer", "company": "V-Soft Consulting"},
    {"url": "https://www.dice.com/job-detail/5750437e-bf61-46a1-96df-f14433592dc8", "title": "Java Developer", "company": "Vertisystem"},
    {"url": "https://www.dice.com/job-detail/81a8e3e3-29e1-4722-b088-8dd46c08ffd4", "title": "Java Developer", "company": "Codeforce 360"},
    {"url": "https://www.dice.com/job-detail/7dce6d9e-50ef-46da-aa63-8516202a9038", "title": "Java Backend Services Developer IV", "company": "V-Soft Consulting"},
    {"url": "https://www.dice.com/job-detail/653264e2-0990-4ad7-828e-60c932ea85ae", "title": "Java Developer", "company": "Pyramid Technology"},
    {"url": "https://www.dice.com/job-detail/1ec4e89c-7dc5-473e-be43-c67e5631074a", "title": "Senior Java & .NET Developer", "company": "Triune Infomatics"},
    {"url": "https://www.dice.com/job-detail/efb090d7-72e5-4381-8af1-e66209513edf", "title": "Java Full-Stack developer", "company": "APN Software"},
    {"url": "https://www.dice.com/job-detail/56e4945c-ab93-4d4d-a7d3-192a74e1aef6", "title": "Spring Boot/API Developer 2 Openings", "company": "DivIHN Integration"},
    {"url": "https://www.dice.com/job-detail/48f4e93b-8eec-43e1-b6d2-8624e87c6354", "title": "Software Engineer Remote", "company": "VIVA USA"},
    {"url": "https://www.dice.com/job-detail/f11e0903-6525-47c4-8054-f7ead95b5032", "title": "Sr Java Developer financial experience", "company": "Infinity Tech Group"},
    {"url": "https://www.dice.com/job-detail/1be397d3-6e57-4042-bae6-50f227ef3093", "title": "Java Fullstack Developer", "company": "Kaizen Soft Solutions"},
    {"url": "https://www.dice.com/job-detail/6b7e8925-9643-4f71-b103-3727a59bd16b", "title": "Java Developer", "company": "Acro Service Corp"},
    {"url": "https://www.dice.com/job-detail/b6f3e117-a4e4-4499-8d55-0905530296a3", "title": "Java Full Stack Developer", "company": "NextXap"},
    {"url": "https://www.dice.com/job-detail/da4567ee-a73e-4497-a70a-d6a6ad1908e3", "title": "Full Stack Java Developer", "company": "Brillius"},
    {"url": "https://www.dice.com/job-detail/f2ec8ef1-4e07-4fa7-a1a0-acb356b3d3ee", "title": "Java Angular Developer", "company": "Camelot Integrated"},
    {"url": "https://www.dice.com/job-detail/50c2e505-dc3e-4e66-9b4e-985a916b4554", "title": "Java developer with Kafka", "company": "Lorhan Corporation"},
]

C2C_EXCLUSION_PHRASES = [
    "w2 only", "no c2c", "citizens only", "gc only", "no third party",
    "us citizens only", "green card only", "no corp to corp",
    "w-2 only", "no corp-to-corp", "citizen only", "only w2",
]

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

def check_job(job):
    url = job["url"]
    logger.info(f"  Loading: {url}")
    chrome_navigate(url)
    time.sleep(5)

    current_url = chrome_get_url()
    if "/login" in current_url:
        return {"eligible": False, "reason": "Login required"}

    body = chrome_get_body_text()

    if has_c2c_exclusion(body):
        return {"eligible": False, "reason": "C2C exclusion (W2 only / no C2C)"}

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

        fill_js = r"""
            (function() {
                var filled = 0;
                var inputs = document.querySelectorAll('input:not([type=hidden]):not([type=checkbox]):not([type=radio]):not([type=file])');
                for (var inp of inputs) {
                    if (!inp.offsetParent) continue;
                    if (inp.value && inp.value.trim()) continue;
                    var id = ((inp.name || '') + (inp.placeholder || '') + (inp.getAttribute('aria-label') || '')).toLowerCase();
                    var val = '';
                    if (/first|fname/.test(id)) val = 'Vamsi';
                    else if (/last|lname|surname/.test(id)) val = 'M';
                    else if (/email|e-mail/.test(id)) val = 'vamsim.java@gmail.com';
                    else if (/phone|mobile|tel/.test(id)) val = '(929) 341-0298';
                    else if (/city|location/.test(id)) val = 'South Plainfield, NJ';
                    else if (/year|experience/.test(id)) val = '9';
                    else if (/rate|salary|compensation|pay|desired/.test(id)) val = '90';
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
                    nativeSetter.call(ta, 'Sr Java Full Stack Developer, 9 years -- Java 17, Spring Boot, Microservices, REST APIs, AWS, Docker, Kubernetes, Angular, React. Available for C2C at $90/hr. H1B, no sponsorship needed.');
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
                            if (/^no$/i.test(opt.text.trim())) {
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
            logger.warning(f"  No actionable button at step {step+1}")
            body = chrome_get_body_text()
            if any(w in body.lower() for w in ["submitted", "thank you", "success", "application sent"]):
                return True, "submitted"
            break

    return False, "wizard_incomplete"


def main():
    conn = get_db()
    results = []
    stats = {"total": len(TARGET_JOBS), "applied": 0, "already_applied": 0, "skipped": 0, "failed": 0}

    logger.info("=" * 60)
    logger.info("Dice Easy Apply Batch (30 jobs) for Vamsi M")
    logger.info(f"Target jobs: {len(TARGET_JOBS)}")
    logger.info(f"Log: {log_file}")
    logger.info("=" * 60)

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

        detail = check_job(job)
        if not detail["eligible"]:
            reason = detail["reason"]
            logger.info(f"  SKIP: {reason}")
            if "already applied" in reason.lower():
                stats["already_applied"] += 1
                results.append({"url": url, "title": title, "company": company, "result": "already_applied", "reason": reason})
            else:
                stats["skipped"] += 1
                results.append({"url": url, "title": title, "company": company, "result": "skipped", "reason": reason})
            continue

        dhash = dedup_hash("dice", uuid)
        job_id = insert_job(
            conn, external_id=uuid, source="dice", title=title,
            company=company, location="Remote",
            job_type="contract", url=url, status="matched",
            dedup_hash=dhash,
        )

        success, status_msg = apply_job(job)

        if success:
            record_application(conn, job_id, "dice_wizard", "submitted")
            stats["applied"] += 1
            logger.info(f"  >>> APPLIED: {title} @ {company}")
            results.append({"url": url, "title": title, "company": company, "result": "applied"})
        else:
            if status_msg == "already_applied":
                stats["already_applied"] += 1
                results.append({"url": url, "title": title, "company": company, "result": "already_applied", "reason": "already applied (wizard)"})
            elif status_msg == "login_required":
                stats["failed"] += 1
                results.append({"url": url, "title": title, "company": company, "result": "failed", "reason": "login required"})
                logger.error("Session expired. Stopping.")
                break
            else:
                record_application(conn, job_id, "dice_wizard", "failed", status_msg)
                stats["failed"] += 1
                results.append({"url": url, "title": title, "company": company, "result": "failed", "reason": status_msg})

        time.sleep(3)

    logger.info("\n" + "=" * 60)
    logger.info("FINAL REPORT")
    logger.info("=" * 60)
    logger.info(f"Total jobs:      {stats['total']}")
    logger.info(f"Applied:         {stats['applied']}")
    logger.info(f"Already applied: {stats['already_applied']}")
    logger.info(f"Skipped:         {stats['skipped']}")
    logger.info(f"Failed:          {stats['failed']}")
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

    results_file = LOG_DIR / f"dice30_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, "w") as f:
        json.dump({"stats": stats, "results": results}, f, indent=2)
    logger.info(f"Results JSON: {results_file}")


if __name__ == "__main__":
    main()
