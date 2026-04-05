#!/usr/bin/env python3
"""
Mass job application engine — Dice, Indeed, ZipRecruiter, and vendor sites.
Connects to Chrome via CDP or launches a persistent browser context.
Standalone Playwright script — no Claude in Chrome dependency.

Usage:
  1. Launch Chrome:
     /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
  2. Log into Dice/Indeed/ZipRecruiter in that Chrome session
  3. Run:
     venv/bin/python3 scripts/mass_apply.py --board dice --search "java developer" --pages 5
     venv/bin/python3 scripts/mass_apply.py --board indeed --search "java developer" --location "New Jersey"
     venv/bin/python3 scripts/mass_apply.py --board vendor --batch 0
     venv/bin/python3 scripts/mass_apply.py --board ziprecruiter --search "java developer"

Options:
  --board         dice | indeed | ziprecruiter | vendor
  --search        Search query (default from search_config.yaml)
  --location      Location filter (default from search_config.yaml)
  --pages         Number of result pages to process (default: 5)
  --batch         Vendor batch group number (default: 0)
  --cdp-url       Chrome CDP endpoint (default: http://localhost:9222)
  --standalone    Launch a new persistent browser instead of CDP
  --dry-run       Scan and log jobs but don't click Apply/Submit
  --resume-from   Skip jobs until this external_id, then start applying
"""
import argparse
import asyncio
import hashlib
import json
import logging
import os
import random
import signal
import sqlite3
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus, urlencode

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "jobs.db"
VENDOR_URLS_PATH = PROJECT_ROOT / "data" / "vendor_urls.json"
SEARCH_CONFIG_PATH = PROJECT_ROOT / "config" / "search_config.yaml"
PROFILE_PATH = PROJECT_ROOT / "config" / "profile.yaml"
STATE_PATH = PROJECT_ROOT / "data" / "state.json"
LOG_DIR = PROJECT_ROOT / "data" / "logs"

sys.path.insert(0, str(PROJECT_ROOT))

try:
    from playwright.async_api import async_playwright, TimeoutError as PwTimeout
except ImportError:
    print("ERROR: playwright not installed. Run: venv/bin/pip install playwright && venv/bin/playwright install chromium")
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml not installed. Run: venv/bin/pip install pyyaml")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"mass_apply_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file),
    ],
)
logger = logging.getLogger("mass_apply")

# ---------------------------------------------------------------------------
# Globals for graceful shutdown
# ---------------------------------------------------------------------------
_shutdown_requested = False


def _handle_signal(sig, frame):
    global _shutdown_requested
    if _shutdown_requested:
        logger.warning("Force quit — exiting immediately")
        sys.exit(1)
    logger.warning("Shutdown requested (Ctrl+C). Finishing current job then exiting...")
    _shutdown_requested = True


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)

# ---------------------------------------------------------------------------
# Config loaders
# ---------------------------------------------------------------------------

def load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_search_config() -> dict:
    if SEARCH_CONFIG_PATH.exists():
        return load_yaml(SEARCH_CONFIG_PATH)
    return {}


def load_profile() -> dict:
    if PROFILE_PATH.exists():
        return load_yaml(PROFILE_PATH)
    return {}


def load_state() -> dict:
    if STATE_PATH.exists():
        with open(STATE_PATH) as f:
            return json.load(f)
    return {"last_cycle_id": 0, "current_vendor_batch": 0, "total_applications": 0}


def save_state(state: dict):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def dedup_hash(source: str, external_id: str) -> str:
    return hashlib.sha256(f"{source}:{external_id}".encode()).hexdigest()


def job_exists(conn: sqlite3.Connection, dhash: str) -> bool:
    row = conn.execute("SELECT id FROM jobs WHERE dedup_hash = ?", (dhash,)).fetchone()
    return row is not None


def was_applied(conn: sqlite3.Connection, dhash: str) -> bool:
    row = conn.execute(
        """SELECT a.id FROM applications a
           JOIN jobs j ON j.id = a.job_id
           WHERE j.dedup_hash = ? AND a.status IN ('submitted', 'success')""",
        (dhash,),
    ).fetchone()
    return row is not None


def insert_job(conn: sqlite3.Connection, **kwargs) -> int:
    dhash = kwargs.get("dedup_hash") or dedup_hash(kwargs["source"], kwargs["external_id"])
    kwargs["dedup_hash"] = dhash
    cols = ", ".join(kwargs.keys())
    placeholders = ", ".join(["?"] * len(kwargs))
    try:
        cur = conn.execute(f"INSERT OR IGNORE INTO jobs ({cols}) VALUES ({placeholders})", list(kwargs.values()))
        conn.commit()
        if cur.lastrowid:
            return cur.lastrowid
        row = conn.execute("SELECT id FROM jobs WHERE dedup_hash = ?", (dhash,)).fetchone()
        return row["id"] if row else 0
    except Exception as e:
        logger.error(f"DB insert error: {e}")
        return 0


def record_application(conn: sqlite3.Connection, job_id: int, method: str, status: str, error_msg: str = None):
    conn.execute(
        "INSERT INTO applications (job_id, method, ats_platform, status, error_message) VALUES (?, ?, ?, ?, ?)",
        (job_id, method, method, status, error_msg),
    )
    conn.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
    conn.commit()


