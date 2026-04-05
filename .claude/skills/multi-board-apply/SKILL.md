---
name: multi-board-apply
description: >
  Apply to Java contract jobs across multiple job boards: Dice, Indeed, LinkedIn,
  and vendor staffing sites. Handles login, search, and application for each board.
  Credentials in config/profile.yaml. Use when expanding beyond Dice.
user-invocable: true
model: opus
effort: high
allowed-tools:
  - Bash
  - Read
  - Write
  - Agent
---

# Multi-Board Job Application Agent

Expands job applications beyond Dice to Indeed, LinkedIn, and vendor sites.

## Credentials
- Email: Read from config/profile.yaml → email field
- Password: Read from config/credentials.yaml → password field
- Resume: Read from config/profile.yaml → resume_path field

## Board 1: Indeed

### Login
1. Navigate to `https://secure.indeed.com/auth`
2. Enter email, click Continue
3. Enter password, click Sign In
4. If 2FA: mark as manual_review

### Search
Navigate to:
```
https://www.indeed.com/jobs?q=java+developer+c2c&l=New+Jersey&sc=0kf%3Ajt%28contract%29%3B&fromage=3
```
Filters: contract type, last 3 days, New Jersey

### Apply
- Look for "Apply now" or "Apply with Indeed" buttons
- If "Apply on company site" → mark as manual_review (external ATS)
- Indeed Easy Apply: fill form from profile.yaml, upload resume, submit

## Board 2: LinkedIn

### Login
1. Navigate to `https://www.linkedin.com/login`
2. Enter email and password
3. If CAPTCHA or 2FA: mark as manual_review

### Search
Navigate to:
```
https://www.linkedin.com/jobs/search/?keywords=java%20developer&location=New%20Jersey&f_JT=C&f_TPR=r604800
```
Filters: Contract, past week

### Apply
- LinkedIn Easy Apply only (blue "Easy Apply" button)
- Multi-step form: fill each page from profile.yaml
- Upload resume on the resume step
- Submit

## Board 3: Vendor Sites (from vendor_urls.json)

### Strategy
For each vendor URL in the current batch:
1. Navigate to the vendor's job page
2. Search for "Java Developer" if search is available
3. Look for job listings with "Apply" buttons
4. Fill application forms from profile.yaml
5. Upload resume
6. Submit

### ATS Detection
Check URL for known ATS platforms:
- myworkdayjobs.com → Workday (multi-step, complex)
- greenhouse.io → Greenhouse (single page)
- lever.co → Lever (single page)
- icims.com → iCIMS (iframe-heavy)
- jobdiva.com → JobDiva (staffing platform)

## Error Handling
- CAPTCHA → skip, mark manual_review
- Login expired → re-login with credentials
- Form validation error → retry once, then skip
- Timeout (30s) → skip
- Already applied → skip

## Recording
All applications recorded in data/jobs.db with:
- source: 'indeed', 'linkedin', 'vendor:{name}'
- ats_platform: detected platform name
- status: 'applied', 'failed', 'manual_review'
