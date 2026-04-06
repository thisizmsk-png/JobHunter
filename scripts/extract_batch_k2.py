#!/usr/bin/env python3
"""
extract_batch_k2.py — Extract new Java contract jobs from Apify Dice search results
and merge into batch_K_jobs.json and apify_dice_jobs.json.
"""

import json
import re
import sys
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE = Path("/Users/saikrishnamadavarapu/Development/JobBoard")
POOL_FILE   = BASE / "data/apify_dice_jobs.json"
BATCH_K_FILE = BASE / "data/batch_K_jobs.json"

SEARCH_FILES = [
    Path("/Users/saikrishnamadavarapu/.claude/projects/-Users-saikrishnamadavarapu-Development-JobBoard"
         "/7a924142-f712-4afb-a96b-d282a727e224/tool-results"
         "/mcp-1bc48676-d7a1-4f60-b429-2400ae9ea07d-search_jobs-1775490422809.txt"),
    Path("/Users/saikrishnamadavarapu/.claude/projects/-Users-saikrishnamadavarapu-Development-JobBoard"
         "/7a924142-f712-4afb-a96b-d282a727e224/tool-results"
         "/mcp-1bc48676-d7a1-4f60-b429-2400ae9ea07d-search_jobs-1775490424239.txt"),
]

# ── Known new job to inject manually ──────────────────────────────────────────
KNOWN_NEW_JOB = {
    "guid":     "021d8f9f-5a6d-4c28-b0da-0fce92ac3dc5",
    "title":    "Java Full-Stack Developer",
    "company":  "Sincera Technologies, Inc.",
    "url":      "https://www.dice.com/job-detail/021d8f9f-5a6d-4c28-b0da-0fce92ac3dc5",
    "easy_apply": True,
    "location": "New York, NY (Hybrid)",
    "posted":   "2026-03-31",
}

# ── Filter rules ───────────────────────────────────────────────────────────────
TITLE_EXCLUDE_WORDS = [
    "lead", "architect", "principal", "director", "manager",
    "vp", "chief", "staff engineer",
]

TEXT_EXCLUDE_PHRASES = [
    "w2 only", "only w2", "strictly w2", "no c2c", "no h1b",
    "no corp to corp", "top secret", "w2 citizens only",
    "visa independent", "usc only", "ead only",
    "green card only",
]

# "local only to X" — allowed states
ALLOWED_LOCAL_STATES = {"nj", "ny", "ct", "pa", "new jersey", "new york", "connecticut", "pennsylvania"}

# Java-related keywords — at least one must appear in title or summary
JAVA_KEYWORDS = [
    "java", "spring", "j2ee", "jvm", "hibernate", "microservice",
    "full stack", "fullstack", "backend", "jee",
]

# Non-Java-only role indicators (skip if title matches these but NOT java keywords)
NON_JAVA_ONLY = [
    r"\bpython\b(?!.*java)", r"\.net\b(?!.*java)", r"\bqa\b", r"\bqe\b",
    r"quality assurance", r"sdet",
]


def normalize(text: str) -> str:
    return text.lower()


def title_excluded(title: str) -> bool:
    t = normalize(title)
    for word in TITLE_EXCLUDE_WORDS:
        # Match as whole word or phrase
        pattern = r'\b' + re.escape(word) + r'\b'
        if re.search(pattern, t):
            return True
    return False


def text_excluded(title: str, summary: str) -> bool:
    combined = normalize(title + " " + summary)

    for phrase in TEXT_EXCLUDE_PHRASES:
        if phrase in combined:
            return True

    # "local only to X" — skip unless X is NJ/NY/CT/PA
    local_match = re.search(r'local only to ([^,;.\n]+)', combined)
    if local_match:
        location_text = local_match.group(1).strip()
        allowed = any(state in location_text for state in ALLOWED_LOCAL_STATES)
        if not allowed:
            return True

    return False


def is_java_role(title: str, summary: str) -> bool:
    combined = normalize(title + " " + summary)
    return any(kw in combined for kw in JAVA_KEYWORDS)


def normalize_job(raw: dict) -> dict:
    """Convert raw Apify search result record to pool/batch schema."""
    guid = raw.get("guid", "")
    title = raw.get("title", "")
    company = raw.get("companyName", "")
    url = raw.get("detailsPageUrl", f"https://www.dice.com/job-detail/{guid}")
    # Strip query params from URL
    url = url.split("?")[0]
    easy_apply = raw.get("easyApply", False)
    location = (raw.get("jobLocation") or {}).get("displayName", "")
    posted = (raw.get("postedDate") or "")[:10]  # YYYY-MM-DD

    return {
        "guid":       guid,
        "title":      title,
        "company":    company,
        "url":        url,
        "easy_apply": easy_apply,
        "location":   location,
        "posted":     posted,
    }


