#!/usr/bin/env python3
"""
Greenhouse Boards API bulk scraper for Java contract jobs.
No auth needed — uses the public boards API.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional

SLUGS = [
    # Tech companies with large Greenhouse boards
    "tcs", "airbnb", "stripe", "coinbase", "cloudflare",
    "datadog", "twilio", "gitlab", "mongodb", "elastic",
    "databricks", "figma", "discord", "brex", "gusto",
    "affirm", "chime", "robinhood", "lyft", "instacart",
    "toast", "pagerduty", "newrelic",
    # Consulting / staffing / additional
    "thoughtworks", "valtech", "cockroachlabs", "neo4j",
    "sofi", "betterment", "block", "asana",
]

INCLUDE_PATTERNS = re.compile(
    r"(?i)\b(java|spring\s*boot|j2ee|microservices|full\s*stack)\b"
)

EXCLUDE_PATTERNS = re.compile(
    r"(?i)\b(lead|architect|principal|director|manager|vp|chief)\b"
)

BASE_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"


def fetch_jobs(slug: str) -> list[dict]:
    """Fetch all jobs from a Greenhouse board slug."""
    url = BASE_URL.format(slug=slug)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "JobHunter/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return data.get("jobs", [])
    except urllib.error.HTTPError as e:
        print(f"  [{slug}] HTTP {e.code} — skipping", file=sys.stderr)
        return []
    except Exception as e:
        print(f"  [{slug}] Error: {e} — skipping", file=sys.stderr)
        return []


def filter_jobs(jobs: list[dict]) -> list[dict]:
    """Keep Java-related titles, exclude senior leadership titles."""
    results = []
    for job in jobs:
        title = job.get("title", "")
        if INCLUDE_PATTERNS.search(title) and not EXCLUDE_PATTERNS.search(title):
            loc = job.get("location", {}).get("name", "Unknown")
            job_id = job.get("id", "")
            absolute_url = job.get("absolute_url", "")
            results.append({
                "title": title,
                "location": loc,
                "id": job_id,
                "apply_url": absolute_url,
            })
    return results


def main(slugs: list[str] | None = None):
    if slugs is None:
        slugs = SLUGS

    all_results = {}
    total = 0

    for slug in slugs:
        print(f"Fetching {slug}...", file=sys.stderr)
        jobs = fetch_jobs(slug)
        print(f"  {len(jobs)} total jobs found", file=sys.stderr)
        matched = filter_jobs(jobs)
        print(f"  {len(matched)} Java-related jobs after filtering", file=sys.stderr)
        if matched:
            all_results[slug] = matched
            total += len(matched)

    output = {
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "total_matched": total,
        "by_company": all_results,
    }

    print(json.dumps(output, indent=2))
    print(f"\nTotal matched jobs: {total}", file=sys.stderr)


if __name__ == "__main__":
    # Accept slugs as CLI args, or use defaults
    slugs = sys.argv[1:] if len(sys.argv) > 1 else None
    main(slugs)
