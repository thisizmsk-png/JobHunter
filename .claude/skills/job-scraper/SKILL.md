---
name: job-scraper
description: >
  Scrapes job listings from multiple sources: Indeed, LinkedIn, Glassdoor, ZipRecruiter,
  Google Jobs via python-jobspy, Dice.com via Claude in Chrome, and a rotating batch of
  456 vendor/staffing sites. Stores results in SQLite. Use when running the job hunt pipeline.
user-invocable: true
context: fork
agent: general-purpose
model: sonnet
allowed-tools:
  - Bash
  - Read
  - Write
  - Grep
  - Glob
  - Agent
---

# Job Scraper Agent

You are the job scraper agent for the JobHunter pipeline.

## Your Mission

Scrape Java contract jobs from multiple sources and insert them into the SQLite database.

## Step 1: Read State

```bash
cat /Users/saikrishnamadavarapu/Development/JobBoard/data/state.json
```

Note the `current_vendor_batch` number.

## Step 2: Scrape Major Boards (python-jobspy)

Run this via Bash:

```bash
cd /Users/saikrishnamadavarapu/Development/JobBoard && /Users/saikrishnamadavarapu/Development/JobBoard/venv/bin/python3 -c "
from jobspy import scrape_jobs
import json, hashlib, sqlite3, datetime

# Search multiple terms
all_jobs = []
for term in ['Java Developer C2C', 'Java Full Stack Contract', 'Sr Java Developer C2C']:
    try:
        jobs = scrape_jobs(
            site_name=['indeed', 'linkedin', 'glassdoor', 'zip_recruiter', 'google'],
            search_term=term,
            location='New Jersey',
            results_wanted=30,
            hours_old=24,
            job_type='contract',
            country_indeed='USA',
        )
        all_jobs.extend(jobs.to_dict('records'))
    except Exception as e:
        print(f'Warning: {term} failed: {e}')

# Insert into SQLite
conn = sqlite3.connect('data/jobs.db')
inserted = 0
for j in all_jobs:
    title = str(j.get('title', ''))
    company = str(j.get('company', ''))
    location = str(j.get('location', ''))
    dedup = hashlib.sha256((title + company + location).lower().strip().encode()).hexdigest()
    try:
        conn.execute('''INSERT INTO jobs (external_id, source, title, company, location,
            job_type, url, apply_url, posted_date, dedup_hash, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')''',
            (str(j.get('id', '')), str(j.get('site', 'jobspy')), title, company, location,
             str(j.get('job_type', '')), str(j.get('job_url', '')),
             str(j.get('job_url', '')), str(j.get('date_posted', '')), dedup))
        inserted += 1
    except sqlite3.IntegrityError:
        pass  # duplicate
conn.commit()
conn.close()
print(f'JobSpy: inserted {inserted} new jobs from {len(all_jobs)} total')
"
```

## Step 3: Scrape Dice.com (Claude in Chrome)

Use Claude in Chrome MCP to:
1. Get a tab: `tabs_context_mcp(createIfEmpty=true)`, then `tabs_create_mcp()`
2. Navigate to: `https://www.dice.com/jobs?q=java+developer&countryCode=US&radius=30&radiusUnit=mi&page=1&pageSize=20&filters.employmentType=CONTRACTS&filters.postedDate=ONE&language=en`
3. Wait 3 seconds for page load
4. Use `get_page_text` to extract job listings
5. Parse each job: title, company, location, URL
6. Insert into SQLite with `source='dice'`
7. Check page 2 if results exist

## Step 4: Scrape Vendor Batch (Claude in Chrome)

Read vendor batch from SQLite:
```bash
cd /Users/saikrishnamadavarapu/Development/JobBoard && /Users/saikrishnamadavarapu/Development/JobBoard/venv/bin/python3 -c "
import sqlite3, json
conn = sqlite3.connect('data/jobs.db')
state = json.load(open('data/state.json'))
batch = state.get('current_vendor_batch', 0)
rows = conn.execute('SELECT id, name, url FROM vendor_sites WHERE batch_group = ?', (batch,)).fetchall()
for r in rows:
    print(f'{r[0]}|{r[1]}|{r[2]}')
conn.close()
"
```

For each vendor URL (up to 50):
1. Navigate to the URL using Claude in Chrome
2. Look for a search bar — if found, search for "Java"
3. Read the page text to find job listings
4. Extract: title, company (vendor name), URL
5. Insert into SQLite with `source='vendor:{vendor_name}'`
6. Skip if page times out or shows no jobs (15s timeout)

## Step 5: Report Results

```bash
cd /Users/saikrishnamadavarapu/Development/JobBoard && /Users/saikrishnamadavarapu/Development/JobBoard/venv/bin/python3 -c "
import sqlite3
conn = sqlite3.connect('data/jobs.db')
total = conn.execute('SELECT count(*) FROM jobs WHERE status = \"new\"').fetchone()[0]
print(f'Scraper complete: {total} new jobs ready for filtering')
conn.close()
"
```
