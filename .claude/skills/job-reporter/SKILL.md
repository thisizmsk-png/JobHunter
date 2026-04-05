---
name: job-reporter
description: >
  Generates cycle summary report, updates state.json, writes daily log,
  and commits+pushes data to GitHub. Run at the end of each pipeline cycle.
user-invocable: true
model: haiku
allowed-tools:
  - Bash
  - Read
  - Write
---

# Job Reporter Agent

Summarize the current cycle and persist results.

## Step 1: Collect Stats and Update Cycle

```bash
cd /Users/saikrishnamadavarapu/Development/JobBoard && /Users/saikrishnamadavarapu/Development/JobBoard/venv/bin/python3 -c "
import sqlite3, json, datetime

conn = sqlite3.connect('data/jobs.db')

# Get current cycle stats
stats = {
    'jobs_found': conn.execute('SELECT count(*) FROM jobs').fetchone()[0],
    'jobs_new': conn.execute('SELECT count(*) FROM jobs WHERE scraped_at > datetime(\"now\", \"-2 hours\")').fetchone()[0],
    'jobs_matched': conn.execute('SELECT count(*) FROM jobs WHERE status = \"matched\"').fetchone()[0],
    'jobs_applied': conn.execute('SELECT count(*) FROM applications WHERE applied_at > datetime(\"now\", \"-2 hours\") AND status = \"applied\"').fetchone()[0],
    'jobs_failed': conn.execute('SELECT count(*) FROM applications WHERE applied_at > datetime(\"now\", \"-2 hours\") AND status != \"applied\"').fetchone()[0],
}

# Insert cycle record
conn.execute('''INSERT INTO cycles (completed_at, jobs_found, jobs_new, jobs_matched, jobs_applied, jobs_failed, status)
    VALUES (datetime('now'), ?, ?, ?, ?, ?, 'completed')''',
    (stats['jobs_found'], stats['jobs_new'], stats['jobs_matched'], stats['jobs_applied'], stats['jobs_failed']))
cycle_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
conn.commit()

# Update state.json
state = json.load(open('data/state.json'))
state['last_cycle_id'] = cycle_id
state['total_applications'] = conn.execute('SELECT count(*) FROM applications WHERE status = \"applied\"').fetchone()[0]
state['last_run_at'] = datetime.datetime.utcnow().isoformat() + 'Z'
# Advance vendor batch
max_batch = conn.execute('SELECT MAX(batch_group) FROM vendor_sites').fetchone()[0] or 0
state['current_vendor_batch'] = (state.get('current_vendor_batch', 0) + 1) % (max_batch + 1)
with open('data/state.json', 'w') as f:
    json.dump(state, f, indent=2)

conn.close()

print(f'Cycle #{cycle_id} complete:')
for k, v in stats.items():
    print(f'  {k}: {v}')
print(f'Next vendor batch: {state[\"current_vendor_batch\"]}')
"
```

## Step 2: Write Daily Log

```bash
cd /Users/saikrishnamadavarapu/Development/JobBoard && /Users/saikrishnamadavarapu/Development/JobBoard/venv/bin/python3 -c "
import sqlite3, json, datetime, os

today = datetime.date.today().isoformat()
log_path = f'data/logs/{today}.json'
os.makedirs('data/logs', exist_ok=True)

conn = sqlite3.connect('data/jobs.db')
conn.row_factory = sqlite3.Row

# Get recent applications
apps = conn.execute('''SELECT a.*, j.title, j.company, j.url
    FROM applications a JOIN jobs j ON a.job_id = j.id
    WHERE a.applied_at > datetime('now', '-2 hours')''').fetchall()

log_entry = {
    'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
    'applications': [dict(a) for a in apps],
}

# Append to daily log
if os.path.exists(log_path):
    with open(log_path) as f:
        daily = json.load(f)
else:
    daily = []
daily.append(log_entry)
with open(log_path, 'w') as f:
    json.dump(daily, f, indent=2)

conn.close()
print(f'Log written: {log_path}')
"
```

## Step 3: Git Commit and Push

```bash
cd /Users/saikrishnamadavarapu/Development/JobBoard && git add data/jobs.db data/state.json data/vendor_urls.json && git commit -m "cycle: $(/Users/saikrishnamadavarapu/Development/JobBoard/venv/bin/python3 -c "import json; s=json.load(open('data/state.json')); print(f'#{s[\"last_cycle_id\"]} — {s[\"total_applications\"]} total apps')")" && git push 2>/dev/null || echo "Push skipped (no remote or auth issue)"
```
