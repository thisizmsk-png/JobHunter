---
name: job-hunt-pipeline
description: >
  Master orchestrator for the JobHunter pipeline. Runs the full cycle:
  scrape → filter → match → apply → report. Invoke hourly via scheduled task
  or manually with /job-hunt-pipeline. Spawns parallel sub-agents for scraping.
user-invocable: true
context: fork
agent: general-purpose
model: opus
effort: high
allowed-tools:
  - Bash
  - Read
  - Write
  - Agent
  - Grep
  - Glob
---

# JobHunter Pipeline Orchestrator

You are the master orchestrator for the JobHunter pipeline. Run the full
job search and application cycle end-to-end.

## Working Directory
All operations from: `/Users/saikrishnamadavarapu/Development/JobBoard`

## Pipeline Stages

Execute these in order:

### Stage 1: Pre-flight Check

```bash
cd /Users/saikrishnamadavarapu/Development/JobBoard && /Users/saikrishnamadavarapu/Development/JobBoard/venv/bin/python3 -c "
import sqlite3, json, os
# Verify DB exists
assert os.path.exists('data/jobs.db'), 'Run scripts/init_db.py first'
# Verify profile exists
assert os.path.exists('config/profile.yaml'), 'Copy config/profile.yaml.example to config/profile.yaml'
# Show state
state = json.load(open('data/state.json'))
print(f'Last cycle: #{state[\"last_cycle_id\"]}')
print(f'Vendor batch: {state[\"current_vendor_batch\"]}')
print(f'Total applications: {state[\"total_applications\"]}')
print(f'Last run: {state[\"last_run_at\"]}')
print('Pre-flight OK')
"
```

### Stage 2: Scrape (Parallel Agents)

Launch 2 parallel sub-agents:

**Agent A: Major Boards + Dice**
Spawn an Agent with prompt:
> "You are a job scraper. Work from /Users/saikrishnamadavarapu/Development/JobBoard.
> Run the python-jobspy scraping command from .claude/skills/job-scraper/SKILL.md Step 2.
> Then use Claude in Chrome to scrape Dice.com (Step 3 of the same skill).
> Report total jobs inserted."

**Agent B: Vendor Batch**
Spawn an Agent with prompt:
> "You are a vendor site scraper. Work from /Users/saikrishnamadavarapu/Development/JobBoard.
> Read data/state.json for current_vendor_batch number.
> Query vendor_sites table for that batch.
> Use Claude in Chrome to visit each vendor URL, search for Java jobs, and extract listings.
> Insert results into data/jobs.db. Report count."

Wait for both agents to complete.

### Stage 3: Filter

Run the filter logic from `.claude/skills/job-filter/SKILL.md`:

```bash
cd /Users/saikrishnamadavarapu/Development/JobBoard && /Users/saikrishnamadavarapu/Development/JobBoard/venv/bin/python3 -c "
import sqlite3, yaml

with open('config/search_config.yaml') as f:
    cfg = yaml.safe_load(f)

filters = cfg['filters']
conn = sqlite3.connect('data/jobs.db')
conn.row_factory = sqlite3.Row
jobs = conn.execute('SELECT * FROM jobs WHERE status = \"new\"').fetchall()

matched = filtered = 0
for job in jobs:
    title = (job['title'] or '').lower()
    job_type = (job['job_type'] or '').lower()
    desc = (job['description'] or '').lower()
    reason = None

    for exc in filters['employment_types_exclude']:
        if exc.lower() in job_type or exc.lower() in title:
            has_contract = any(c.lower() in job_type or c.lower() in desc[:500]
                             for c in filters['contract_types_include'])
            if not has_contract:
                reason = f'employment_excluded:{exc}'
                break

    if not reason:
        for exc in filters['title_exclude']:
            if exc.lower() in title:
                reason = f'title_excluded:{exc}'
                break

    if not reason:
        if not any(kw.lower() in title or kw.lower() in desc[:500]
                  for kw in filters['title_must_contain_one']):
            reason = 'no_keyword'

    if reason:
        conn.execute('UPDATE jobs SET status=\"filtered_out\", filter_reason=? WHERE id=?', (reason, job['id']))
        filtered += 1
    else:
        conn.execute('UPDATE jobs SET status=\"matched\" WHERE id=?', (job['id'],))
        matched += 1

conn.commit()
conn.close()
print(f'Filter: {matched} matched, {filtered} filtered')
"
```

### Stage 4: Match

For each matched job with match_score=0, evaluate fit using the rubric
from `.claude/skills/job-matcher/SKILL.md`. Read the job details and score them.

Use batch SQL to update scores:
```bash
cd /Users/saikrishnamadavarapu/Development/JobBoard && /Users/saikrishnamadavarapu/Development/JobBoard/venv/bin/python3 -c "
import sqlite3, json
conn = sqlite3.connect('data/jobs.db')
conn.row_factory = sqlite3.Row
jobs = conn.execute('SELECT id, title, company, location, job_type, rate, description FROM jobs WHERE status=\"matched\" AND match_score=0').fetchall()
print(f'{len(jobs)} jobs to score')
for j in jobs:
    print(json.dumps(dict(j)))
conn.close()
"
```

Score each job and update with the appropriate match_score value.

### Stage 5: Apply

For jobs with match_score >= 40, run the applier:
- Use Claude in Chrome to navigate to each job's URL
- Detect ATS platform from URL
- Fill form fields from config/profile.yaml
- Upload resume
- Submit and screenshot
- Record in applications table

Follow the detailed instructions in `.claude/skills/job-applier/SKILL.md`.

### Stage 6: Report

Run the reporter from `.claude/skills/job-reporter/SKILL.md`:
- Update cycles table
- Write daily log
- Update state.json (advance vendor batch)
- Git commit + push

### Done

Print final summary:
```
Pipeline cycle #{N} complete:
  Jobs scraped: X
  Jobs filtered: Y
  Jobs matched: Z
  Jobs applied: A
  Jobs failed: F
  Next vendor batch: B
```
