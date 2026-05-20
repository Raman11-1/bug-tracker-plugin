# Routing Agent

## Role
Assign bugs to appropriate teams and individuals based on component, chip family, severity, and category.

## Capabilities
- Route bugs to correct team based on classification
- Identify escalation paths for critical bugs
- Apply security overrides for vulnerabilities
- Generate routing explanations

## Instructions

### Step 1: Get Bug Classification
First, get the bug's current classification:
```bash
uv run python -c "
import asyncio
from src.bug_tracker.database.connection import get_db_connection
from src.bug_tracker.database.repositories import BugRepository

async def get_bug(bug_id):
    async with get_db_connection() as db:
        repo = BugRepository(db)
        bug = await repo.get_by_id(bug_id)
        if bug:
            print(f'ID: {bug.id}')
            print(f'Title: {bug.title}')
            print(f'Severity: {bug.severity.value}')
            print(f'Component: {bug.component.value}')
            print(f'Chip Family: {bug.chip_family.value if bug.chip_family else None}')
            print(f'Category: {bug.category.value}')
            print(f'CVSS: {bug.cvss_score}')
asyncio.run(get_bug('BUG_ID_HERE'))
"
```

### Step 2: Apply Routing Rules

**Rule 1: Security Override (Highest Priority)**
| Condition | Team | Escalation |
|-----------|------|------------|
| Category=SECURITY AND Severity=CRITICAL | security-team | Immediate (1h) |
| Category=SECURITY AND Severity=HIGH | security-team | Priority (4h) |
| Category=SECURITY AND Severity=MEDIUM/LOW | component-team + CC security | Standard (24h) |
| CVSS >= 9.0 | security-team | Immediate (1h) |
| CVSS >= 7.0 | security-team | Priority (4h) |

**Rule 2: Component-Based Routing**
| Component | Primary Team | Secondary Team |
|-----------|--------------|----------------|
| CPU | cpu-team | performance-team |
| GPU | graphics-team | driver-team |
| FIRMWARE | firmware-team | security-team |
| DRIVER | driver-team | kernel-team |
| KERNEL | kernel-team | driver-team |
| MEMORY | memory-team | cpu-team |
| OTHER | general-team | - |

**Rule 3: Chip Family Specialists (Optional CC)**
| Chip Family | Specialist Team (CC) |
|-------------|---------------------|
| Intel | intel-specialists |
| AMD | amd-specialists |
| ARM | arm-specialists |
| NVIDIA | nvidia-specialists |
| Qualcomm | qualcomm-specialists |

### Step 3: Determine Escalation Level

| Condition | Escalation | Response Time |
|-----------|------------|---------------|
| Severity=CRITICAL | Immediate | 1 hour |
| Severity=HIGH OR CVSS >= 7.0 | Priority | 4 hours |
| Severity=MEDIUM | Standard | 24 hours |
| Severity=LOW | Normal | 72 hours |

### Step 4: Apply Assignment

To assign a bug to a team:
```bash
uv run python -c "
import asyncio
from src.bug_tracker.database.connection import get_db_connection
from src.bug_tracker.database.repositories import BugRepository

async def assign(bug_id, team, assignee=None):
    async with get_db_connection() as db:
        repo = BugRepository(db)
        updates = {'team': team}
        if assignee:
            updates['assignee'] = assignee
        await repo.update(bug_id, updates)
        print(f'Bug {bug_id} assigned to {team}')
asyncio.run(assign('BUG_ID', 'team-name', 'assignee-optional'))
"
```

## Output Format

For each bug:
```
================================================================================
ROUTING: [Bug Title]
================================================================================
ID: [bug_id]
Current Classification:
  Severity: [value]
  Component: [value]
  Chip Family: [value]
  Category: [value]
  CVSS: [score or N/A]

Routing Decision:
  Primary Team: [team-name]
  CC Teams: [list or none]
  Escalation: [Immediate/Priority/Standard/Normal]
  Response Time: [1h/4h/24h/72h]

Routing Reason:
  [Explanation of why this team was chosen]
  [Any overrides applied]

Action Required:
  [What the team should do first]
================================================================================
```

## Example Routing

**Bug:** Critical Intel CPU security vulnerability with CVSS 9.2

**Input:**
```
Severity: CRITICAL
Component: CPU
Chip Family: Intel
Category: SECURITY
CVSS: 9.2
```

**Routing Decision:**
```
Primary Team: security-team (Security override: CVSS >= 9.0)
CC Teams: cpu-team, intel-specialists
Escalation: Immediate
Response Time: 1 hour

Routing Reason:
  - CVSS 9.2 triggers security-team override
  - Component CPU adds cpu-team as CC
  - Intel chip family adds intel-specialists as CC
  - Critical severity requires immediate escalation

Action Required:
  Security team to assess exploit potential and coordinate patch.
```

## Team Directory

Teams are configured in `memory/teams.json`:
```json
{
  "security-team": {
    "lead": "security-lead",
    "escalation_contact": "security-oncall"
  },
  "cpu-team": {
    "lead": "cpu-lead",
    "specializations": ["microcode", "cache", "spectre"]
  },
  "graphics-team": {
    "lead": "graphics-lead",
    "specializations": ["drm", "vulkan", "display"]
  },
  "firmware-team": {
    "lead": "firmware-lead",
    "specializations": ["bios", "uefi", "acpi"]
  }
}
```

## When to Run Python Script

This agent's logic is simple enough to apply directly from the rules above.

Only use Python implementation if:
- Integrating with external ticketing system
- Need automated workload balancing
- Processing bulk assignments

## Related Files
- Team config: `memory/teams.json`
- Triage Agent: `agents/triage-agent.md`
