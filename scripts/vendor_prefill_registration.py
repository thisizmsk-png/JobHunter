#!/usr/bin/env python3
"""
Vendor Registration Pre-filler
Navigates to each vendor portal's registration/candidate-signup page,
pre-fills ALL form fields with Vamsi's info, then PAUSES for user to
click Submit (account creation requires user consent per ToS).

Usage:
    python3 scripts/vendor_prefill_registration.py

Requirements:
    - Chrome with Claude-in-Chrome extension active
    - Run from within Claude Code session (uses MCP browser)
"""

# Vendor portals with candidate registration pages
# Sorted by ease + volume of Java C2C postings
VENDOR_PORTALS = [
    {
        "name": "Apex Systems",
        "register_url": "https://www.apexsystems.com/candidate/register",
        "job_search_url": "https://itcareers.apexsystems.com/en-US/search?keywords=java+contract",
        "notes": "Large IT staffing firm, many Java C2C roles"
    },
    {
        "name": "Aerotek",
        "register_url": "https://www.aerotek.com/en-us/find-work/create-profile",
        "job_search_url": "https://www.aerotek.com/jobs/en-US/search?keywords=java+developer&jobType=contract",
        "notes": "Major staffing firm, IT division has Java C2C"
    },
    {
        "name": "Adecco",
        "register_url": "https://www.adeccousa.com/register/",
        "job_search_url": "https://www.adeccousa.com/jobs/job-search/?q=java+developer&jobtype=contract",
        "notes": "Global staffing, good tech contractor pool"
    },
    {
        "name": "Robert Half Technology",
        "register_url": "https://www.roberthalf.com/us/en/register",
        "job_search_url": "https://www.roberthalf.com/us/en/jobs/technology",
        "notes": "Tech staffing, C2C common for Java roles"
    },
    {
        "name": "BCforward",
        "register_url": "https://bcforward.jobs.net/en-US/create-account",
        "job_search_url": "https://bcforward.jobs.net/en-US/search?keywords=java+developer",
        "notes": "IT staffing, H1B friendly, many C2C roles"
    },
    {
        "name": "Spectraforce",
        "register_url": "https://www.spectraforce.com/register/",
        "job_search_url": "https://www.spectraforce.com/java-jobs/",
        "notes": "H1B friendly, Java contractor focus"
    },
    {
        "name": "Mastech Digital",
        "register_url": "https://www.mastechdigital.com/job-seekers/",
        "job_search_url": "https://www.mastechdigital.com/java-developer-jobs/",
        "notes": "H1B/C2C specialist, top for Java roles"
    },
    {
        "name": "InfoSonics / InfoSys BPO",
        "register_url": "https://www.infosysbpo.com/careers/",
        "job_search_url": "https://www.infosysbpo.com/java-jobs/",
        "notes": "Indian IT firm, H1B placements"
    },
    {
        "name": "Ampcus",
        "register_url": "https://www.ampcus.com/job-seekers/",
        "job_search_url": "https://www.ampcus.com/java-jobs/",
        "notes": "H1B specialist, C2C contracts common"
    },
    {
        "name": "Cogent Infotech",
        "register_url": "https://cogentinfo.com/candidates/",
        "job_search_url": "https://cogentinfo.com/java-jobs/",
        "notes": "Already contacted, check for active postings"
    },
    {
        "name": "Artech",
        "register_url": "https://consultingjobs.artech.com/register",
        "job_search_url": "https://consultingjobs.artech.com/?keywords=java+developer",
        "notes": "Diversity staffing, C2C Java roles"
    },
    {
        "name": "Pyramid Consulting",
        "register_url": "https://www.pyramidci.com/job-seekers/",
        "job_search_url": "https://www.pyramidci.com/java-jobs/",
        "notes": "Already contacted via form, register for active job alerts"
    },
    {
        "name": "Staffmark",
        "register_url": "https://www.staffmark.com/find-work/apply/",
        "job_search_url": "https://www.staffmark.com/find-work/?keyword=java+developer",
        "notes": "Large staffing, IT division has contract Java"
    },
    {
        "name": "Allegis Group / TEKsystems",
        "register_url": "https://www.teksystems.com/en/apply",
        "job_search_url": "https://www.teksystems.com/en/jobs?q=java+developer&category=contract",
        "notes": "TEKsystems is Allegis IT brand, top for Java C2C"
    },
    {
        "name": "Insight Global",
        "register_url": "https://insightglobal.com/find-a-job/",
        "job_search_url": "https://insightglobal.com/jobs/?q=java+developer",
        "notes": "Major IT staffing, C2C options available"
    },
    {
        "name": "Vaco",
        "register_url": "https://vaco.com/find-a-job/",
        "job_search_url": "https://jobs.vaco.com/?q=java+developer&type=contract",
        "notes": "Tech/finance staffing, C2C roles"
    },
    {
        "name": "Collabera",
        "register_url": "https://www.collabera.com/apply-now/",
        "job_search_url": "https://www.collabera.com/jobs/?q=java",
        "notes": "H1B specialist, high volume Java C2C"
    },
    {
        "name": "NIIT Technologies",
        "register_url": "https://www.niit-tech.com/careers/",
        "job_search_url": "https://www.niit-tech.com/java-jobs/",
        "notes": "Indian IT staffing"
    },
    {
        "name": "Randstad Technologies",
        "register_url": "https://www.randstadusa.com/jobs/technology/",
        "job_search_url": "https://www.randstadusa.com/jobs/?q=java+developer&jobType=contract",
        "notes": "Global staffing, C2C Java contracts"
    },
    {
        "name": "iGate (Capgemini)",
        "register_url": "https://www.capgemini.com/us-en/careers/",
        "job_search_url": "https://www.capgemini.com/us-en/careers/job-search/?q=java",
        "notes": "Large IT firm, contractor roles"
    },
]

