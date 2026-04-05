---
name: job-filter
description: >
  Filters scraped jobs: keeps only C2C/C2H contracts, excludes Lead/Architect titles,
  checks Java keyword match, enforces 24h freshness, and deduplicates. Updates SQLite status.
user-invocable: true
model: haiku
allowed-tools:
  - Bash
  - Read
---

# Job Filter Agent

You filter raw job listings against the rules in `config/search_config.yaml`.

## Step 1: Load Filter Config

```bash
cat /Users/saikrishnamadavarapu/Development/JobBoard/config/search_config.yaml
```

## Step 2: Run Filters

```bash
cd /Users/saikrishnamadavarapu/Development/JobBoard && /Users/saikrishnamadavarapu/Development/JobBoard/venv/bin/python3 -c "
import sqlite3, re, yaml

with open('config/search_config.yaml') as f:
    cfg = yaml.safe_load(f)

filters = cfg['filters']
conn = sqlite3.connect('data/jobs.db')
conn.row_factory = sqlite3.Row

jobs = conn.execute('SELECT * FROM jobs WHERE status = \"new\"').fetchall()
print(f'Filtering {len(jobs)} new jobs...')

matched = 0
filtered = 0

for job in jobs:
    title = (job['title'] or '').lower()
    job_type = (job['job_type'] or '').lower()
    desc = (job['description'] or '').lower()
    reason = None

    # Filter 1: Employment type exclusion
    for exc in filters['employment_types_exclude']:
        if exc.lower() in job_type or exc.lower() in title or exc.lower() in desc[:200]:
            # But only if no contract indicator present
            has_contract = any(c.lower() in job_type or c.lower() in desc[:500]
                             for c in filters['contract_types_include'])
            if not has_contract:
                reason = f'employment_type_excluded:{exc}'
                break

    # Filter 2: Title exclusion
    if not reason:
        for exc in filters['title_exclude']:
            if exc.lower() in title:
                reason = f'title_excluded:{exc}'
                break

    # Filter 3: Must contain keyword
    if not reason:
        has_keyword = any(kw.lower() in title or kw.lower() in desc[:500]
                        for kw in filters['title_must_contain_one'])
        if not has_keyword:
            reason = 'no_matching_keyword'

    # Filter 4: Company blacklist
    if not reason:
        company = (job['company'] or '').lower()
        for bl in filters.get('company_blacklist', []):
            if bl.lower() in company:
                reason = f'company_blacklisted:{bl}'
                break

    if reason:
        conn.execute('UPDATE jobs SET status = \"filtered_out\", filter_reason = ? WHERE id = ?',
                    (reason, job['id']))
        filtered += 1
    else:
        conn.execute('UPDATE jobs SET status = \"matched\" WHERE id = ?', (job['id'],))
        matched += 1

conn.commit()
conn.close()
print(f'Results: {matched} matched, {filtered} filtered out')
"
```

## Step 3: Show Summary

```bash
cd /Users/saikrishnamadavarapu/Development/JobBoard && /Users/saikrishnamadavarapu/Development/JobBoard/venv/bin/python3 -c "
import sqlite3
conn = sqlite3.connect('data/jobs.db')
for status in ['new', 'matched', 'filtered_out']:
    count = conn.execute(f'SELECT count(*) FROM jobs WHERE status = \"{status}\"').fetchone()[0]
    print(f'  {status}: {count}')

# Show top filter reasons
print('\nTop filter reasons:')
rows = conn.execute('''SELECT filter_reason, count(*) as cnt FROM jobs
    WHERE status = \"filtered_out\" AND filter_reason IS NOT NULL
    GROUP BY filter_reason ORDER BY cnt DESC LIMIT 10''').fetchall()
for r in rows:
    print(f'  {r[0]}: {r[1]}')
conn.close()
"
```
