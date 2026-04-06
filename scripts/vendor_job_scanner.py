#!/usr/bin/env python3
"""
Vendor Job Scanner - Scans vendor/staffing site job boards for Java C2C contract jobs.
For each job found, checks if it can be applied to without a login (Greenhouse, Lever,
simple HTML forms). Outputs actionable apply URLs.

Usage:
    python3 scripts/vendor_job_scanner.py [--batch N] [--offset M]
"""

import json
import re
import sqlite3
import ssl
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime

# --- Config ---
KEYWORDS = ["java", "spring boot", "j2ee", "microservices", "full stack java"]
CONTRACT_TERMS = ["c2c", "corp-to-corp", "contract", "c2h", "1099", "w2 contract"]
EXCLUDE_TITLES = ["lead", "architect", "principal", "director", "manager", "vp", "chief", "staff engineer"]
BATCH_SIZE = 30
DB_PATH = "data/jobs.db"
VENDOR_JSON = "data/vendor_urls.json"

# ATS platforms that allow apply WITHOUT login
NO_LOGIN_ATS = {
    "greenhouse": re.compile(r'boards\.greenhouse\.io|grnh\.se'),
    "lever": re.compile(r'jobs\.lever\.co'),
    "ashby": re.compile(r'jobs\.ashbyhq\.com'),
    "workable": re.compile(r'apply\.workable\.com'),
    "jobvite": re.compile(r'jobs\.jobvite\.com'),
}

# ATS platforms that REQUIRE login/account
LOGIN_REQUIRED_ATS = {
    "workday": re.compile(r'myworkdayjobs\.com|wd\d+\.myworkday\.com'),
    "icims": re.compile(r'icims\.com'),
    "taleo": re.compile(r'taleo\.net'),
    "successfactors": re.compile(r'successfactors\.com'),
    "jobdiva": re.compile(r'jobdiva\.com'),
    "bullhorn": re.compile(r'bullhornstaffing\.com'),
}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.read().decode('utf-8', errors='ignore'), r.geturl()
    except Exception as e:
        return None, str(e)

def detect_ats(url, html=''):
    """Detect ATS platform from URL or page content."""
    text = (url + ' ' + html).lower()
    for name, pattern in NO_LOGIN_ATS.items():
        if pattern.search(text):
            return name, 'no_login'
    for name, pattern in LOGIN_REQUIRED_ATS.items():
        if pattern.search(text):
            return name, 'login_required'
    return 'unknown', 'unknown'

def is_relevant_title(title):
    t = title.lower()
    if any(ex in t for ex in EXCLUDE_TITLES):
        return False
    if any(kw in t for kw in KEYWORDS):
        return True
    return False

def is_contract(text):
    t = text.lower()
    return any(ct in t for ct in CONTRACT_TERMS)

def extract_job_links(html, base_url):
    """Extract job listing links from a page."""
    links = []
    # Look for job links
    pattern = re.compile(r'href=["\']([^"\']*(?:job|position|opening|career|role)[^"\']*)["\']', re.IGNORECASE)
    for match in pattern.finditer(html):
        href = match.group(1)
        if href.startswith('http'):
            links.append(href)
        elif href.startswith('/'):
            parsed = urllib.parse.urlparse(base_url)
            links.append(f"{parsed.scheme}://{parsed.netloc}{href}")
    return list(set(links))[:20]

def check_job_page(url):
    """Fetch a job page and determine if it's applyable without login."""
    html, final_url = fetch(url)
    if not html:
        return None

    # Check for apply button / link
    apply_links = re.findall(r'href=["\']([^"\']*(?:apply|application)[^"\']*)["\']', html, re.IGNORECASE)

    ats, login_type = detect_ats(final_url, html[:5000])

    # Extract title
    title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
    title = title_match.group(1).strip() if title_match else url

    # Check if it has a direct apply form (no login)
    has_form = bool(re.search(r'<form', html, re.IGNORECASE))
    has_email_field = bool(re.search(r'input[^>]*type=["\']email["\']', html, re.IGNORECASE))
    has_resume_field = bool(re.search(r'input[^>]*type=["\']file["\']', html, re.IGNORECASE))
    has_recaptcha = bool(re.search(r'g-recaptcha|data-sitekey|grecaptcha', html, re.IGNORECASE))

    return {
        'url': final_url,
        'title': title[:100],
        'ats': ats,
        'login_required': login_type == 'login_required',
        'has_form': has_form,
        'has_email': has_email_field,
        'has_resume': has_resume_field,
        'has_recaptcha': has_recaptcha,
        'apply_links': apply_links[:3],
    }

