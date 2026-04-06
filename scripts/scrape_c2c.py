#!/usr/bin/env python3
"""
Scrape C2C/C2H Java contract jobs from multiple boards using python-jobspy.
Outputs jobs to SQLite and prints unapplied ones for batch application.
"""
import sqlite3
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

try:
    from jobspy import scrape_jobs
except ImportError:
    print("ERROR: jobspy not installed. Run: pip3 install jobspy")
    exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "jobs.db"

# C2C filter keywords
C2C_KEYWORDS = ["c2c", "corp to corp", "corp-to-corp", "c2h", "contract to hire", "1099"]
W2_ONLY_KEYWORDS = ["w2 only", "no c2c", "only w2", "w2 contract only"]
TITLE_EXCLUDE = ["lead", "architect", "principal", "director", "manager", "vp", "chief", "staff engineer"]

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn

def dedup_hash(source, external_id):
    return hashlib.sha256(f"{source}:{external_id}".encode()).hexdigest()

def job_exists(conn, dhash):
    row = conn.execute("SELECT id FROM jobs WHERE dedup_hash = ?", (dhash,)).fetchone()
    return row is not None

def is_c2c_eligible(desc):
    """Check if job description mentions C2C/C2H and doesn't say W2 only."""
    if not desc:
        return True  # If no description, assume eligible
    desc_lower = desc.lower()
    # Explicit W2-only exclusion
    for kw in W2_ONLY_KEYWORDS:
        if kw in desc_lower:
            return False
    return True

def should_skip_title(title):
    t = title.lower().strip()
    return any(exc in t for exc in TITLE_EXCLUDE)

def run_search(search_term, location, site_names, results_wanted=50, hours_old=360):
    """Run a single search across specified sites."""
    print(f"\n{'='*60}")
    print(f"Searching: '{search_term}' in '{location}'")
    print(f"Sites: {site_names}, Max results: {results_wanted}, Hours old: {hours_old}")
    print(f"{'='*60}")

    try:
        jobs = scrape_jobs(
            site_name=site_names,
            search_term=search_term,
            location=location,
            results_wanted=results_wanted,
            hours_old=hours_old,
            job_type="contract",
            country_indeed="USA",
        )
        print(f"Found {len(jobs)} jobs")
        return jobs
    except Exception as e:
        print(f"Error scraping: {e}")
        return None

def main():
    conn = get_db()

    # Search configurations
    searches = [
        # (search_term, location, sites)
        ("Java Developer C2C", "New Jersey", ["indeed", "glassdoor", "google"]),
        ("Java Developer C2C", "New York, NY", ["indeed", "glassdoor", "google"]),
        ("Java Developer C2C", "Remote", ["indeed", "glassdoor", "google"]),
        ("Java Full Stack C2C", "New Jersey", ["indeed", "glassdoor", "google"]),
        ("Java Spring Boot contract", "New Jersey", ["indeed", "glassdoor", "google"]),
        ("Java Spring Boot contract", "New York, NY", ["indeed", "glassdoor", "google"]),
        ("Java Microservices contract", "Remote", ["indeed", "glassdoor", "google"]),
        ("Senior Java Developer contract", "New Jersey", ["indeed", "glassdoor", "google"]),
        ("Senior Java Developer contract", "New York, NY", ["indeed", "glassdoor", "google"]),
    ]

    total_found = 0
    total_new = 0
    total_c2c = 0
    all_new_jobs = []

    for search_term, location, sites in searches:
        jobs_df = run_search(search_term, location, sites, results_wanted=30, hours_old=360)

        if jobs_df is None or len(jobs_df) == 0:
            continue

        for _, job in jobs_df.iterrows():
            total_found += 1
            title = str(job.get("title", ""))
            company = str(job.get("company", ""))
            loc = str(job.get("location", ""))
            desc = str(job.get("description", ""))
            url = str(job.get("job_url", ""))
            source = str(job.get("site", "unknown"))
            date_posted = job.get("date_posted", "")

            # Skip excluded titles
            if should_skip_title(title):
                continue

            # Check C2C eligibility
            if not is_c2c_eligible(desc):
                continue

            total_c2c += 1

            # Check if already in DB
            ext_id = url.split("/")[-1][:50] if url else hashlib.md5(f"{title}{company}".encode()).hexdigest()[:20]
            dhash = dedup_hash(source, ext_id)

            if job_exists(conn, dhash):
                continue

            total_new += 1

            # Insert into DB
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO jobs (external_id, source, title, company, location, job_type, url, status, dedup_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (ext_id, source, title, company, loc, "contract", url, "scraped", dhash)
                )
                conn.commit()
            except Exception as e:
                print(f"  DB error: {e}")
                continue

            all_new_jobs.append({
                "title": title,
                "company": company,
                "location": loc,
                "source": source,
                "url": url,
                "date_posted": str(date_posted),
            })

            print(f"  NEW: {title[:60]} @ {company} [{source}] {loc}")

    print(f"\n{'='*60}")
    print(f"SCRAPE COMPLETE")
    print(f"  Total found: {total_found}")
    print(f"  C2C eligible: {total_c2c}")
    print(f"  New (not in DB): {total_new}")
    print(f"{'='*60}")

    # Save new jobs to JSON for review
    if all_new_jobs:
        output_path = PROJECT_ROOT / "data" / "new_c2c_jobs.json"
        with open(output_path, "w") as f:
            json.dump(all_new_jobs, f, indent=2)
        print(f"New jobs saved to: {output_path}")

    conn.close()

if __name__ == "__main__":
    main()
