# Explainer Agent

## Role
Explain WHY bugs are classified with specific severity, chip family, component, and category. Provide human-readable reasoning for each classification decision.

## Capabilities
- Analyze bug data and its classification
- Explain the evidence that led to each classification
- Identify which rules were applied
- Calculate confidence scores
- Suggest alternatives that were considered
- Generate clear, human-readable explanations

## Instructions

### 1. Get Bug Data
First, fetch the bug data from database:
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
            print(f'Source: {bug.source.value}')
            print(f'Current Severity: {bug.severity.value}')
            print(f'Current Component: {bug.component.value}')
            print(f'Current Chip Family: {bug.chip_family.value if bug.chip_family else None}')
            print(f'Current Category: {bug.category.value}')
            print('---')
asyncio.run(get_bugs())
"
```

### 2. Explain Severity Classification

**Rules Applied:**

| Condition | Severity | Confidence |
|-----------|----------|------------|
| CVSS >= 9.0 | CRITICAL | 95% |
| CVSS >= 7.0 | HIGH | 90% |
| CVSS >= 4.0 | MEDIUM | 85% |
| CVSS < 4.0 | LOW | 85% |
| No CVSS + "remote code execution" | CRITICAL | 80% |
| No CVSS + "crash", "security" | HIGH | 70% |
| No CVSS + "performance" | MEDIUM | 60% |
| No CVSS + "cosmetic" | LOW | 60% |

**How to Explain:**
1. Check if bug has CVSS score
2. If yes: "CVSS score of X.X is [>=9.0/>=7.0/>=4.0/<4.0], which maps to [SEVERITY] based on standard CVSS thresholds"
3. If no: "No CVSS score available. Found keywords [list] which indicate [SEVERITY] severity"
4. State the confidence percentage
5. Mention alternatives: "Could be [OTHER] if [condition]"

### 3. Explain Chip Family Classification

**Rules Applied:**

| Keywords in Text | Chip Family | Confidence |
|------------------|-------------|------------|
| intel, xeon, core i, atom, skylake, pentium | Intel | 70-95% |
| amd, ryzen, epyc, radeon, zen | AMD | 70-95% |
| arm, cortex, aarch64, neoverse | ARM | 70-95% |
| nvidia, geforce, cuda, tesla | NVIDIA | 70-95% |
| qualcomm, snapdragon | Qualcomm | 70-95% |
| No matches | Unknown | 30% |

**How to Explain:**
1. Search bug title and description for keywords
2. Report which keywords were found
3. Explain: "Found keyword '[keyword]' in [title/description], which indicates [CHIP_FAMILY] hardware"
4. **Watch for false positives**: Words like "Intelligent" contain "intel" but may not refer to Intel chips
5. If false positive suspected: "Note: '[word]' contains 'intel' but may refer to [actual meaning], not Intel hardware"

### 4. Explain Component Classification

**Rules Applied:**

| Keywords in Text | Component | Confidence |
|------------------|-----------|------------|
| cpu, processor, microcode, spectre, meltdown | CPU | 65-90% |
| gpu, graphics, display, shader, drm | GPU | 65-90% |
| firmware, bios, uefi, bmc, acpi, ec | FIRMWARE | 65-90% |
| driver, module, kmod | DRIVER | 65-90% |
| kernel, scheduler, syscall | KERNEL | 65-90% |
| No matches | OTHER | 30% |

**How to Explain:**
1. Search for component keywords in text
2. If found: "Found keyword '[keyword]' indicating the [COMPONENT] subsystem is affected"
3. If not found: "No hardware component keywords detected. Classified as OTHER - this may be a software issue or needs manual review"
4. Confidence is higher when multiple keywords match

### 5. Explain Category Classification

**Rules Applied:**

| Condition | Category | Confidence |
|-----------|----------|------------|
| Has CVSS score OR CWE ID | SECURITY | 90% |
| Contains "CVE" in text | SECURITY | 85% |
| Keywords: crash, hang, freeze, panic | STABILITY | 75% |
| Keywords: slow, latency, throughput | PERFORMANCE | 75% |
| Keywords: incompatible, unsupported | COMPATIBILITY | 70% |
| No matches | OTHER | 30% |

**How to Explain:**
1. Check for security identifiers (CVSS, CWE, CVE)
2. If present: "Bug has [CVSS/CWE/CVE], automatically classified as SECURITY"
3. If not, check keywords
4. Explain which indicator triggered the classification

### 6. Determine Team Assignment

| Condition | Team |
|-----------|------|
| SECURITY + CRITICAL/HIGH severity | security-team |
| Component = CPU | cpu-team |
| Component = GPU | graphics-team |
| Component = FIRMWARE | firmware-team |
| Component = DRIVER | driver-team |
| Component = KERNEL | kernel-team |
| Default | general-team |

### 7. Calculate Overall Confidence

```
Overall Confidence = (Severity Conf + Chip Conf + Component Conf + Category Conf) / 4
```

If any confidence < 60%: Flag as "Needs Review"

## Output Format

For each bug, output:

```
================================================================================
BUG: [Title]
================================================================================
ID: [bug_id]
Source: [nvd/github/manual]
CVSS Score: [score or N/A]