def scan_vendor(vendor, verbose=True):
    """Scan one vendor's job board URL for relevant Java contract jobs."""
    name = vendor.get('name', '')
    url = vendor.get('url', '')
    if not url:
        return []

    if verbose:
        print(f"\n[{name}] Scanning: {url}")

    html, final_url = fetch(url)
    if not html or len(html) < 500:
        if verbose:
            print(f"  SKIP: fetch failed")
        return []

    # Check if page has Java-related content
    h = html.lower()
    has_java = any(kw in h for kw in ['java', 'spring boot', 'j2ee', 'microservices'])
    has_contract = is_contract(h)

    if verbose:
        print(f"  Java content: {has_java}, Contract terms: {has_contract}")

    results = []

    # Try to add java search param to URL
    search_urls = [url]
    if '?' not in url:
        search_urls.append(url + '?q=java+contract')
        search_urls.append(url + '?keyword=java&type=contract')

    for search_url in search_urls[:2]:
        shtml, sfinal = fetch(search_url)
        if not shtml:
            continue

        # Look for job cards / listings
        sh = shtml.lower()

        # Check for iframes (ATS embedded)
        if re.search(r'<iframe[^>]*(job|career|position|apply)[^>]*>', sh):
            if verbose:
                print(f"  ATS iframe detected - needs browser")
            ats, _ = detect_ats(sfinal, shtml[:3000])
            results.append({
                'vendor': name,
                'vendor_url': url,
                'job_url': sfinal,
                'title': f'Java Contract Jobs @ {name}',
                'type': 'iframe_ats',
                'ats': ats,
                'applyable': False,
                'note': 'ATS iframe - needs browser/account'
            })
            break

        # Look for direct job links
        job_links = extract_job_links(shtml, sfinal)
        relevant = [l for l in job_links if any(kw in l.lower() for kw in ['java', 'spring', 'contract', 'software', 'developer', 'engineer'])]

        if relevant:
            if verbose:
                print(f"  Found {len(relevant)} relevant job links")
            for jlink in relevant[:5]:
                ats, login_type = detect_ats(jlink)
                applyable = login_type == 'no_login'
                results.append({
                    'vendor': name,
                    'vendor_url': url,
                    'job_url': jlink,
                    'title': f'Java job @ {name}',
                    'type': 'direct_link',
                    'ats': ats,
                    'applyable': applyable,
                    'note': f'{ats} - {"no login needed" if applyable else "login required"}'
                })

    return results

def already_applied(conn, url):
    """Check if we already applied to this job URL."""
    domain = urllib.parse.urlparse(url).netloc
    result = conn.execute(
        "SELECT id FROM jobs WHERE url LIKE ?", (f'%{domain}%',)
    ).fetchone()
    return bool(result)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Scan vendor job boards for Java C2C contract jobs')
    parser.add_argument('--batch', type=int, default=BATCH_SIZE, help='Number of vendors to scan')
    parser.add_argument('--offset', type=int, default=0, help='Start from this vendor index')
    parser.add_argument('--output', default='data/vendor_jobs.json', help='Output file for found jobs')
    parser.add_argument('--no-login-only', action='store_true', help='Only show jobs that need no login to apply')
    args = parser.parse_args()

    with open(VENDOR_JSON) as f:
        vendors = json.load(f)

    batch = vendors[args.offset:args.offset + args.batch]
    print(f"Scanning {len(batch)} vendors (offset={args.offset})...")

    conn = sqlite3.connect(DB_PATH)
    all_results = []

    for i, vendor in enumerate(batch):
        print(f"\n[{args.offset + i + 1}/{args.offset + len(batch)}]", end='')
        try:
            results = scan_vendor(vendor)
            for r in results:
                if not already_applied(conn, r['vendor_url']):
                    all_results.append(r)
            time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nInterrupted.")
            break
        except Exception as e:
            print(f"  ERROR: {e}")

    conn.close()

    # Save results
    with open(args.output, 'w') as f:
        json.dump(all_results, f, indent=2)

    print(f"\n{'='*60}")
    print(f"SCAN COMPLETE: {len(all_results)} job opportunities found")
    print(f"{'='*60}")

    # Summary by type
    no_login = [r for r in all_results if r.get('applyable')]
    iframe = [r for r in all_results if r.get('type') == 'iframe_ats']

    print(f"\nDirect apply (no login): {len(no_login)}")
    for r in no_login[:10]:
        print(f"  [{r['ats']}] {r['vendor']}: {r['job_url'][:80]}")

    print(f"\nNeeds account/browser ({len(iframe)} vendors with job boards):")
    for r in iframe[:20]:
        print(f"  [{r['ats']}] {r['vendor']}: {r['vendor_url']}")

    print(f"\nFull results saved to: {args.output}")
    print("\nNext steps:")
    print("  - For 'direct apply' jobs: run scripts/vendor_apply_nologin.py")
    print("  - For 'iframe ATS' jobs: create account on vendor site, then Claude applies via browser")

if __name__ == '__main__':
    main()
