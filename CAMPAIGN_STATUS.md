# C2C Java Campaign — Status Report
**Candidate:** Vamsi M | vamsim.java@gmail.com | (929) 341-0298
**Target:** Sr Java Full Stack Developer | C2C $90/hr | H1B
**Location:** South Plainfield, NJ (Remote/Hybrid OK)
**Last Updated:** 2026-04-06

---

## Total Applications: 679

| Channel | Count |
|---------|-------|
| Vendor contact forms (email blast) | 416 |
| ZipRecruiter 1-click apply | 38 |
| Dice Easy Apply / Wizard | 28 |
| Direct ATS (Playwright) | ~60 |
| Indeed Smart Apply | 3 |
| Manual | 3 |
| **Total** | **679** |

---

## Application Methods Breakdown

| Method | Count |
|--------|-------|
| `auto_form` (vendor contact forms) | 373 |
| `playwright` (direct ATS) | 49 |
| `vendor_form` (vendor portals) | 43 |
| `ziprecruiter_1click` | 38 |
| `dice_wizard` | 18 |
| `easy_apply_wizard` | 10 |
| `1-click-apply` | 6 |
| `api-1click` | 5 |
| Other | 11 |

---

## Jobs Scraped by Source

| Source | Jobs |
|--------|------|
| Dice.com | 253 |
| Vendor portals | 96 |
| Indeed | 55 |
| ZipRecruiter | 38 |
| Other | 2 |

---

## Vendor Campaign (456 Vendors Total)

### What Was Done
- **416 contact forms** submitted across ~78 unique vendor domains
- Generic outreach: "Sr Java Full Stack Developer, 9 yrs, C2C $90/hr, H1B, NJ"
- This was Phase 1 — email blast to get on recruiter radar

### What's Running Now (NEW)
`scripts/vendor_portal_pipeline.py` — visits actual job listing pages on vendor sites, finds Java contract openings, and applies directly to those specific roles.

- Scrapes each vendor's `/jobs`, `/careers`, `/open-positions` page
- Searches for "Java" keywords
- Filters: skips W2-only, Lead/Architect/Principal titles
- Fills application form: name, email, phone, cover message, resume upload
- Target: 444 public vendors in batches of 50

---

## Vendor Login-Required (Manual Action Needed)

These 12 vendors require you to **create an account / log in** before applying. Please sign up and submit your profile manually:

| # | Vendor | Portal URL |
|---|--------|------------|
| 1 | **Diverse Lynx** | https://www2.jobdiva.com/portal/?a=9xjdnw687b7a7nvvdyut936kpjlgy0023blrozaecads0pdnwppcswnaaku8ji2g |
| 2 | **GTT** | https://www1.jobdiva.com/portal/?a=5cjdnwenzpqejkgxijtvgahld0va90009c0e3c8jutidwbg0unjxodtsm81az828 |
| 3 | **Mitchell Martin** | https://www.mitchellmartin.com/career-portal |
| 4 | **OnPoint Solutions** | https://pfs.aviontego.com/portals/Portals/JobBoard/JobSearch.aspx?CompanyID=PFS |
| 5 | **PRC Staffing** | https://careers.topechelon.com/portals/1b194f13-cf75-45ab-bfec-8ae9d150ca70 |
| 6 | **Procom Services** | https://portal.procomservices.com/jobs?loginType=contractor |
| 7 | **Reaction Search** | https://www.reactionsearch.com/candidate-register-login/ |
| 8 | **Synergy Staffing** | https://www1.jobdiva.com/portal/?a=itjdnww9ir46ta1ogvudrr7futlntp0ab1trx55z489xzsmaqukw2c7sm4apm4na |
| 9 | **Talascend** | https://www.talascend.com/portal/jobseekers/jobs/search |
| 10 | **VSoft Consulting** | https://www.vsoftconsulting.com/career-portal |
| 11 | **The CSI Companies** | https://thecsicompanies.com/job-portal/careers |

**For JobDiva portals (Diverse Lynx, GTT, Synergy):** Create one account and the same login works across all of them.

---

## Also Recommended — Manual Signups (Major Job Boards)

These require Indeed account for Easy Apply:

| Platform | Why | Action |
|----------|-----|--------|
| **Indeed** | 5+ Easy Apply jobs pending | Login at indeed.com, search "Java C2C contract" |
| **Dice.com** | Already logged in via Chrome | ✅ Active session |
| **Glassdoor** | 100+ contract Java jobs | Login + Easy Apply |
| **LinkedIn** | Many C2C roles | Premium helps |

---

## Filter Rules

- **Keep:** C2C, C2H, Contract, W2 Contract, 1099
- **Remove:** Full-Time, Permanent, Direct Hire, FTE, W2 Only, No C2C
- **Title must contain:** Java, Spring, J2EE, Microservices, Full Stack
- **Title exclude:** Lead, Architect, Principal, Director, Manager, VP, Chief
- **Rate:** $90/hr C2C

---

## Pipeline Architecture

```
vendor_portal_pipeline.py (NEW - running)
  └── 444 public vendor job pages
      ├── Navigate to /jobs or /careers
      ├── Search "Java"
      ├── Parse job listings
      ├── Filter (C2C eligible, Java, no Lead/Arch)
      └── Apply: fill form + upload resume

scrape_c2c.py (jobspy)
  └── Indeed + Google + ZipRecruiter
      └── "Java C2C contract" searches

dice_c2c_apply.py
  └── Dice.com Easy Apply (logged in via Chrome)

vendor_apply_with_resume.py (legacy)
  └── Resume upload to specific vendor forms
```

---

## Git History (Recent)

| Commit | Apps | Notes |
|--------|------|-------|
| dfd9a2a | 679 | CTP Consulting added, vendor form blitz complete |
| f4e083f | 678 | 78 vendors contacted via form |
| 624f412 | 675 | Vendor contact form batch |
| f9ec185 | 501 | Vendor contact forms batch |
| 6463fee | 495 | New scanner + prefill scripts |
