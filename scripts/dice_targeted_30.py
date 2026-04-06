#!/usr/bin/env python3
"""
Dice Targeted Apply — 30 specific Java contract jobs via CDP.
Connects to an already-running Chrome instance with remote debugging.

Usage:
    python3 scripts/dice_targeted_30.py
    python3 scripts/dice_targeted_30.py --port 9222
"""
import argparse
import asyncio
import hashlib
import json
import logging
import os
import random
import sqlite3
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "jobs.db"
LOG_DIR = PROJECT_ROOT / "data" / "logs"

sys.path.insert(0, str(PROJECT_ROOT))

from playwright.async_api import async_playwright, TimeoutError as PwTimeout

LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"dice_targeted30_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file),
    ],
)
logger = logging.getLogger("dice_targeted30")

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
    "pitch": (
        "Sr Java Full Stack Developer with 9 years experience in Java 17, "
        "Spring Boot, Microservices, REST APIs, AWS, Docker, Kubernetes, "
        "Angular, React. Available for C2C contract at $90/hr. "
        "H1B visa — authorized to work, no sponsorship needed. "
        "South Plainfield NJ, open to remote/hybrid."
    ),
}

# ---------------------------------------------------------------------------
# Target jobs — all 30
# ---------------------------------------------------------------------------
TARGET_JOBS = [
    {"url": "https://www.dice.com/job-detail/5932f762-4796-4c4e-849a-a66b493d1ac3", "title": "Java Developer", "company": "TSR Consulting"},
    {"url": "https://www.dice.com/job-detail/d6c4cc17-99a9-4181-9717-fef3afc950c0", "title": "Senior Java Developer Curam", "company": "Maxpath"},
    {"url": "https://www.dice.com/job-detail/4ede3bb4-e5f5-4be9-9810-565c48796283", "title": "Java Developer Front Office", "company": "Brains Workgroup"},
    {"url": "https://www.dice.com/job-detail/5b190c45-6435-44bc-81e9-2636774110db", "title": "Java eTrading Consultant", "company": "Brains Workgroup"},
    {"url": "https://www.dice.com/job-detail/e2ddf9d6-e985-402d-9fd7-c6e54bf6cb17", "title": "Java Production Support", "company": "Resource Point"},
    {"url": "https://www.dice.com/job-detail/b082680a-e848-4c55-b602-32c1dab43e0a", "title": "Java / Angular Developer", "company": "Vector Consulting"},
    {"url": "https://www.dice.com/job-detail/582d6313-d4d8-46e5-86c6-bf1adf92b0bf", "title": "Java Curam Developer", "company": "Vector Consulting"},
    {"url": "https://www.dice.com/job-detail/51d671ca-6834-481a-8d41-a41fc17f003c", "title": "FileNet Java Developer", "company": "Javen Technologies"},
    {"url": "https://www.dice.com/job-detail/b20fdc48-06e1-4fa9-938e-8b69b5b8a2f9", "title": "Software Engineering Core Java", "company": "BCforward"},
    {"url": "https://www.dice.com/job-detail/bec46618-559f-415d-a1af-976e44138a7f", "title": "Curam V6/7/8 Developer", "company": "Chandra Technologies"},
    {"url": "https://www.dice.com/job-detail/5e52607c-18a1-416b-a79d-f07f483ed5f4", "title": "Senior AWS/Java/ETL Developer", "company": "Chandra Technologies"},
    {"url": "https://www.dice.com/job-detail/8a72fba6-d782-4592-8c48-0db750d751d5", "title": "Java Angular Developer", "company": "PETADATA"},
    {"url": "https://www.dice.com/job-detail/37b5f769-00c9-40c1-996d-0891ee438dbf", "title": "Java Full Stack Developer", "company": "Javen Technologies"},
    {"url": "https://www.dice.com/job-detail/044fc55b-e6e9-4d38-9f93-bb0dafbc9a7e", "title": "Java/J2EE Specialist", "company": "Gov Services Hub"},
    {"url": "https://www.dice.com/job-detail/e1bee2d7-5906-4e76-803b-4e2c02219099", "title": "Sr Java Developer NJ", "company": "PamTen Inc"},
    {"url": "https://www.dice.com/job-detail/332de34c-f23d-4901-abd0-3dd887cc8f3c", "title": "Java Software Engineer", "company": "Dexian DISYS"},
    {"url": "https://www.dice.com/job-detail/c64a8da3-8195-4d28-a2f8-db0a564e5f41", "title": "Azure Java Developer", "company": "Alltech Consulting"},
    {"url": "https://www.dice.com/job-detail/d0beda8b-6f2b-4dc7-b1fa-eecfaeede9e2", "title": "Senior Java with DevOps Micronaut", "company": "LEO DOES IT"},
    {"url": "https://www.dice.com/job-detail/e636eca4-6660-4c54-9b77-d9a2cf3181d8", "title": "Senior Software Engineer", "company": "Oraapps Inc"},
    {"url": "https://www.dice.com/job-detail/938463ea-2133-4a68-b555-2832008a1f5d", "title": "Sr. Software Engineer Payment", "company": "WB Solutions"},
    {"url": "https://www.dice.com/job-detail/ee93fb34-b410-4834-9295-815e234cbbda", "title": "Java Developer", "company": "Innova Solutions"},
    {"url": "https://www.dice.com/job-detail/0200161e-f171-4371-ab20-36890456c540", "title": "Java Developer", "company": "Global Soft Systems"},
    {"url": "https://www.dice.com/job-detail/e35265a6-e9d1-4288-b32a-2e76b1932716", "title": "Senior Software Engineer", "company": "LOGICEXCELL"},
    {"url": "https://www.dice.com/job-detail/958c5dd7-d472-4bd3-a6db-7750682d9bf7", "title": "Senior Software Engineer Java AWS", "company": "Liberty Personnel"},
    {"url": "https://www.dice.com/job-detail/fd78c863-de6d-4546-bb49-2496f40e6b92", "title": "Full Stack Java Developer", "company": "Hirekeyz"},
    {"url": "https://www.dice.com/job-detail/4fb55ddc-d6e7-4eae-9cf7-83afaeba5a30", "title": "Full Stack Senior Software Engineer", "company": "Compunnel"},
    {"url": "https://www.dice.com/job-detail/c2e8f3ff-826a-4f14-9b9c-0b6dc3164be9", "title": "Senior Software Engineer", "company": "Compunnel"},
    {"url": "https://www.dice.com/job-detail/b5107576-4371-4ea6-9b43-bd5a3bf60b8f", "title": "Senior Software Engineer", "company": "INSPYR Solutions"},
    {"url": "https://www.dice.com/job-detail/613c82820a32afa46c658c8ad34ca17c", "title": "Senior Software Engineer", "company": "AIT Global"},
    {"url": "https://www.dice.com/job-detail/0f5cdb40-2b20-45d8-b511-014455b094a6", "title": "Software Engineer II", "company": "GDH"},
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
        (job_id, method, "dice_easy_apply", status, error_msg),
    )
    conn.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
    conn.commit()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def human_delay(lo=1.0, hi=3.0):
    await asyncio.sleep(random.uniform(lo, hi))

