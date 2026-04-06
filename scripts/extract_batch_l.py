#!/usr/bin/env python3
"""
Extract Batch L — new eligible Java contract jobs from 3 Apify Dice search result files.
Deduplicates against existing pool (apify_dice_jobs.json) and across the 3 files.
Saves to data/batch_L_jobs.json and appends new jobs to apify_dice_jobs.json.
"""

import json
import os
from datetime import datetime

# ── Paths ────────────────────────────────────────────────────────────────────
BASE = "/Users/saikrishnamadavarapu/Development/JobBoard"
POOL_FILE = os.path.join(BASE, "data", "apify_dice_jobs.json")
BATCH_OUT  = os.path.join(BASE, "data", "batch_L_jobs.json")

SOURCE_FILES = [
    "/Users/saikrishnamadavarapu/.claude/projects/-Users-saikrishnamadavarapu-Development-JobBoard/7a924142-f712-4afb-a96b-d282a727e224/tool-results/mcp-1bc48676-d7a1-4f60-b429-2400ae9ea07d-search_jobs-1775490373636.txt",
    "/Users/saikrishnamadavarapu/.claude/projects/-Users-saikrishnamadavarapu-Development-JobBoard/7a924142-f712-4afb-a96b-d282a727e224/tool-results/mcp-1bc48676-d7a1-4f60-b429-2400ae9ea07d-search_jobs-1775490375165.txt",
    "/Users/saikrishnamadavarapu/.claude/projects/-Users-saikrishnamadavarapu-Development-JobBoard/7a924142-f712-4afb-a96b-d282a727e224/tool-results/mcp-1bc48676-d7a1-4f60-b429-2400ae9ea07d-search_jobs-1775490462298.txt",
]

# ── Filter keyword sets (all lowercase for comparison) ───────────────────────
TITLE_SENIORITY_EXCLUDE = {
    "lead", "architect", "principal", "director", "manager",
    "vp", "chief", "staff engineer",
}

# Phrases that, if found in title or summary, disqualify the job
DISQUALIFY_PHRASES = [
    "w2 only", "only w2", "strictly w2", "no c2c", "no h1b",
    "no corp to corp", "top secret", "w2 citizens only",
    "visa independent", "w2 role", "usc only",
    "permanent full time only",
]

# A job must match at least one of these to be considered Java/JVM
JAVA_KEYWORDS = [
    "java", "spring", "j2ee", "jvm", "hibernate", "maven", "gradle",
    "microservices", "springboot", "spring boot", "jakarta",
    "kotlin", "scala", "groovy", "fullstack java", "full stack java",
]

# Non-Java roles — if title matches these and no java keyword found, skip
NON_JAVA_ROLES = [
    "python only", ".net developer", "qa tester", "quality assurance",
    "devops engineer", "penetration tester", "salesforce", "oracle ebs",
    "data scientist", "machine learning engineer", "android developer",
    "ios developer", "react developer", "angular developer",
    "vue developer", "php developer", "ruby developer",
]


def load_pool_guids(pool_file: str) -> set:
    if not os.path.exists(pool_file):
        return set()
    with open(pool_file) as f:
        pool = json.load(f)
    return {entry["guid"] for entry in pool if "guid" in entry}


def load_pool(pool_file: str) -> list:
    if not os.path.exists(pool_file):
        return []
    with open(pool_file) as f:
        return json.load(f)


def title_has_seniority_word(title_lower: str) -> bool:
    """Return True if any seniority-exclusion keyword appears as a whole word."""
    import re
    for kw in TITLE_SENIORITY_EXCLUDE:
        # Use word boundary for single-word keywords; phrase match for multi-word
        if " " in kw:
            if kw in title_lower:
                return True
        else:
            if re.search(r'\b' + re.escape(kw) + r'\b', title_lower):
                return True
    return False


def has_disqualify_phrase(text_lower: str) -> bool:
    return any(phrase in text_lower for phrase in DISQUALIFY_PHRASES)


def is_java_role(title_lower: str, summary_lower: str) -> bool:
    combined = title_lower + " " + summary_lower
    return any(kw in combined for kw in JAVA_KEYWORDS)


def is_non_java_only_role(title_lower: str, summary_lower: str) -> bool:
    """True if the role is clearly a non-Java technology with no Java content."""
    combined = title_lower + " " + summary_lower
    # If it has Java keywords it's fine regardless of other techs
    if any(kw in combined for kw in JAVA_KEYWORDS):
        return False
    return any(role in title_lower for role in NON_JAVA_ROLES)


def extract_jobs_from_file(path: str) -> list:
    with open(path) as f:
        raw = json.load(f)
    return raw.get("data", [])