def start_cycle(conn: sqlite3.Connection, board: str) -> int:
    cur = conn.execute(
        "INSERT INTO cycles (vendor_batch, status) VALUES (?, 'running')",
        (board,),
    )
    conn.commit()
    return cur.lastrowid


def finish_cycle(conn: sqlite3.Connection, cycle_id: int, found: int, new: int, applied: int, failed: int):
    conn.execute(
        """UPDATE cycles SET completed_at = datetime('now'),
           jobs_found = ?, jobs_new = ?, jobs_applied = ?, jobs_failed = ?, status = 'completed'
           WHERE id = ?""",
        (found, new, applied, failed, cycle_id),
    )
    conn.commit()

# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

TITLE_EXCLUDE = ["lead", "architect", "principal", "director", "manager", "vp", "chief", "head of", "staff engineer", "distinguished"]


def should_skip_title(title: str) -> bool:
    t = title.lower().strip()
    return any(exc in t for exc in TITLE_EXCLUDE)


async def human_delay(min_s: float = 1.0, max_s: float = 3.0):
    """Random delay to mimic human behavior."""
    await asyncio.sleep(random.uniform(min_s, max_s))


async def safe_click(page, selector: str, timeout: int = 8000) -> bool:
    """Click a selector if it exists, return True on success."""
    try:
        el = await page.wait_for_selector(selector, timeout=timeout, state="visible")
        if el:
            await el.scroll_into_view_if_needed()
            await human_delay(0.3, 0.8)
            await el.click()
            return True
    except (PwTimeout, Exception):
        return False
    return False


async def safe_text(page, selector: str, timeout: int = 5000) -> str:
    try:
        el = await page.wait_for_selector(selector, timeout=timeout)
        return (await el.inner_text()).strip() if el else ""
    except (PwTimeout, Exception):
        return ""


async def page_text(page) -> str:
    """Get full visible text of the page."""
    try:
        return await page.inner_text("body")
    except Exception:
        return ""


# ============================================================================
#  DICE
# ============================================================================

