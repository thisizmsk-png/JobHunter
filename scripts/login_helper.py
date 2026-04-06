#!/usr/bin/env python3
"""
Login helper — opens a persistent Playwright browser so you can log into job boards.
The session is saved to data/browser_profile/ and reused by mass_apply.py --standalone.

Usage: python3 scripts/login_helper.py [url]
Default URL: https://www.indeed.com
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROFILE_DIR = PROJECT_ROOT / "data" / "browser_profile"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

url = sys.argv[1] if len(sys.argv) > 1 else "https://www.indeed.com"

print(f"Opening persistent browser (profile: {PROFILE_DIR})")
print(f"Navigating to: {url}")
print("Log in, accept cookies, then close the browser window to save the session.")

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        str(PROFILE_DIR),
        headless=False,
        viewport={"width": 1400, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.goto(url, wait_until="domcontentloaded")

    print("\n>>> Browser is open. Log in and close the window when done. <<<\n")

    # Wait for the browser to be closed by the user
    try:
        page.wait_for_event("close", timeout=300000)  # 5 minutes
    except Exception:
        pass

    context.close()
    print("Session saved! You can now run mass_apply.py --standalone")
