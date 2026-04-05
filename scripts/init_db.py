#!/usr/bin/env python3
"""Initialize SQLite database with schema and import vendor URLs."""
import json
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "jobs.db")
VENDORS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "vendor_urls.json")
STATE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "state.json")

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id     TEXT,
    source          TEXT NOT NULL,
    title           TEXT NOT NULL,
    company         TEXT,
    location        TEXT,
    job_type        TEXT,
    rate            TEXT,
    description     TEXT,
    url             TEXT NOT NULL,
    apply_url       TEXT,
    posted_date     TEXT,
    scraped_at      TEXT DEFAULT (datetime('now')),
    dedup_hash      TEXT UNIQUE NOT NULL,
    match_score     REAL DEFAULT 0,
    status          TEXT DEFAULT 'new',
    filter_reason   TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS applications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id          INTEGER NOT NULL REFERENCES jobs(id),
    applied_at      TEXT DEFAULT (datetime('now')),
    method          TEXT,
    ats_platform    TEXT,
    status          TEXT DEFAULT 'submitted',
    error_message   TEXT,
    screenshot_id   TEXT
);

CREATE TABLE IF NOT EXISTS cycles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at      TEXT DEFAULT (datetime('now')),
    completed_at    TEXT,
    jobs_found      INTEGER DEFAULT 0,
    jobs_new        INTEGER DEFAULT 0,
    jobs_matched    INTEGER DEFAULT 0,
    jobs_applied    INTEGER DEFAULT 0,
    jobs_failed     INTEGER DEFAULT 0,
    vendor_batch    TEXT,
    status          TEXT DEFAULT 'running'
);

CREATE TABLE IF NOT EXISTS vendor_sites (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    url             TEXT NOT NULL,
    url_type        TEXT,
    last_scraped_at TEXT,
    success_count   INTEGER DEFAULT 0,
    failure_count   INTEGER DEFAULT 0,
    batch_group     INTEGER
);

CREATE INDEX IF NOT EXISTS idx_jobs_dedup ON jobs(dedup_hash);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);
CREATE INDEX IF NOT EXISTS idx_vendor_batch ON vendor_sites(batch_group);
"""


def init():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)

    # Import vendors if available
    if os.path.exists(VENDORS_PATH):
        with open(VENDORS_PATH) as f:
            vendors = json.load(f)

        # Clear existing vendors
        conn.execute("DELETE FROM vendor_sites")

        batch_size = 50
        for i, v in enumerate(vendors):
            batch_group = i // batch_size
            conn.execute(
                "INSERT INTO vendor_sites (name, url, url_type, batch_group) VALUES (?, ?, ?, ?)",
                (v.get("name", ""), v["url"], v.get("url_type", "confirmed"), batch_group),
            )

        conn.commit()
        total_batches = (len(vendors) // batch_size) + 1
        print(f"Imported {len(vendors)} vendors into {total_batches} batches")
    else:
        print("No vendor_urls.json found — skipping vendor import")

    conn.close()

    # Initialize state.json
    if not os.path.exists(STATE_PATH):
        state = {
            "last_cycle_id": 0,
            "current_vendor_batch": 0,
            "total_applications": 0,
            "last_run_at": None,
        }
        with open(STATE_PATH, "w") as f:
            json.dump(state, f, indent=2)
        print(f"Created {STATE_PATH}")

    print(f"Database initialized at {DB_PATH}")


if __name__ == "__main__":
    init()