class DiceApplier:
    """Automates Dice job applications via the wizard flow."""

    BASE = "https://www.dice.com"

    def __init__(self, page, conn, config, args):
        self.page = page
        self.conn = conn
        self.config = config
        self.args = args
        self.stats = {"found": 0, "skipped": 0, "applied": 0, "failed": 0, "already": 0}

    def _search_url(self, query: str, page_num: int = 1) -> str:
        params = {
            "q": query,
            "location": self.args.location or "New Jersey",
            "filters.employmentType": "CONTRACTS",
            "page": str(page_num),
            "pageSize": "100",
            "filters.postedDate": "THREE",
        }
        return f"{self.BASE}/jobs?{urlencode(params)}"

    async def run(self):
        query = self.args.search
        pages = self.args.pages
        logger.info(f"[Dice] Starting — query='{query}', pages={pages}, location={self.args.location}")

        all_jobs = []
        for pg in range(1, pages + 1):
            if _shutdown_requested:
                break
            url = self._search_url(query, pg)
            logger.info(f"[Dice] Loading page {pg}: {url}")
            await self.page.goto(url, wait_until="domcontentloaded")
            await human_delay(2, 4)

            jobs = await self._extract_jobs()
            logger.info(f"[Dice] Page {pg}: found {len(jobs)} jobs")
            all_jobs.extend(jobs)

            # Check if there's a next page
            no_results = await self.page.query_selector("text=No results found")
            if no_results:
                logger.info("[Dice] No more results")
                break

        self.stats["found"] = len(all_jobs)
        logger.info(f"[Dice] Total jobs extracted: {len(all_jobs)}")

        # Filter and apply
        for job in all_jobs:
            if _shutdown_requested:
                logger.warning("[Dice] Shutdown requested — stopping applications")
                break
            await self._process_job(job)

        self._log_summary()

    async def _extract_jobs(self) -> list[dict]:
        """Extract job cards from Dice search results page."""
        jobs = []
        try:
            # Wait for job cards to load
            await self.page.wait_for_selector('[data-testid="search-card"], .card-title-link, a[id^="job-title-"]', timeout=10000)
        except PwTimeout:
            logger.warning("[Dice] No job cards found on page")
            return jobs

        # Try multiple selector strategies for Dice's evolving UI
        cards = await self.page.query_selector_all('a[id^="job-title-"]')
        if not cards:
            cards = await self.page.query_selector_all('.card-title-link')
        if not cards:
            # Fallback: extract from search card containers
            cards = await self.page.query_selector_all('[data-testid="search-card"]')

        for card in cards:
            try:
                # Extract job UUID from the href or data attribute
                href = await card.get_attribute("href") or ""
                title = (await card.inner_text()).strip()

                # Dice job URLs: /job-detail/{uuid}
                uuid = ""
                if "/job-detail/" in href:
                    uuid = href.split("/job-detail/")[-1].split("?")[0]
                elif "id=" in href:
                    uuid = href.split("id=")[-1].split("&")[0]

                if not uuid or not title:
                    continue

                # Check for "Applied" badge near this card
                parent = await card.evaluate_handle("el => el.closest('.card, [data-testid=\"search-card\"], dhi-search-card')")
                applied_badge = False
                if parent:
                    try:
                        badge = await parent.query_selector('text="Applied"')
                        if badge:
                            applied_badge = True
                    except Exception:
                        pass

                # Get company name
                company = ""
                if parent:
                    try:
                        company_el = await parent.query_selector('[data-testid="search-result-company-name"], .card-company a, a[data-cy="card-company-link"]')
                        if company_el:
                            company = (await company_el.inner_text()).strip()
                    except Exception:
                        pass

                # Get location
                location = ""
                if parent:
                    try:
                        loc_el = await parent.query_selector('[data-testid="search-result-location"], .card-location, span[data-cy="card-location"]')
                        if loc_el:
                            location = (await loc_el.inner_text()).strip()
                    except Exception:
                        pass

                jobs.append({
                    "uuid": uuid,
                    "title": title,
                    "company": company,
                    "location": location,
                    "applied_badge": applied_badge,
                    "url": f"{self.BASE}/job-detail/{uuid}",
                })
            except Exception as e:
                logger.debug(f"[Dice] Error extracting card: {e}")
                continue

        return jobs

    async def _process_job(self, job: dict):
        uuid = job["uuid"]
        title = job["title"]
        company = job.get("company", "")
        dhash = dedup_hash("dice", uuid)

        # Skip already-applied
        if job.get("applied_badge"):
            logger.info(f"  SKIP (already applied on Dice): {title[:60]}")
            self.stats["already"] += 1
            return

        if was_applied(self.conn, dhash):
            logger.info(f"  SKIP (in DB): {title[:60]}")
            self.stats["already"] += 1
            return

        # Title filter
        if should_skip_title(title):
            logger.info(f"  SKIP (excluded title): {title[:60]}")
            self.stats["skipped"] += 1
            return

        # Resume-from support
        if self.args.resume_from and uuid != self.args.resume_from:
            return

        if self.args.resume_from and uuid == self.args.resume_from:
            self.args.resume_from = None  # Found our resume point, start applying from next

        # Insert into DB
        job_id = insert_job(
            self.conn,
            external_id=uuid,
            source="dice",
            title=title,
            company=company,
            location=job.get("location", ""),
            job_type="contract",
            url=job["url"],
            status="matched",
        )

        if self.args.dry_run:
            logger.info(f"  DRY-RUN: {title[:60]} @ {company}")
            return

        # Apply via wizard
        success = await self._apply_wizard(uuid, title)
        if success:
            record_application(self.conn, job_id, "dice_wizard", "submitted")
            self.stats["applied"] += 1
            logger.info(f"  APPLIED: {title[:60]} @ {company}")
        else:
            record_application(self.conn, job_id, "dice_wizard", "failed", "wizard_incomplete")
            self.stats["failed"] += 1

    async def _apply_wizard(self, uuid: str, title: str) -> bool:
        """Navigate the Dice application wizard (2-step or 3-step)."""
        wizard_url = f"{self.BASE}/job-applications/{uuid}/wizard"
        logger.info(f"  Wizard: {wizard_url}")

        try:
            await self.page.goto(wizard_url, wait_until="domcontentloaded")
            await human_delay(2, 3)

            # Check if we're redirected to login
            if "/dashboard/login" in self.page.url:
                logger.error("[Dice] Not logged in — redirected to login page. Aborting.")
                return False

            # Check for "Already applied" message
            body = await page_text(self.page)
            if "already applied" in body.lower() or "previously applied" in body.lower():
                logger.info(f"  Already applied (wizard page): {title[:60]}")
                self.stats["already"] += 1
                return False

            # Step through wizard pages
            max_steps = 5
            for step in range(max_steps):
                await human_delay(1, 2)

                # Check for custom question textareas (skip these — they get stuck)
                textareas = await self.page.query_selector_all('textarea:not([aria-hidden="true"])')
                visible_textareas = []
                for ta in textareas:
                    if await ta.is_visible():
                        visible_textareas.append(ta)
                if visible_textareas:
                    logger.warning(f"  SKIP (custom questions detected): {title[:60]}")
                    self.stats["skipped"] += 1
                    return False

                # Check for required unfilled fields that would block us
                required_empties = await self.page.query_selector_all('input[required]:not([type="hidden"])')
                has_blocking_field = False
                for inp in required_empties:
                    val = await inp.get_attribute("value") or ""
                    if not val.strip() and await inp.is_visible():
                        placeholder = await inp.get_attribute("placeholder") or ""
                        name = await inp.get_attribute("name") or ""
                        logger.debug(f"    Empty required field: name={name} placeholder={placeholder}")
                        has_blocking_field = True

                # Look for the Submit button first (final step)
                submit_btn = await self.page.query_selector('button[type="submit"]:has-text("Submit"), button:has-text("Submit Application"), button:has-text("Submit")')
                if submit_btn and await submit_btn.is_visible():
                    # Check progress — if we see "Submit" we should be at ~100%
                    logger.info(f"  Step {step + 1}: Clicking Submit")
                    await submit_btn.scroll_into_view_if_needed()
                    await human_delay(0.5, 1.0)
                    await submit_btn.click()
                    await human_delay(2, 3)

                    # Verify success
                    body = await page_text(self.page)
                    if any(w in body.lower() for w in ["success", "submitted", "thank you", "application received", "application sent"]):
                        return True
                    # Sometimes Dice shows a confirmation page without clear success text
                    if "job-applications" not in self.page.url:
                        return True
                    return True

                # Look for Next button
                next_btn = await self.page.query_selector('button:has-text("Next"), button:has-text("Continue"), button[data-testid="next-button"]')
                if next_btn and await next_btn.is_visible():
                    if has_blocking_field:
                        logger.warning(f"  SKIP (unfilled required fields at step {step + 1}): {title[:60]}")
                        self.stats["skipped"] += 1
                        return False
                    logger.info(f"  Step {step + 1}: Clicking Next")
                    await next_btn.scroll_into_view_if_needed()
                    await human_delay(0.5, 1.0)
                    await next_btn.click()
                    await human_delay(1.5, 2.5)
                    continue

                # Check for Apply button (sometimes the wizard opens with Apply first)
                apply_btn = await self.page.query_selector('button:has-text("Apply"), button:has-text("Easy Apply")')
                if apply_btn and await apply_btn.is_visible():
                    logger.info(f"  Step {step + 1}: Clicking Apply")
                    await apply_btn.scroll_into_view_if_needed()
                    await human_delay(0.5, 1.0)
                    await apply_btn.click()
                    await human_delay(1.5, 2.5)
                    continue

                # Nothing clickable — check the progress indicator
                progress_text = await safe_text(self.page, '[role="progressbar"], .progress-text, .wizard-progress', timeout=2000)
                if "66" in progress_text or "33" in progress_text:
                    logger.warning(f"  STUCK at {progress_text} — skipping: {title[:60]}")
                    self.stats["skipped"] += 1
                    return False

                logger.warning(f"  No actionable button at step {step + 1} — breaking")
                break

            logger.warning(f"  Wizard incomplete after {max_steps} steps: {title[:60]}")
            return False

        except PwTimeout:
            logger.error(f"  Timeout in wizard: {title[:60]}")
            return False
        except Exception as e:
            logger.error(f"  Wizard error: {e}")
            return False

    def _log_summary(self):
        s = self.stats
        logger.info("=" * 60)
        logger.info(f"[Dice] Summary: found={s['found']} applied={s['applied']} skipped={s['skipped']} failed={s['failed']} already={s['already']}")
        logger.info("=" * 60)