def passes_filters(raw: dict) -> tuple[bool, str]:
    """Return (passes, reason_if_skipped)."""
    title   = raw.get("title", "")
    summary = raw.get("summary", "")
    easy    = raw.get("easyApply", False)

    if not easy:
        return False, "easyApply=false"

    if title_excluded(title):
        return False, f"title exclusion: {title[:60]}"

    if text_excluded(title, summary):
        return False, f"text exclusion: {title[:60]}"

    if not is_java_role(title, summary):
        return False, f"not Java role: {title[:60]}"

    return True, ""


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    # 1. Load existing pool
    with open(POOL_FILE) as f:
        pool: list[dict] = json.load(f)
    pool_guids = {j["guid"] for j in pool}
    print(f"Pool loaded: {len(pool)} jobs, {len(pool_guids)} unique GUIDs")

    # 2. Load existing batch K
    if BATCH_K_FILE.exists():
        with open(BATCH_K_FILE) as f:
            batch_k: list[dict] = json.load(f)
        batch_k_guids = {j["guid"] for j in batch_k}
        print(f"Batch K loaded: {len(batch_k)} existing jobs")
    else:
        batch_k = []
        batch_k_guids = set()
        print("Batch K file not found — creating fresh")

    # 3. Parse search result files
    raw_jobs: list[dict] = []
    for sf in SEARCH_FILES:
        with open(sf) as f:
            data = json.load(f)
        jobs = data.get("data", [])
        print(f"  {sf.name}: {len(jobs)} raw records")
        raw_jobs.extend(jobs)

    print(f"Total raw records across both files: {len(raw_jobs)}")

    # 4. Deduplicate raw by GUID (across both files)
    seen_raw: set[str] = set()
    unique_raw: list[dict] = []
    for j in raw_jobs:
        g = j.get("guid", "")
        if g and g not in seen_raw:
            seen_raw.add(g)
            unique_raw.append(j)
    print(f"Unique raw records (deduped across files): {len(unique_raw)}")

    # 5. Apply filters and collect new jobs
    new_for_pool: list[dict] = []
    new_for_batch_k: list[dict] = []
    skipped_pool_dup = 0
    skipped_batch_dup = 0
    skipped_filter: list[tuple[str, str]] = []

    for raw in unique_raw:
        guid = raw.get("guid", "")

        # Already in pool → skip entirely
        if guid in pool_guids:
            skipped_pool_dup += 1
            continue

        # Apply filters
        ok, reason = passes_filters(raw)
        if not ok:
            skipped_filter.append((guid, reason))
            continue

        # Normalize to our schema
        job = normalize_job(raw)

        # Add to pool
        new_for_pool.append(job)
        pool_guids.add(guid)

        # Add to batch K if not already there
        if guid not in batch_k_guids:
            new_for_batch_k.append(job)
            batch_k_guids.add(guid)
        else:
            skipped_batch_dup += 1

    # 6. Handle the known new job
    known = KNOWN_NEW_JOB.copy()
    kg = known["guid"]
    if kg in pool_guids:
        print(f"\nKnown new job already in pool: {known['title']}")
    else:
        # It passes all filters by definition (manually verified)
        new_for_pool.append(known)
        pool_guids.add(kg)
        if kg not in batch_k_guids:
            new_for_batch_k.append(known)
            batch_k_guids.add(kg)
        print(f"\nKnown new job added: {known['title']}")

    # 7. Merge into pool
    pool.extend(new_for_pool)

    # 8. Merge into batch K
    batch_k.extend(new_for_batch_k)

    # 9. Save files
    with open(POOL_FILE, "w") as f:
        json.dump(pool, f, indent=2)
    print(f"\nPool saved: {len(pool)} total jobs ({len(new_for_pool)} added)")

    with open(BATCH_K_FILE, "w") as f:
        json.dump(batch_k, f, indent=2)
    print(f"Batch K saved: {len(batch_k)} total jobs ({len(new_for_batch_k)} new added)")

    # 10. Summary
    print("\n── Filter Summary ──")
    print(f"  Skipped (already in pool):    {skipped_pool_dup}")
    print(f"  Skipped (already in batch K): {skipped_batch_dup}")
    print(f"  Skipped (filter rules):       {len(skipped_filter)}")
    print(f"  Added to pool:                {len(new_for_pool)}")
    print(f"  Added to batch K:             {len(new_for_batch_k)}")

    if skipped_filter:
        print("\n── Filtered-out jobs ──")
        for guid, reason in skipped_filter:
            print(f"  [{guid[:8]}] {reason}")

    print(f"\n✓ BATCH K TOTAL: {len(batch_k)} jobs")

    # 11. Print batch K contents
    print("\n── Batch K Jobs ──")
    for i, j in enumerate(batch_k, 1):
        print(f"  {i:2}. [{j['guid'][:8]}] {j['title'][:65]} | {j.get('company','')[:30]}")


if __name__ == "__main__":
    main()
