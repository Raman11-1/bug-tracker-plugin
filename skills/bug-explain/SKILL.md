---
name: bug-explain
description: Explain how bugs were classified (severity, chip family, component, category) with evidence and reasoning
---

# Bug Explain Skill

## Usage
```
/bug-explain                   # Explain all bugs
/bug-explain --bug-id=<id>     # Explain specific bug
/bug-explain --summary         # Show classification rules only
```

## Instructions

### Step 1: Get Bug Data
```bash
uv run python -c "
import asyncio
from src.bug_tracker.database.connection import get_db_connection
from src.bug_tracker.database.repositories import BugRepository

async def get_bugs():
    async with get_db_connection() as db:
        repo = BugRepository(db)
        bugs = await repo.list_bugs(limit=50)
        for bug in bugs:
            print(f'ID: {bug.id}')
            print(f'Title: {bug.title}')
            print(f'Description: {bug.description}')
            print(f'CVSS: {bug.cvss_score}')
            print(f'CWE: {bug.cwe_id}')
            print(f'Source: {bug.source.value}')
            print(f'Severity: {bug.severity.value}')
            print(f'Component: {bug.component.value}')
            print(f'Chip Family: {bug.chip_family.value if bug.chip_family else None}')
            print(f'Category: {bug.category.value}')
            print('---')
asyncio.run(get_bugs())
"
```

### Step 2: Explain Severity

**Rules:**
| Condition | Severity | Confidence |
|-----------|----------|------------|
| CVSS >= 9.0 | CRITICAL | 95% |
| CVSS >= 7.0 | HIGH | 90% |
| CVSS >= 4.0 | MEDIUM | 85% |
| CVSS < 4.0 | LOW | 85% |
| No CVSS + "remote code execution" | CRITICAL | 80% |
| No CVSS + "crash", "security" | HIGH | 70% |

**How to Explain:**
1. Check if CVSS exists
2. If yes: "CVSS score [X.X] is [>=9.0/>=7.0/>=4.0/<4.0], indicating [SEVERITY] severity"
3. If no: "No CVSS. Keywords [list] suggest [SEVERITY] severity"
4. State confidence and possible alternatives

### Step 3: Explain Chip Family

**Rules:**
| Keywords | Chip Family |
|----------|-------------|
| intel, xeon, pentium, core i | Intel |
| amd, ryzen, epyc, radeon | AMD |
| arm, cortex, aarch64 | ARM |
| nvidia, cuda, geforce | NVIDIA |
| qualcomm, snapdragon | Qualcomm |

**How to Explain:**
1. Search text for keywords
2. Report: "Found keyword '[X]' in [title/description]"
3. **Check for false positives:**
   - "Intelligent" contains "intel" but means smart
   - "execute" contains "ec" but not embedded controller
4. If false positive: "Note: '[word]' contains '[keyword]' but likely refers to [actual meaning]"

### Step 4: Explain Component

**Rules:**
| Keywords | Component |
|----------|-----------|
| cpu, processor, microcode | CPU |
| gpu, graphics, display | GPU |
| firmware, bios, uefi, ec | FIRMWARE |
| driver, module | DRIVER |
| kernel, scheduler | KERNEL |

**How to Explain:**
1. Search text for keywords
2. If found: "Found '[keyword]' indicating [COMPONENT] subsystem"
3. If not: "No component keywords found - classified as OTHER"

### Step 5: Explain Category

**Rules:**
| Condition | Category |
|-----------|----------|
| Has CVSS/CWE | SECURITY |
| "CVE" in text | SECURITY |
| "crash", "hang" keywords | STABILITY |
| "slow", "latency" keywords | PERFORMANCE |

**How to Explain:**
1. Check for security identifiers first
2. Then check keywords
3. Report which indicator triggered classification

### Step 6: Output Format

For each bug:
```
================================================================================
BUG: [Title]
================================================================================
ID: [bug_id]
Source: [nvd/github/manual]
CVSS: [score or N/A]

SEVERITY: [VALUE] ([CONFIDENCE]%)
  Evidence: [what triggered this]
  Rule: [the specific rule matched]
  Reasoning: [1-2 sentence explanation]

CHIP FAMILY: [VALUE] ([CONFIDENCE]%)
  Evidence: [keywords found]
  Rule: [the matching rule]
  Reasoning: [explanation, note false positives]

COMPONENT: [VALUE] ([CONFIDENCE]%)
  Evidence: [keywords found or "no matches"]
  Rule: [the matching rule]
  Reasoning: [why this component]

CATEGORY: [VALUE] ([CONFIDENCE]%)
  Evidence: [security identifiers or keywords]
  Rule: [the matching rule]
  Reasoning: [why this category]

Team: [assigned team]
Confidence: [overall %]
Needs Review: [YES/NO]
================================================================================
```

## Example Explanation

**Bug:** CVE-1999-1476 - Intel Pentium processor denial of service

```
================================================================================
BUG: CVE-1999-1476
================================================================================
ID: f9957144...
Source: nvd
CVSS: 2.1

SEVERITY: LOW (85%)
  Evidence: CVSS score 2.1
  Rule: CVSS < 4.0 → LOW
  Reasoning: CVSS of 2.1 is below 4.0 threshold. This is a local DoS requiring physical access, limiting impact.

CHIP FAMILY: Intel (70%)
  Evidence: Found "intel", "pentium" in text
  Rule: Keywords intel/pentium → Intel
  Reasoning: Description explicitly mentions "Intel Pentium processor" - correctly identifies Intel hardware.

COMPONENT: CPU (65%)
  Evidence: Found "processor"
  Rule: Keyword "processor" → CPU
  Reasoning: Bug affects Pentium processor instruction handling - clearly a CPU issue.

CATEGORY: SECURITY (90%)
  Evidence: Has CVSS score (2.1)
  Rule: Has CVSS → SECURITY
  Reasoning: CVE with CVSS score is automatically a security vulnerability.

Team: cpu-team
Confidence: 77%
Needs Review: NO
================================================================================
```

## When to Run Python Script

Run `skills/bug-explain/Scripts/bug_explain.py` only if:
- Need to save explanations to database
- Called from frontend
- Processing many bugs programmatically

For interactive explanation, follow the steps above.

## Related
- Explainer Agent: `agents/explainer-agent/explainer-agent.md`
- Classification Agent: `agents/classification-agent/classification-agent.md`