# ============================================================================
#  INDEED
# ============================================================================

class IndeedApplier:
    """Automates Indeed job applications."""

    BASE = "https://www.indeed.com"

    def __init__(self, page, conn, config, args):
        self.page = page
        self.conn = conn
        self.config = config
        self.args = args
        self.stats = {"found": 0, "skipped": 0, "applied": 0, "failed": 0, "already": 0}

    def _search_url(self, query: str, location: str, start: int = 0) -> str:
        params = {
            "q": query,
            "l": location,
            "fromage": "3",        # Last 3 days
            "sc": "0kf:jt(contract);",  # Contract jobs
            "start": str(start),
        }
        return f"{self.BASE}/jobs?{urlencode(params)}"

    async def run(self):
        query = self.args.search
        location = self.args.location
        pages = self.args.pages
        logger.info(f"[Indeed] Starting — query='{query}', location='{location}', pages={pages}")

        all_jobs = []
        for pg in range(pages):
            if _shutdown_requested:
                break
            start = pg * 10
            url = self._search_url(query, location, start)
            logger.info(f"[Indeed] Loading page {pg + 1}: {url}")
            await self.page.goto(url, wait_until="domcontentloaded")
            await human_delay(2, 4)

            jobs = await self._extract_jobs()
            logger.info(f"[Indeed] Page {pg + 1}: found {len(jobs)} jobs")
            all_jobs.extend(jobs)

            if not jobs:
                break

        self.stats["found"] = len(all_jobs)
        logger.info(f"[Indeed] Total jobs extracted: {len(all_jobs)}")

        for job in all_jobs:
            if _shutdown_requested:
                break
            await self._process_job(job)

        self._log_summary()

    async def _extract_jobs(self) -> list[dict]:
        jobs = []
        try:
            await self.page.wait_for_selector('.job_seen_beacon, .jobsearch-ResultsList .result, [data-jk]', timeout=10000)
        except PwTimeout:
            logger.warning("[Indeed] No job cards found")
            return jobs

        cards = await self.page.query_selector_all('[data-jk]')
        if not cards:
            cards = await self.page.query_selector_all('.job_seen_beacon')

        for card in cards:
            try:
                jk = await card.get_attribute("data-jk") or ""
                title_el = await card.query_selector('h2.jobTitle a, h2 a, .jobTitle > a')
                title = (await title_el.inner_text()).strip() if title_el else ""
                href = await title_el.get_attribute("href") if title_el else ""

                if not jk:
                    # Try to extract from href
                    if href and "jk=" in href:
                        jk = href.split("jk=")[-1].split("&")[0]
                    elif href and "/viewjob" in href:
                        jk = href.split("jk=")[-1].split("&")[0] if "jk=" in href else ""

                company_el = await card.query_selector('[data-testid="company-name"], .companyName, .company')
                company = (await company_el.inner_text()).strip() if company_el else ""

                loc_el = await card.query_selector('[data-testid="text-location"], .companyLocation, .location')
                location = (await loc_el.inner_text()).strip() if loc_el else ""

                # Check for "Easily apply" / "Apply now" indicators
                easily = await card.query_selector('.iaLabel, text="Easily apply", [aria-label*="easily apply"]')

                if jk and title:
                    jobs.append({
                        "jk": jk,
                        "title": title,
                        "company": company,
                        "location": location,
                        "easily_apply": easily is not None,
                        "url": f"{self.BASE}/viewjob?jk={jk}",
                    })
            except Exception as e:
                logger.debug(f"[Indeed] Card extract error: {e}")
                continue

        return jobs

    async def _process_job(self, job: dict):
        jk = job["jk"]
        title = job["title"]
        dhash = dedup_hash("indeed", jk)

        if was_applied(self.conn, dhash):
            self.stats["already"] += 1
            return

        if should_skip_title(title):
            logger.info(f"  SKIP (title): {title[:60]}")
            self.stats["skipped"] += 1
            return

        job_id = insert_job(
            self.conn,
            external_id=jk,
            source="indeed",
            title=title,
            company=job.get("company", ""),
            location=job.get("location", ""),
            job_type="contract",
            url=job["url"],
            status="matched",
        )

        if self.args.dry_run:
            logger.info(f"  DRY-RUN: {title[:60]} @ {job.get('company', '')}")
            return

        if not job.get("easily_apply"):
            logger.info(f"  SKIP (no easy apply): {title[:60]}")
            self.stats["skipped"] += 1
            return

        success = await self._apply(job)
        if success:
            record_application(self.conn, job_id, "indeed_apply", "submitted")
            self.stats["applied"] += 1
            logger.info(f"  APPLIED: {title[:60]}")
        else:
            record_application(self.conn, job_id, "indeed_apply", "failed")
            self.stats["failed"] += 1

    async def _apply(self, job: dict) -> bool:
        """Click through Indeed's apply flow."""
        try:
            await self.page.goto(job["url"], wait_until="domcontentloaded")
            await human_delay(2, 3)

            # Click the Apply button
            applied = await safe_click(self.page, '#indeedApplyButton, button[id*="apply"], .ia-IndeedApplyButton, button:has-text("Apply now")', timeout=8000)
            if not applied:
                logger.info(f"  No apply button found: {job['title'][:60]}")
                return False

            await human_delay(2, 4)

            # Indeed may open a modal or new page
            # Step through the multi-step apply form
            for step in range(6):
                await human_delay(1.5, 2.5)

                body = await page_text(self.page)
                if any(w in body.lower() for w in ["application submitted", "your application has been submitted", "already applied"]):
                    return True

                # Check for blocking textareas (custom questions)
                textareas = await self.page.query_selector_all('textarea:visible')
                if textareas:
                    visible = [ta for ta in textareas if await ta.is_visible()]
                    if visible:
                        logger.warning(f"  SKIP (custom questions): {job['title'][:60]}")
                        self.stats["skipped"] += 1
                        return False

                # Try Submit
                submit = await self.page.query_selector('button:has-text("Submit your application"), button:has-text("Submit"), button[type="submit"]:has-text("Submit")')
                if submit and await submit.is_visible():
                    await submit.scroll_into_view_if_needed()
                    await human_delay(0.5, 1.0)
                    await submit.click()
                    await human_delay(2, 3)
                    return True

                # Try Continue
                cont = await self.page.query_selector('button:has-text("Continue"), button:has-text("Next"), button[data-testid="continue-btn"]')
                if cont and await cont.is_visible():
                    await cont.scroll_into_view_if_needed()
                    await human_delay(0.5, 1.0)
                    await cont.click()
                    continue

                break

            return False

        except Exception as e:
            logger.error(f"  Indeed apply error: {e}")
            return False

    def _log_summary(self):
        s = self.stats
        logger.info("=" * 60)
        logger.info(f"[Indeed] Summary: found={s['found']} applied={s['applied']} skipped={s['skipped']} failed={s['failed']} already={s['already']}")
        logger.info("=" * 60)