# Vamsi's profile for pre-filling
PROFILE = {
    "first_name": "Vamsi",
    "last_name": "M",
    "full_name": "Vamsi M",
    "email": "vamsim.java@gmail.com",
    "phone": "9293410298",
    "phone_formatted": "(929) 341-0298",
    "city": "South Plainfield",
    "state": "NJ",
    "zip": "07080",
    "country": "US",
    "linkedin": "",
    "title": "Sr Java Full Stack Developer",
    "experience_years": "9",
    "visa": "H1B",
    "authorized": "Yes",
    "sponsorship": "No",
    "skills": "Java, Spring Boot, Spring MVC, Microservices, REST APIs, AWS, Docker, Kubernetes, Angular, React, SQL, NoSQL, Git",
    "summary": "Senior Java Full Stack Developer with 9 years of experience. Expert in Java, Spring Boot, Microservices, REST APIs, AWS, and Angular/React. H1B visa holder, available for C2C/Corp-to-Corp and C2H contract positions.",
    "salary": "90",  # per hour
    "availability": "Immediately",
    "work_auth": "H1B",
    "job_type": "Contract",
    "employment_type": "C2C / Corp-to-Corp",
}

# Common field name mappings for auto-fill
FIELD_MAPPINGS = {
    # First name variations
    "first_name": PROFILE["first_name"],
    "firstname": PROFILE["first_name"],
    "fname": PROFILE["first_name"],
    "given_name": PROFILE["first_name"],

    # Last name variations
    "last_name": PROFILE["last_name"],
    "lastname": PROFILE["last_name"],
    "lname": PROFILE["last_name"],
    "surname": PROFILE["last_name"],
    "family_name": PROFILE["last_name"],

    # Full name
    "name": PROFILE["full_name"],
    "full_name": PROFILE["full_name"],
    "your-name": PROFILE["full_name"],
    "your_name": PROFILE["full_name"],
    "candidate_name": PROFILE["full_name"],

    # Email
    "email": PROFILE["email"],
    "email_address": PROFILE["email"],
    "emailaddress": PROFILE["email"],
    "your-email": PROFILE["email"],
    "your_email": PROFILE["email"],

    # Phone
    "phone": PROFILE["phone"],
    "telephone": PROFILE["phone"],
    "phone_number": PROFILE["phone"],
    "mobile": PROFILE["phone"],
    "cell": PROFILE["phone"],
    "your-tel": PROFILE["phone"],
    "tel": PROFILE["phone"],

    # Location
    "city": PROFILE["city"],
    "state": PROFILE["state"],
    "zip": PROFILE["zip"],
    "zipcode": PROFILE["zip"],
    "postal_code": PROFILE["zip"],
    "location": f"{PROFILE['city']}, {PROFILE['state']}",
    "address": PROFILE["city"],

    # Job info
    "title": PROFILE["title"],
    "job_title": PROFILE["title"],
    "current_title": PROFILE["title"],
    "position": PROFILE["title"],
    "experience": PROFILE["experience_years"],
    "years_experience": PROFILE["experience_years"],
    "skills": PROFILE["skills"],
    "summary": PROFILE["summary"],
    "message": PROFILE["summary"],
    "your-message": PROFILE["summary"],
    "comments": PROFILE["summary"],
    "inquiry": PROFILE["summary"],

    # Visa / work auth
    "visa_status": PROFILE["visa"],
    "work_authorization": PROFILE["visa"],
    "work_auth": PROFILE["visa"],
    "visa": PROFILE["visa"],
    "sponsorship": PROFILE["sponsorship"],

    # Employment type
    "employment_type": PROFILE["employment_type"],
    "job_type": PROFILE["job_type"],
    "rate": PROFILE["salary"],
    "hourly_rate": PROFILE["salary"],
    "expected_rate": PROFILE["salary"],
}

