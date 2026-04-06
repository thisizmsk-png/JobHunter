#!/usr/bin/env python3
"""
Extract new Java contract jobs from 3 Apify Dice search result files.
Deduplicates against existing pool, applies filter rules, saves batch K.
"""

import json
import re
from datetime import datetime
from pathlib import Path

# File paths
POOL_FILE = Path("/Users/saikrishnamadavarapu/Development/JobBoard/data/apify_dice_jobs.json")
BATCH_K_FILE = Path("/Users/saikrishnamadavarapu/Development/JobBoard/data/batch_K_jobs.json")

SEARCH_RESULT_FILES = [
    "/Users/saikrishnamadavarapu/.claude/projects/-Users-saikrishnamadavarapu-Development-JobBoard/7a924142-f712-4afb-a96b-d282a727e224/tool-results/mcp-1bc48676-d7a1-4f60-b429-2400ae9ea07d-search_jobs-1775490347776.txt",
    "/Users/saikrishnamadavarapu/.claude/projects/-Users-saikrishnamadavarapu-Development-JobBoard/7a924142-f712-4afb-a96b-d282a727e224/tool-results/mcp-1bc48676-d7a1-4f60-b429-2400ae9ea07d-search_jobs-1775490349632.txt",
    "/Users/saikrishnamadavarapu/.claude/projects/-Users-saikrishnamadavarapu-Development-JobBoard/7a924142-f712-4afb-a96b-d282a727e224/tool-results/mcp-1bc48676-d7a1-4f60-b429-2400ae9ea07d-search_jobs-1775490351211.txt",
]

# Filter rules
TITLE_EXCLUDE_ROLES = [
    r"\blead\b", r"\barchitect\b", r"\bprincipal\b", r"\bdirector\b",
    r"\bmanager\b", r"\bvp\b", r"\bchief\b", r"\bstaff engineer\b",
]

DISQUALIFYING_PHRASES = [
    "w2 only", "only w2", "strictly w2", "no c2c", "no h1b",
    "no corp to corp", "top secret clearance", "w2 citizens only",
    "visa independent",
]

NON_JAVA_TITLE_PATTERNS = [
    r"\bpython\s+developer\b", r"\b\.net\s+developer\b", r"\bqa\s+engineer\b",
    r"\bqa\s+analyst\b", r"\bquality\s+assurance\b", r"\b\.net\s+engineer\b",
    r"\bruby\s+developer\b", r"\bphp\s+developer\b", r"\bios\s+developer\b",
    r"\bandroid\s+developer\b", r"\bgolang\s+developer\b", r"\bgo\s+developer\b",
    r"\bscala\s+developer\b", r"\bkotlin\s+developer\b", r"\bswift\s+developer\b",
    r"\bc\+\+\s+developer\b", r"\bc#\s+developer\b", r"\bnode\.?js\s+developer\b",
    r"\breact\s+developer\b", r"\bangular\s+developer\b",
    r"\bdata\s+engineer\b", r"\bdata\s+scientist\b", r"\bdevops\s+engineer\b",
    r"\binfrastructure\s+engineer\b", r"\bnetwork\s+engineer\b",
    r"\bsecurity\s+engineer\b", r"\bcloud\s+engineer\b",
    r"\bmachine\s+learning\s+engineer\b", r"\bml\s+engineer\b",
]


def is_excluded_by_title(title_lower: str) -> bool:
    """Check if title contains excluded seniority/role keywords."""
    for pattern in TITLE_EXCLUDE_ROLES:
        if re.search(pattern, title_lower):
            return True
    return False


def has_disqualifying_phrase(title_lower: str, summary_lower: str) -> bool:
    """Check if title or summary contains disqualifying phrases."""
    combined = title_lower + " " + summary_lower
    for phrase in DISQUALIFYING_PHRASES:
        if phrase in combined:
            return True
    return False


def is_non_java_role(title_lower: str) -> bool:
    """Check if role is explicitly non-Java (by title) with no Java mention."""
    if "java" in title_lower:
        return False  # Java is mentioned — keep it
    for pattern in NON_JAVA_TITLE_PATTERNS:
        if re.search(pattern, title_lower):
            return True
    return False