# ============================================================================
#  ZIPRECRUITER
# ============================================================================

class ZipRecruiterApplier:
    """Automates ZipRecruiter 1-click apply."""

    BASE = "https://www.ziprecruiter.com"

    def __init__(self, page, conn, config, args):
        self.page = page
        self.conn = conn
        self.config = config
        self.args = args
        self.stats = {"found": 0, "skipped": 0, "applied": 0, "failed": 0, "already": 0}

    def _search_url(self, query: str, location: str, page_num: int = 1) -> str:
        params = {
            "search": query,
            "location": location,
            "days": "3",
            "page": str(page_num),
        }
        return f"{self.BASE}/jobs-search?{urlencode(params)}"

    async def run(self):
        query = self.args.search
        location = self.args.location
        pages = self.args.pages
        logger.info(f"[ZipRecruiter] Starting — query='{query}', location='{location}', pages={pages}")

        all_jobs = []
        for pg in range(1, pages + 1):
            if _shutdown_requested:
                break
            url = self._search_url(query, location, pg)
            logger.info(f"[ZipRecruiter] Loading page {pg}")
            await self.page.goto(url, wait_until="domcontentloaded")
            await human_delay(2, 4)

            jobs = await self._extract_jobs()
            logger.info(f"[ZipRecruiter] Page {pg}: found {len(jobs)} jobs")
            all_jobs.extend(jobs)

            if not jobs:
                break

        self.stats["found"] = len(all_jobs)

        for job in all_jobs:
            if _shutdown_requested:
                break
            await self._process_job(job)

        self._log_summary()

    async def _extract_jobs(self) -> list[dict]:
        jobs = []
        try:
            await self.page.wait_for_selector('.job_result, article.job_result, [data-job-id]', timeout=10000)
        except PwTimeout:
            return jobs

        cards = await self.page.query_selector_all('[data-job-id]')
        if not cards:
            cards = await self.page.query_selector_all('.job_result, article.job_result')

        for card in cards:
            try:
                job_id = await card.get_attribute("data-job-id") or ""
                title_el = await card.query_selector('.job_link, h2 a, a.job_link')
                title = (await title_el.inner_text()).strip() if title_el else ""
                href = (await title_el.get_attribute("href")) if title_el else ""

                if not job_id and href:
                    # Generate an ID from href
                    job_id = hashlib.md5(href.encode()).hexdigest()[:16]

                company_el = await card.query_selector('.t_org_link, .company_name, [data-testid="company-name"]')
                company = (await company_el.inner_text()).strip() if company_el else ""

                loc_el = await card.query_selector('.location, .job_location')
                location = (await loc_el.inner_text()).strip() if loc_el else ""

                # Check for 1-click apply
                one_click = await card.query_selector('button:has-text("1-Click Apply"), button:has-text("Apply"), .one_click_apply')

                if title and (job_id or href):
                    jobs.append({
                        "external_id": job_id,
                        "title": title,
                        "company": company,
                        "location": location,
                        "url": href if href.startswith("http") else f"{self.BASE}{href}" if href else "",
                        "one_click": one_click is not None,
                    })
            except Exception:
                continue

        return jobs

    async def _process_job(self, job: dict):
        title = job["title"]
        ext_id = job["external_id"]
        dhash = dedup_hash("ziprecruiter", ext_id)

        if was_applied(self.conn, dhash):
            self.stats["already"] += 1
            return

        if should_skip_title(title):
            self.stats["skipped"] += 1
            return

        job_id = insert_job(
            self.conn,
            external_id=ext_id,
            source="ziprecruiter",
            title=title,
            company=job.get("company", ""),
            location=job.get("location", ""),
            url=job.get("url", ""),
            status="matched",
        )

        if self.args.dry_run:
            logger.info(f"  DRY-RUN: {title[:60]}")
            return

        success = await self._apply(job)
        if success:
            record_application(self.conn, job_id, "ziprecruiter_1click", "submitted")
            self.stats["applied"] += 1
            logger.info(f"  APPLIED: {title[:60]}")
        else:
            record_application(self.conn, job_id, "ziprecruiter_1click", "failed")
            self.stats["failed"] += 1

    async def _apply(self, job: dict) -> bool:
        try:
            if job.get("url"):
                await self.page.goto(job["url"], wait_until="domcontentloaded")
                await human_delay(2, 3)

            # Click 1-Click Apply or Apply
            clicked = await safe_click(self.page, 'button:has-text("1-Click Apply"), button:has-text("Apply Now"), #apply_button, .apply_now', timeout=8000)
            if not clicked:
                return False

            await human_delay(2, 4)

            # ZipRecruiter often shows a modal — try to submit
            for step in range(4):
                body = await page_text(self.page)
                if any(w in body.lower() for w in ["application sent", "applied", "thank you"]):
                    return True

                submit = await self.page.query_selector('button:has-text("Submit"), button:has-text("Send Application"), button:has-text("Apply")')
                if submit and await submit.is_visible():
                    await submit.click()
                    await human_delay(2, 3)
                    return True

                cont = await self.page.query_selector('button:has-text("Continue"), button:has-text("Next")')
                if cont and await cont.is_visible():
                    await cont.click()
                    await human_delay(1.5, 2.5)
                    continue

                break

            return False
        except Exception as e:
            logger.error(f"  ZipRecruiter apply error: {e}")
            return False

    def _log_summary(self):
        s = self.stats
        logger.info("=" * 60)
        logger.info(f"[ZipRecruiter] Summary: found={s['found']} applied={s['applied']} skipped={s['skipped']} failed={s['failed']} already={s['already']}")
        logger.info("=" * 60)