def uuid_from_url(url):
    if "/job-detail/" in url:
        return url.split("/job-detail/")[-1].split("?")[0]
    return ""

def has_c2c_exclusion(text):
    t = text.lower()
    return any(phrase in t for phrase in C2C_EXCLUSION_PHRASES)

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
            itype = (await inp.get_attribute("type") or "").lower()
            field_id = name + placeholder + label

            if any(k in field_id for k in ["first", "fname"]):
                await inp.fill(PROFILE["first_name"])
            elif any(k in field_id for k in ["last", "lname", "surname"]):
                await inp.fill(PROFILE["last_name"])
            elif any(k in field_id for k in ["email", "e-mail"]) or itype == "email":
                await inp.fill(PROFILE["email"])
            elif any(k in field_id for k in ["phone", "mobile", "tel"]) or itype == "tel":
                await inp.fill(PROFILE["phone"])
            elif any(k in field_id for k in ["city", "location", "address"]):
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

    # Handle radio buttons
    await _handle_radios(page)

    # Handle checkboxes (agree/terms)
    await _handle_checkboxes(page)

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
                    matching = [ot for ot in option_texts if opt_text in ot]
                    if matching:
                        await sel.select_option(label=matching[0])
                        break
            elif any(k in field_id for k in ["sponsor"]):
                matching = [ot for ot in option_texts if "no" == ot.strip()]
                if matching:
                    await sel.select_option(label=matching[0])
        except Exception:
            continue