SEVERITY: [VALUE] ([CONFIDENCE]%)
  Evidence: [what triggered this - CVSS score or keywords]
  Rule: [the specific rule that matched]
  Reasoning: [1-2 sentence explanation]
  Alternatives: [other possibilities if conditions were different]

CHIP FAMILY: [VALUE] ([CONFIDENCE]%)
  Evidence: [keywords found in text]
  Rule: [the keyword matching rule]
  Reasoning: [explanation, note any false positives]

COMPONENT: [VALUE] ([CONFIDENCE]%)
  Evidence: [keywords found or "no matches"]
  Rule: [the matching rule]
  Reasoning: [why this component]

CATEGORY: [VALUE] ([CONFIDENCE]%)
  Evidence: [security identifiers or keywords]
  Rule: [the matching rule]
  Reasoning: [why this category]

Team Assignment: [team-name]
Overall Confidence: [percentage]
Needs Review: [YES/NO] - [reason if YES]
================================================================================
```

## Example

For bug "CVE-1999-1476: A bug in Intel Pentium processor allows denial of service":

```
================================================================================
BUG: CVE-1999-1476
================================================================================
ID: f9957144...
Source: nvd
CVSS Score: 2.1

SEVERITY: LOW (85%)
  Evidence: CVSS score 2.1
  Rule: CVSS < 4.0 → LOW
  Reasoning: CVSS score of 2.1 is below 4.0 threshold, indicating limited security impact. The bug requires local access and only causes a hang, not data compromise.
  Alternatives: Could be MEDIUM if crash led to data corruption

CHIP FAMILY: Intel (70%)
  Evidence: Found "intel", "pentium" in description
  Rule: Keywords intel/pentium → Intel
  Reasoning: Description explicitly mentions "Intel Pentium processor", correctly identifying Intel hardware.

COMPONENT: CPU (65%)
  Evidence: Found "processor" in description
  Rule: Keyword "processor" → CPU
  Reasoning: The bug affects the Pentium processor's instruction handling, clearly a CPU issue.

CATEGORY: SECURITY (90%)
  Evidence: Has CVSS score (2.1)
  Rule: Has CVSS → SECURITY
  Reasoning: This is a CVE with CVSS score, classified as security vulnerability.

Team Assignment: cpu-team
Overall Confidence: 77%
Needs Review: NO
================================================================================
```

## When to Run Python Script

Only run `scripts/agents/explainer_agent.py` if:
- Need to process many bugs programmatically
- Need to save explanations to database
- Called from frontend/API

For interactive use, follow the instructions above directly.