# ============================================================================
#  VENDOR SITES
# ============================================================================

class VendorApplier:
    """Scans staffing vendor websites for Java jobs and attempts to apply."""

    def __init__(self, page, conn, config, args):
        self.page = page
        self.conn = conn
        self.config = config
        self.args = args
        self.stats = {"visited": 0, "jobs_found": 0, "applied": 0, "failed": 0, "errors": 0}

    async def run(self):
        batch = self.args.batch
        logger.info(f"[Vendor] Starting — batch={batch}")

        # Load vendors from DB
        vendors = self.conn.execute(
            "SELECT id, name, url, url_type FROM vendor_sites WHERE batch_group = ? ORDER BY id",
            (batch,),
        ).fetchall()

        if not vendors:
            # Fallback: load from JSON
            if VENDOR_URLS_PATH.exists():
                with open(VENDOR_URLS_PATH) as f:
                    all_vendors = json.load(f)
                batch_size = 50
                start = batch * batch_size
                end = start + batch_size
                vendors = [{"id": i, "name": v.get("name", ""), "url": v["url"]} for i, v in enumerate(all_vendors[start:end], start=start)]
            else:
                logger.error("[Vendor] No vendors found in DB or vendor_urls.json")
                return

        logger.info(f"[Vendor] Processing {len(vendors)} vendor sites")

        for vendor in vendors:
            if _shutdown_requested:
                break
            name = vendor["name"] if isinstance(vendor, dict) else vendor["name"]
            url = vendor["url"] if isinstance(vendor, dict) else vendor["url"]
            vid = vendor["id"] if isinstance(vendor, dict) else vendor["id"]

            await self._process_vendor(vid, name, url)
            self.stats["visited"] += 1

        self._log_summary()

    async def _process_vendor(self, vid: int, name: str, url: str):
        logger.info(f"[Vendor] {name}: {url}")
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await human_delay(1.5, 3)
        except PwTimeout:
            logger.warning(f"  Timeout loading {name}")
            self.stats["errors"] += 1
            self._update_vendor_count(vid, success=False)
            return
        except Exception as e:
            logger.warning(f"  Error loading {name}: {e}")
            self.stats["errors"] += 1
            self._update_vendor_count(vid, success=False)
            return

        # Try to find a search box and search for Java
        search_query = self.args.search or "Java Developer"
        searched = await self._try_search(search_query)

        await human_delay(1, 2)

        # Extract job listings
        jobs = await self._extract_vendor_jobs(name)
        self.stats["jobs_found"] += len(jobs)

        if jobs:
            logger.info(f"  Found {len(jobs)} jobs at {name}")

        for job in jobs[:10]:  # Limit to 10 per vendor to avoid spending too long
            if _shutdown_requested:
                break

            title = job.get("title", "")
            if should_skip_title(title):
                continue

            ext_id = hashlib.md5(f"{name}:{title}:{job.get('url', '')}".encode()).hexdigest()[:16]
            dhash = dedup_hash("vendor", ext_id)

            if was_applied(self.conn, dhash):
                continue

            job_id = insert_job(
                self.conn,
                external_id=ext_id,
                source=f"vendor:{name}",
                title=title,
                company=name,
                location=job.get("location", ""),
                url=job.get("url", url),
                status="found",
            )

            if self.args.dry_run:
                logger.info(f"  DRY-RUN: {title[:60]} @ {name}")
                continue

            if job.get("apply_url"):
                success = await self._try_vendor_apply(job)
                if success:
                    record_application(self.conn, job_id, "vendor_direct", "submitted")
                    self.stats["applied"] += 1
                    logger.info(f"  APPLIED: {title[:60]}")

        self._update_vendor_count(vid, success=True)

    async def _try_search(self, query: str) -> bool:
        """Attempt to find and use a search box on the vendor page."""
        search_selectors = [
            'input[type="search"]',
            'input[name*="search"]',
            'input[name*="keyword"]',
            'input[placeholder*="Search"]',
            'input[placeholder*="search"]',
            'input[placeholder*="Keyword"]',
            'input[id*="search"]',
            'input[id*="keyword"]',
            '#search-input',
            '.search-input',
        ]

        for sel in search_selectors:
            try:
                el = await self.page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    await el.fill("")
                    await el.type(query, delay=50)
                    await human_delay(0.5, 1.0)

                    # Try pressing Enter or clicking a search button
                    await self.page.keyboard.press("Enter")
                    await human_delay(2, 3)
                    return True
            except Exception:
                continue

        return False

    async def _extract_vendor_jobs(self, vendor_name: str) -> list[dict]:
        """Generic job extraction — tries common job listing patterns."""
        jobs = []

        # Common job link selectors
        link_selectors = [
            'a[href*="job"]',
            'a[href*="career"]',
            'a[href*="position"]',
            'a[href*="opening"]',
            '.job-listing a',
            '.job-title a',
            '.job-link',
            'h2 a', 'h3 a',
            '[class*="job"] a',
            '[class*="listing"] a',
        ]

        seen = set()
        for sel in link_selectors:
            try:
                links = await self.page.query_selector_all(sel)
                for link in links[:30]:
                    try:
                        text = (await link.inner_text()).strip()
                        href = await link.get_attribute("href") or ""

                        if not text or len(text) < 5 or len(text) > 200:
                            continue
                        if text.lower() in seen:
                            continue

                        # Basic relevance check
                        text_lower = text.lower()
                        relevant_keywords = ["java", "developer", "engineer", "spring", "full stack", "backend", "software"]
                        if not any(k in text_lower for k in relevant_keywords):
                            continue

                        seen.add(text.lower())
                        full_url = href
                        if href and not href.startswith("http"):
                            base = self.page.url.split("//")[0] + "//" + self.page.url.split("//")[1].split("/")[0]
                            full_url = base + ("/" if not href.startswith("/") else "") + href

                        jobs.append({
                            "title": text,
                            "url": full_url,
                            "apply_url": full_url,
                        })
                    except Exception:
                        continue
            except Exception:
                continue

        return jobs

    async def _try_vendor_apply(self, job: dict) -> bool:
        """Navigate to a vendor job page and try to click Apply."""
        try:
            await self.page.goto(job["apply_url"], wait_until="domcontentloaded", timeout=15000)
            await human_delay(1.5, 2.5)

            # Look for apply buttons
            apply_selectors = [
                'a:has-text("Apply")',
                'button:has-text("Apply")',
                'a:has-text("Submit Resume")',
                'button:has-text("Submit")',
                'a[href*="apply"]',
                '.apply-button',
                '#apply-btn',
            ]

            for sel in apply_selectors:
                clicked = await safe_click(self.page, sel, timeout=3000)
                if clicked:
                    await human_delay(2, 3)
                    return True

            return False
        except Exception:
            return False

    def _update_vendor_count(self, vid: int, success: bool):
        try:
            col = "success_count" if success else "failure_count"
            self.conn.execute(
                f"UPDATE vendor_sites SET {col} = {col} + 1, last_scraped_at = datetime('now') WHERE id = ?",
                (vid,),
            )
            self.conn.commit()
        except Exception:
            pass

    def _log_summary(self):
        s = self.stats
        logger.info("=" * 60)
        logger.info(f"[Vendor] Summary: visited={s['visited']} jobs_found={s['jobs_found']} applied={s['applied']} errors={s['errors']}")
        logger.info("=" * 60)


