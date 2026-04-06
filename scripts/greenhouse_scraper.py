#!/usr/bin/env python3
"""
Greenhouse ATS API Scraper — scrapes Java jobs from companies using Greenhouse.
Uses the public boards-api.greenhouse.io endpoint (no auth required).

Usage: python3 scripts/greenhouse_scraper.py
"""
import json
import hashlib
import sqlite3
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "jobs.db"

# Known Greenhouse board slugs for IT staffing companies
# These are public and don't require authentication
GREENHOUSE_BOARDS = [
    "collabera",
    "maslowtechnologies",
    "infovisioninc",
    "hexaware",
    "maborotechnologies",
    "cogentinfotech",
    "sielotech",
    "tekskillsinc",
    "novusintellect",
    "quadranttechnologies",
    "vsoftconsulting",
    "zensar",
    "ltimindtree",
    "niittech",
    "hcltech",
    "birlasoft",
    "mphasis",
    "mindtree",
    "wipro",
    "techmahindra",
    "cyient",
    "persistent",
    "sonata",
    "mastech",
    "datamatics",
    "igate",
    "l2infotech",
    "suntech",
    "ustech",
]

JAVA_KEYWORDS = ["java", "spring", "j2ee", "microservices", "full stack", "fullstack", "backend"]
TITLE_EXCLUDE = ["lead", "architect", "principal", "director", "manager", "vp", "chief", "staff engineer"]
W2_KEYWORDS = ["w2 only", "no c2c", "only w2"]

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn

def dedup_hash(source, ext_id):
    return hashlib.sha256(f"{source}:{ext_id}".encode()).hexdigest()

def fetch_greenhouse_jobs(board_slug):
    """Fetch all jobs from a Greenhouse board via public API."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_slug}/jobs"
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("jobs", [])
    except (URLError, HTTPError, json.JSONDecodeError) as e:
        return []

def is_java_job(title, content=""):
    """Check if job title/content contains Java keywords."""
    text = (title + " " + content).lower()
    return any(kw in text for kw in JAVA_KEYWORDS)

def should_skip_title(title):
    t = title.lower()
    return any(exc in t for exc in TITLE_EXCLUDE)

def main():
    conn = get_db()
    total_found = 0
    total_java = 0
    total_new = 0

    print(f"Scanning {len(GREENHOUSE_BOARDS)} Greenhouse boards for Java C2C jobs...")
    print("=" * 60)

    for slug in GREENHOUSE_BOARDS:
        jobs = fetch_greenhouse_jobs(slug)
        if not jobs:
            continue

        java_jobs = [j for j in jobs if is_java_job(j.get("title", ""))]
        total_found += len(jobs)
        total_java += len(java_jobs)

        if java_jobs:
            print(f"\n[{slug}] {len(jobs)} total, {len(java_jobs)} Java jobs:")

        for job in java_jobs:
            title = job.get("title", "")
            location = job.get("location", {}).get("name", "Unknown")
            job_id = str(job.get("id", ""))
            job_url = job.get("absolute_url", "")

            if should_skip_title(title):
                print(f"  SKIP (title): {title}")
                continue

            dhash = dedup_hash(f"greenhouse_{slug}", job_id)
            existing = conn.execute("SELECT id FROM jobs WHERE dedup_hash = ?", (dhash,)).fetchone()
            if existing:
                print(f"  EXISTS: {title}")
                continue

            total_new += 1
            print(f"  NEW: {title} | {location} | {job_url}")

            conn.execute(
                "INSERT OR IGNORE INTO jobs (external_id, source, title, company, location, job_type, url, status, dedup_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (job_id, f"greenhouse_{slug}", title, slug, location, "contract", job_url, "scraped", dhash)
            )
            conn.commit()

    print(f"\n{'=' * 60}")
    print(f"GREENHOUSE SCAN COMPLETE")
    print(f"  Boards scanned: {len(GREENHOUSE_BOARDS)}")
    print(f"  Total jobs found: {total_found}")
    print(f"  Java jobs: {total_java}")
    print(f"  New (not in DB): {total_new}")
    print(f"{'=' * 60}")

    conn.close()

if __name__ == "__main__":
    main()
