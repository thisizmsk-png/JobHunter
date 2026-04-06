#!/usr/bin/env python3
"""
Vendor Apply With Resume — Playwright-based form filler that can upload resume.
Targets vendor contact/apply forms that require a resume file.

Usage:
    python3 scripts/vendor_apply_with_resume.py
"""

import sqlite3
import time
from pathlib import Path

RESUME_PATH = str(Path(__file__).parent.parent / "assets" / "Vamsi_M Sr. Java Full Stack Developer.docx")

PROFILE = {
    "first_name": "Vamsi",
    "last_name": "M",
    "full_name": "Vamsi M",
    "email": "vamsim.java@gmail.com",
    "phone": "9293410298",
    "phone_formatted": "(929) 341-0298",
    "city": "South Plainfield",
    "state": "NJ",
    "zip": "07080",
    "title": "Sr Java Full Stack Developer",
    "experience": "9",
    "visa": "H1B",
    "summary": "Sr Java Full Stack Developer with 9 years of experience. Expert in Java, Spring Boot, Microservices, REST APIs, AWS, Docker, Kubernetes, Angular, and React. H1B visa holder, available for C2C/Corp-to-Corp contract positions.",
    "rate": "90",
    "company": "Independent Contractor",
    "linkedin": "linkedin.com/in/vamsim",
}

MSG = (
    f"Hi, I am {PROFILE['full_name']}, {PROFILE['title']} with {PROFILE['experience']} years of experience. "
    "Java, Spring Boot, Microservices, AWS, Angular/React. "
    f"H1B visa holder, {PROFILE['city']} {PROFILE['state']}. "
    f"Seeking C2C contract roles at ${PROFILE['rate']}/hr. Available immediately. "
    f"Contact: {PROFILE['email']} | {PROFILE['phone_formatted']}."
)

# Sites with required file upload — checked clean (no reCAPTCHA)
TARGETS = [
    {
        "name": "Mondo Staffing",
        "url": "https://mondo.com/contact/",
        "type": "mondo_custom",
        "fields": {
            "input_2": PROFILE["first_name"],
            "input_3": PROFILE["last_name"],
            "input_8": PROFILE["email"],
            "input_4": PROFILE["phone"],
        },
        "file_field": "input_29",
        "submit_id": "gform_submit_button_1",
        "success_selector": ".gform_confirmation_message,.gform-confirmation-message",
    },
    {
        "name": "Inceed",
        "url": "https://jobs.inceed.com/upload-resume/",
        "type": "gravity_forms",
        "fields": {
            "input_3": PROFILE["first_name"],
            "input_5": PROFILE["last_name"],
            "input_6": PROFILE["email"],
            "input_7": PROFILE["phone"],
            "input_8": PROFILE["city"],
            "input_9": PROFILE["state"],
        },
        "file_field": "input_11",
        "consent_checkbox": "input_10.1",
        "submit_id": "gform_submit_button_8",
        "success_selector": ".gform_confirmation_message,.gform-confirmation-message",
    },
    {
        "name": "Green Key Resources",
        "url": "https://greenkeyllc.com/contact-accounting-finance-client-team/",
        "type": "cf7",
        "fields": {
            "your-name": PROFILE["first_name"],
            "your-lastname": PROFILE["last_name"],
            "your-email": PROFILE["email"],
            "your-phone": PROFILE["phone"],
            "PracticeArea": "Information Technology",
            "message": MSG,
        },
        "file_field": "file-412",
        "submit_selector": ".wpcf7-submit",
        "success_selector": ".wpcf7-mail-sent-ok,.wpcf7-response-output",
    },
    {
        "name": "Team Bradley",
        "url": "https://teambradley.com/contact-us/",
        "type": "gravity_forms",
        "fields": {
            "input_4": "job seeker",  # radio — handled separately
            "input_1": PROFILE["full_name"],
            "input_5": PROFILE["company"],
            "input_2": PROFILE["email"],
            "input_3": PROFILE["phone"],
            "input_6": "Internet Search",
        },
        "radio_field": "input_4",
        "radio_value": "job seeker",
        "file_field": "",  # handled by GF custom upload
        "submit_id": "gform_submit_button_1",
        "success_selector": ".gform_confirmation_message",
    },
]


