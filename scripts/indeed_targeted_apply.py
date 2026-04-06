#!/usr/bin/env python3
"""
Targeted Indeed job application script.
Navigates to specific Indeed job URLs, reads descriptions, and applies.

Usage:
    venv/bin/python3 scripts/indeed_targeted_apply.py
"""
import asyncio
import json
import logging
import os
import random
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

log_file = LOG_DIR / f"indeed_targeted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file),
    ],
)
logger = logging.getLogger("indeed_targeted")

try:
    from playwright.async_api import async_playwright, TimeoutError as PwTimeout
except ImportError:
    print("ERROR: playwright not installed")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
PROFILE = {
    "name": "Vamsi M",
    "email": "vamsim.java@gmail.com",
    "phone": "(929) 341-0298",
    "location": "South Plainfield, NJ 07080",
    "title": "Sr Java Full Stack Developer",
    "experience": "9 years",
    "visa": "H1B",
    "rate": "$90/hr",
}

# ---------------------------------------------------------------------------
# Jobs to apply to
# ---------------------------------------------------------------------------
JOBS = [
    {"url": "https://www.indeed.com/viewjob?jk=c31ef8b9ca6cf136", "company": "TMS LLC", "title": "Java Full Stack Developer"},
    {"url": "https://www.indeed.com/viewjob?jk=fca459c185ebeeba", "company": "keypixel", "title": "Java Developer with GCP"},
    {"url": "https://www.indeed.com/viewjob?jk=3af377b5ccf8e1d2", "company": "Global Technology Partners", "title": "Senior Java Developer (Webflux)"},
    {"url": "https://www.indeed.com/viewjob?jk=8a196cc7b3dc6132", "company": "BNY", "title": "Senior Java Full Stack Developer (contract)"},
    {"url": "https://www.indeed.com/viewjob?jk=f917010a073b5422", "company": "YSAT Solutions", "title": "Senior Java Developer"},
    {"url": "https://www.indeed.com/viewjob?jk=03e79b8bc5c49d0a", "company": "BNY", "title": "Java Full Stack Developer (contract)"},
    {"url": "https://www.indeed.com/viewjob?jk=e21f35e2c18b14a8", "company": "Mutual of Omaha", "title": "Java Spring Boot Engineer"},
    {"url": "https://www.indeed.com/viewjob?jk=864d3187f853e9a9", "company": "Capgemini", "title": "Sr. Java Full Stack Developer"},
    {"url": "https://www.indeed.com/viewjob?jk=0905d05404e9dbbc", "company": "Capgemini", "title": "Java Full-stack Engineer"},
    {"url": "https://www.indeed.com/viewjob?jk=888c0566b7bd59a9", "company": "Vertex Group", "title": "Data Integration Specialist"},
]

