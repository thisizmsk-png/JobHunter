# JobHunter: Autonomous C2C/C2H Java Contract Job Application System

> **Spec v1.0** | 2026-04-04 | Status: DRAFT

---

## Phase 1: Requirements

### 1. Problem Statement

**What**: Vamsi M (Sr. Java Full Stack Developer, 9 YoE, H1B) needs to find and apply to Java C2C/C2H contract roles across 362+ vendor/staffing sites plus major job boards. Currently this is a manual, time-consuming process that misses fresh postings.

**Who**: Solo job seeker targeting contract (C2C/C2H) roles through Indian-American staffing vendor ecosystem + major boards.

**Cost of inaction**: Fresh contract roles get filled within hours. Manual searching across 362+ vendor sites is physically impossible. Missing the 24-hour posting window means missing the role entirely.

**Why now**: Active job search. Has compiled a 362-vendor list, resume, and profile YAML. Needs automation to run 24/7.

---

### 2. User Stories

**US-1: Hourly Job Discovery**
> As Vamsi, I want the system to search all job boards every hour so that I never miss a fresh Java contract posting.

**US-2: Smart Filtering**
> As Vamsi, I want only C2C/C2H contract roles (NOT full-time, NOT Lead/Architect) from the last 24 hours so that I only see relevant opportunities.

**US-3: Auto-Application**
> As Vamsi, I want the system to automatically apply to matching roles using my resume and profile so that I don't lose time on manual form-filling.

**US-4: Persistent Browser**
> As Vamsi, I want the system to use my own Chrome browser (with saved logins/cookies) instead of a temporary session so that I stay logged into job sites.

**US-5: Never-Stop Operation**
> As Vamsi, I want the system to keep running indefinitely, applying whenever the hourly schedule fires, so that coverage is continuous.

**US-6: Application Tracking**
> As Vamsi, I want to see what jobs were found, which were applied to, and which failed so that I have full visibility into my job search.

**US-7: Vendor Site Coverage**
> As Vamsi, I want the system to search beyond the 362 vendor sites in my Excel — also scrape major boards (Indeed, LinkedIn, Dice, Glassdoor, ZipRecruiter) and C2C-specific platforms.

---

### 3. Acceptance Criteria

#### AC-1: Job Discovery (US-1, US-7)
```
GIVEN the system is running
WHEN the hourly scheduler fires
THEN it searches:
  - Major boards via JobSpy (Indeed, LinkedIn, Glassdoor, ZipRecruiter, Google Jobs)
  - Dice.com via Playwright scraper
  - C2C-specific boards (CorpToCorp.org, Recruut.com)
  - A rotating batch of vendor sites from the 362-vendor list (50-75 per cycle)
AND returns all jobs posted in the last 24 hours
```

#### AC-2: Filtering (US-2)
```
GIVEN raw job listings are scraped
WHEN the filter agent processes them
THEN it keeps ONLY jobs that:
  - Match keywords: Java, Spring Boot, Microservices, AWS, Full Stack
  - Are contract type: C2C, C2H, Corp-to-Corp, Contract-to-Hire, W2 Contract
  - Exclude employment types: Full-Time, Permanent, Direct Hire
  - Exclude titles containing: Lead, Architect, Principal, Director, Manager, VP, Chief
  - Were posted within the last 24 hours
AND deduplicates against previously seen jobs (by title + company + location hash)
```

#### AC-3: Application (US-3)
```
GIVEN a filtered, matched job listing
WHEN the apply agent processes it
THEN it:
  - Navigates to the application page using the persistent Chrome session
  - Fills in profile fields from profile.yaml (name, email, phone, address, etc.)
  - Uploads the resume DOCX
  - Handles common ATS forms (Workday, Greenhouse, Lever, iCIMS, BambooHR, JobDiva)
  - Submits the application
AND logs the result (success/failure/requires-manual) to the tracking database
```

#### AC-4: Persistent Browser (US-4)
```
GIVEN Chrome is launched with --remote-debugging-port=9222
WHEN the system starts
THEN it connects via Playwright CDP (connect_over_cdp)
AND uses the existing Chrome profile with all cookies, sessions, and saved logins
AND does NOT launch a separate headless browser
```

#### AC-5: Continuous Operation (US-5)
```
GIVEN the system is started
WHEN the process runs
THEN APScheduler fires the job search pipeline every 60 minutes
AND the process runs indefinitely (daemon mode)
AND if the process crashes, supervisord/launchd restarts it automatically
AND application state persists in SQLite across restarts
```

#### AC-6: Tracking & Reporting (US-6)
```
GIVEN jobs have been processed
WHEN the user checks the dashboard or logs
THEN they can see:
  - Total jobs found per cycle
  - Jobs filtered in vs filtered out (with reasons)
  - Applications submitted (success)
  - Applications failed (with error details)
  - Jobs requiring manual intervention
  - Duplicate jobs skipped
  - Historical application log
```

---

### 4. Scope Boundaries

#### In Scope
- Hourly automated job discovery across major boards + vendor sites + C2C boards
- C2C/C2H/Contract filtering with title exclusions (Lead, Architect)
- 24-hour freshness window
- Auto-fill and submit applications on standard ATS platforms
- Resume upload (DOCX)
- Persistent Chrome browser via CDP
- SQLite job tracking and dedup
- Console/log-based reporting
- GitHub repo creation and push
- APScheduler-based daemon process

