#!/usr/bin/env python3
"""
Guest Apply Batch — Hourly mini-batch for no-login-required vendor sites.

Handles two site types:
  1. ats_*        — Search for Java jobs, apply per listing (guest apply, no account needed)
  2. resume_form  — Submit contact/resume form (once per cooldown_days, default 7)

Runs automatically in the hourly job-hunt-pipeline.

Usage:
    python3 scripts/guest_apply_batch.py
"""
import hashlib
import json
import logging
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH      = PROJECT_ROOT / "data" / "jobs.db"
LOG_DIR      = PROJECT_ROOT / "data" / "logs"
SITES_FILE   = PROJECT_ROOT / "data" / "guest_apply_sites.json"
STATE_FILE   = PROJECT_ROOT / "data" / "guest_apply_state.json"
RESUME_PATH  = PROJECT_ROOT / "assets" / "Vamsi_M Sr. Java Full Stack Developer.docx"

LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"guest_apply_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file),
    ],
)
logger = logging.getLogger("guest_apply")

PROFILE = {
    "first_name":  "Vamsi",
    "last_name":   "M",
    "full_name":   "Vamsi M",
    "email":       "vamsim.java@gmail.com",
    "phone":       "9293410298",
    "phone_fmt":   "(929) 341-0298",
    "city":        "South Plainfield",
    "state":       "NJ",
    "zip":         "07080",
    "title":       "Sr Java Full Stack Developer",
    "experience":  "9",
    "visa":        "H1B",
    "rate":        "90",
    "linkedin":    "linkedin.com/in/vamsim",
    "summary": (
        "Sr Java Full Stack Developer, 9 years exp. "
        "Java 8/11/17, Spring Boot, Microservices, REST APIs, AWS, Docker, Kubernetes, "
        "Angular, React. H1B visa, South Plainfield NJ. "
        "Seeking C2C/Corp-to-Corp contract at $90/hr. Available immediately."
    ),
}

TITLE_EXCLUDE = re.compile(
    r'\b(lead|architect|principal|director|manager|vp|chief)\b', re.IGNORECASE
)
W2_TITLE = re.compile(r'\bw2\b', re.IGNORECASE)
JAVA_KW   = re.compile(
    r'\b(java|spring|j2ee|microservice|full.?stack|jvm|hibernate|maven|gradle|rest.?api)\b',
    re.IGNORECASE
)

# ─────────────────────────────────────────────────────────────────────────────
# AppleScript Chrome helpers (same pattern as Dice batch scripts)
# ─────────────────────────────────────────────────────────────────────────────

def run_applescript(script):
    try:
        r = subprocess.run(["osascript", "-e", script],
                           capture_output=True, text=True, timeout=30)
        return r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return "", "timeout"
    except Exception as e:
        return "", str(e)


def chrome_navigate(url):
    script = f'''
    tell application "Google Chrome"
        set URL of active tab of window 1 to "{url}"
    end tell'''
    return run_applescript(script)


def chrome_get_url():
    out, _ = run_applescript('''
    tell application "Google Chrome"
        return URL of active tab of window 1
    end tell''')
    return out


def chrome_js(js):
    escaped = js.replace("\\", "\\\\").replace('"', '\\"')
    out, err = run_applescript(f'''
    tell application "Google Chrome"
        return execute active tab of window 1 javascript "{escaped}"
    end tell''')
    if err and "error" in err.lower():
        logger.debug(f"JS err: {err[:80]}")
    return out


def chrome_body():
    return chrome_js("document.body.innerText.substring(0, 8000)")


# ─────────────────────────────────────────────────────────────────────────────
# State helpers (cooldown tracking for resume forms)
# ─────────────────────────────────────────────────────────────────────────────

def load_state():
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {"last_submitted": {}}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def cooldown_ok(state, name, cooldown_days):
    """Return True if enough time has passed since last submission."""
    if cooldown_days == 0:
        return True
    last = state["last_submitted"].get(name)
    if not last:
        return True
    last_dt = datetime.fromisoformat(last)
    return datetime.now() - last_dt >= timedelta(days=cooldown_days)