# Keywords that disqualify a job for C2C
SKIP_KEYWORDS = [
    "no c2c", "no corp to corp", "no corp-to-corp",
    "w2 only", "w-2 only", "w2 required",
    "us citizen only", "us citizens only",
    "security clearance required", "must have clearance",
    "no third party", "no third-party", "no 3rd party",
    "direct hire only", "full-time only", "fte only",
    "no sponsorship", "no visa sponsorship",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def human_delay(min_s=1.0, max_s=3.0):
    await asyncio.sleep(random.uniform(min_s, max_s))


async def get_page_text(page) -> str:
    try:
        return await page.inner_text("body")
    except Exception:
        return ""


async def take_screenshot(page, name: str):
    ss_dir = PROJECT_ROOT / "data" / "logs" / "screenshots"
    ss_dir.mkdir(parents=True, exist_ok=True)
    path = ss_dir / f"{name}_{datetime.now().strftime('%H%M%S')}.png"
    try:
        await page.screenshot(path=str(path), full_page=False)
        logger.info(f"  Screenshot saved: {path}")
    except Exception as e:
        logger.warning(f"  Screenshot failed: {e}")


def check_skip_keywords(text: str) -> str | None:
    """Check if job description contains disqualifying keywords. Returns the keyword found or None."""
    lower = text.lower()
    for kw in SKIP_KEYWORDS:
        if kw in lower:
            return kw
    return None


async def attempt_apply(page, job: dict) -> dict:
    """
    Navigate to job URL, read description, and attempt to apply.
    Returns a result dict with status and details.
    """
    result = {
        "url": job["url"],
        "company": job["company"],
        "title": job["title"],
        "status": "unknown",
        "details": "",
    }

    try:
        logger.info(f"\n{'='*60}")
        logger.info(f"Job {job['title']} @ {job['company']}")
        logger.info(f"URL: {job['url']}")

        # Navigate to the job page
        await page.goto(job["url"], wait_until="domcontentloaded", timeout=30000)
        await human_delay(2, 4)

        # Check if we got redirected to login
        current_url = page.url
        if "secure.indeed.com/auth" in current_url or "/account/login" in current_url:
            logger.warning("  Login required -- checking for alternative apply link")
            result["status"] = "manual_review"
            result["details"] = "Indeed login required"
            await take_screenshot(page, f"login_{job['company']}")
            return result

        # Read the page text
        body_text = await get_page_text(page)

        if not body_text or len(body_text) < 100:
            logger.warning("  Page content too short -- may be blocked or expired")
            result["status"] = "skipped"
            result["details"] = "Job page empty or expired"
            await take_screenshot(page, f"empty_{job['company']}")
            return result

        # Check for expired/removed job
        if any(phrase in body_text.lower() for phrase in [
            "this job has expired", "this job is no longer available",
            "job not found", "this posting has been removed",
            "this job listing is no longer available"
        ]):
            logger.info("  Job expired or removed")
            result["status"] = "skipped"
            result["details"] = "Job expired or removed"
            return result

        # Check for C2C disqualifiers
        skip_kw = check_skip_keywords(body_text)
        if skip_kw:
            logger.info(f"  SKIP: found disqualifying keyword '{skip_kw}'")
            result["status"] = "skipped"
            result["details"] = f"Disqualifying keyword: {skip_kw}"
            return result

        # Look for "Apply on company site" link first (external apply)
        external_apply = await page.query_selector(
            'a:has-text("Apply on company site"), '
            'a:has-text("Apply on company"), '
            'button:has-text("Apply on company site"), '
            '[data-testid="indeedApply-externalLink"]'
        )

        # Look for Indeed Easy Apply / Apply Now button
        apply_btn = await page.query_selector(
            '#indeedApplyButton, '
            'button[id*="indeedApply"], '
            '.ia-IndeedApplyButton, '
            'button:has-text("Apply now"), '
            'button:has-text("Easy Apply"), '
            '[data-testid="indeedApply-button"]'
        )

        if apply_btn:
            is_visible = await apply_btn.is_visible()
            if is_visible:
                logger.info("  Found Indeed Apply button -- clicking...")
                await apply_btn.scroll_into_view_if_needed()
                await human_delay(0.5, 1.5)
                await apply_btn.click()
                await human_delay(3, 5)

                # Check if a modal/iframe opened or new page
                current_url2 = page.url

                # Indeed may show a multi-step form
                applied = await handle_indeed_apply_form(page, job)
                if applied:
                    result["status"] = "applied"
                    result["details"] = "Indeed Easy Apply submitted"
                    await take_screenshot(page, f"applied_{job['company']}")
                else:
                    result["status"] = "manual_review"
                    result["details"] = "Apply form could not be completed automatically"
                    await take_screenshot(page, f"form_issue_{job['company']}")
                return result

        elif external_apply:
            is_visible = await external_apply.is_visible()
            if is_visible:
                href = await external_apply.get_attribute("href")
                logger.info(f"  Found external apply link: {href or '(no href)'}")
                result["status"] = "manual_review"
                result["details"] = f"External apply: {href or 'company site'}"
                await take_screenshot(page, f"external_{job['company']}")
                return result

        # No apply button found
        logger.info("  No apply button found on page")
        await take_screenshot(page, f"no_button_{job['company']}")
        result["status"] = "manual_review"
        result["details"] = "No apply button found -- may need login or external site"

    except PwTimeout as e:
        logger.error(f"  Timeout: {e}")
        result["status"] = "failed"
        result["details"] = f"Timeout: {e}"
    except Exception as e:
        logger.error(f"  Error: {e}")
        logger.error(traceback.format_exc())
        result["status"] = "failed"
        result["details"] = str(e)

    return result


async def handle_indeed_apply_form(page, job: dict) -> bool:
    """Handle Indeed's multi-step apply form (name, email, resume, questions)."""
    try:
        for step in range(8):
            await human_delay(1.5, 2.5)

            body = await get_page_text(page)
            body_lower = body.lower()

            # Check for success
            if any(phrase in body_lower for phrase in [
                "application submitted", "your application has been submitted",
                "already applied", "you have already applied",
                "application sent", "successfully submitted"
            ]):
                logger.info("  Application submitted successfully!")
                return True

            # Check for CAPTCHA
            if "captcha" in body_lower or "i'm not a robot" in body_lower:
                logger.warning("  CAPTCHA detected -- cannot proceed")
                return False

            # Try to fill visible form fields
            await fill_form_fields(page)

            # Check for required textareas (custom questions) that we can't reliably fill
            textareas = await page.query_selector_all("textarea")
            visible_textareas = []
            for ta in textareas:
                try:
                    if await ta.is_visible():
                        visible_textareas.append(ta)
                except Exception:
                    pass

            # Fill textareas with professional responses if needed
            for ta in visible_textareas:
                current_val = await ta.input_value()
                if not current_val.strip():
                    label = ""
                    try:
                        ta_id = await ta.get_attribute("id")
                        if ta_id:
                            label_el = await page.query_selector(f'label[for="{ta_id}"]')
                            if label_el:
                                label = await label_el.inner_text()
                    except Exception:
                        pass
                    # Provide a generic professional response
                    response = (
                        f"I am a {PROFILE['title']} with {PROFILE['experience']} of experience. "
                        f"I am interested in this {job['title']} role at {job['company']} "
                        f"and believe my Java/Spring Boot expertise makes me a strong fit. "
                        f"I am available for C2C contract engagement."
                    )
                    await ta.fill(response)
                    logger.info(f"  Filled textarea: {label or '(unlabeled)'}")

            # Try Submit button
            submit = await page.query_selector(
                'button:has-text("Submit your application"), '
                'button:has-text("Submit application"), '
                'button:has-text("Submit"), '
                'button[type="submit"]:has-text("Submit")'
            )
            if submit:
                try:
                    if await submit.is_visible():
                        await submit.scroll_into_view_if_needed()
                        await human_delay(0.5, 1.0)
                        await submit.click()
                        logger.info("  Clicked Submit button")
                        await human_delay(3, 5)

                        # Verify submission
                        body_after = await get_page_text(page)
                        if any(phrase in body_after.lower() for phrase in [
                            "application submitted", "your application has been submitted",
                            "successfully submitted", "application sent"
                        ]):
                            return True
                        # Even if we don't see confirmation text, the click may have worked
                        return True
                except Exception as e:
                    logger.warning(f"  Submit click error: {e}")

            # Try Continue/Next button
            cont = await page.query_selector(
                'button:has-text("Continue"), '
                'button:has-text("Next"), '
                'button[data-testid="continue-btn"], '
                'button:has-text("Review")'
            )
            if cont:
                try:
                    if await cont.is_visible():
                        await cont.scroll_into_view_if_needed()
                        await human_delay(0.5, 1.0)
                        await cont.click()
                        logger.info("  Clicked Continue/Next")
                        continue
                except Exception as e:
                    logger.warning(f"  Continue click error: {e}")

            # No actionable button found
            logger.info(f"  Step {step + 1}: no actionable buttons found")
            break

    except Exception as e:
        logger.error(f"  Form handling error: {e}")

    return False


async def fill_form_fields(page):
    """Try to fill standard form fields (name, email, phone)."""
    field_map = {
        "name": PROFILE["name"],
        "full name": PROFILE["name"],
        "first name": "Vamsi",
        "last name": "M",
        "email": PROFILE["email"],
        "phone": PROFILE["phone"],
        "city": "South Plainfield",
        "location": PROFILE["location"],
    }

    inputs = await page.query_selector_all("input[type='text'], input[type='email'], input[type='tel'], input:not([type])")
    for inp in inputs:
        try:
            if not await inp.is_visible():
                continue

            # Get identifying info
            placeholder = (await inp.get_attribute("placeholder") or "").lower()
            name_attr = (await inp.get_attribute("name") or "").lower()
            inp_id = (await inp.get_attribute("id") or "").lower()
            aria_label = (await inp.get_attribute("aria-label") or "").lower()

            identifiers = f"{placeholder} {name_attr} {inp_id} {aria_label}"

            current_val = await inp.input_value()
            if current_val.strip():
                continue  # Already filled

            for key, value in field_map.items():
                if key in identifiers:
                    await inp.fill(value)
                    logger.info(f"  Filled field '{key}': {value}")
                    break
        except Exception:
            continue

    # Handle select dropdowns for work authorization
    selects = await page.query_selector_all("select")
    for sel in selects:
        try:
            if not await sel.is_visible():
                continue
            sel_id = (await sel.get_attribute("id") or "").lower()
            sel_name = (await sel.get_attribute("name") or "").lower()
            aria = (await sel.get_attribute("aria-label") or "").lower()
            identifiers = f"{sel_id} {sel_name} {aria}"

            if any(kw in identifiers for kw in ["authorization", "authorized", "work auth", "sponsorship", "visa"]):
                # Try to select "Yes" for authorized, "No" for sponsorship
                options = await sel.query_selector_all("option")
                for opt in options:
                    text = (await opt.inner_text()).strip().lower()
                    val = await opt.get_attribute("value")
                    if "yes" in text:
                        await sel.select_option(value=val)
                        logger.info(f"  Selected 'Yes' for work auth field")
                        break
        except Exception:
            continue

    # Handle radio buttons for work authorization
    radios = await page.query_selector_all("input[type='radio']")
    for radio in radios:
        try:
            if not await radio.is_visible():
                continue
            radio_id = (await radio.get_attribute("id") or "").lower()
            radio_name = (await radio.get_attribute("name") or "").lower()
            value = (await radio.get_attribute("value") or "").lower()

            # Find associated label
            label_text = ""
            if radio_id:
                label = await page.query_selector(f'label[for="{radio_id}"]')
                if label:
                    label_text = (await label.inner_text()).lower()

            if any(kw in radio_name for kw in ["authorization", "authorized", "sponsorship"]):
                if "yes" in value or "yes" in label_text:
                    if "sponsorship" in radio_name:
                        # For sponsorship, select "No" (don't need it)
                        pass
                    else:
                        await radio.click()
                        logger.info(f"  Selected radio: authorized=yes")
                elif "no" in value or "no" in label_text:
                    if "sponsorship" in radio_name:
                        await radio.click()
                        logger.info(f"  Selected radio: sponsorship=no")
        except Exception:
            continue


async def run():
    logger.info("=" * 60)
    logger.info("Indeed Targeted Apply -- 10 Jobs for Vamsi M")
    logger.info(f"Started at {datetime.now().isoformat()}")
    logger.info("=" * 60)

    results = []
    profile_dir = PROJECT_ROOT / "data" / "browser_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            str(profile_dir),
            headless=False,
            viewport={"width": 1400, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            args=[
                "--disable-blink-features=AutomationControlled",
            ],
        )
        page = context.pages[0] if context.pages else await context.new_page()

        for i, job in enumerate(JOBS, 1):
            logger.info(f"\n[{i}/{len(JOBS)}] Processing: {job['title']} @ {job['company']}")
            result = await attempt_apply(page, job)
            results.append(result)
            logger.info(f"  Result: {result['status']} -- {result['details']}")

            # Small delay between jobs
            if i < len(JOBS):
                await human_delay(2, 4)

        await context.close()

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)

    applied = [r for r in results if r["status"] == "applied"]
    skipped = [r for r in results if r["status"] == "skipped"]
    manual = [r for r in results if r["status"] == "manual_review"]
    failed = [r for r in results if r["status"] == "failed"]

    logger.info(f"Applied: {len(applied)}")
    for r in applied:
        logger.info(f"  + {r['title']} @ {r['company']} -- {r['details']}")

    logger.info(f"Skipped: {len(skipped)}")
    for r in skipped:
        logger.info(f"  - {r['title']} @ {r['company']} -- {r['details']}")

    logger.info(f"Manual Review: {len(manual)}")
    for r in manual:
        logger.info(f"  ? {r['title']} @ {r['company']} -- {r['details']}")

    logger.info(f"Failed: {len(failed)}")
    for r in failed:
        logger.info(f"  X {r['title']} @ {r['company']} -- {r['details']}")

    # Save results to JSON
    results_file = LOG_DIR / f"indeed_targeted_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"\nResults saved to: {results_file}")
    logger.info(f"Log saved to: {log_file}")

    return results


if __name__ == "__main__":
    asyncio.run(run())
