---
name: bug-report
description: Generate bug tracking reports - summary, security, component breakdown, chip family analysis
---

# Bug Report Skill

## Usage
```
/bug-report summary              # Overall statistics
/bug-report security             # Security bugs only  
/bug-report component            # Breakdown by component
/bug-report chip                 # Breakdown by chip family
```

## Instructions

### Summary Report

**Step 1: Get Statistics**
```bash
uv run python -c "
import asyncio
from src.bug_tracker.database.connection import get_db_connection
from src.bug_tracker.database.repositories import BugRepository

async def get_stats():
    async with get_db_connection() as db:
        repo = BugRepository(db)
        
        # Total count
        total = await db.count('bugs')
        print(f'Total Bugs: {total}')
        
        # By status
        by_status = await repo.count_by_status()
        print(f'\nBy Status:')
        for status, count in by_status.items():
            print(f'  {status}: {count}')
        
        # By severity
        by_severity = await repo.count_by_severity()
        print(f'\nBy Severity:')
        for sev, count in by_severity.items():
            print(f'  {sev}: {count}')
        
        # Open vs closed
        open_count = by_status.get('new', 0) + by_status.get('triaged', 0) + by_status.get('in_progress', 0)
        closed_count = by_status.get('closed', 0) + by_status.get('resolved', 0)
        print(f'\nOpen: {open_count}, Closed: {closed_count}')

asyncio.run(get_stats())
"
```

**Step 2: Format Output**
```
Bug Tracking Summary Report
===========================
Generated: [current datetime]

Total Bugs: [N]
  - Open: [N] ([%])
  - Closed: [N] ([%])

By Severity:
  Critical: [N] ([%])
  High: [N] ([%])
  Medium: [N] ([%])
  Low: [N] ([%])

By Status:
  New: [N]
  Triaged: [N]
  In Progress: [N]
  Resolved: [N]
  Closed: [N]
```

### Security Report

**Step 1: Get Security Bugs**
```bash
uv run python -c "
import asyncio
from src.bug_tracker.database.connection import get_db_connection
from src.bug_tracker.database.repositories import BugRepository

async def get_security():
    async with get_db_connection() as db:
        repo = BugRepository(db)
        bugs = await repo.get_security_bugs(min_cvss=0)
        
        print(f'Total Security Bugs: {len(bugs)}\n')
        
        # By CVSS range
        critical = [b for b in bugs if b.cvss_score and b.cvss_score >= 9.0]
        high = [b for b in bugs if b.cvss_score and 7.0 <= b.cvss_score < 9.0]
        medium = [b for b in bugs if b.cvss_score and 4.0 <= b.cvss_score < 7.0]
        low = [b for b in bugs if b.cvss_score and b.cvss_score < 4.0]
        
        print(f'By CVSS:')
        print(f'  Critical (>=9.0): {len(critical)}')
        print(f'  High (7.0-8.9): {len(high)}')
        print(f'  Medium (4.0-6.9): {len(medium)}')
        print(f'  Low (<4.0): {len(low)}')
        
        print(f'\nTop Security Bugs:')
        for bug in sorted(bugs, key=lambda b: b.cvss_score or 0, reverse=True)[:5]:
            print(f'  {bug.title}: CVSS {bug.cvss_score}')

asyncio.run(get_security())
"
```

**Step 2: Format Output**
```
Security Bug Report
===================
Generated: [datetime]

Total Security Bugs: [N]

By CVSS Score:
  Critical (>=9.0): [N] - IMMEDIATE ACTION
  High (7.0-8.9): [N] - Priority
  Medium (4.0-6.9): [N] - Standard
  Low (<4.0): [N] - Low priority

Top 5 Critical Vulnerabilities:
  1. [CVE-XXX]: [Title] (CVSS: [score])
  2. [CVE-YYY]: [Title] (CVSS: [score])
  ...
```

### Component Report

**Step 1: Get Component Breakdown**
```bash
uv run python -c "
import asyncio
from src.bug_tracker.database.connection import get_db_connection

async def get_by_component():
    async with get_db_connection() as db:
        result = await db.fetchall('''
            SELECT component, COUNT(*) as count, 
                   SUM(CASE WHEN severity = \"critical\" THEN 1 ELSE 0 END) as critical,
                   SUM(CASE WHEN severity = \"high\" THEN 1 ELSE 0 END) as high
            FROM bugs 
            GROUP BY component 
            ORDER BY count DESC
        ''')
        print('Component Breakdown:\n')
        for row in result:
            print(f'{row[\"component\"].upper()}: {row[\"count\"]} bugs')
            print(f'  Critical: {row[\"critical\"]}, High: {row[\"high\"]}')

asyncio.run(get_by_component())
"
```

**Step 2: Format Output**
```
Component Report
================
Generated: [datetime]

| Component | Total | Critical | High | Medium | Low |
|-----------|-------|----------|------|--------|-----|
| CPU       | [N]   | [N]      | [N]  | [N]    | [N] |
| GPU       | [N]   | [N]      | [N]  | [N]    | [N] |
| FIRMWARE  | [N]   | [N]      | [N]  | [N]    | [N] |
| DRIVER    | [N]   | [N]      | [N]  | [N]    | [N] |
| OTHER     | [N]   | [N]      | [N]  | [N]    | [N] |
```

### Chip Family Report

**Step 1: Get Chip Breakdown**
```bash
uv run python -c "
import asyncio
from src.bug_tracker.database.connection import get_db_connection

async def get_by_chip():
    async with get_db_connection() as db:
        result = await db.fetchall('''
            SELECT chip_family, COUNT(*) as count,
                   AVG(cvss_score) as avg_cvss
            FROM bugs 
            WHERE chip_family IS NOT NULL
            GROUP BY chip_family 
            ORDER BY count DESC
        ''')
        print('Chip Family Breakdown:\n')
        for row in result:
            avg = row['avg_cvss'] or 0
            print(f'{row[\"chip_family\"]}: {row[\"count\"]} bugs (Avg CVSS: {avg:.1f})')

asyncio.run(get_by_chip())
"
```

**Step 2: Format Output**
```
Chip Family Report
==================
Generated: [datetime]

| Chip Family | Total Bugs | Avg CVSS | Critical | High |
|-------------|------------|----------|----------|------|
| Intel       | [N]        | [X.X]    | [N]      | [N]  |
| AMD         | [N]        | [X.X]    | [N]      | [N]  |
| ARM         | [N]        | [X.X]    | [N]      | [N]  |
| NVIDIA      | [N]        | [X.X]    | [N]      | [N]  |
| Unknown     | [N]        | [X.X]    | [N]      | [N]  |
```

## When to Run Python Script

Run `skills/bug-report/Scripts/bug_report.py` only if:
- Need to export to file (CSV, JSON)
- Need charts/visualizations
- Called from frontend

For quick reports, follow the steps above.

## Related
- Dashboard: `frontend/app.py`
- MCP Tools: `get_bug_stats`, `list_bugs`
