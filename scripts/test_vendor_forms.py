#!/usr/bin/env python3
"""
Test vendor/staffing websites for simple contact/apply forms.
Checks for name, email, phone fields and absence of reCAPTCHA/file uploads.
"""

import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}
TIMEOUT = 10

URLS = [
    (1,  "https://apnconsulting.com/job-seekers/"),
    (2,  "https://www.approfessionals.com/job-seekers/"),
    (3,  "https://appstek.com/job-seekers/"),
    (4,  "https://ascentsg.com/search/job/"),
    (5,  "https://www.assetemploymentgroup.com/jobs/"),
    (6,  "https://atrilogy.catsone.com/careers/"),
    (7,  "https://www.avidtr.com/job-search/"),
    (8,  "https://www.bachrachgroup.com/candidates/"),
    (9,  "https://www.benchmarkitsolutions.com/job-seekers/"),
    (10, "https://www.bravensinc.com/careers/"),
    (11, "https://www.brilliantfs.com/job-seekers/"),
    (12, "https://www.ccsglobaltech.com/careers/"),
    (13, "https://www.centizen.com/ats/careers/index.php"),
    (14, "https://www.boston-technology.com/career-openings/"),
    (15, "https://www.arrowstrategies.com/job-seekers/"),
    (16, "https://ascentsg.com/contact/"),
    (17, "https://www.atrinternational.com/category/it-jobs/"),
    (18, "https://www.axiustek.com/careers/"),
    (19, "https://bcforward.jobs.net/en-US/search"),
    (20, "https://www.bravens.com/careers"),
]

# Fallback URLs to try if primary fails or has no form
FALLBACK_URLS = {
    1:  "https://apnconsulting.com/contact/",
    2:  "https://www.approfessionals.com/contact/",
    3:  "https://appstek.com/contact/",
    4:  "https://ascentsg.com/contact/",
    5:  "https://www.assetemploymentgroup.com/contact/",
    7:  "https://www.avidtr.com/contact/",
    8:  "https://www.bachrachgroup.com/contact/",
    9:  "https://www.benchmarkitsolutions.com/contact/",
    10: "https://www.bravensinc.com/contact/",
    11: "https://www.brilliantfs.com/contact/",
    12: "https://www.ccsglobaltech.com/contact/",
    14: "https://www.boston-technology.com/contact/",
    15: "https://www.arrowstrategies.com/contact/",
    17: "https://www.atrinternational.com/contact/",
    18: "https://www.axiustek.com/contact/",
    19: "https://bcforward.com/contact",
    20: "https://www.bravensinc.com/contact/",
}