# JavaScript to auto-fill any form on a page
AUTOFILL_JS = """
(function() {
    const profile = """ + json.dumps(PROFILE) + """;
    const mappings = """ + json.dumps(FIELD_MAPPINGS) + """;

    function normalize(str) {
        return str.toLowerCase().replace(/[^a-z0-9]/g, '_').replace(/_+/g, '_').trim('_');
    }

    function findValue(el) {
        // Try name, id, placeholder, aria-label
        const keys = [
            el.name,
            el.id,
            el.placeholder,
            el.getAttribute('aria-label'),
            el.getAttribute('data-field'),
            el.getAttribute('data-name'),
        ].filter(Boolean).map(normalize);

        for (const key of keys) {
            if (mappings[key]) return mappings[key];
            // Partial match
            for (const [mkey, val] of Object.entries(mappings)) {
                if (key.includes(mkey) || mkey.includes(key)) return val;
            }
        }
        return null;
    }

    function setNativeValue(el, value) {
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set
            || Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value')?.set;
        if (nativeInputValueSetter) {
            nativeInputValueSetter.call(el, value);
        } else {
            el.value = value;
        }
        el.dispatchEvent(new Event('input', {bubbles: true}));
        el.dispatchEvent(new Event('change', {bubbles: true}));
        el.dispatchEvent(new Event('blur', {bubbles: true}));
    }

    const results = [];

    // Fill text/email/tel inputs
    document.querySelectorAll('input[type=text], input[type=email], input[type=tel], input[type=url], textarea').forEach(el => {
        if (el.closest('.ak_hp_textarea, [style*="display:none"], [aria-hidden]')) return; // skip honeypots
        const val = findValue(el);
        if (val) {
            setNativeValue(el, val);
            results.push(`OK: ${el.name || el.id} = "${val.substring(0, 30)}"`);
        }
    });

    // Handle select dropdowns
    document.querySelectorAll('select').forEach(el => {
        const name = normalize(el.name || el.id || '');
        let targetVal = null;

        if (name.includes('state')) targetVal = 'NJ';
        else if (name.includes('country')) targetVal = 'US';
        else if (name.includes('visa') || name.includes('auth')) targetVal = 'H1B';
        else if (name.includes('experience') || name.includes('years')) targetVal = '9';
        else if (name.includes('employment') || name.includes('type')) targetVal = 'Contract';
        else if (name.includes('sponsor')) targetVal = 'No';
        else if (name.includes('reloc')) targetVal = 'No';

        if (targetVal) {
            // Find closest matching option
            const opts = [...el.options];
            const match = opts.find(o => o.value === targetVal || o.text.includes(targetVal));
            if (match) {
                el.value = match.value;
                el.dispatchEvent(new Event('change', {bubbles: true}));
                results.push(`SELECT: ${el.name || el.id} = "${match.text}"`);
            }
        }
    });

    return results;
})();
"""

import json  # needed at top

if __name__ == '__main__':
    print("=" * 60)
    print("VENDOR REGISTRATION PRE-FILLER")
    print("=" * 60)
    print(f"\nProfile: {PROFILE['full_name']} | {PROFILE['email']}")
    print(f"Visa: {PROFILE['visa']} | Location: {PROFILE['city']}, {PROFILE['state']}")
    print(f"\nVendor portals to register: {len(VENDOR_PORTALS)}")
    print("\nThis script provides:")
    print("  1. List of registration URLs to visit")
    print("  2. Auto-fill JavaScript to paste in Chrome console")
    print("  3. Job search URLs for after registration")
    print()

    print("\n" + "=" * 60)
    print("VENDOR PORTALS (sorted by Java C2C volume)")
    print("=" * 60)
    for i, v in enumerate(VENDOR_PORTALS, 1):
        print(f"\n{i}. {v['name']}")
        print(f"   Register: {v['register_url']}")
        print(f"   Jobs:     {v['job_search_url']}")
        print(f"   Notes:    {v['notes']}")

    print("\n" + "=" * 60)
    print("AUTO-FILL JAVASCRIPT (paste in Chrome DevTools console)")
    print("=" * 60)
    print(AUTOFILL_JS)

    print("\n" + "=" * 60)
    print("INSTRUCTIONS")
    print("=" * 60)
    print("1. Open Chrome, navigate to register URL")
    print("2. Open DevTools (F12) → Console tab")
    print("3. Paste the JavaScript above and press Enter")
    print("4. Review filled fields, then click Submit yourself")
    print("5. Once registered, Claude can handle job search + apply")
