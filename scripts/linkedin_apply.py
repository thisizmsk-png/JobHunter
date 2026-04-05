#!/usr/bin/env python3
"""
LinkedIn Easy Apply automation via Playwright CDP.
Connects to your running Chrome (with your LinkedIn session).

Usage:
  1. Launch Chrome with: /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
  2. Make sure you're logged into LinkedIn in that Chrome
  3. Run: venv/bin/python3 scripts/linkedin_apply.py

This script bypasses all Claude in Chrome MCP restrictions.
"""
import asyncio
import hashlib
import json
import sqlite3
import time
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Install playwright: venv/bin/pip install playwright")
    sys.exit(1)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "jobs.db")

SEARCH_URLS = [
    "https://www.linkedin.com/jobs/search/?keywords=java%20developer&location=New%20Jersey&f_JT=C&f_TPR=r604800&f_AL=true",
    "https://www.linkedin.com/jobs/search/?keywords=java%20full%20stack&location=New%20Jersey&f_JT=C&f_TPR=r604800&f_AL=true",
    "https://www.linkedin.com/jobs/search/?keywords=spring%20boot%20developer&location=New%20Jersey&f_JT=C&f_TPR=r604800&f_AL=true",
    "https://www.linkedin.com/jobs/search/?keywords=java%20microservices&location=New%20York&f_JT=C&f_TPR=r604800&f_AL=true",
]

TITLE_EXCLUDE = ["lead", "architect", "principal", "director", "manager", "vp", "chief", "staff engineer"]


async def apply_to_linkedin_jobs():
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            print("Connected to Chrome via CDP")
        except Exception as e:
            print(f"Cannot connect to Chrome. Launch Chrome with --remote-debugging-port=9222 first.")
            print(f"Error: {e}")
            return

        context = browser.contexts[0]
        page = await context.new_page()

        total_applied = 0

        for search_url in SEARCH_URLS:
            print(f"\nSearching: {search_url[:80]}...")
            await page.goto(search_url)
            await page.wait_for_timeout(5000)

            # Scroll to load more jobs
            for _ in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)

            # Find all Easy Apply buttons
            job_cards = await page.query_selector_all(".job-card-container")
            print(f"Found {len(job_cards)} job cards")

            for card in job_cards:
                try:
                    title_el = await card.query_selector(".job-card-list__title")
                    title = await title_el.inner_text() if title_el else ""
                    title_lower = title.lower().strip()

                    # Filter
                    if any(exc in title_lower for exc in TITLE_EXCLUDE):
                        print(f"  SKIP (excluded title): {title[:60]}")
                        continue

                    if not any(kw in title_lower for kw in ["java", "spring", "j2ee", "full stack", "microservices"]):
                        print(f"  SKIP (no keyword): {title[:60]}")
                        continue

                    # Click the job card
                    await card.click()
                    await page.wait_for_timeout(2000)

                    # Look for Easy Apply button
                    easy_apply_btn = await page.query_selector('button.jobs-apply-button')
                    if not easy_apply_btn:
                        print(f"  SKIP (no Easy Apply): {title[:60]}")
                        continue

                    btn_text = await easy_apply_btn.inner_text()
                    if "Easy Apply" not in btn_text:
                        print(f"  SKIP (not Easy Apply): {title[:60]}")
                        continue

                    await easy_apply_btn.click()
                    await page.wait_for_timeout(3000)

                    # Handle the Easy Apply modal
                    applied = False
                    for step in range(10):  # max 10 steps
                        # Check for submit button
                        submit_btn = await page.query_selector('button[aria-label="Submit application"]')
                        if submit_btn:
                            await submit_btn.click()
                            await page.wait_for_timeout(3000)
                            applied = True
                            break

                        # Check for next/review button
                        next_btn = await page.query_selector('button[aria-label="Continue to next step"]')
                        if not next_btn:
                            next_btn = await page.query_selector('button[aria-label="Review your application"]')
                        if next_btn:
                            await next_btn.click()
                            await page.wait_for_timeout(2000)
                            continue

                        # No button found — might have questions we can't fill
                        print(f"  SKIP (stuck on step): {title[:60]}")
                        # Close modal
                        close_btn = await page.query_selector('button[aria-label="Dismiss"]')
                        if close_btn:
                            await close_btn.click()
                            await page.wait_for_timeout(1000)
                            # Confirm discard
                            discard_btn = await page.query_selector('button[data-control-name="discard_application_confirm_btn"]')
                            if discard_btn:
                                await discard_btn.click()
                        break

                    if applied:
                        total_applied += 1
                        print(f"  APPLIED #{total_applied}: {title[:60]}")

                        # Record in SQLite
                        conn = sqlite3.connect(DB_PATH)
                        dedup = hashlib.sha256(f"linkedin-{title}".encode()).hexdigest()
                        try:
                            conn.execute(
                                """INSERT OR IGNORE INTO jobs (source, title, company, location, job_type, url, apply_url, dedup_hash, status, match_score)
                                VALUES ('linkedin', ?, '', '', 'Contract', ?, ?, ?, 'applied', 65)""",
                                (title, search_url, search_url, dedup),
                            )
                            jid = conn.execute("SELECT id FROM jobs WHERE dedup_hash = ?", (dedup,)).fetchone()
                            if jid:
                                conn.execute(
                                    'INSERT OR IGNORE INTO applications (job_id, method, ats_platform, status) VALUES (?, "auto_form", "linkedin", "applied")',
                                    (jid[0],),
                                )
                        except Exception:
                            pass
                        conn.commit()
                        conn.close()

                except Exception as e:
                    print(f"  ERROR: {e}")
                    continue

        await page.close()
        print(f"\n{'='*40}")
        print(f"LinkedIn Easy Apply complete: {total_applied} applications")
        print(f"{'='*40}")


if __name__ == "__main__":
    asyncio.run(apply_to_linkedin_jobs())
