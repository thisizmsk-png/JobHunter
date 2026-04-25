---
title: ZipRecruiter 1-Click Apply SOP
version: 1.0
description: Apply to ZipRecruiter Easy Apply jobs via the CreateApplication/SubmitApplication API
---

## Overview

ZipRecruiter has a native apply API (`apply.engine.proto.v1beta1.API`) that can submit applications without filling forms, for jobs that support native ZipRecruiter apply. This works **only on weekdays** when fresh C2C contract jobs appear. Most jobs either redirect to external ATS or require screening questions.

> ⚠️ **Known Limitation**: Confirmation emails are NOT reliably sent by ZipRecruiter. Verify applications by checking `ziprecruiter.com/profile/applications`. Dice is the only board confirmed to send emails.

---

## Parameters

- **search_terms** (list, required): Keywords for ZipRecruiter job search
  - Proven terms: `"J2EE Developer C2C"`, `"Java Developer Corp to Corp"`, `"Full Stack Java C2C"`, `"Spring Boot Developer C2C"`
- **location** (string, default: `"US"`): Use `"New Jersey"`, `"New York"`, or `"US"` for nationwide
- **employment_type** (string, default: `"contract"`): Always `contract`
- **placement_id** (int, default: `44071`): ZipRecruiter placement ID for Easy Apply tracking

---

## Steps

### 1. Navigate to Search Results

```
URL: https://www.ziprecruiter.com/jobs-search?search={TERM}&location={LOC}&employment_type=contract&refine_by_apply_type=easy_apply
```

#### 1.1 Extract LKs from Job Cards

```javascript
const lks = [...new Set(
  [...document.querySelectorAll('article[id^="job-card-"]')]
  .map(a => a.id.replace('job-card-', ''))
)];
```

#### 1.2 Filter Already-Tried LKs

Maintain a `Set` of previously tried LKs across searches. Only process fresh LKs.

### 2. Batch Apply via API

```javascript
(async () => {
  const results = [];
  for (const lk of lks) {
    // Step 1: Create application
    const cr = await fetch('/api/apply/apply.engine.proto.v1beta1.API/CreateApplication', {
      method: 'POST', credentials: 'include',
      headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
      body: JSON.stringify({listing_key: lk, placement_id: 44071})
    });
    const cd = await cr.json();

    // Classify response
    if (cd.code === 'unknown') { results.push(lk + ':fail'); continue; }  // expired/already applied
    const ext = cd.actions?.find(a => a.jobApplyGtm)?.jobApplyGtm?.applicationId;
    if (ext) { results.push(lk + ':external'); continue; }  // redirects to external ATS
    const group = cd.actions?.find(a => a.screeningQuestions)?.screeningQuestions?.questionAnswerGroups?.[0];
    const appId = group?.applicationId;
    const qCount = group?.questions?.length || 0;
    if (!appId) { results.push(lk + ':no_id'); continue; }
    if (qCount > 0) { results.push(lk + ':has_q(' + qCount + ')'); continue; }  // skip screened

    // Step 2: Submit (0 questions only)
    const sr = await fetch('/api/apply/apply.engine.proto.v1beta1.API/SubmitApplication', {
      method: 'POST', credentials: 'include',
      headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
      body: JSON.stringify({applicationId: appId})
    });
    const sd = await sr.json();
    results.push(lk + ':' + (sd.applicationId ? 'submitted' : 'err'));
  }
  window._applyResults = results;
})();
```

#### 2.1 Result Classification

| Code | Meaning | Action |
|------|---------|--------|
| `fail` | API error (expired or already applied) | Skip |
| `external` | Redirects to external ATS (Workday, Greenhouse, etc.) | Skip via API; could apply manually |
| `no_id` | Unexpected response structure | Skip |
| `has_q(N)` | Has N screening questions | Skip (SaveScreeningAnswersGroup API unreliable) |
| `submitted` | Successfully submitted | Record in DB |

### 3. Record Submitted Applications

For each `submitted` result:

```python
import sqlite3
conn = sqlite3.connect('data/jobs.db')
# Insert job if not exists
conn.execute("""
  INSERT OR IGNORE INTO jobs (source, title, company, location, job_type, url, apply_url, dedup_hash, match_score, status)
  VALUES ('ziprecruiter', ?, ?, 'US', 'Contract', ?, ?, hex(randomblob(16)), 75, 'applied')
""", (title, company, f"https://www.ziprecruiter.com/jobs/{lk}", f"https://www.ziprecruiter.com/jobs/{lk}"))
job_id = conn.execute("SELECT id FROM jobs WHERE url LIKE ?", (f'%{lk}%',)).fetchone()[0]
conn.execute("INSERT INTO applications (job_id, method, ats_platform, status) VALUES (?, 'ziprecruiter_api', 'ziprecruiter', 'submitted')", (job_id,))
conn.commit()
```

---

## Desired Outcome

- `SubmitApplication` returns JSON with `applicationId` field
- DB row inserted
- **Note:** ZipRecruiter does NOT consistently send confirmation emails; verify via `ziprecruiter.com/profile/applications`

---

## Examples

### Example 1: Successful batch — J2EE Developer C2C

```
Search: "J2EE Developer C2C", location: US
LKs found: 20 unique
Results: 9 external, 1 has_q, 10 fail
Submitted: 0 direct submissions (pool saturated)
```

### Example 2: Fresh weekday batch — Java Developer Corp to Corp

```
Search: "Java Developer Corp to Corp", location: US
LKs found: 30 unique
Results: 3 submitted:OK, 15 fail, 8 has_q, 4 external
DB: 3 new applications inserted
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| All results are `fail` | Pool saturated; try different search term or wait until Mon morning for fresh postings |
| All results are `external` | These jobs use external ATS; must apply manually via browser |
| `SaveScreeningAnswersGroup` always fails | Known issue — API rejects all answer formats; skip screened jobs |
| Rate limit errors | Wait 5 minutes between search terms; ZipRecruiter limits ~5 consecutive searches |
| No new LKs across all search terms | Pool fully exhausted; shift to Dice or wait for weekday refresh |
| Applications not showing in ZipRecruiter account | `SubmitApplication` may not have fully registered; check `ziprecruiter.com/profile/applications` |