async def _handle_radios(page):
    """Handle Yes/No radio buttons for work authorization and sponsorship."""
    try:
        await page.evaluate("""
            (() => {
                document.querySelectorAll('label, div[role="radiogroup"], fieldset').forEach(el => {
                    const text = el.textContent.toLowerCase();
                    if (text.includes('authorized') || text.includes('legally') || text.includes('right to work') || text.includes('work authorization')) {
                        const yesRadio = el.querySelector('input[type="radio"][value="Yes"], input[type="radio"][value="yes"], input[type="radio"][value="true"]');
                        if (yesRadio && !yesRadio.checked) yesRadio.click();
                    }
                    if (text.includes('sponsor')) {
                        const noRadio = el.querySelector('input[type="radio"][value="No"], input[type="radio"][value="no"], input[type="radio"][value="false"]');
                        if (noRadio && !noRadio.checked) noRadio.click();
                    }
                });
            })()
        """)
    except Exception:
        pass


async def _handle_checkboxes(page):
    """Check agree/terms/consent checkboxes."""
    try:
        await page.evaluate("""
            (() => {
                document.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                    if (cb.checked) return;
                    const parent = cb.closest('label, div, fieldset');
                    const text = parent ? parent.textContent.toLowerCase() : '';
                    if (text.includes('agree') || text.includes('terms') || text.includes('consent') || text.includes('certify') || text.includes('confirm')) {
                        cb.click();
                    }
                });
            })()
        """)
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Apply logic
# ---------------------------------------------------------------------------

async def check_job_detail(page, job):
    """Navigate to job detail, check for C2C exclusions and apply eligibility."""
    url = job["url"]
    logger.info(f"  Loading: {url}")
    await page.goto(url, wait_until="domcontentloaded")
    await human_delay(3, 5)

    # Check ONLY the main job description div
    desc_text = await page.evaluate("""
        (() => {
            const selectors = [
                '[data-cy="jobDescription"]',
                '[data-testid="jobDescription"]',
                '#jobDescription',
                '.job-description',
                '[class*="jobDescription"]',
                '[class*="job-description"]',
            ];
            for (const sel of selectors) {
                const el = document.querySelector(sel);
                if (el) return el.innerText;
            }
            const main = document.querySelector('main') || document.querySelector('[role="main"]');
            if (main) return main.innerText;
            return document.body.innerText;
        })()
    """)

    if has_c2c_exclusion(desc_text):
        return {"eligible": False, "reason": "W2 only / no C2C in description"}

    # Check if already applied — look for "Applied" text/badge anywhere on page
    already = await page.evaluate("""
        (() => {
            const body = document.body.innerText;
            // Check for applied badge text near top
            const top = body.substring(0, 2000).toLowerCase();
            if (top.includes('you applied') || top.includes('already applied')) return true;

            // Check for "Applied" badge elements
            const badges = document.querySelectorAll('[data-testid="applied-badge"], .applied-badge');
            if (badges.length > 0) return true;

            // Check apply button web component shadow DOM for "Applied" text
            const wc = document.querySelector('apply-button-wc');
            if (wc && wc.shadowRoot) {
                const text = wc.shadowRoot.textContent || '';
                if (text.includes('Applied')) return true;
            }

            // Check for anchor links that say "Applied"
            const links = document.querySelectorAll('a[href*="job-applications"]');
            for (const l of links) {
                if (l.textContent.trim() === 'Applied') return true;
            }

            return false;
        })()
    """)
    if already:
        return {"eligible": False, "reason": "Already applied"}

    # Check for Apply button/link — Dice uses EITHER:
    #  1. <apply-button-wc> web component
    #  2. <a href="/job-applications/UUID/wizard"> with text "Apply" or "Easy Apply"
    #  3. <button> with text "Apply" or "Easy Apply"
    apply_info = await page.evaluate("""
        (() => {
            // Check for <a> link to wizard
            const links = document.querySelectorAll('a[href*="job-applications"]');
            for (const l of links) {
                const text = l.textContent.trim().toLowerCase();
                if (text.includes('apply')) {
                    return {found: true, type: 'link', href: l.href, text: l.textContent.trim()};
                }
            }

            // Check for apply-button-wc web component
            const wc = document.querySelector('apply-button-wc');
            if (wc) {
                return {found: true, type: 'wc'};
            }

            // Check for button with Apply text
            const btns = document.querySelectorAll('button');
            for (const b of btns) {
                const text = b.textContent.trim().toLowerCase();
                if (text.includes('easy apply') || text === 'apply') {
                    return {found: true, type: 'button', text: b.textContent.trim()};
                }
            }

            return {found: false};
        })()
    """)

    if not apply_info["found"]:
        return {"eligible": False, "reason": "No apply button found"}

    logger.info(f"  Apply button found: {apply_info.get('type', '?')} - {apply_info.get('text', '')}")
    return {"eligible": True, "apply_info": apply_info}


