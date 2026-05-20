---
name: data-import
description: Import bugs from external sources - NVD (CVE vulnerabilities) and GitHub Issues
---

# Data Import Skill

## Usage
```
/data-import nvd                      # Import from NVD (CVE database)
/data-import github                   # Import from GitHub Issues
/data-import nvd --limit=20           # Import 20 CVEs
/data-import github --repo=torvalds/linux --limit=10
```

## Instructions

### Import from NVD (National Vulnerability Database)

**Step 1: Fetch CVEs**
```bash
uv run python -c "
import asyncio
from api.nvd.client import NVDClient

async def fetch_nvd(limit=10, keywords='Intel'):
    client = NVDClient()
    cves = await client.fetch_cves(keyword=keywords, limit=limit)
    print(f'Fetched {len(cves)} CVEs\n')
    for cve in cves:
        print(f'CVE ID: {cve[\"id\"]}')
        print(f'Title: {cve[\"title\"]}')
        print(f'CVSS: {cve.get(\"cvss_score\", \"N/A\")}')
        print(f'Description: {cve[\"description\"][:150]}...')
        print('---')
asyncio.run(fetch_nvd(limit=10))
"
```

**Step 2: Transform to Bug Format**
For each CVE, create a bug with:
- `title`: CVE ID
- `description`: CVE description
- `source`: "nvd"
- `external_id`: CVE ID
- `cvss_score`: From NVD data
- `cwe_id`: From NVD data (if available)
- `category`: "security"

**Step 3: Save to Database**
```bash
uv run python -c "
import asyncio
from src.bug_tracker.database.connection import get_db_connection
from src.bug_tracker.database.repositories import BugRepository
from src.bug_tracker.domain.entities import Bug
from src.bug_tracker.domain.enums import DataSource, BugCategory

async def save_bug(title, description, cvss, external_id):
    async with get_db_connection() as db:
        repo = BugRepository(db)
        # Check for duplicate
        existing = await repo.get_by_external_id(external_id)
        if existing:
            print(f'Duplicate: {external_id}')
            return
        bug = Bug(
            title=title,
            description=description,
            source=DataSource.NVD,
            external_id=external_id,
            cvss_score=cvss,
            category=BugCategory.SECURITY
        )
        await repo.create(bug)
        print(f'Created: {external_id}')
asyncio.run(save_bug('CVE-XXX', 'description', 7.5, 'CVE-XXX'))
"
```

### Import from GitHub Issues

**Step 1: Fetch Issues**
```bash
uv run python -c "
import asyncio
from api.github.client import GitHubClient

async def fetch_github(repo='intel/linux-intel-lts', limit=10):
    client = GitHubClient()
    issues = await client.fetch_issues(repo=repo, limit=limit)
    print(f'Fetched {len(issues)} issues from {repo}\n')
    for issue in issues:
        print(f'Issue #: {issue[\"number\"]}')
        print(f'Title: {issue[\"title\"]}')
        print(f'Labels: {issue.get(\"labels\", [])}')
        print(f'Body: {issue[\"body\"][:150] if issue[\"body\"] else \"N/A\"}...')
        print('---')
asyncio.run(fetch_github())
"
```

**Step 2: Transform to Bug Format**
For each issue:
- `title`: Issue title
- `description`: Issue body
- `source`: "github"
- `external_id`: "repo#number" (e.g., "intel/linux-intel-lts#123")
- `category`: Derive from labels (bug, security, performance)

**Step 3: Save to Database**
Same as NVD step 3, but with:
- `source=DataSource.GITHUB`
- Check labels for severity hints

### Default Repositories

| Repository | Focus |
|------------|-------|
| intel/linux-intel-lts | Intel Linux LTS kernel |
| AMDESE/linux | AMD Linux development |
| ARM-software/arm-trusted-firmware | ARM firmware |
| torvalds/linux | Linux kernel |

### Keywords for NVD Search

| Chip Family | Keywords |
|-------------|----------|
| Intel | "Intel processor", "Intel microcode", "Intel CPU" |
| AMD | "AMD processor", "AMD microcode" |
| ARM | "ARM processor", "ARM firmware" |
| General | "microcode", "firmware vulnerability" |

## Output Summary

After import:
```
Import Summary
==============
Source: [NVD/GitHub]
Fetched: [N] items
New bugs created: [N]
Duplicates skipped: [N]

Sample Imports:
  [CVE-XXX]: Intel processor vulnerability (CVSS: 7.5)
  [CVE-YYY]: AMD firmware issue (CVSS: 5.0)
  ...
```

## When to Run Python Script

Run `skills/data-import/Scripts/data_import.py` only if:
- Need full batch import with progress bar
- Called from frontend
- Need rate limiting and retry logic

For quick imports, follow the steps above.

## API Rate Limits

| Source | Without Token | With Token |
|--------|---------------|------------|
| NVD | 5 req/30s | 50 req/30s |
| GitHub | 60 req/hr | 5000 req/hr |

Set tokens in `.env`:
```
GITHUB_TOKEN=your_token
NVD_API_KEY=your_key
```

## Related
- NVD Client: `api/nvd/client.py`
- GitHub Client: `api/github/client.py`