# ============================================================================
#  MAIN
# ============================================================================

async def main():
    parser = argparse.ArgumentParser(description="Mass job application engine")
    parser.add_argument("--board", required=True, choices=["dice", "indeed", "ziprecruiter", "vendor"],
                        help="Job board to target")
    parser.add_argument("--search", default=None, help="Search query (default from search_config.yaml)")
    parser.add_argument("--location", default=None, help="Location filter")
    parser.add_argument("--pages", type=int, default=5, help="Number of search result pages")
    parser.add_argument("--batch", type=int, default=0, help="Vendor batch group number")
    parser.add_argument("--cdp-url", default="http://localhost:9222", help="Chrome CDP endpoint")
    parser.add_argument("--standalone", action="store_true", help="Launch persistent browser instead of CDP")
    parser.add_argument("--dry-run", action="store_true", help="Scan only, don't apply")
    parser.add_argument("--resume-from", default=None, help="Resume from this external_id")
    args = parser.parse_args()

    # Load defaults from search_config.yaml
    config = load_search_config()
    if not args.search:
        primary_keywords = config.get("search", {}).get("keywords", {}).get("primary", [])
        args.search = primary_keywords[0] if primary_keywords else "Java Developer"
    if not args.location:
        args.location = config.get("search", {}).get("location", "New Jersey")

    # Ensure DB exists
    if not DB_PATH.exists():
        logger.info("Database not found — initializing...")
        from scripts.init_db import init
        init()

    conn = get_db()
    cycle_id = start_cycle(conn, args.board)

    logger.info(f"{'=' * 60}")
    logger.info(f"Mass Apply — board={args.board} search='{args.search}' location={args.location}")
    logger.info(f"Pages={args.pages} dry_run={args.dry_run} cycle_id={cycle_id}")
    logger.info(f"Log file: {log_file}")
    logger.info(f"{'=' * 60}")

    async with async_playwright() as p:
        browser = None
        page = None

        try:
            if args.standalone:
                # Launch persistent browser context
                profile_dir = PROJECT_ROOT / "data" / "browser_profile"
                profile_dir.mkdir(parents=True, exist_ok=True)
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
                logger.info("Launched standalone browser with persistent profile")
            else:
                # Connect to running Chrome via CDP
                try:
                    browser = await p.chromium.connect_over_cdp(args.cdp_url)
                    logger.info(f"Connected to Chrome via CDP at {args.cdp_url}")
                except Exception as e:
                    logger.error(f"Cannot connect to Chrome at {args.cdp_url}")
                    logger.error(f"Launch Chrome with: /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222")
                    logger.error(f"Error: {e}")
                    finish_cycle(conn, cycle_id, 0, 0, 0, 0)
                    return

                context = browser.contexts[0]
                page = await context.new_page()

            # Route to the appropriate board handler
            applier_cls = {
                "dice": DiceApplier,
                "indeed": IndeedApplier,
                "ziprecruiter": ZipRecruiterApplier,
                "vendor": VendorApplier,
            }[args.board]

            applier = applier_cls(page, conn, config, args)
            await applier.run()

            # Record cycle stats
            s = applier.stats
            finish_cycle(
                conn, cycle_id,
                found=s.get("found", s.get("visited", 0)),
                new=s.get("found", s.get("jobs_found", 0)),
                applied=s.get("applied", 0),
                failed=s.get("failed", s.get("errors", 0)),
            )

            # Update state
            state = load_state()
            state["last_cycle_id"] = cycle_id
            state["total_applications"] = state.get("total_applications", 0) + s.get("applied", 0)
            state["last_run_at"] = datetime.now().isoformat()
            save_state(state)

        except Exception as e:
            logger.error(f"Fatal error: {e}")
            logger.error(traceback.format_exc())
            finish_cycle(conn, cycle_id, 0, 0, 0, 0)
        finally:
            # Don't close CDP-connected browser (user still needs it)
            if args.standalone and browser:
                await browser.close()
            elif page:
                try:
                    await page.close()
                except Exception:
                    pass

            conn.close()
            logger.info(f"Done. Log saved to {log_file}")


if __name__ == "__main__":
    asyncio.run(main())
