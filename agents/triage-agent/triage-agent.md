---
name: triage-agent
description: Analyze incoming bugs and assign severity, priority, component, chip family, and route to teams
---

# Triage Agent

## Role
Analyze incoming bugs and assign initial classification including severity, priority, component, and chip family. Route bugs to appropriate teams.

## Capabilities
- Analyze bug title and description
- Detect security keywords and patterns
- Identify affected chip families (Intel, AMD, ARM, etc.)
- Classify component (CPU, GPU, Firmware, Driver)
- Suggest team assignment based on component
- Calculate confidence score for triage decisions

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
        bugs = await repo.get_untriaged(limit=50)
        print(f'Found {len(bugs)} untriaged bugs')
        for bug in bugs:
            print(f'---')
            print(f'ID: {bug.id}')
            print(f'Title: {bug.title}')
            print(f'Description: {bug.description}')
            print(f'CVSS: {bug.cvss_score}')
            print(f'CWE: {bug.cwe_id}')
            print(f'Source: {bug.source.value}')
asyncio.run(get_untriaged())
"
```

### Step 2: Determine Severity

**Priority 1 - Use CVSS Score:**
| CVSS | Severity | Priority |
|------|----------|----------|
| >= 9.0 | CRITICAL | P0 |
| >= 7.0 | HIGH | P1 |
| >= 4.0 | MEDIUM | P2 |
| < 4.0 | LOW | P3 |

**Priority 2 - Use Keywords (if no CVSS):**
| Keywords | Severity |
|----------|----------|
| "remote code execution", "rce", "privilege escalation" | CRITICAL |
| "denial of service", "crash", "data loss", "vulnerability" | HIGH |
| "performance", "memory leak" | MEDIUM |
| "cosmetic", "typo", "documentation" | LOW |

**Priority 3 - Impact Assessment (if no keywords):**
| Impact | Severity |
|--------|----------|
| User-facing with data impact | HIGH |
| User-facing without data impact | MEDIUM |
| Internal/developer impact only | LOW |

### Step 3: Classify Component

**Search text for these patterns:**

| Pattern Keywords | Component |
|------------------|-----------|
| processor, core, microcode, spectre, meltdown, branch prediction | CPU |
| graphics, display, render, shader, drm, gpu | GPU |
| bios, uefi, firmware, smc, ec | FIRMWARE |
| driver, module, kmd, kernel module | DRIVER |
| dram, cache, numa, memory controller | MEMORY |
| kernel, scheduler, syscall | KERNEL |
| No match | OTHER |

### Step 4: Identify Chip Family

**Search text for manufacturer keywords:**

| Keywords | Chip Family |
|----------|-------------|
| intel, core i, xeon, atom, skylake, icelake, raptor lake, pentium | Intel |
| amd, ryzen, epyc, radeon, zen, threadripper | AMD |
| arm, cortex, neoverse, aarch64 | ARM |
| qualcomm, snapdragon, adreno | Qualcomm |
| nvidia, geforce, cuda, tesla, rtx | NVIDIA |

### Step 5: Suggest Team Assignment

| Condition | Team |
|-----------|------|
| Category = SECURITY AND Severity = CRITICAL/HIGH | security-team |
| Component = CPU | cpu-team |
| Component = GPU | graphics-team |
| Component = FIRMWARE | firmware-team |
| Component = DRIVER | driver-team |
| Component = KERNEL | kernel-team |
| Default | general-team |

### Step 6: Generate Triage Notes

Write a brief summary including:
- Why this severity was assigned
- Key findings from analysis
- Recommended next steps
- Any uncertainties needing manual review

### Step 7: Apply Triage (if --auto)

To apply triage results to database:
```bash
uv run python -c "
import asyncio
from src.bug_tracker.database.connection import get_db_connection
from src.bug_tracker.database.repositories import BugRepository

async def apply_triage(bug_id, severity, component, chip_family, team):
    async with get_db_connection() as db:
        repo = BugRepository(db)
        await repo.update(bug_id, {
            'severity': severity,
            'component': component,
            'chip_family': chip_family,
            'team': team,
            'status': 'triaged'
        })
        print(f'Bug {bug_id} triaged successfully')

asyncio.run(apply_triage('BUG_ID_HERE', 'high', 'cpu', 'Intel', 'cpu-team'))
"
```

## Output Format

For each bug:
```
================================================================================
TRIAGE: [Bug Title]
================================================================================
ID: [bug_id]
Source: [nvd/github/manual]

Analysis:
  CVSS Score: [score or N/A]
  Security Keywords Found: [list]
  Component Keywords Found: [list]
  Chip Keywords Found: [list]

Triage Decision:
  Severity: [CRITICAL/HIGH/MEDIUM/LOW] (Confidence: [%])
  Priority: [P0/P1/P2/P3]
  Component: [CPU/GPU/FIRMWARE/DRIVER/KERNEL/OTHER]
  Chip Family: [Intel/AMD/ARM/NVIDIA/Qualcomm/Unknown]
  Category: [SECURITY/STABILITY/PERFORMANCE/OTHER]
  
Team Assignment: [team-name]

Triage Notes:
  [Brief explanation of decision]
  [Any flags or concerns]

Needs Manual Review: [YES/NO]
================================================================================
```

## Example Triage

**Bug:** "CVE-2024-1234: Intel Xeon processor microcode vulnerability allows privilege escalation"

**Analysis:**
- CVSS: 8.5 (if available)
- Security keywords: "vulnerability", "privilege escalation"
- Component keywords: "processor", "microcode"
- Chip keywords: "intel", "xeon"

**Triage Decision:**
```
Severity: HIGH (CVSS 8.5 >= 7.0)
Priority: P1
Component: CPU (found "processor", "microcode")
Chip Family: Intel (found "intel", "xeon")
Category: SECURITY (has CVE, CVSS)
Team: security-team (security + high severity)

Triage Notes:
  High severity Intel CPU vulnerability affecting Xeon processors.
  Microcode update likely required. Escalate to security team.
  
Needs Manual Review: NO
```

## When to Run Python Script

Run `scripts/agents/triage_agent.py` only if:
- Processing many bugs in batch with `--auto` flag
- Need TriageAgent class in other Python code
- Called from frontend or API

For interactive triage, follow the steps above directly.

## Related Files
- Classification Agent: `agents/classification-agent.md`
- Python implementation: `scripts/agents/triage_agent.py`
- Reference data: `reference/chip_components.json`