def mark_submitted(state, name):
    state["last_submitted"][name] = datetime.now().isoformat()
    save_state(state)


# ─────────────────────────────────────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def already_applied_db(conn, url):
    h = hashlib.sha256(f"guest:{url}".encode()).hexdigest()
    row = conn.execute("SELECT id FROM jobs WHERE dedup_hash=?", (h,)).fetchone()
    if not row:
        return False
    app = conn.execute("SELECT id FROM applications WHERE job_id=?", (row["id"],)).fetchone()
    return app is not None


def record_guest_apply(conn, site_name, job_title, company, url, status="submitted"):
    h = hashlib.sha256(f"guest:{url}".encode()).hexdigest()
    conn.execute("""
        INSERT OR IGNORE INTO jobs
          (source, title, company, location, job_type, url, apply_url, dedup_hash, match_score, status)
        VALUES ('vendor_guest', ?, ?, 'US', 'contract', ?, ?, ?, 75, 'applied')
    """, (job_title, company or site_name, url, url, h))
    conn.commit()
    row = conn.execute("SELECT id FROM jobs WHERE dedup_hash=?", (h,)).fetchone()
    if row:
        conn.execute("""
            INSERT OR IGNORE INTO applications
              (job_id, method, ats_platform, status)
            VALUES (?, 'guest_apply', ?, ?)
        """, (row["id"], site_name, status))
        conn.commit()


