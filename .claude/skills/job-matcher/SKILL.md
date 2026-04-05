---
name: job-matcher
description: >
  Scores matched jobs against the user's resume profile (0-100). Claude evaluates
  skill overlap, location match, rate match, and overall fit. Updates match_score in SQLite.
user-invocable: true
allowed-tools:
  - Bash
  - Read
---

# Job Matcher Agent

You ARE the LLM. Score each matched job against the candidate's profile.

## Step 1: Load Profile

```bash
cat /Users/saikrishnamadavarapu/Development/JobBoard/config/profile.yaml
```

## Step 2: Load Matched Jobs

```bash
cd /Users/saikrishnamadavarapu/Development/JobBoard && /Users/saikrishnamadavarapu/Development/JobBoard/venv/bin/python3 -c "
import sqlite3, json
conn = sqlite3.connect('data/jobs.db')
conn.row_factory = sqlite3.Row
jobs = conn.execute('SELECT id, title, company, location, job_type, rate, description, url FROM jobs WHERE status = \"matched\" AND match_score = 0').fetchall()
print(json.dumps([dict(j) for j in jobs], indent=2))
conn.close()
"
```

## Step 3: Score Each Job

For each job, evaluate fit on this rubric:

| Factor | Points | Criteria |
|--------|--------|----------|
| Title contains "Java" | +15 | Core skill match |
| Title contains "Full Stack" or "Fullstack" | +10 | Exact role match |
| Description mentions Spring Boot | +10 | Primary framework |
| Description mentions AWS/Cloud | +5 | Cloud experience |
| Description mentions Microservices | +5 | Architecture match |
| Description mentions React/Angular | +5 | Frontend overlap |
| Location is NJ/NY/Remote/Hybrid | +10 | Location preference |
| Rate >= $50/hr (if listed) | +10 | Rate match |
| Years experience ≤ 10 (if listed) | +5 | Level match |
| C2C/C2H explicitly mentioned | +10 | Contract type confirmed |
| Negative: requires clearance | -20 | Cannot obtain on H1B |
| Negative: requires US Citizen only | -30 | Visa restriction |

**Threshold: Apply to jobs scoring >= 40.**

## Step 4: Update Scores

For each job, run:
```bash
cd /Users/saikrishnamadavarapu/Development/JobBoard && /Users/saikrishnamadavarapu/Development/JobBoard/venv/bin/python3 -c "
import sqlite3
conn = sqlite3.connect('data/jobs.db')
conn.execute('UPDATE jobs SET match_score = {SCORE} WHERE id = {JOB_ID}')
conn.commit()
conn.close()
"
```

Replace `{SCORE}` and `{JOB_ID}` with actual values.

## Step 5: Summary

```bash
cd /Users/saikrishnamadavarapu/Development/JobBoard && /Users/saikrishnamadavarapu/Development/JobBoard/venv/bin/python3 -c "
import sqlite3
conn = sqlite3.connect('data/jobs.db')
above = conn.execute('SELECT count(*) FROM jobs WHERE status = \"matched\" AND match_score >= 40').fetchone()[0]
below = conn.execute('SELECT count(*) FROM jobs WHERE status = \"matched\" AND match_score > 0 AND match_score < 40').fetchone()[0]
unscored = conn.execute('SELECT count(*) FROM jobs WHERE status = \"matched\" AND match_score = 0').fetchone()[0]
print(f'Matcher: {above} above threshold, {below} below, {unscored} unscored')

# Show top matches
print('\nTop 10 matches:')
rows = conn.execute('SELECT title, company, location, match_score FROM jobs WHERE status = \"matched\" AND match_score >= 40 ORDER BY match_score DESC LIMIT 10').fetchall()
for r in rows:
    print(f'  [{r[3]}] {r[0]} @ {r[1]} ({r[2]})')
conn.close()
"
```