async def apply_via_wizard(page, job, apply_info=None):
    """Apply using Dice Easy Apply wizard. Navigates directly to wizard URL."""
    uuid = uuid_from_url(job["url"])
    wizard_url = f"https://www.dice.com/job-applications/{uuid}/wizard"

    try:
        # Strategy: Navigate directly to the wizard URL — this is the most reliable approach
        # since the Apply button (whether <a>, <button>, or web component) all lead here
        logger.info(f"  Navigating to wizard: {wizard_url}")
        await page.goto(wizard_url, wait_until="domcontentloaded")
        await human_delay(3, 5)

        current_url = page.url
        if "/dashboard/login" in current_url or "/login" in current_url:
            logger.error("  Redirected to login")
            return False, "login_required"

        body_text = await page.evaluate("document.body.innerText.toLowerCase()")
        if "already applied" in body_text or "previously applied" in body_text:
            return False, "already_applied"

        # Step through wizard (up to 8 steps)
        for step in range(8):
            await human_delay(1.5, 2.5)

            # Get current page state
            page_state = await page.evaluate("""
                (() => {
                    const body = document.body.innerText.toLowerCase();
                    const result = {
                        hasSubmit: false,
                        hasNext: false,
                        hasApply: false,
                        isSuccess: false,
                        bodySnippet: body.substring(0, 300),
                    };

                    // Check for success
                    const successWords = ['application submitted', 'successfully applied', 'thank you for applying', 'application complete', "you've applied", 'application sent'];
                    result.isSuccess = successWords.some(w => body.includes(w));

                    // Check buttons
                    document.querySelectorAll('button').forEach(b => {
                        const text = b.textContent.trim().toLowerCase();
                        const visible = b.offsetParent !== null;
                        if (!visible) return;
                        if (text.includes('submit')) result.hasSubmit = true;
                        if (text === 'next' || text === 'continue') result.hasNext = true;
                        if (text.includes('apply')) result.hasApply = true;
                    });

                    return result;
                })()
            """)

            if page_state["isSuccess"]:
                logger.info(f"  Step {step+1}: Application submitted!")
                return True, "submitted"

            # Fill form fields
            await _fill_form_fields(page)

            # Click Submit if available
            if page_state["hasSubmit"]:
                submit_btn = await page.query_selector(
                    'button:has-text("Submit"):visible'
                )
                if submit_btn:
                    logger.info(f"  Step {step+1}: Clicking Submit")
                    await submit_btn.scroll_into_view_if_needed()
                    await human_delay(0.5, 1)
                    await submit_btn.click()
                    await human_delay(3, 5)

                    # Check success after submit
                    body = await page.evaluate("document.body.innerText.toLowerCase()")
                    if any(w in body for w in ["submitted", "thank you", "success", "application received", "applied"]):
                        logger.info("  Submission confirmed!")
                        return True, "submitted"
                    # If URL changed away from wizard, assume success
                    if "wizard" not in page.url and "job-applications" not in page.url:
                        return True, "submitted"
                    return True, "submitted"

            # Click Next/Continue if available
            if page_state["hasNext"]:
                next_btn = await page.query_selector(
                    'button:has-text("Next"):visible, button:has-text("Continue"):visible'
                )
                if next_btn:
                    logger.info(f"  Step {step+1}: Clicking Next")
                    await next_btn.scroll_into_view_if_needed()
                    await human_delay(0.5, 1)
                    await next_btn.click()
                    await human_delay(2, 3)
                    continue

            # Click Apply if available (initial wizard step)
            if page_state["hasApply"]:
                apply_btn = await page.query_selector(
                    'button:has-text("Apply"):visible'
                )
                if apply_btn:
                    logger.info(f"  Step {step+1}: Clicking Apply")
                    await apply_btn.scroll_into_view_if_needed()
                    await human_delay(0.5, 1)
                    await apply_btn.click()
                    await human_delay(2, 3)
                    continue

            logger.warning(f"  No actionable button at step {step+1}")
            logger.info(f"  Page snippet: {page_state['bodySnippet'][:150]}")
            try:
                ss_path = LOG_DIR / f"stuck_{uuid[:8]}_step{step}.png"
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
        return False, str(e)[:120]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9222, help="CDP port")
    args = parser.parse_args()

    CDP_PORT = args.port
    conn = get_db()
    results = []
    stats = {"total": len(TARGET_JOBS), "applied": 0, "skipped": 0, "failed": 0, "already": 0}

    logger.info("=" * 60)
    logger.info("Dice Targeted Apply — 30 Java Contract Jobs")
    logger.info(f"Profile: {PROFILE['first_name']} {PROFILE['last_name']}")
    logger.info(f"Target: {len(TARGET_JOBS)} jobs | CDP port: {CDP_PORT}")
    logger.info(f"Log: {log_file}")
    logger.info("=" * 60)

    async with async_playwright() as p:
        try:
            logger.info(f"Connecting to Chrome via CDP on port {CDP_PORT}...")
            browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP_PORT}")
            logger.info("Connected!")

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
                logger.warning("NOT logged into Dice! Please log in at the Chrome window...")
                logger.info("Waiting 120s for manual login...")
                for i in range(60):
                    await asyncio.sleep(2)
                    if "/login" not in page.url:
                        logger.info("Login detected!")
                        break
                    if i % 15 == 0 and i > 0:
                        logger.info(f"  Waiting... ({i*2}s)")
                else:
                    logger.error("Login timeout. Exiting.")
                    return
            else:
                logger.info("Logged into Dice!")

            # Process each job
            for i, job in enumerate(TARGET_JOBS):
                title = job["title"]
                company = job["company"]
                url = job["url"]
                uuid = uuid_from_url(url)

                logger.info(f"\n{'='*55}")
                logger.info(f"[{i+1}/{len(TARGET_JOBS)}] {title} @ {company}")

                # Check job detail page
                detail = await check_job_detail(page, job)
                if not detail["eligible"]:
                    reason = detail["reason"]
                    logger.info(f"  SKIP: {reason}")
                    if "already" in reason.lower():
                        stats["already"] += 1
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

                apply_info = detail.get("apply_info")

                # Insert into DB
                dhash = dedup_hash("dice", uuid)
                job_id = insert_job(
                    conn, external_id=uuid, source="dice", title=title,
                    company=company, location="",
                    job_type="contract", url=url, status="matched",
                    dedup_hash=dhash,
                )

                # Apply via wizard
                success, status_msg = await apply_via_wizard(page, job, apply_info)

                if success:
                    record_application(conn, job_id, "dice_easy_apply", "submitted")
                    stats["applied"] += 1
                    logger.info(f"  >>> APPLIED #{stats['applied']}: {title} @ {company}")
                    results.append({
                        "url": url, "title": title, "company": company,
                        "result": "applied"
                    })
                    try:
                        ss_path = LOG_DIR / f"applied_{uuid[:8]}.png"
                        await page.screenshot(path=str(ss_path))
                    except Exception:
                        pass
                else:
                    if status_msg == "already_applied":
                        stats["already"] += 1
                        logger.info(f"  Already applied (wizard)")
                        results.append({
                            "url": url, "title": title, "company": company,
                            "result": "already_applied", "reason": "wizard"
                        })
                    elif status_msg == "login_required":
                        stats["failed"] += 1
                        logger.error("  SESSION EXPIRED - stopping")
                        results.append({
                            "url": url, "title": title, "company": company,
                            "result": "failed", "reason": "login expired"
                        })
                        break
                    else:
                        record_application(conn, job_id, "dice_easy_apply", "failed", status_msg)
                        stats["failed"] += 1
                        logger.info(f"  FAILED: {status_msg}")
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
    logger.info(f"Total jobs:      {stats['total']}")
    logger.info(f"Applied:         {stats['applied']}")
    logger.info(f"Already applied: {stats['already']}")
    logger.info(f"Skipped (W2):    {stats['skipped']}")
    logger.info(f"Failed:          {stats['failed']}")
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

    # Save results JSON
    results_file = LOG_DIR / f"dice_30_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, "w") as f:
        json.dump({"stats": stats, "results": results}, f, indent=2)
    logger.info(f"Results JSON: {results_file}")


if __name__ == "__main__":
    asyncio.run(main())