def parse_posted_date(posted_date_str: str) -> str:
    """Convert ISO date string to YYYY-MM-DD."""
    if not posted_date_str:
        return ""
    try:
        dt = datetime.fromisoformat(posted_date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return posted_date_str[:10] if len(posted_date_str) >= 10 else posted_date_str


def load_existing_guids() -> set:
    """Load GUIDs from the existing pool file."""
    if not POOL_FILE.exists():
        return set()
    with open(POOL_FILE) as f:
        pool = json.load(f)
    return {entry["guid"] for entry in pool}


def load_all_raw_jobs() -> list:
    """Load and merge jobs from all 3 search result files."""
    all_jobs = []
    for filepath in SEARCH_RESULT_FILES:
        with open(filepath) as f:
            data = json.load(f)
        jobs = data.get("data", [])
        all_jobs.extend(jobs)
        print(f"  Loaded {len(jobs)} jobs from {Path(filepath).name}")
    return all_jobs


def filter_and_deduplicate(raw_jobs: list, existing_guids: set) -> list:
    """Apply all filter rules and deduplicate."""
    seen_guids = set(existing_guids)
    eligible = []

    skipped_guid = 0
    skipped_easy_apply = 0
    skipped_title_exclude = 0
    skipped_disqualifying = 0
    skipped_non_java = 0
    accepted = 0

    for job in raw_jobs:
        guid = job.get("guid", "")
        title = job.get("title", "")
        summary = job.get("summary", "") or ""
        easy_apply = job.get("easyApply", False)
        location = (job.get("jobLocation") or {}).get("displayName", "")
        company = job.get("companyName", "")
        posted = parse_posted_date(job.get("postedDate", ""))

        title_lower = title.lower()
        summary_lower = summary.lower()

        # Rule 1: GUID already in pool or seen this batch
        if guid in seen_guids:
            skipped_guid += 1
            continue

        # Rule 2: easyApply must be true
        if not easy_apply:
            skipped_easy_apply += 1
            seen_guids.add(guid)
            continue

        # Rule 3: Title excludes (lead, architect, etc.)
        if is_excluded_by_title(title_lower):
            skipped_title_exclude += 1
            seen_guids.add(guid)
            continue

        # Rule 4: Disqualifying phrases in title or summary
        if has_disqualifying_phrase(title_lower, summary_lower):
            skipped_disqualifying += 1
            seen_guids.add(guid)
            continue

        # Rule 5: Non-Java role by title with no Java mention
        if is_non_java_role(title_lower):
            skipped_non_java += 1
            seen_guids.add(guid)
            continue

        # Passed all filters
        seen_guids.add(guid)
        accepted += 1
        eligible.append({
            "guid": guid,
            "title": title,
            "company": company,
            "url": f"https://www.dice.com/job-detail/{guid}",
            "easy_apply": True,
            "location": location,
            "posted": posted,
        })

    print(f"\nFilter summary:")
    print(f"  Skipped (already in pool/batch): {skipped_guid}")
    print(f"  Skipped (easyApply=false):       {skipped_easy_apply}")
    print(f"  Skipped (title exclusion):        {skipped_title_exclude}")
    print(f"  Skipped (disqualifying phrase):   {skipped_disqualifying}")
    print(f"  Skipped (non-Java role):          {skipped_non_java}")
    print(f"  Accepted:                         {accepted}")

    return eligible


def append_to_pool(new_jobs: list):
    """Append new jobs to the existing pool file."""
    with open(POOL_FILE) as f:
        pool = json.load(f)

    for job in new_jobs:
        pool.append({
            "guid": job["guid"],
            "title": job["title"],
            "company": job["company"],
            "url": job["url"],
            "remote": "remote" in job["location"].lower(),
            "location": job["location"],
            "easy_apply": True,
        })

    with open(POOL_FILE, "w") as f:
        json.dump(pool, f, indent=2)

    print(f"\nPool updated: {len(pool)} total entries in {POOL_FILE.name}")


def main():
    print("=== Batch K Extraction ===\n")

    # Step 1: Load existing GUIDs
    existing_guids = load_existing_guids()
    print(f"Existing pool: {len(existing_guids)} GUIDs\n")

    # Step 2: Load all raw jobs from search result files
    print("Loading search result files:")
    raw_jobs = load_all_raw_jobs()
    print(f"\nTotal raw jobs across all files: {len(raw_jobs)}")

    # Step 3: Filter and deduplicate
    print("\nApplying filters...")
    eligible = filter_and_deduplicate(raw_jobs, existing_guids)

    # Step 4: Save batch K
    with open(BATCH_K_FILE, "w") as f:
        json.dump(eligible, f, indent=2)
    print(f"\nBatch K saved: {len(eligible)} jobs → {BATCH_K_FILE}")

    # Step 5: Append new jobs to pool
    if eligible:
        append_to_pool(eligible)

    print(f"\n=== RESULT: {len(eligible)} new jobs found for Batch K ===")
    if eligible:
        print("\nSample of new jobs:")
        for job in eligible[:5]:
            print(f"  [{job['posted']}] {job['title']} @ {job['company']} — {job['location']}")
        if len(eligible) > 5:
            print(f"  ... and {len(eligible) - 5} more")

    return len(eligible)


if __name__ == "__main__":
    main()