def filter_job(job: dict, existing_guids: set) -> tuple:
    """
    Returns (keep: bool, reason: str)
    """
    guid = job.get("guid", "")
    title = job.get("title", "") or ""
    summary = job.get("summary", "") or ""
    easy_apply = job.get("easyApply", False)

    title_l = title.lower()
    summary_l = summary.lower()
    combined_l = title_l + " " + summary_l

    # 1. Already in pool
    if guid in existing_guids:
        return False, "duplicate"

    # 2. easyApply required
    if not easy_apply:
        return False, "no_easy_apply"

    # 3. Seniority exclusion (title only)
    if title_has_seniority_word(title_l):
        return False, "seniority_excluded"

    # 4. Disqualify phrases in title or summary
    if has_disqualify_phrase(combined_l):
        return False, "disqualify_phrase"

    # 5. Must be a Java/JVM role
    if not is_java_role(title_l, summary_l):
        return False, "not_java"

    # 6. Clearly non-Java role
    if is_non_java_only_role(title_l, summary_l):
        return False, "non_java_role"

    return True, "eligible"


def main():
    print("=== Batch L Extraction ===")

    # Load existing pool
    existing_pool = load_pool(POOL_FILE)
    existing_guids = {e["guid"] for e in existing_pool if "guid" in e}
    print(f"Pool: {len(existing_pool)} existing jobs, {len(existing_guids)} unique GUIDs")

    # Load all 3 source files
    all_raw_jobs = []
    for i, path in enumerate(SOURCE_FILES, 1):
        jobs = extract_jobs_from_file(path)
        print(f"File {i}: {len(jobs)} raw jobs")
        all_raw_jobs.extend(jobs)

    print(f"Total raw jobs across all files: {len(all_raw_jobs)}")

    # Deduplicate across the 3 files (by guid) — track already-seen in this batch
    seen_in_batch: set = set()
    stats = {"duplicate": 0, "no_easy_apply": 0, "seniority_excluded": 0,
             "disqualify_phrase": 0, "not_java": 0, "non_java_role": 0,
             "cross_file_dup": 0, "eligible": 0}

    batch_l = []
    new_pool_entries = []
    # Combined seen set = pool + batch so far
    all_seen = set(existing_guids)

    for job in all_raw_jobs:
        guid = job.get("guid", "")

        # Cross-file dedup (guid already processed in this batch run)
        if guid in seen_in_batch:
            stats["cross_file_dup"] += 1
            continue
        seen_in_batch.add(guid)

        keep, reason = filter_job(job, all_seen)
        stats[reason] += 1

        if keep:
            # Mark as seen so cross-file duplicates beyond this point are caught
            all_seen.add(guid)

            location = ""
            loc_obj = job.get("jobLocation")
            if isinstance(loc_obj, dict):
                location = loc_obj.get("displayName", "")
            elif isinstance(loc_obj, str):
                location = loc_obj

            entry = {
                "guid": guid,
                "title": job.get("title", ""),
                "company": job.get("companyName", ""),
                "url": job.get("detailsPageUrl", f"https://www.dice.com/job-detail/{guid}"),
                "easy_apply": True,
                "location": location,
                "posted": job.get("postedDate", ""),
            }
            batch_l.append(entry)

            # Pool entry (preserves easy_apply bool as in existing pool format)
            pool_entry = {
                "guid": guid,
                "title": entry["title"],
                "company": entry["company"],
                "url": entry["url"],
                "remote": job.get("isRemote", False),
                "location": location,
                "easy_apply": True,
            }
            new_pool_entries.append(pool_entry)

    # Save batch L
    with open(BATCH_OUT, "w") as f:
        json.dump(batch_l, f, indent=2)
    print(f"\nBatch L saved: {len(batch_l)} eligible jobs → {BATCH_OUT}")

    # Append to pool
    updated_pool = existing_pool + new_pool_entries
    with open(POOL_FILE, "w") as f:
        json.dump(updated_pool, f, indent=2)
    print(f"Pool updated: {len(existing_pool)} → {len(updated_pool)} entries (+{len(new_pool_entries)})")

    # Summary
    print("\n── Filter breakdown ──")
    print(f"  Cross-file duplicates skipped : {stats['cross_file_dup']}")
    print(f"  Pool duplicates skipped       : {stats['duplicate']}")
    print(f"  No easyApply                  : {stats['no_easy_apply']}")
    print(f"  Seniority excluded            : {stats['seniority_excluded']}")
    print(f"  Disqualify phrase             : {stats['disqualify_phrase']}")
    print(f"  Not Java/JVM                  : {stats['not_java']}")
    print(f"  Non-Java role                 : {stats['non_java_role']}")
    print(f"  ELIGIBLE (Batch L)            : {stats['eligible']}")

    if batch_l:
        print("\n── Batch L jobs ──")
        for i, j in enumerate(batch_l, 1):
            print(f"  {i:3}. [{j['company'][:30]}] {j['title'][:70]}")


if __name__ == "__main__":
    main()