def fill_and_submit(page, target):
    """Fill form fields and upload resume."""
    name = target["name"]
    print(f"\n[{name}] Loading: {target['url']}")
    page.goto(target["url"], wait_until="domcontentloaded", timeout=20000)
    page.wait_for_timeout(1500)

    # Check for reCAPTCHA (abort if found)
    if page.locator("[data-sitekey], .g-recaptcha").count() > 0:
        print(f"  SKIP: reCAPTCHA detected")
        return False

    # Mondo-specific: select "I'm looking for a job" first to reveal conditional fields
    if target.get("type") == "mondo_custom":
        try:
            page.locator('#input_1_7').select_option("I'm looking for a job")
            page.wait_for_timeout(1500)
            print("  Mondo: selected 'I'm looking for a job'")
        except Exception as e:
            print(f"  Mondo select err: {e}")

    # Fill text/email/tel/select fields
    for field_name, value in target.get("fields", {}).items():
        try:
            sel = f'[name="{field_name}"]'
            all_els = page.locator(sel)
            if all_els.count() == 0:
                print(f"  NF: {field_name}")
                continue
            el = all_els.first
            tag = el.evaluate("el => el.tagName.toLowerCase()")
            input_type = el.evaluate("el => el.type || ''")
            is_visible = el.is_visible()
            if not is_visible:
                # Try scrolling into view then recheck
                try:
                    el.scroll_into_view_if_needed(timeout=3000)
                    is_visible = el.is_visible()
                except:
                    pass
            if not is_visible:
                print(f"  SKIP (hidden): {field_name}")
                continue
            if tag == "select":
                el.select_option(value)
            elif input_type == "radio":
                page.locator(f'[name="{field_name}"][value="{value}"]').check()
            elif input_type == "checkbox":
                el.check()
            else:
                el.fill(value)
            print(f"  OK: {field_name} = {str(value)[:30]}")
        except Exception as e:
            print(f"  ERR {field_name}: {e}")

    # Upload resume file
    file_field = target.get("file_field")
    if file_field:
        try:
            # Try named field first; if hidden, fall back to any visible file input
            named = page.locator(f'[name="{file_field}"]').first
            visible_type = named.evaluate("el => el.type") if named.count() > 0 else "hidden"
            if named.count() > 0 and visible_type != "hidden":
                named.set_input_files(RESUME_PATH)
                print(f"  UPLOAD: {RESUME_PATH.split('/')[-1]}")
            else:
                # GF custom upload — find any visible file input
                fallback = page.locator('input[type=file]').first
                if fallback.count() > 0:
                    fallback.set_input_files(RESUME_PATH)
                    print(f"  UPLOAD (fallback file input): {RESUME_PATH.split('/')[-1]}")
                else:
                    print(f"  NF file input: {file_field}")
            page.wait_for_timeout(1000)
        except Exception as e:
            print(f"  UPLOAD ERR: {e}")

    # Consent checkbox for Inceed (input_10.1)
    consent = target.get("consent_checkbox")
    if consent:
        try:
            page.locator(f'[name="{consent}"]').first.check()
            print(f"  CONSENT: checked {consent}")
        except Exception as e:
            print(f"  CONSENT ERR: {e}")

    # Submit
    submit_id = target.get("submit_id")
    submit_sel = target.get("submit_selector", "")
    try:
        if submit_id:
            page.locator(f"#{submit_id}").click()
        elif submit_sel:
            page.locator(submit_sel).first.click()
        else:
            page.locator("input[type=submit],button[type=submit]").first.click()
        page.wait_for_timeout(2500)
    except Exception as e:
        print(f"  SUBMIT ERR: {e}")
        return False

    # Check success
    success_sel = target.get("success_selector", "")
    if success_sel:
        try:
            conf = page.locator(success_sel).first
            if conf.is_visible():
                msg = conf.inner_text().strip()[:100]
                print(f"  SUCCESS: {msg}")
                return True
        except:
            pass

    # Check for validation errors
    err_sel = ".gform_validation_errors,.gfield_error,.wpcf7-not-valid-tip"
    try:
        errs = page.locator(err_sel)
        if errs.count() > 0:
            err_text = errs.first.inner_text().strip()[:80]
            print(f"  ERROR: {err_text}")
            return False
    except:
        pass

    # Check URL change
    final_url = page.url
    if final_url != target["url"] and ("thank" in final_url or "success" in final_url):
        print(f"  SUCCESS (redirect): {final_url}")
        return True

    print(f"  UNCERTAIN — check manually: {final_url}")
    return False


def log_to_db(name, url, success):
    if not success:
        return
    conn = sqlite3.connect("data/jobs.db")
    conn.execute(
        "INSERT OR IGNORE INTO jobs (source,title,company,location,job_type,url,apply_url,dedup_hash,match_score,status) "
        "VALUES ('vendor','Sr Java Full Stack Developer',?,?,?,'{}','{}',hex(randomblob(16)),80,'applied')".format(url, url),
        (name, "US", "Contract"),
    )
    job_id = conn.execute("SELECT id FROM jobs WHERE url=? ORDER BY id DESC LIMIT 1", (url,)).fetchone()
    if job_id:
        conn.execute(
            "INSERT INTO applications (job_id,method,ats_platform,status) VALUES (?,?,?,?)",
            (job_id[0], "vendor_form_resume", "gravity_forms", "submitted"),
        )
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM applications WHERE status='submitted'").fetchone()[0]
    conn.close()
    print(f"  DB: logged — total={count}")


def main():
    from playwright.sync_api import sync_playwright

    print(f"Resume: {RESUME_PATH}")
    print(f"Targets: {len(TARGETS)}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
        page = ctx.new_page()

        for target in TARGETS:
            try:
                success = fill_and_submit(page, target)
                log_to_db(target["name"], target["url"], success)
                time.sleep(1)
            except Exception as e:
                print(f"  FATAL [{target['name']}]: {e}")

        browser.close()

    print("\nDone.")


if __name__ == "__main__":
    main()
