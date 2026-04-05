---
name: dice-auto-apply
description: >
  Rapid-fire Dice Easy Apply automation. Searches Dice for Java contract jobs,
  extracts unapplied UUIDs, and applies via the 2-step wizard (Next → Submit).
  Handles 2-step and 3-step wizards. Skips jobs with custom questions.
user-invocable: true
model: sonnet
allowed-tools:
  - Bash
  - Read
  - Write
---

# Dice Auto-Apply Agent

Applies to ALL unapplied Java contract jobs on Dice via Easy Apply.

## Prerequisites
- Must be logged into Dice in Chrome (Vamsi M account)
- Claude in Chrome MCP must be connected

## Search Terms to Rotate
```
java developer, java full stack, java microservices, spring boot developer,
java C2C, senior software engineer java, java backend developer,
java aws developer, J2EE developer, java react developer,
java angular developer, java kafka developer
```

## Step 1: Search and Extract UUIDs

Navigate to Dice search with contract filter:
```
https://www.dice.com/jobs?q={SEARCH_TERM}&countryCode=US&radius=200&radiusUnit=mi&page={PAGE}&pageSize=20&filters.employmentType=CONTRACTS&filters.postedDate=SEVEN&language=en
```

Wait 4 seconds, then extract unapplied UUIDs via javascript_exec:
```javascript
const links=document.querySelectorAll('a[href*="/job-detail/"]');
const seen=new Set();const uuids=[];
links.forEach(a=>{
    const t=a.textContent.trim();
    if(!t||t.length<8||t==='Easy Apply'||seen.has(a.href))return;
    seen.add(a.href);
    let c=a;for(let i=0;i<8;i++){if(c.parentElement)c=c.parentElement;}
    const txt=c.innerText||'';
    if(!txt.includes('Applied')){
        const l=t.toLowerCase();
        const ex=l.includes('lead')||l.includes('architect')||l.includes('manager')
            ||l.includes('director')||l.includes('principal');
        if(!ex)uuids.push(a.href.split('/job-detail/')[1]);
    }
});
JSON.stringify({count:uuids.length,uuids});
```

## Step 2: Apply to Each UUID

For each UUID:
1. Navigate to `https://www.dice.com/job-applications/{UUID}/wizard`
2. Wait 4 seconds
3. Run auto-apply JS:
```javascript
function a(){
    const b=document.querySelectorAll('button');
    for(const x of b){
        const t=x.textContent.trim();
        if(t==='Submit'){x.click();return'done';}
        if(t==='Next'){x.click();setTimeout(a,2500);return'next';}
    }
    const s=document.querySelector('button[type="submit"]');
    if(s){s.click();setTimeout(a,2500);return'sub';}
    return'none';
}
a();
```
4. Wait 6 seconds
5. Check tab title:
   - "Application Success" → recorded as applied
   - "Already Applied" → skip
   - Still on wizard at 66% progress → has custom questions, SKIP
   - "Leave site?" dialog → use `window.onbeforeunload=null` then navigate away

## Step 3: Record in SQLite

```bash
cd /Users/saikrishnamadavarapu/Development/JobBoard && /Users/saikrishnamadavarapu/Development/JobBoard/venv/bin/python3 -c "
import sqlite3, hashlib
conn = sqlite3.connect('data/jobs.db')
# For each applied UUID:
url = 'https://www.dice.com/job-detail/{UUID}'
dedup = hashlib.sha256(f'dice-{UUID}'.encode()).hexdigest()
conn.execute('''INSERT OR IGNORE INTO jobs (source, title, company, location, job_type, url, apply_url, dedup_hash, status, match_score)
    VALUES ('dice', 'Java Developer (Dice)', '', '', 'Contract', ?, ?, ?, 'applied', 65)''', (url, url, dedup))
jid = conn.execute('SELECT id FROM jobs WHERE url = ?', (url,)).fetchone()[0]
conn.execute('INSERT OR IGNORE INTO applications (job_id, method, ats_platform, status) VALUES (?, \"auto_form\", \"dice\", \"applied\")', (jid,))
conn.execute('UPDATE jobs SET status = \"applied\" WHERE id = ?', (jid,))
conn.commit()
conn.close()
"
```

## Performance
- ~10 seconds per application (4s load + 6s submit)
- ~6 applications per minute
- ~360 applications per hour theoretical max
- Actual: ~30-40/hour accounting for duplicates, 3-step wizards, and page loads