def update_state_json(applied_count):
    sf = PROJECT_ROOT / "data" / "state.json"
    try:
        s = json.loads(sf.read_text())
        s["total_applications"] = s.get("total_applications", 0) + applied_count
        s["last_run_at"] = datetime.now().isoformat()
        sf.write_text(json.dumps(s, indent=2))
        logger.info(f"state.json → total_applications = {s['total_applications']}")
    except Exception as e:
        logger.error(f"state.json update failed: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# JS form-fill helper (universal — works on most ATS / contact forms)
# ─────────────────────────────────────────────────────────────────────────────

def fill_form_js(message_override=None):
    msg = (message_override or PROFILE["summary"]).replace("'", "\\'")
    fn  = PROFILE["first_name"]
    ln  = PROFILE["last_name"]
    em  = PROFILE["email"]
    ph  = PROFILE["phone"]
    ph2 = PROFILE["phone_fmt"]
    loc = f"{PROFILE['city']}, {PROFILE['state']}"
    exp = PROFILE["experience"]
    rate= PROFILE["rate"]

    return f"""
    (function() {{
        var filled = 0;
        function setVal(el, val) {{
            try {{
                var ns = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value');
                if (ns) {{ ns.set.call(el, val); }}
                else {{ el.value = val; }}
                el.dispatchEvent(new Event('input',  {{bubbles:true}}));
                el.dispatchEvent(new Event('change', {{bubbles:true}}));
                el.dispatchEvent(new Event('blur',   {{bubbles:true}}));
                filled++;
            }} catch(e) {{}}
        }}
        function setTa(el, val) {{
            try {{
                var ns = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value');
                if (ns) {{ ns.set.call(el, val); }}
                else {{ el.value = val; }}
                el.dispatchEvent(new Event('input',  {{bubbles:true}}));
                el.dispatchEvent(new Event('change', {{bubbles:true}}));
                filled++;
            }} catch(e) {{}}
        }}

        var inputs = document.querySelectorAll('input:not([type=hidden]):not([type=checkbox]):not([type=radio]):not([type=file]):not([type=submit])');
        for (var inp of inputs) {{
            if (!inp.offsetParent) continue;
            if (inp.value && inp.value.trim()) continue;
            var id = ((inp.name||'')+(inp.placeholder||'')+(inp.getAttribute('aria-label')||'')+(inp.id||'')).toLowerCase();
            var val = '';
            if (/first|fname/.test(id))                          val = '{fn}';
            else if (/last|lname|surname/.test(id))              val = '{ln}';
            else if (/email|e-mail/.test(id))                    val = '{em}';
            else if (/phone|mobile|tel|cell/.test(id))           val = '{ph}';
            else if (/city|location/.test(id))                   val = '{loc}';
            else if (/zip|postal/.test(id))                      val = '{PROFILE["zip"]}';
            else if (/state/.test(id))                           val = '{PROFILE["state"]}';
            else if (/year|experience/.test(id))                 val = '{exp}';
            else if (/rate|salary|pay|compensation/.test(id))    val = '{rate}';
            else if (/title|position|role/.test(id))             val = 'Sr Java Full Stack Developer';
            else if (/company|employer|current/.test(id))        val = 'Independent Contractor';
            else if (/linkedin/.test(id))                        val = 'linkedin.com/in/vamsim';
            else if (/visa|auth|work.?auth/.test(id))            val = 'H1B';
            else if (/name/.test(id) && !val)                    val = '{fn} {ln}';
            if (val) setVal(inp, val);
        }}

        var areas = document.querySelectorAll('textarea');
        for (var ta of areas) {{
            if (!ta.offsetParent) continue;
            if (ta.value && ta.value.trim()) continue;
            setTa(ta, '{msg}');
        }}

        var sels = document.querySelectorAll('select');
        for (var sel of sels) {{
            if (!sel.offsetParent) continue;
            var sid = ((sel.name||'')+(sel.getAttribute('aria-label')||'')).toLowerCase();
            if (/state|province/.test(sid)) {{
                for (var opt of sel.options) {{
                    if (/^NJ$|new jersey/i.test(opt.text||opt.value)) {{
                        sel.value = opt.value;
                        sel.dispatchEvent(new Event('change',{{bubbles:true}}));
                        filled++; break;
                    }}
                }}
            }} else if (/visa|auth|work.?auth/.test(sid)) {{
                for (var opt of sel.options) {{
                    if (/yes|h1b|authorized/i.test(opt.text)) {{
                        sel.value = opt.value;
                        sel.dispatchEvent(new Event('change',{{bubbles:true}}));
                        filled++; break;
                    }}
                }}
            }} else if (/exp|year/.test(sid)) {{
                for (var opt of sel.options) {{
                    if (/9|10|11|12|13|14|15/.test(opt.text)) {{
                        sel.value = opt.value;
                        sel.dispatchEvent(new Event('change',{{bubbles:true}}));
                        filled++; break;
                    }}
                }}
            }}
        }}

        return 'filled:' + filled;
    }})()
    """


def click_submit_js():
    return """
    (function() {
        var btns = document.querySelectorAll('button, input[type=submit]');
        for (var b of btns) {
            if (!b.offsetParent) continue;
            if (b.disabled) continue;
            var txt = (b.textContent || b.value || '').trim().toLowerCase();
            if (txt.includes('submit') || txt.includes('apply') || txt === 'send'
                || txt.includes('join') || txt.includes('upload') || txt.includes('continue')) {
                b.scrollIntoView({block:'center'});
                b.click();
                return 'clicked:' + txt;
            }
        }
        // fallback — last visible button
        var allBtns = Array.from(document.querySelectorAll('button[type=submit],input[type=submit]'));
        var vis = allBtns.filter(b => b.offsetParent && !b.disabled);
        if (vis.length > 0) {
            vis[vis.length-1].scrollIntoView({block:'center'});
            vis[vis.length-1].click();
            return 'fallback_clicked';
        }
        return 'no_button';
    })()
    """


def check_success():
    return chrome_js("""
    (function() {
        var body = document.body.innerText.toLowerCase();
        var url  = window.location.href.toLowerCase();
        var success_words = ['thank you','thanks','success','submitted','received',
                             'we will','we\\'ll','confirmation','application sent',
                             'your resume','your information'];
        for (var w of success_words) {
            if (body.includes(w)) return 'success:body';
        }
        if (url.includes('thank') || url.includes('success') || url.includes('confirm'))
            return 'success:url';
        var conf = document.querySelector('.gform_confirmation_message,.gform-confirmation-message,.confirmation,.success-message,[class*=success],[class*=confirm]');
        if (conf && conf.offsetParent) return 'success:selector';
        return 'uncertain';
    })()
    """)


# ─────────────────────────────────────────────────────────────────────────────
# ATS handlers — search for Java jobs and guest-apply to each listing
# ─────────────────────────────────────────────────────────────────────────────

def handle_ats_generic(site, conn):
    """
    Generic ATS handler:
    1. Navigate to search URL
    2. Try to fill search box with 'Java' and submit
    3. Extract job links
    4. For each eligible job, navigate and apply
    """
    name = site["name"]
    search_url = site["search_url"]
    applied = 0
    skipped = 0

    logger.info(f"  → Navigating: {search_url}")
    chrome_navigate(search_url)
    time.sleep(4)

    # Try to search for Java
    search_filled = chrome_js("""
    (function() {
        var inputs = document.querySelectorAll('input[type=text],input[type=search],input[name*=keyword i],input[placeholder*=keyword i],input[placeholder*=search i],input[placeholder*=job i]');
        for (var inp of inputs) {
            if (!inp.offsetParent) continue;
            inp.value = 'Java';
            inp.dispatchEvent(new Event('input',{bubbles:true}));
            inp.dispatchEvent(new Event('change',{bubbles:true}));
            // Try pressing Enter
            inp.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',keyCode:13,bubbles:true}));
            return 'searched';
        }
        return 'no_search_box';
    })()
    """)
    logger.info(f"  Search: {search_filled}")

    if search_filled == "searched":
        time.sleep(3)
        # Also try clicking a Search button
        chrome_js("""
        (function() {
            var btns = document.querySelectorAll('button,input[type=submit]');
            for (var b of btns) {
                var txt = (b.textContent||b.value||'').trim().toLowerCase();
                if (txt.includes('search') || txt.includes('find') || txt === 'go') {
                    b.click(); return 'clicked';
                }
            }
        })()
        """)
        time.sleep(3)

    # Extract job links from the page
    body = chrome_body()
    current_url = chrome_get_url()

    # Get all job-like links
    job_links_raw = chrome_js("""
    (function() {
        var links = document.querySelectorAll('a[href]');
        var out = [];
        for (var a of links) {
            var href = a.href;
            var txt  = a.textContent.trim();
            if (!href || !txt) continue;
            // Job listing links typically have /job/ /position/ /opening/ /career/ /apply/ in path
            if (/\\/job[\\/s]|\\/position|\\/opening|\\/career|\\/apply|\\/requisition|\\/id=|jobid|job_id/i.test(href)) {
                out.push(href + '||' + txt.substring(0,80));
            }
        }
        return out.join('\\n');
    })()
    """)

    job_entries = [l for l in (job_links_raw or "").split("\n") if "||" in l]
    logger.info(f"  Found {len(job_entries)} potential job links on {name}")

    if not job_entries:
        logger.info(f"  No job links found on {name} — page may require JS rendering or login")
        return 0, 1

    for entry in job_entries[:20]:  # cap at 20 per site per cycle
        parts = entry.split("||", 1)
        job_url = parts[0].strip()
        job_title = parts[1].strip() if len(parts) > 1 else "Java Developer"

        # Filter by title
        if W2_TITLE.search(job_title):
            continue
        if TITLE_EXCLUDE.search(job_title):
            continue
        if not JAVA_KW.search(job_title):
            # Title doesn't mention Java — but could still be relevant; check body later
            pass

        # Skip if already applied
        if already_applied_db(conn, job_url):
            logger.info(f"  ALREADY APPLIED: {job_title[:50]}")
            continue

        logger.info(f"  Applying to: {job_title[:55]} @ {job_url[:60]}")
        chrome_navigate(job_url)
        time.sleep(4)

        # Check description for C2C exclusions
        desc = chrome_js("""
        (function() {
            var el = document.querySelector('[class*=description],[class*=details],[class*=content],[id*=description]');
            return el ? el.innerText.substring(0,2000).toLowerCase() : document.body.innerText.substring(0,2000).toLowerCase();
        })()
        """)

        c2c_exclusions = ["w2 only","no c2c","no h1b","citizens only","gc only","no corp","w-2 only","only w2"]
        if any(p in (desc or "") for p in c2c_exclusions):
            logger.info(f"  SKIP: C2C exclusion in description")
            skipped += 1
            continue

        # Look for an Apply button
        apply_clicked = chrome_js("""
        (function() {
            var btns = document.querySelectorAll('a,button');
            for (var b of btns) {
                var txt = b.textContent.trim().toLowerCase();
                if (txt === 'apply' || txt === 'apply now' || txt === 'apply for this job'
                    || txt === 'apply online' || txt.includes('quick apply')) {
                    b.scrollIntoView({block:'center'});
                    b.click();
                    return 'apply_clicked:' + txt;
                }
            }
            return 'no_apply_btn';
        })()
        """)
        logger.info(f"  Apply btn: {apply_clicked}")

        if "no_apply_btn" in apply_clicked:
            # Maybe this IS the apply page already — try to fill form directly
            pass

        time.sleep(3)

        # Fill form
        fill_result = chrome_js(fill_form_js())
        logger.info(f"  Fill: {fill_result}")
        time.sleep(1)

        # Submit
        sub = chrome_js(click_submit_js())
        logger.info(f"  Submit: {sub}")
        time.sleep(4)

        outcome = check_success()
        if "success" in outcome:
            logger.info(f"  ✓ APPLIED: {job_title[:55]}")
            record_guest_apply(conn, name, job_title, name, job_url)
            applied += 1
        else:
            logger.info(f"  ? UNCERTAIN ({outcome}): {job_title[:50]}")
            # Still record as attempted
            record_guest_apply(conn, name, job_title, name, job_url, status="uncertain")

        time.sleep(2)

    return applied, skipped


# ─────────────────────────────────────────────────────────────────────────────
# Resume form handler — submit once per cooldown period
# ─────────────────────────────────────────────────────────────────────────────

def handle_resume_form(site, conn, state):
    name = site["name"]
    form_url = site["form_url"]
    cooldown = site.get("cooldown_days", 7)

    if not cooldown_ok(state, name, cooldown):
        logger.info(f"  COOLDOWN: {name} — submitted within last {cooldown} days, skipping")
        return 0

    logger.info(f"  → Navigating: {form_url}")
    chrome_navigate(form_url)
    time.sleep(4)

    # Check for CAPTCHA
    cap = chrome_js("""
    (function() {
        if (document.querySelector('.g-recaptcha,iframe[src*=recaptcha],iframe[src*=hcaptcha],.h-captcha'))
            return 'captcha';
        return 'ok';
    })()
    """)
    if cap == "captcha":
        logger.info(f"  SKIP: CAPTCHA detected on {name}")
        return 0

    # Fill form
    fill_result = chrome_js(fill_form_js())
    logger.info(f"  Fill: {fill_result}")
    time.sleep(1)

    # Try to find file upload and set resume path
    upload_result = chrome_js(f"""
    (function() {{
        var inputs = document.querySelectorAll('input[type=file]');
        for (var inp of inputs) {{
            try {{
                // Can't set file value via JS for security — mark it
                inp.setAttribute('data-resume-needed', 'true');
                return 'file_input_found';
            }} catch(e) {{}}
        }}
        return 'no_file_input';
    }})()
    """)
    logger.info(f"  File input: {upload_result}")

    # Submit
    sub = chrome_js(click_submit_js())
    logger.info(f"  Submit: {sub}")
    time.sleep(4)

    outcome = check_success()
    if "success" in outcome:
        logger.info(f"  ✓ SUBMITTED: {name}")
        mark_submitted(state, name)
        record_guest_apply(conn, name, "Resume Submission", name, form_url)
        return 1
    else:
        logger.info(f"  ? UNCERTAIN ({outcome}): {name} — marking submitted to avoid loop")
        # Mark as submitted anyway to respect cooldown
        mark_submitted(state, name)
        record_guest_apply(conn, name, "Resume Submission", name, form_url, status="uncertain")
        return 0


# ─────────────────────────────────────────────────────────────────────────────
# Specialized ATS handlers
# ─────────────────────────────────────────────────────────────────────────────

def handle_workable(site, conn):
    """Workable ATS — clean JSON API, predictable apply flow."""
    name = site["name"]
    search_url = site["search_url"]
    applied = 0

    logger.info(f"  → Workable: {search_url}")
    chrome_navigate(search_url)
    time.sleep(4)

    # Workable exposes jobs as JSON via its API
    jobs_json = chrome_js("""
    (function() {
        var cards = document.querySelectorAll('[data-ui="job"] a, .jobs-list a, li[role=listitem] a');
        var out = [];
        for (var a of cards) {
            if (a.href && a.textContent.trim())
                out.push(a.href + '||' + a.textContent.trim().substring(0,80));
        }
        return out.join('\\n');
    })()
    """)

    entries = [l for l in (jobs_json or "").split("\n") if "||" in l]
    logger.info(f"  Workable: {len(entries)} jobs found")

    for entry in entries[:15]:
        parts = entry.split("||", 1)
        job_url = parts[0].strip()
        title   = parts[1].strip()

        if W2_TITLE.search(title) or TITLE_EXCLUDE.search(title):
            continue
        if not JAVA_KW.search(title):
            continue
        if already_applied_db(conn, job_url):
            continue

        logger.info(f"  Applying: {title[:50]}")
        chrome_navigate(job_url)
        time.sleep(4)

        # Workable has a clean "Apply for this job" button
        chrome_js("""
        (function() {
            var btn = document.querySelector('button[data-ui=application-cta],button[data-ui=apply-button]');
            if (!btn) {
                var btns = document.querySelectorAll('button,a');
                for (var b of btns) {
                    if (/apply/i.test(b.textContent.trim())) { btn = b; break; }
                }
            }
            if (btn) btn.click();
        })()
        """)
        time.sleep(3)

        fill_result = chrome_js(fill_form_js())
        logger.info(f"  Fill: {fill_result}")
        time.sleep(1)

        sub = chrome_js(click_submit_js())
        logger.info(f"  Submit: {sub}")
        time.sleep(4)

        outcome = check_success()
        if "success" in outcome:
            logger.info(f"  ✓ APPLIED: {title}")
            record_guest_apply(conn, name, title, name, job_url)
            applied += 1

        time.sleep(2)

    return applied, 0


def handle_smartsearch(site, conn):
    """SmartSearch Online ATS — adhocjobsearch.asp pattern."""
    name = site["name"]
    search_url = site["search_url"]
    applied = 0

    # SmartSearch search URL takes keyword as query param
    search_with_keyword = search_url + ("&" if "?" in search_url else "?") + "keywords=Java+Spring+Boot"
    logger.info(f"  → SmartSearch: {search_with_keyword}")
    chrome_navigate(search_with_keyword)
    time.sleep(4)

    # SmartSearch lists jobs in table rows with apply links
    entries_raw = chrome_js("""
    (function() {
        var rows = document.querySelectorAll('tr, .job-result, .jobResult, .job-listing');
        var out = [];
        for (var row of rows) {
            var link = row.querySelector('a[href*=jobId],a[href*=job_id],a[href*=position],a[href*=apply]');
            if (link) {
                var title = link.textContent.trim() || row.textContent.trim().substring(0,60);
                out.push(link.href + '||' + title.substring(0,80));
            }
        }
        return out.join('\\n');
    })()
    """)

    entries = [l for l in (entries_raw or "").split("\n") if "||" in l]
    logger.info(f"  SmartSearch: {len(entries)} listings")

    for entry in entries[:15]:
        parts = entry.split("||", 1)
        job_url = parts[0].strip()
        title   = parts[1].strip()

        if W2_TITLE.search(title) or TITLE_EXCLUDE.search(title):
            continue
        if already_applied_db(conn, job_url):
            continue

        logger.info(f"  Applying: {title[:50]}")
        chrome_navigate(job_url)
        time.sleep(4)

        fill_result = chrome_js(fill_form_js())
        logger.info(f"  Fill: {fill_result}")
        time.sleep(1)

        sub = chrome_js(click_submit_js())
        logger.info(f"  Submit: {sub}")
        time.sleep(4)

        outcome = check_success()
        if "success" in outcome:
            logger.info(f"  ✓ APPLIED: {title}")
            record_guest_apply(conn, name, title, name, job_url)
            applied += 1

        time.sleep(2)

    return applied, 0


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    sites  = json.loads(SITES_FILE.read_text())
    state  = load_state()
    conn   = get_db()

    logger.info("=" * 60)
    logger.info("Guest Apply Batch — No-Login Vendor Sites")
    logger.info(f"Sites: {len(sites)} | Resume: {RESUME_PATH.name}")
    logger.info("=" * 60)

    total_applied  = 0
    total_skipped  = 0
    total_cooldown = 0
    results = []

    for site in sites:
        name     = site["name"]
        stype    = site["type"]
        logger.info(f"\n{'─'*50}")
        logger.info(f"[{stype.upper()}] {name}")

        try:
            if stype == "resume_form":
                n = handle_resume_form(site, conn, state)
                if n == 0 and not cooldown_ok(state, name, site.get("cooldown_days", 7)):
                    total_cooldown += 1
                    results.append({"site": name, "result": "cooldown"})
                else:
                    total_applied += n
                    results.append({"site": name, "result": "submitted" if n > 0 else "uncertain"})

            elif stype == "ats_workable":
                a, s = handle_workable(site, conn)
                total_applied += a; total_skipped += s
                results.append({"site": name, "result": f"applied={a} skipped={s}"})

            elif stype == "ats_smartsearch":
                a, s = handle_smartsearch(site, conn)
                total_applied += a; total_skipped += s
                results.append({"site": name, "result": f"applied={a} skipped={s}"})

            else:
                # Generic ATS handler (CATSOne, WorkBright, TopEchelon, Aviontego, Applicant Manager)
                a, s = handle_ats_generic(site, conn)
                total_applied += a; total_skipped += s
                results.append({"site": name, "result": f"applied={a} skipped={s}"})

        except Exception as e:
            logger.error(f"  FATAL [{name}]: {e}")
            results.append({"site": name, "result": f"error: {e}"})

        time.sleep(2)

    # Final report
    logger.info("\n" + "=" * 60)
    logger.info("FINAL REPORT — GUEST APPLY BATCH")
    logger.info("=" * 60)
    logger.info(f"Total applied:       {total_applied}")
    logger.info(f"Total skipped:       {total_skipped}")
    logger.info(f"Cooldown (skipped):  {total_cooldown}")
    logger.info("")
    logger.info("SITE RESULTS:")
    for r in results:
        logger.info(f"  {r['site']:35s} → {r['result']}")
    logger.info(f"\nLog: {log_file}")

    conn.close()

    if total_applied > 0:
        update_state_json(total_applied)

    # Save results
    results_file = LOG_DIR / "guest_apply_results.json"
    results_file.write_text(json.dumps({
        "run_at": datetime.now().isoformat(),
        "applied": total_applied,
        "skipped": total_skipped,
        "cooldown": total_cooldown,
        "results": results,
    }, indent=2))
    logger.info(f"Results: {results_file}")


if __name__ == "__main__":
    main()
