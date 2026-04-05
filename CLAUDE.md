# JobHunter — Claude Code-Native Job Application System

> Autonomous C2C/C2H Java contract job search and auto-apply pipeline.
> Runs entirely inside Claude Code. No separate app to build or maintain.

---

## What This Project Does

Hourly scheduled pipeline that:
1. Scrapes job boards (Indeed, LinkedIn, Glassdoor, ZipRecruiter, Google, Dice) via python-jobspy + Claude in Chrome
2. Scrapes 456 vendor/staffing sites in rotating batches of 50
3. Filters for C2C/C2H contract roles only (no Full-Time, no Lead/Architect)
4. Matches jobs against resume using Claude's built-in LLM
5. Auto-applies via Claude in Chrome (form fill + resume upload)
6. Tracks everything in SQLite and commits to GitHub

---

## Quick Start

```bash
# 1. First-time setup (already done if cloning from existing repo)
python3 scripts/export_vendors.py   # xlsx → vendor_urls.json
python3 scripts/init_db.py          # create SQLite tables + import vendors

# 2. Copy and fill in your profile
cp config/profile.yaml.example config/profile.yaml
# Edit config/profile.yaml with your details

# 3. Place your resume
cp "Your Resume.docx" assets/

# 4. Install python-jobspy
pip3 install python-jobspy

# 5. Run pipeline manually (or let scheduled task handle it)
# Use /job-hunt-pipeline skill in Claude Code
```

---

## Project Structure

```
JobBoard/
├── CLAUDE.md                          ← You are here
├── .claude/
│   ├── skills/
│   │   ├── job-scraper/SKILL.md       ← Scrapes all job boards
│   │   ├── job-filter/SKILL.md        ← Filters C2C/C2H, excludes Lead/Architect
│   │   ├── job-matcher/SKILL.md       ← Scores job-resume fit (0-100)
│   │   ├── job-applier/SKILL.md       ← Fills forms + submits via Chrome
│   │   ├── job-reporter/SKILL.md      ← Logs cycle + git push
│   │   └── job-hunt-pipeline/SKILL.md ← Master orchestrator
│   └── agents/
│       ├── scraper-agent.md           ← Fast scraping sub-agent (sonnet)
│       └── applier-agent.md           ← Smart form-filling sub-agent (opus)
├── config/
│   ├── search_config.yaml             ← Search terms, filters, thresholds
│   └── profile.yaml                   ← YOUR profile (gitignored)
├── data/
│   ├── jobs.db                        ← SQLite: jobs, applications, cycles
│   ├── state.json                     ← Cycle cursor, batch pointer
│   ├── vendor_urls.json               ← 456 vendor site URLs
│   └── logs/                          ← Daily cycle logs (gitignored)
├── assets/                            ← Resume DOCX (gitignored)
├── scripts/
│   ├── init_db.py                     ← DB setup + vendor import
│   └── export_vendors.py              ← xlsx → JSON
└── docs/specs/job-hunter-spec.md      ← Full spec
```

---

## How the Pipeline Works

```
Scheduled Task (hourly) → /job-hunt-pipeline
  │
  ├─ Agent: job-scraper (parallel sub-agents)
  │    ├─ python-jobspy → Indeed, LinkedIn, Glassdoor, ZipRecruiter, Google
  │    ├─ Claude in Chrome → Dice.com
  │    └─ Claude in Chrome → Vendor batch (50 sites)
  │
  ├─ job-filter (inline)
  │    └─ Contract type → Title exclusion → Keyword → Freshness → Dedup
  │
  ├─ job-matcher (inline — Claude IS the LLM)
  │    └─ Score 0-100 against resume profile
  │
  ├─ job-applier (Claude in Chrome)
  │    └─ Navigate → Detect ATS → Fill form → Upload resume → Submit
  │
  └─ job-reporter
       └─ Update DB → Write log → Git commit + push
```

---

## Key Files

| File | Purpose |
|------|---------|
| `config/search_config.yaml` | All search terms, filters, score thresholds |
| `config/profile.yaml` | Your PII — name, email, address, skills, resume path |
| `data/jobs.db` | SQLite with 4 tables: jobs, applications, cycles, vendor_sites |
| `data/state.json` | Current vendor batch, last cycle ID |
| `data/vendor_urls.json` | 456 vendor URLs extracted from Excel |

---

## Filter Rules (from search_config.yaml)

- **Keep**: C2C, C2H, Contract, W2 Contract, 1099
- **Remove**: Full-Time, Permanent, Direct Hire, FTE
- **Title must contain**: Java, Spring Boot, J2EE, Microservices, Full Stack
- **Title exclude**: Lead, Architect, Principal, Director, Manager, VP, Chief
- **Freshness**: Last 24 hours only
- **Dedup**: SHA-256(title + company + location)

---

## ATS Platform Detection

| Signal in URL | Platform | Complexity |
|---------------|----------|------------|
| `myworkdayjobs.com` | Workday | High (multi-step wizard) |
| `greenhouse.io` | Greenhouse | Medium (single page) |
| `lever.co` | Lever | Low (clean form) |
| `icims.com` | iCIMS | High (iframe-heavy) |
| `jobdiva.com` | JobDiva | Medium |
| `smartrecruiters.com` | SmartRecruiters | Medium |

---

## Common Failure Modes

| Symptom | Fix |
|---------|-----|
| Chrome not connected | Ensure Claude in Chrome extension is active |
| python-jobspy import error | `pip3 install python-jobspy` |
| No jobs found | Check search_config.yaml keywords, expand radius |
| CAPTCHA on vendor site | Skip — marked as manual_review |
| Git push fails | Check remote: `git remote -v` |
| SQLite locked | Should not happen (single process) — restart |

---

## Development Conventions

- All data in `data/` — SQLite for structured, JSON for config/state
- Skills in `.claude/skills/` — one directory per agent
- Agents in `.claude/agents/` — sub-agent definitions for parallel work
- Never hardcode profile values — always read from `config/profile.yaml`
- PII stays local — `.gitignore` protects profile, resume, vendor Excel
- Log everything — every cycle, every filter decision, every application result
