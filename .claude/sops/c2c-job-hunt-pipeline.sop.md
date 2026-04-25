---
title: C2C Job Hunt Pipeline SOP
version: 1.0
description: Master orchestration SOP for the 10,000 C2C/C2H Java contract job application campaign
---

## Overview

Automated pipeline to find and apply to C2C/C2H Java contract roles across multiple job boards. Target profile: Vamsi M, Sr Java Full Stack Developer, H1B, South Plainfield NJ, 9 years experience. Goal: 10,000 applications.

---

## Parameters

- **target_applications** (int, default: 10000): Total application goal
- **daily_target** (int, default: 50): Applications per day on weekdays
- **boards_priority** (list): Ordered by reliability: `["dice", "ziprecruiter", "glassdoor"]`
- **contract_types** (list): `["C2C", "C2H", "Corp-to-Corp", "Contract", "W2 Contract", "1099"]`

---

## Steps

### 1. Pre-Run Checks

```bash
# Check current count
sqlite3 data/jobs.db "SELECT COUNT(*) FROM applications WHERE status='submitted';"
# Check state
cat data/state.json
# Ensure Chrome extension active (for MCP tools)
```

**MUST run on weekdays (Mon–Fri).** Weekend job boards show stale postings with no new C2C roles.

### 2. Board Execution Order

Run boards in priority order. Stop a board when pool is exhausted (all results return "Already Applied" or API errors).

#### 2.1 Dice.com (PRIMARY — Confirmed Email Delivery)

See: `dice-easy-apply.sop.md`

- Search 4 keyword variants: `"Java Developer C2C"`, `"Spring Boot Developer"`, `"Java Full Stack"`, `"Java Microservices"`
- Pages 1–3 of 7-day results
- Apply via `/wizard` URL pattern
- **Expected yield:** 5–20 new apps/day on weekdays

#### 2.2 ZipRecruiter (SECONDARY — No Email Confirmation)

See: `ziprecruiter-apply.sop.md`

- Search terms: `"Java Developer Corp to Corp"`, `"Full Stack Java C2C"`, `"J2EE Developer C2C"`, `"Spring Boot Developer C2C"`
- Batch apply via `CreateApplication` → `SubmitApplication` API
- Only submit jobs with 0 screening questions
- **Expected yield:** 0–5 new apps/day (most pool already exhausted as of Apr 5 2026)
- **Verify** at `ziprecruiter.com/profile/applications`

#### 2.3 Glassdoor Easy Apply (TERTIARY — No Email Confirmation)

See: `glassdoor-indeed-easy-apply.sop.md`

- Search: `glassdoor.com/Job/java-contract-jobs-SRCH_KO0,14.htm?jobType=contract&applicationType=1`
- 8 Easy Apply Java contract roles visible at a time
- Route through Indeed Smart Apply using React fiber click
- **Expected yield:** 2–5 new apps/day (pool refreshes slowly)
- **Verify** at `indeed.com/my-jobs`

#### 2.4 LinkedIn (BLOCKED — DO NOT USE)

User explicitly said: risk of account flag/strike. Skip entirely.

### 3. Filter Rules (apply to all boards)

| Rule | Value |
|------|-------|
| Contract types INCLUDE | C2C, C2H, Corp-to-Corp, Contract, W2 Contract, 1099 |
| Employment types EXCLUDE | Full-Time, Permanent, Direct Hire, FTE |
| Title MUST contain one of | Java, Spring Boot, J2EE, Microservices, Full Stack |
| Title EXCLUDE | Lead, Architect, Principal, Director, Manager, VP, Chief, Staff Engineer |
| Max job age | 15 days (prefer 3–7 days for freshness) |
| Skip if | "Only W2", "W2 only", "USC only", "Locals only" (for non-NJ locations) |

### 4. Database Logging

After each application:
1. `INSERT OR IGNORE INTO jobs (...)` with source, title, company, url, dedup_hash
2. `INSERT INTO applications (job_id, method, ats_platform, status)` with `status='submitted'`
3. Update `data/state.json` total_applications count

### 5. Post-Run Summary

```bash
sqlite3 data/jobs.db "
  SELECT source, COUNT(*) as count
  FROM applications a
  JOIN jobs j ON a.job_id=j.id
  GROUP BY source
  ORDER BY count DESC;
"
```

---

## Desired Outcome

- Applications recorded in SQLite with `status='submitted'`
- Dice applications confirmed via email
- ZipRecruiter/Glassdoor verified via account pages
- `state.json` updated with new total
- Git committed with summary message

---

## Board Status (as of April 5, 2026)

| Board | Apps | Status | Notes |
|-------|------|--------|-------|
| Dice | ~455 | Near saturation | Refreshes Mon–Fri morning with new postings |
| ZipRecruiter | ~40 | Saturated via API | Most jobs return `fail`/`external`/`has_q` |
| Glassdoor | ~5 | Mostly saturated | Small pool, slow refresh |
| Indeed Direct | 3 | Dead | No C2C contract filter works reliably |
| LinkedIn | 0 | BLOCKED | Account risk |
| Vendor Sites | 0 | Untested | 456 URLs in `data/vendor_urls.json` — next priority |

---

## Next Priorities (to scale from 457 → 10,000)

1. **Vendor sites** (`data/vendor_urls.json`) — 456 staffing firm URLs; simple HTML forms, no ATS
2. **Python upgrade** → `python-jobspy` (requires Python 3.11+) for automated multi-board scraping
3. **Dice weekday automation** — scheduled task at Mon–Fri 8am EST when fresh postings appear
4. **CareerBuilder / Monster** — untested boards with contract job filters

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| 0 new apps after full run | Weekend — wait until Monday; or try vendor sites |
| Dice returns only "Already Applied" | Pool saturated; wait for next day's postings |
| ZipRecruiter API all fails | Expected — pool exhausted; rely on Dice |
| No confirmation emails | Only Dice sends them; check ZipRecruiter/Indeed account pages manually |
| Chrome extension disconnected | Ensure Claude in Chrome extension is active and signed in |
| SQLite locked | Single-process; restart if stuck |