def check_page(url):
    """Fetch a URL and check for form fields and CAPTCHAs."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        if resp.status_code >= 400:
            return None, f"HTTP {resp.status_code}"
        html = resp.text
    except requests.exceptions.Timeout:
        return None, "TIMEOUT"
    except requests.exceptions.ConnectionError:
        return None, "CONN_ERR"
    except Exception as e:
        return None, str(e)[:30]

    soup = BeautifulSoup(html, 'html.parser')

    # Check for name field — input type=text or name/id containing 'name'
    name_inputs = soup.find_all('input', {'type': ['text', None]})
    has_name = False
    for inp in name_inputs:
        attrs = ' '.join([
            str(inp.get('name', '')),
            str(inp.get('id', '')),
            str(inp.get('placeholder', '')),
            str(inp.get('aria-label', '')),
        ]).lower()
        if re.search(r'\bname\b|fname|lname|fullname|first.name|last.name', attrs):
            has_name = True
            break

    # Check for email field
    email_inputs = soup.find_all('input', {'type': 'email'})
    if not email_inputs:
        # Also check text inputs with email in name/id
        for inp in name_inputs:
            attrs = ' '.join([
                str(inp.get('name', '')),
                str(inp.get('id', '')),
                str(inp.get('placeholder', '')),
            ]).lower()
            if 'email' in attrs:
                email_inputs.append(inp)
    has_email = len(email_inputs) > 0

    # Also check if email appears in html at all (for JS-rendered forms, at least check the raw text)
    if not has_email:
        if re.search(r'type=["\']email["\']|name=["\']email', html, re.IGNORECASE):
            has_email = True

    # Check for phone field
    phone_inputs = soup.find_all('input', {'type': 'tel'})
    if not phone_inputs:
        for inp in name_inputs:
            attrs = ' '.join([
                str(inp.get('name', '')),
                str(inp.get('id', '')),
                str(inp.get('placeholder', '')),
            ]).lower()
            if re.search(r'phone|mobile|cell|tel', attrs):
                phone_inputs.append(inp)

    # Check for file upload
    file_inputs = soup.find_all('input', {'type': 'file'})
    has_file = len(file_inputs) > 0
    if not has_file:
        if re.search(r'type=["\']file["\']', html, re.IGNORECASE):
            has_file = True

    # Check for reCAPTCHA
    has_recaptcha = bool(
        soup.find(class_=re.compile(r'g-recaptcha', re.I)) or
        soup.find(attrs={'data-sitekey': True}) or
        re.search(r'g-recaptcha|grecaptcha|recaptcha\.net|google\.com/recaptcha', html, re.IGNORECASE)
    )

    # Check for math captcha (common in some job boards)
    has_math_captcha = bool(
        soup.find(attrs={'data-first_digit': True}) or
        soup.find(attrs={'data-second_digit': True}) or
        re.search(r'data-first_digit|data-second_digit|math.captcha|mathcaptcha', html, re.IGNORECASE)
    )

    result = {
        'loads': True,
        'has_name': has_name,
        'has_email': has_email,
        'has_file': has_file,
        'has_recaptcha': has_recaptcha,
        'has_math_captcha': has_math_captcha,
        'final_url': resp.url,
    }
    return result, "OK"


def yn(val):
    return "YES" if val else "NO"


def main():
    print(f"\n{'#':<4} {'URL':<55} {'Loads':<7} {'Name':<7} {'Email':<7} {'FileUp':<8} {'reCAPT':<8} {'MathCap':<9} {'GOOD?'}")
    print("-" * 130)

    results = []
    for num, url in URLS:
        result, status = check_page(url)

        # If primary failed or has no form fields, try fallback
        tried_fallback = False
        fallback_url = FALLBACK_URLS.get(num)
        if fallback_url and (result is None or (not result['has_name'] and not result['has_email'])):
            fb_result, fb_status = check_page(fallback_url)
            if fb_result and (fb_result['has_name'] or fb_result['has_email']):
                result = fb_result
                status = fb_status
                url = fallback_url
                tried_fallback = True

        if result is None:
            display_url = url[:54]
            print(f"{num:<4} {display_url:<55} {'NO':<7} {'NO':<7} {'NO':<7} {'NO':<8} {'NO':<8} {'NO':<9} NO  ({status})")
            results.append((num, url, False, False, False, False, False, False))
        else:
            good = (
                result['loads'] and
                result['has_name'] and
                result['has_email'] and
                not result['has_file'] and
                not result['has_recaptcha']
            )
            display_url = url[:54]
            fallback_marker = " [fb]" if tried_fallback else ""
            print(f"{num:<4} {display_url:<55} {yn(result['loads']):<7} {yn(result['has_name']):<7} {yn(result['has_email']):<7} {yn(result['has_file']):<8} {yn(result['has_recaptcha']):<8} {yn(result['has_math_captcha']):<9} {'*** YES ***' if good else 'no'}{fallback_marker}")
            results.append((num, url, result['loads'], result['has_name'], result['has_email'], result['has_file'], result['has_recaptcha'], result['has_math_captcha']))

    # Summary
    good_candidates = [r for r in results if r[2] and r[3] and r[4] and not r[5] and not r[6]]
    print(f"\n{'='*130}")
    print(f"SUMMARY: {len(good_candidates)}/{len(URLS)} sites are GOOD_CANDIDATES (loads + name + email + no file upload + no reCAPTCHA)")
    if good_candidates:
        print("\nGood candidates:")
        for r in good_candidates:
            print(f"  #{r[0]}: {r[1]}")


if __name__ == '__main__':
    main()