#### Out of Scope (v1)
- Web dashboard UI (console/logs only for POC)
- LinkedIn Easy Apply (requires LinkedIn-specific OAuth — Phase 2)
- Cover letter generation (Phase 2)
- Salary negotiation automation
- Interview scheduling
- Email monitoring for C2C hotlists
- Proxy rotation for anti-bot bypass (local Chrome with real profile avoids most detection)
- Mobile notifications (Phase 2 — Telegram integration)
- Account creation on vendor sites (profile.yaml has passwords but auto-signup is out of scope for safety — manual login first, then system maintains sessions)

#### Dependencies
- Chrome browser with `--remote-debugging-port=9222` must be running
- Python 3.11+ with venv
- Ollama running locally (for LLM-based job matching) OR fallback to keyword matching
- Internet connectivity
- Job board accounts already logged in via Chrome (Indeed, LinkedIn, Dice)

#### Assumptions
- Vamsi has existing accounts on major job boards (logged in via Chrome)
- Vendor sites that require accounts will be handled by manual login first; the system maintains sessions
- Job boards won't aggressively block a real Chrome profile with normal browsing patterns
- 362 vendor sites will be scraped in rotating batches (not all 362 every hour — that would trigger rate limits)

---

### 5. Non-Functional Requirements

#### Performance
- Full scrape cycle (major boards + 50-75 vendor batch) completes within 30 minutes
- Application submission per job: < 3 minutes
- SQLite queries: < 100ms

#### Reliability
- Process auto-restarts on crash (launchd plist on macOS)
- SQLite WAL mode for crash-safe writes
- Each job application is atomic — failure on one doesn't block others
- Graceful degradation: if a vendor site is down, skip and continue

#### Security
- `profile.yaml` and `vendor_sites.xlsx` are in `.gitignore` (contain PII)
- No credentials stored in code — read from profile.yaml at runtime
- Chrome profile stays local — no cloud browser sessions
- All PII (SSN, bank details) are NEVER automated — only basic profile fields

#### Observability
- Structured JSON logging (each cycle, each job, each application)
- `data/logs/` directory with daily rotation
- `data/jobs.db` SQLite with full audit trail
- Summary stats printed after each cycle

---

---

## Phase 2: Design (REVISED — Claude Code-Native Architecture)

> **Key pivot**: No separate Python application. Claude Code IS the application.
> Browser automation via Claude in Chrome MCP. Scheduling via Claude Code scheduled tasks.
> GitHub repo stores context, skills, and state so any Claude Code session can resume.
> Multi-agent orchestration via Oh-My-ClaudeCode + Hermes Agent MCP.

---

### 1. Architecture Decision Records (ADRs)

#### ADR-1: Runtime Platform
**Decision**: Claude Code itself is the runtime. No separate Python app.

**Context**: User wants multi-agent orchestration that runs inside Claude Code, not a standalone daemon.

**Alternatives considered**:
| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Claude Code + MCP tools | Zero build, uses existing browser (Claude in Chrome), LLM is built-in, scheduled tasks available | Session-based (needs scheduled task to re-invoke) | **Selected** |
| Standalone Python app (APScheduler + Playwright) | Full control, daemon mode | Separate app to build/maintain, duplicate LLM setup | Rejected |
| CrewAI / LangGraph app | Framework support | Heavy deps, separate from Claude Code | Rejected |
| Apify cloud actors | Scalable | Can't use local browser, costs money | Rejected |

**Result**: Claude Code is the orchestrator. `Claude in Chrome` MCP handles all browser automation. `Scheduled tasks` MCP handles hourly triggers. GitHub repo stores all persistent state.

---

