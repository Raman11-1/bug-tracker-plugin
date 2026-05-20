---
name: bug-triage
description: Triage bugs by classifying severity, component, chip family, and assigning to teams
---

# Bug Triage Skill

## Usage
```
/bug-triage                    # Triage all untriaged bugs interactively
/bug-triage --auto             # Auto-triage without prompts
/bug-triage --bug-id=<id>      # Triage specific bug
```

## Instructions

### Step 1: Get Untriaged Bugs
```bash
uv run python -c "
import asyncio
from src.bug_tracker.database.connection import get_db_connection
from src.bug_tracker.database.repositories import BugRepository

async def get_untriaged():
    async with get_db_connection() as db:
        repo = BugRepository(db)
        bugs = await repo.get_untriaged(limit=20)
        print(f'Found {len(bugs)} untriaged bugs\n')
        for bug in bugs:
            print(f'ID: {bug.id}')
            print(f'Title: {bug.title}')
            print(f'Description: {bug.description[:200]}...' if len(bug.description) > 200 else f'Description: {bug.description}')
            print(f'CVSS: {bug.cvss_score}')
            print(f'Source: {bug.source.value}')
            print('---')
asyncio.run(get_untriaged())
"
```

### Step 2: Classify Each Bug

For each bug, apply these rules:

**Severity (from CVSS or keywords):**
| CVSS Score | Severity |
|------------|----------|
| >= 9.0 | CRITICAL |
| >= 7.0 | HIGH |
| >= 4.0 | MEDIUM |
| < 4.0 | LOW |

If no CVSS, use keywords:
- "remote code execution", "privilege escalation" → CRITICAL
- "crash", "security", "vulnerability" → HIGH
- "performance", "memory leak" → MEDIUM
- "cosmetic", "typo" → LOW

**Component (from keywords):**
| Keywords | Component |
|----------|-----------|
| cpu, processor, microcode | CPU |
| gpu, graphics, display | GPU |
| firmware, bios, uefi | FIRMWARE |
| driver, module | DRIVER |
| kernel, scheduler | KERNEL |

**Chip Family (from keywords):**
| Keywords | Chip Family |
|----------|-------------|
| intel, xeon, pentium | Intel |
| amd, ryzen, epyc | AMD |
| arm, cortex | ARM |
| nvidia, cuda | NVIDIA |

**Team Assignment:**
| Condition | Team |
|-----------|------|
| SECURITY + HIGH/CRITICAL | security-team |
| CPU component | cpu-team |
| GPU component | graphics-team |
| FIRMWARE component | firmware-team |
| Default | general-team |

### Step 3: Present Triage Decision

For each bug, output:
```
TRIAGE: [Bug Title]
-----------------------------------------
Suggested Classification:
  Severity: [VALUE] (because [reason])
  Component: [VALUE] (found keywords: [list])
  Chip Family: [VALUE] (found keywords: [list])
  Category: [VALUE]
  Team: [team-name]

Confidence: [HIGH/MEDIUM/LOW]
Needs Review: [YES/NO]
```

### Step 4: Apply Triage (if --auto or confirmed)

```bash
uv run python -c "
import asyncio
from src.bug_tracker.database.connection import get_db_connection
from src.bug_tracker.database.repositories import BugRepository
from datetime import datetime

async def apply_triage(bug_id, severity, component, chip_family, team):
    async with get_db_connection() as db:
        repo = BugRepository(db)
        await repo.update(bug_id, {
            'severity': severity,
            'component': component,
            'chip_family': chip_family,
            'team': team,
            'status': 'triaged',
            'triaged_at': datetime.utcnow().isoformat()
        })
        print(f'Triaged: {bug_id}')
asyncio.run(apply_triage('BUG_ID', 'high', 'cpu', 'Intel', 'cpu-team'))
"
```

## Output Summary

After triaging all bugs:
```
Triage Summary
==============
Total Processed: [N]
Auto-triaged: [N] (confidence >= 70%)
Needs Review: [N] (confidence < 70%)

By Severity:
  CRITICAL: [N]
  HIGH: [N]
  MEDIUM: [N]
  LOW: [N]

By Team:
  security-team: [N]
  cpu-team: [N]
  ...
```

## When to Run Python Script

Run `skills/bug-triage/Scripts/bug_triage.py` only if:
- Need batch processing with progress tracking
- Called from frontend/API
- Need detailed logging

For interactive triage, follow the steps above.

## Related
- Triage Agent: `agents/triage-agent/triage-agent.md`
- Classification Agent: `agents/classification-agent/classification-agent.md`