#### ADR-2: Browser Automation
**Decision**: Claude in Chrome MCP (already connected to user's Chrome).

**Context**: User's Chrome is already connected via the Claude in Chrome extension. No need for Playwright CDP or Selenium.

**Alternatives considered**:
| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Claude in Chrome MCP | Already connected, real browser, real cookies, navigate/click/fill/screenshot/read_page built-in | Requires Chrome extension running | **Selected** |
| Playwright CDP | Full API control | Requires separate setup, not integrated with Claude Code | Rejected |
| Selenium | Well-known | Slow, not MCP-integrated | Rejected |

**Result**: All scraping and form-filling happens through Claude in Chrome MCP tools (`navigate`, `find`, `form_input`, `file_upload`, `get_page_text`, `read_page`, `computer`).

---

#### ADR-3: Multi-Agent Orchestration
**Decision**: Oh-My-ClaudeCode for parallel agent coordination + Hermes Agent MCP for messaging.

**Alternatives considered**:
| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Oh-My-ClaudeCode (OMC) | 19 agents, parallel execution via tmux, smart model routing, magic keywords, built for Claude Code | Requires npm + tmux | **Selected** for orchestration |
| Hermes Agent MCP | 40+ tools, messaging gateway (Telegram/Discord), cron, skills system, MCP server mode | Heavier setup | **Selected** for messaging + skill learning |
| Claude Code native Agent tool | Built-in, no deps | No parallel workers, no persistent state across sessions | Used as fallback |
| AutoAgent patterns | Self-improving meta-agent loop | Overkill for job search, designed for benchmarks | Borrow patterns only (keep/discard scoring) |

**Result**: Install OMC for parallel scraping agents. Install Hermes as MCP server for Telegram notifications and cross-session skill persistence. Use AutoAgent's self-improving pattern for the matcher (learns which jobs get responses).

---

#### ADR-4: Scheduling
**Decision**: Claude Code scheduled tasks (`mcp__scheduled-tasks__create_scheduled_task`).

**Alternatives considered**:
| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Claude Code scheduled tasks | Built-in, fires Claude Code sessions on cron, no infra | Task runs as a new Claude Code session each time | **Selected** |
| APScheduler in Python daemon | In-process, persistent | Requires separate Python app | Rejected (conflicts with ADR-1) |
| System cron calling Claude CLI | OS-level reliability | Cold start, no context | Rejected |
| Hermes cron | Natural language scheduling | Extra dependency for what scheduled tasks already does | Rejected |

**Result**: Create a scheduled task with `cron: "7 * * * *"` (every hour at :07) that triggers the full job search pipeline.

---

#### ADR-5: Persistent State / Data Storage
**Decision**: GitHub repo + JSON files for state. SQLite for job tracking.

**Context**: State must survive across Claude Code sessions. GitHub repo is the single source of truth.

**Alternatives considered**:
| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| GitHub repo + JSON + SQLite | Portable, any Claude Code session can clone and resume, SQLite for queries | Git push needed after each cycle | **Selected** |
| Local-only SQLite | Simple | Lost if machine changes, no cross-session context | Rejected |
| Cloud database (Supabase, etc.) | Always available | Overkill, external dependency | Rejected |

**Result**: GitHub repo stores: skills (SKILL.md files), config, vendor list, job history JSON, and SQLite DB. Each cycle commits + pushes updated state. `.gitignore` protects PII (profile.yaml, passwords).

---

### 2. Data Model

**Primary: `data/jobs.db` (SQLite, committed to repo without PII)**

```sql
CREATE TABLE jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id     TEXT,
    source          TEXT NOT NULL,           -- 'indeed', 'dice', 'vendor:artech', 'c2c:corptocorp'
    title           TEXT NOT NULL,
    company         TEXT,
    location        TEXT,
    job_type        TEXT,                    -- 'C2C', 'C2H', 'W2 Contract', 'Contract'
    rate            TEXT,
    url             TEXT NOT NULL,
    apply_url       TEXT,
    posted_date     TEXT,
    scraped_at      TEXT DEFAULT (datetime('now')),
    dedup_hash      TEXT UNIQUE NOT NULL,
    match_score     REAL DEFAULT 0,
    status          TEXT DEFAULT 'new',      -- new, filtered_out, matched, applied, failed, manual_review
    filter_reason   TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE applications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id          INTEGER NOT NULL REFERENCES jobs(id),
    applied_at      TEXT DEFAULT (datetime('now')),
    method          TEXT,                    -- 'auto_form', 'email', 'manual'
    ats_platform    TEXT,
    status          TEXT DEFAULT 'submitted',
    error_message   TEXT,
    screenshot_id   TEXT                     -- Claude in Chrome screenshot imageId
);

CREATE TABLE cycles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at      TEXT DEFAULT (datetime('now')),
    completed_at    TEXT,
    jobs_found      INTEGER DEFAULT 0,
    jobs_new        INTEGER DEFAULT 0,
    jobs_matched    INTEGER DEFAULT 0,
    jobs_applied    INTEGER DEFAULT 0,
    jobs_failed     INTEGER DEFAULT 0,
    vendor_batch    TEXT,                    -- JSON: which vendor batch was scraped
    status          TEXT DEFAULT 'running'
);

CREATE TABLE vendor_sites (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    url             TEXT NOT NULL,
    url_type        TEXT,
    last_scraped_at TEXT,
    success_count   INTEGER DEFAULT 0,
    failure_count   INTEGER DEFAULT 0,
    batch_group     INTEGER                 -- 0-6, rotates each cycle
);

CREATE INDEX idx_jobs_dedup ON jobs(dedup_hash);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_source ON jobs(source);
CREATE INDEX idx_vendor_batch ON vendor_sites(batch_group);
```

**Secondary: `data/state.json` (cycle cursor, batch pointer)**
```json
{
  "last_cycle_id": 42,
  "current_vendor_batch": 3,
  "total_applications": 156,
  "last_run_at": "2026-04-04T10:07:00Z"
}
```

---

### 3. Component Architecture (Claude Code-Native)

```
JobBoard/                              ← GitHub repo root
├── .claude/
│   ├── settings.json                  ← Claude Code project settings
│   ├── skills/
│   │   ├── job-scraper/SKILL.md       ← Scraper agent skill
│   │   ├── job-filter/SKILL.md        ← Filter agent skill
│   │   ├── job-matcher/SKILL.md       ← Matcher agent skill
│   │   ├── job-applier/SKILL.md       ← Applier agent skill (browser automation)
│   │   └── job-reporter/SKILL.md      ← Reporter agent skill
│   └── scheduled-tasks/
│       └── job-hunt-hourly/SKILL.md   ← Hourly scheduled task prompt
│
├── CLAUDE.md                          ← Project context for Claude Code
├── docs/specs/job-hunter-spec.md      ← This spec
│
├── config/
│   ├── search_config.yaml             ← Search terms, filters, thresholds (committed)
│   └── profile.yaml                   ← PII — .gitignored
│
├── data/
│   ├── jobs.db                        ← SQLite (committed, no PII)
│   ├── state.json                     ← Cycle state cursor
│   ├── vendor_urls.json               ← Extracted from vendor_sites.xlsx (committed)
│   └── logs/
│       └── 2026-04-04.json            ← Daily cycle logs
│
├── assets/
│   └── Vamsi_M Sr. Java Full Stack Developer.docx  ← .gitignored
│
├── scripts/
│   ├── init_db.py                     ← One-time: create SQLite tables + import vendors
│   └── export_vendors.py              ← One-time: xlsx → vendor_urls.json
│
├── vendor_sites.xlsx                  ← .gitignored
├── .gitignore
└── README.md
```

**Key insight**: The "agents" are Claude Code SKILL.md files, not Python modules. Each skill contains the full prompt and instructions for that pipeline stage. The orchestrator is the scheduled task prompt that invokes each skill in sequence.

---

### 4. Data Flow (Claude Code-Native)

```
┌─────────────────────────────────────────────────────────────┐
│  Claude Code Scheduled Task (hourly cron: "7 * * * *")      │
│  Prompt: "Run the job-hunt pipeline. Read CLAUDE.md first." │
└────────────────────────┬────────────────────────────────────┘
                         │ New Claude Code session starts
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  CLAUDE.md loaded → understands project context             │
│  Reads data/state.json → knows current batch, last cycle    │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼─────────────────┐
        │                │                 │
        ▼                ▼                 ▼
┌──────────────┐ ┌──────────────┐ ┌────────────────┐
│ Agent: Scrape │ │ Agent: Scrape│ │ Agent: Scrape  │
│ Major Boards  │ │ Dice.com     │ │ Vendor Batch   │
│ (python-jobspy│ │ (Claude in   │ │ (Claude in     │
│  via Bash)    │ │  Chrome MCP) │ │  Chrome MCP)   │
└──────┬───────┘ └──────┬──────┘ └──────┬─────────┘
       │                │               │
       └────────────────┼───────────────┘
                        │  All results → data/jobs.db
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  Filter Agent (Claude Code inline)                          │
│  - Read jobs with status='new' from SQLite                  │
│  - Apply contract type / title / keyword / freshness rules  │
│  - Update status to 'matched' or 'filtered_out'            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Matcher Agent (Claude Code LLM — built-in)                 │
│  - Score each matched job against resume profile            │
│  - No external LLM needed — Claude IS the LLM              │
│  - Update match_score in SQLite                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Applier Agent (Claude in Chrome MCP)                       │
│  - For each job with match_score >= 40:                     │
│    1. navigate to apply_url                                 │
│    2. read_page → detect ATS platform                       │
│    3. find form fields → form_input with profile data       │
│    4. file_upload resume DOCX                               │
│    5. click submit                                          │
│    6. screenshot confirmation                               │
│    7. Update applications table                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Reporter Agent                                             │
│  - Update cycles table                                      │
│  - Write daily log JSON                                     │
│  - Git commit + push updated data/                          │
│  - (v2) Hermes MCP → send Telegram summary                  │
└─────────────────────────────────────────────────────────────┘
```

---

### 5. Agent Detail Design

#### Agent 1: Scraper

**Three parallel sub-agents** (launched via Claude Code Agent tool):

**Sub-agent 1A: Major Boards (Bash + python-jobspy)**
```bash
python3 -c "
from jobspy import scrape_jobs
import json
jobs = scrape_jobs(
    site_name=['indeed', 'linkedin', 'glassdoor', 'zip_recruiter', 'google'],
    search_term='Java Developer C2C',
    location='New Jersey',
    results_wanted=50,
    hours_old=24,
    job_type='contract',
    country_indeed='USA',
)
print(json.dumps(jobs.to_dict('records')))
"
```
Then Claude Code parses output and inserts into SQLite.

**Sub-agent 1B: Dice.com (Claude in Chrome)**
- `navigate` to `dice.com/jobs?q=java+developer&employmentType=CONTRACTS&postedDate=ONE`
- `read_page` or `get_page_text` to extract job cards
- Parse title, company, location, URL from accessibility tree
- Paginate via `find("next page button")` + `computer(left_click)`

**Sub-agent 1C: Vendor Batch (Claude in Chrome)**
- Read `data/vendor_urls.json` → get current batch (50 URLs)
- For each URL:
  - `navigate` to vendor job page
  - `find("search bar")` → `form_input("Java")`
  - `get_page_text` → extract job listings
  - If no search: `read_page` → look for job links
  - Timeout: skip after 15s
- Increment batch pointer in `data/state.json`

---

#### Agent 2: Filter (inline in orchestrator)

Claude Code reads all `status='new'` jobs from SQLite and applies rules:

**Filter chain**:
1. **Contract type**: Keep if job_type or description contains: C2C, C2H, Corp-to-Corp, Contract-to-Hire, W2 Contract, Contract, 1099. Remove if: Full-Time, Permanent, Direct Hire, FTE.
2. **Title exclusion**: Remove if title contains (case-insensitive): Lead, Architect, Principal, Director, Manager, VP, Chief, Head of, Staff Engineer.
3. **Keyword match**: Keep if title OR description contains: Java, Spring Boot, J2EE, Microservices, Full Stack.
4. **Freshness**: Keep if posted within 24h. No date → keep.
5. **Dedup**: SHA-256 hash check against existing records.

Each rejection logged with `filter_reason`. Update `status` to `matched` or `filtered_out`.

---

#### Agent 3: Matcher (Claude Code LLM — built-in)

**No external LLM needed.** Claude Code IS the LLM. For each matched job:

Claude evaluates fit based on:
- Resume summary from `config/profile.yaml`
- Job title, description, requirements
- Location match (NJ/NY/Remote preferred)
- Rate match ($53/hr target)
- Skill overlap (Java, Spring Boot, AWS, Microservices, React)

Assigns `match_score` 0-100. Threshold: apply if >= 40.

---

#### Agent 4: Applier (Claude in Chrome MCP)

For each job with `match_score >= 40`:

1. **Navigate**: `mcp__Claude_in_Chrome__navigate(url=apply_url, tabId=TAB)`
2. **Detect ATS**: `mcp__Claude_in_Chrome__read_page(tabId=TAB)` → check URL and page structure
3. **Find form fields**: `mcp__Claude_in_Chrome__find(query="name input field", tabId=TAB)`
4. **Fill fields**: `mcp__Claude_in_Chrome__form_input(ref=REF, value=PROFILE_VALUE, tabId=TAB)`
5. **Upload resume**: `mcp__Claude_in_Chrome__file_upload(paths=[RESUME_PATH], ref=FILE_INPUT_REF, tabId=TAB)`
6. **Submit**: `mcp__Claude_in_Chrome__computer(action="left_click", ref=SUBMIT_REF, tabId=TAB)`
7. **Screenshot**: `mcp__Claude_in_Chrome__computer(action="screenshot", tabId=TAB)`
8. **Record**: Insert into `applications` table

**ATS-specific handling** (Claude reads the page and adapts):
- Workday: multi-step wizard → Claude navigates each step
- Greenhouse: single-page form → fill all at once
- Lever: similar to Greenhouse
- iCIMS: iframe-heavy → Claude navigates iframe content
- Generic: Claude uses `find` to locate fields by label text

---

#### Agent 5: Reporter

After all applications:
1. Update `cycles` table with counts
2. Write `data/logs/YYYY-MM-DD.json` with full details
3. Update `data/state.json` (increment batch, cycle count)
4. Git commit + push:
   ```bash
   git add data/ && git commit -m "cycle #N: found X, applied Y" && git push
   ```
5. (v2) Hermes MCP → `hermes send telegram "Cycle #42: 12 applied, 3 failed"`

---

### 6. External Agent Installations

#### 6a. Hermes Agent (MCP Server)
```bash
# Install Hermes
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# Configure as MCP server for Claude Code
# Add to ~/.claude/settings.json:
{
  "mcpServers": {
    "hermes": {
      "command": "hermes",
      "args": ["mcp", "serve"]
    }
  }
}
```
**Provides**: Telegram/Discord messaging, skill learning, cross-session memory, cron scheduling.

#### 6b. Oh-My-ClaudeCode (Multi-Agent Orchestration)
```bash
npm i -g oh-my-claude-sisyphus@latest
# Then in Claude Code:
/plugin install oh-my-claudecode
/setup
```
**Provides**: Parallel agent execution, smart model routing (Haiku for simple, Opus for complex), magic keywords (`autopilot:`, `ulw`), rate limit management.

**Enable experimental teams** in `~/.claude/settings.json`:
```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

#### 6c. AutoAgent Patterns (Borrowed, Not Installed)
From `kevinrgu/autoagent`, we borrow:
- **Keep/discard scoring**: After each application cycle, evaluate if the filtering/matching improved outcomes. If a job type consistently gets rejected → adjust filter.
- **Self-improving loop**: Track which applications get responses. Feed that signal back into the matcher to improve scoring.
- Not installed as a dependency — just the pattern applied in the matcher skill.

---

### 7. Error Handling

| Failure Mode | Detection | Response |
|---|---|---|
| Chrome not connected | `tabs_context_mcp` returns no tabs | Create new tab group, navigate from there |
| Vendor site timeout | Navigation takes > 15s | Skip site, log failure, continue |
| ATS form unrecognizable | `find` returns no form fields | Mark `manual_review`, screenshot, skip |
| CAPTCHA detected | Page contains CAPTCHA elements | Mark `manual_review`, skip |
| Rate limit (job board) | HTTP 429 or empty results | Back off, try next source |
| SQLite write fails | Exception on INSERT | Retry once, then log and continue |
| Git push fails | Non-zero exit | Log warning, push on next cycle |
| Scheduled task missed | Claude Code was closed | Next invocation catches up (24h window covers gaps) |

---

### 8. Security Considerations

- **`.gitignore`**: `profile.yaml`, `vendor_sites.xlsx`, `assets/*.docx` — PII never committed
- **SQLite committed without PII**: Job titles, companies, URLs are public info. No personal data in DB.
- **Chrome session**: Uses user's own browser — no credentials stored in repo
- **Rate limiting**: Human-like delays between navigations (Claude in Chrome inherently slower than raw scraping)
- **No account creation**: System applies on sites where user is already logged in
- **Passwords in profile.yaml**: Local only, never pushed to GitHub

---

### 9. Patterns Borrowed from Open-Source Job Bots

From deep research of 12+ open-source job automation projects:

| Pattern | Source | How We Use It |
|---------|--------|---------------|
| LLM-powered answer generation for freeform questions | AIHawk (28.7k stars) | Claude IS the LLM — reads question, generates answer inline |
| ATS-specific form detection (Workday DOM structure) | job_app_filler, Workday-Application-Automator | Claude in Chrome `read_page` detects Workday's custom web components |
| ATS-specific form detection (Lever/Greenhouse) | workpls | URL pattern matching + page structure analysis |
| Multi-platform concurrent scraping | JobSpy (3.1k stars) | python-jobspy for 5 boards simultaneously |
| Dedup with status lifecycle | JobFunnel (1.8k stars) | SQLite with status progression: new → matched → applied |
| Stealth/anti-detection (randomized intervals) | Auto_job_applier_linkedIn | Claude in Chrome is inherently slow (~human speed) |
| Resume-JD match scoring | ApplyEase (pgvector) | Claude scores directly — no embedding DB needed |
| FAQ answer caching | JobHuntr (Ollama) | Cache common ATS question answers in `data/faq_cache.json` |
| Company blacklist | JobHuntr | `config/search_config.yaml` → `company_blacklist` array |
| Dry-run mode | EasyApplyJobsBot | `--dry-run` flag: scrape + filter + match, skip apply |
| Self-improving scoring | AutoAgent (keep/discard) | Track which applications get callbacks, adjust matcher |

**Key ATS platform coverage** (from research):
| ATS | Market Share | Detection Signal | Form Complexity |
|-----|-------------|------------------|-----------------|
| Workday | ~35% of Fortune 500 | `myworkdayjobs.com`, `wd5.myworkday` | High (multi-step wizard, custom components) |
| Greenhouse | ~25% of tech | `greenhouse.io`, `boards.greenhouse` | Medium (single page, standard HTML) |
| Lever | ~15% of startups | `lever.co`, `jobs.lever.co` | Low (clean single page) |
| iCIMS | ~20% enterprise | `icims.com` | High (iframe-heavy) |
| JobDiva | Common in staffing | `jobdiva.com` | Medium |
| SmartRecruiters | Growing | `smartrecruiters.com` | Medium |
| BambooHR | SMB | `bamboohr.com` | Low |

---

### 10. Portability Design ("Clone + Open Claude Code = Working")

The GitHub repo must be self-contained so anyone can:
1. `git clone` the repo
2. Open Claude Code in the directory
3. Add their own `config/profile.yaml` (from template)
4. Start the scheduled task

**What makes this work:**
- `CLAUDE.md` — full project context, commands, architecture, failure modes
- `.claude/skills/` — all 5 agent skills checked into git
- `.claude/agents/` — sub-agent definitions for parallel work
- `.claude/settings.json` — project-level MCP config and permissions
- `config/profile.yaml.example` — template for user to fill in
- `config/search_config.yaml` — search terms, filters, thresholds (committed)
- `data/jobs.db` — SQLite with schema pre-created (committed empty)
- `data/vendor_urls.json` — extracted from Excel (committed)
- `scripts/init_db.py` — one-time setup script

**What stays local (.gitignored):**
- `config/profile.yaml` (PII)
- `assets/*.docx` (resume)
- `vendor_sites.xlsx` (original Excel)
- `.claude/settings.local.json` (personal overrides)
- `CLAUDE.local.md` (personal notes)

---

## Phase 3: Tasks (Atomic Plan)

### 1. Task Decomposition

#### Task Group A: Repository Setup (Sequential)

**A1: Initialize GitHub repo**
```
- Create repo: gh repo create JobHunter --public --clone
- Or init existing: cd JobBoard && git init && gh repo create
- Acceptance: `gh repo view` returns valid repo
```

**A2: Create directory structure**
```
- Create: .claude/skills/, .claude/agents/, config/, data/, data/logs/, assets/, scripts/, docs/specs/
- Acceptance: `find .claude/skills -type d | wc -l` >= 5
```

**A3: Create .gitignore**
```
Contents:
  config/profile.yaml
  assets/*.docx
  vendor_sites.xlsx
  .claude/settings.local.json
  CLAUDE.local.md
  data/logs/
  __pycache__/
  *.pyc
  .DS_Store
- Acceptance: `git status` does not show profile.yaml after creation
```

**A4: Create config/profile.yaml.example**
```
- Copy profile.yaml, replace all PII with placeholders
- Acceptance: File exists, contains no real email/phone/address
```

**A5: Create config/search_config.yaml**
```yaml
search:
  keywords:
    primary: ["Java Developer", "Java Full Stack", "Sr Java Developer"]
    secondary: ["Spring Boot Developer", "Java Microservices", "J2EE Developer"]
  location: "New Jersey"
  radius_miles: 50
  hours_old: 24

filters:
  contract_types_include:
    - "C2C"
    - "C2H"
    - "Corp-to-Corp"
    - "Contract-to-Hire"
    - "W2 Contract"
    - "Contract"
    - "1099"
  employment_types_exclude:
    - "Full-Time"
    - "Permanent"
    - "Direct Hire"
    - "FTE"
  title_exclude:
    - "Lead"
    - "Architect"
    - "Principal"
    - "Director"
    - "Manager"
    - "VP"
    - "Chief"
    - "Head of"
    - "Staff Engineer"
  title_must_contain_one:
    - "Java"
    - "Spring Boot"
    - "J2EE"
    - "Microservices"
    - "Full Stack"
  company_blacklist: []

matching:
  min_score: 40
  preferred_locations: ["New Jersey", "New York", "Remote", "Hybrid"]
  target_rate: "$53/hr"

vendor_batch_size: 50
```
```
- Acceptance: File parses as valid YAML
```

**A6: Export vendor_urls.json from Excel**
```
- Python script reads vendor_sites.xlsx Sheet "📋 URL List"
- Writes data/vendor_urls.json: array of {name, url, url_type}
- Acceptance: JSON file has 362 entries
```

**A7: Initialize SQLite database**
```
- scripts/init_db.py creates all tables from Phase 2 data model
- Import vendor_urls.json into vendor_sites table with batch_group assignments
- Acceptance: `sqlite3 data/jobs.db ".tables"` returns 4 tables
```

---

#### Task Group B: CLAUDE.md + Project Context (Sequential)

**B1: Write CLAUDE.md**
```
Sections:
  1. What This Project Does (1 paragraph)
  2. Quick Start (3 commands)
  3. How It Works (agent pipeline description)
  4. Project Structure (tree with annotations)
  5. Configuration (search_config.yaml + profile.yaml)
  6. Data Flow (ASCII diagram)
  7. Scheduled Task Setup
  8. Common Failure Modes + Fixes
  9. Development Conventions
- Acceptance: Under 200 lines. New Claude Code session understands project.
```

---

#### Task Group C: Claude Code Skills (Parallel — no dependencies between skills)

**C1: Skill — job-scraper**
```
.claude/skills/job-scraper/SKILL.md
- Frontmatter: name, description, context: fork, agent: general-purpose
- Body: Instructions to scrape Indeed/LinkedIn/Glassdoor/ZipRecruiter/Google via python-jobspy
  + Dice via Claude in Chrome + vendor batch via Claude in Chrome
- References: references/jobspy-usage.md, references/vendor-scraping.md
- Acceptance: /job-scraper runs and returns job data
```

**C2: Skill — job-filter**
```
.claude/skills/job-filter/SKILL.md
- Reads new jobs from SQLite
- Applies filter chain (contract type → title exclusion → keyword → freshness → dedup)
- Updates status to matched/filtered_out with reason
- Acceptance: After running, jobs table has no status='new' rows
```

**C3: Skill — job-matcher**
```
.claude/skills/job-matcher/SKILL.md
- Reads matched jobs from SQLite
- Claude evaluates fit against profile summary
- Assigns match_score 0-100
- Acceptance: All matched jobs have match_score > 0
```

**C4: Skill — job-applier**
```
.claude/skills/job-applier/SKILL.md
- For each job with score >= threshold:
  1. Open in Claude in Chrome
  2. Detect ATS platform
  3. Fill form fields from profile
  4. Upload resume
  5. Submit
  6. Screenshot + record
- ATS-specific handling: Workday (multi-step), Greenhouse (single page), Lever, iCIMS
- Acceptance: Applications table has entries for attempted jobs
```

**C5: Skill — job-reporter**
```
.claude/skills/job-reporter/SKILL.md
- Summarize cycle stats
- Write daily log JSON
- Update state.json
- Git commit + push
- Acceptance: data/logs/ has today's file, git log shows commit
```

---

#### Task Group D: Orchestrator + Scheduled Task (Sequential, depends on C)

**D1: Skill — job-hunt-pipeline (orchestrator)**
```
.claude/skills/job-hunt-pipeline/SKILL.md
- Master skill that runs the full pipeline:
  1. Read state.json for current batch
  2. Spawn scraper agents (parallel via Agent tool)
  3. Run filter (inline)
  4. Run matcher (inline)
  5. Run applier (sequential, one job at a time)
  6. Run reporter
- Acceptance: /job-hunt-pipeline executes full cycle end-to-end
```

**D2: Create scheduled task**
```
mcp__scheduled-tasks__create_scheduled_task:
  taskId: "job-hunt-hourly"
  cronExpression: "7 * * * *"
  prompt: |
    You are the JobHunter pipeline. Read CLAUDE.md for context.
    Run the /job-hunt-pipeline skill to search for and apply to jobs.
    If any step fails, log the error and continue to the next step.
    Always commit and push results at the end.
  description: "Hourly C2C/C2H Java job search and auto-apply pipeline"
- Acceptance: `mcp__scheduled-tasks__list_scheduled_tasks` shows task enabled
```

---

#### Task Group E: Agent Definitions (Parallel)

**E1: Agent — scraper-agent**
```
.claude/agents/scraper-agent.md
- model: sonnet (fast for scraping)
- tools: Bash, Claude in Chrome MCP tools, Read, Write
- Purpose: Run scraping sub-tasks in parallel
```

**E2: Agent — applier-agent**
```
.claude/agents/applier-agent.md
- model: opus (smart for form filling)
- tools: Claude in Chrome MCP tools, Read, Write, Bash
- Purpose: Navigate ATS forms, fill fields, submit applications
```

---

#### Task Group F: External Tools (Sequential)

**F1: Install python-jobspy**
```
pip install python-jobspy
- Acceptance: python3 -c "from jobspy import scrape_jobs; print('OK')"
```

**F2: Install Hermes Agent (optional — for Telegram notifications)**
```
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
- Configure as MCP server in project settings
- Acceptance: hermes --version returns version
```

**F3: Install Oh-My-ClaudeCode (optional — for parallel orchestration)**
```
npm i -g oh-my-claude-sisyphus@latest
- Acceptance: omc --version returns version
```

---

#### Task Group G: POC Validation (Sequential, depends on all above)

**G1: Dry-run test — scrape only**
```
- Run /job-scraper manually
- Verify jobs appear in SQLite
- Acceptance: SELECT count(*) FROM jobs > 0
```

**G2: Dry-run test — filter + match**
```
- Run /job-filter then /job-matcher
- Verify filtered and scored jobs
- Acceptance: SELECT count(*) FROM jobs WHERE status='matched' AND match_score > 0 > 0
```

**G3: Dry-run test — apply one job**
```
- Pick one matched job, run applier manually
- Verify Claude in Chrome navigates, fills, screenshots
- Acceptance: applications table has 1 entry
```

**G4: Full pipeline test**
```
- Run /job-hunt-pipeline end-to-end
- Verify: scrape → filter → match → apply → report → git push
- Acceptance: cycles table has 1 completed entry
```

**G5: Schedule activation**
```
- Enable the hourly scheduled task
- Wait for one fire
- Verify new cycle in data/
- Acceptance: Cycle #2 appears in logs
```

---

### 2. Dependency Graph

```
A1 → A2 → A3 → A4 ──┐
                      ├──→ B1 ──→ D1 → D2 → G4 → G5
A5 ──────────────────┘            ↑
A6 → A7 ─────────────────────────┤
                                  │
C1 ┐                              │
C2 ├── (parallel) ───────────────→┤
C3 │                              │
C4 ┘                              │
C5 ──────────────────────────────→┤
                                  │
E1 ┐                              │
E2 ┘── (parallel) ───────────────→┤
                                  │
F1 ──────────────────────────────→┤
F2 ── (optional) ────────────────→┤
F3 ── (optional) ────────────────→┘

G1 → G2 → G3 → G4 → G5 (sequential validation)
```

**Parallelizable**:
- C1, C2, C3, C4, C5 (all skills independent)
- E1, E2 (agent defs independent)
- A4, A5, A6 (config files independent)

**Sequential gates**:
- A7 depends on A6 (vendor data)
- D1 depends on all C tasks (skills must exist)
- G tests are sequential (each validates a layer)

---

### 3. Test Strategy

| Level | What | How | Target |
|-------|------|-----|--------|
| Unit | SQLite schema + queries | `scripts/init_db.py` + manual SQL verification | All 4 tables created, indexes work |
| Unit | Filter logic | Feed known job data, verify correct filtering | 100% of filter rules tested |
| Unit | Dedup hash | Insert duplicate, verify rejection | Hash collision = rejected |
| Integration | JobSpy scraping | Run python-jobspy with live boards | Returns > 0 jobs for "Java Developer C2C NJ" |
| Integration | Claude in Chrome scraping | Navigate to Dice, extract job cards | Returns structured job data |
| Integration | Form fill | Navigate to a test Greenhouse/Lever form, fill fields | All fields populated correctly |
| E2E | Full pipeline | /job-hunt-pipeline dry run | Complete cycle logged in cycles table |
| E2E | Scheduled fire | Wait for hourly cron | New cycle auto-created |

---

### 4. Rollback Plan

| Scenario | Rollback |
|----------|----------|
| Bad application submitted | Can't undo — but screenshot + log enables manual follow-up |
| SQLite corrupted | `git checkout data/jobs.db` from last good commit |
| Skill broken | `git log .claude/skills/` → `git checkout <sha> -- .claude/skills/job-X/` |
| Vendor batch pointer wrong | Edit `data/state.json` manually |
| Scheduled task misfiring | `mcp__scheduled-tasks__update_scheduled_task(enabled=false)` |
| Need to pause everything | Disable scheduled task + stop Claude Code session |

---

## Appendix: Reference Projects

| Project | Stars | What We Borrow |
|---------|-------|----------------|
| [AIHawk](https://github.com/feder-cr/Jobs_Applier_AI_Agent_AIHawk) | 28.7k | LLM answer generation, YAML config pattern |
| [JobSpy](https://github.com/speedyapply/JobSpy) | 3.1k | Multi-board concurrent scraping library |
| [job_app_filler](https://github.com/berellevy/job_app_filler) | — | Workday + iCIMS form detection patterns |
| [workpls](https://github.com/jeffistyping/workpls) | — | Lever + Greenhouse form filling |
| [JobFunnel](https://github.com/PaulMcInnis/JobFunnel) | 1.8k | Dedup + status lifecycle tracking |
| [JobHuntr](https://github.com/lookr-fyi/job-application-bot-by-ollama-ai) | — | FAQ caching, company blacklist |
| [AutoAgent](https://github.com/kevinrgu/autoagent) | — | Self-improving keep/discard scoring |
| [Hermes Agent](https://github.com/NousResearch/hermes-agent) | 25k | MCP messaging, skill learning |
| [Oh-My-ClaudeCode](https://github.com/yeachan-heo/oh-my-claudecode) | 23.9k | Parallel agent orchestration |

---

## End of Spec

**Ready for implementation. Proceed with Task Group A (repo setup) first.**
