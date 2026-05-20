"""Bug Explain Skill - Explains how bugs are classified."""

import asyncio
import sys
from pathlib import Path

# Add project root to path (4 levels up: Scripts -> bug-explain -> skills -> .claude -> project)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.bug_tracker.database.connection import get_db_connection
from src.bug_tracker.database.repositories import BugRepository
from src.bug_tracker.domain.entities import Bug
from scripts.agents.classification import ClassificationEngine, ClassificationResult


class BugExplainSkill:
    """Skill that explains bug classifications."""

    SEVERITY_RULES = {
        "critical": "CVSS >= 9.0 OR keywords like 'remote code execution', 'privilege escalation'",
        "high": "CVSS >= 7.0 OR keywords like 'crash', 'security', 'vulnerability'",
        "medium": "CVSS >= 4.0 OR keywords like 'bug', 'error', 'performance'",
        "low": "CVSS < 4.0 OR keywords like 'cosmetic', 'typo', 'minor'"
    }

    CHIP_RULES = {
        "Intel": "Found keywords: 'intel', 'xeon', 'core i', 'atom', 'skylake'",
        "AMD": "Found keywords: 'amd', 'ryzen', 'epyc', 'radeon', 'zen'",
        "ARM": "Found keywords: 'arm', 'cortex', 'aarch64', 'neoverse'",
        "NVIDIA": "Found keywords: 'nvidia', 'geforce', 'cuda', 'tesla'",
        "Qualcomm": "Found keywords: 'qualcomm', 'snapdragon'"
    }

    COMPONENT_RULES = {
        "cpu": "Found keywords: 'cpu', 'processor', 'microcode', 'spectre'",
        "gpu": "Found keywords: 'gpu', 'graphics', 'display', 'shader'",
        "firmware": "Found keywords: 'firmware', 'bios', 'uefi', 'bmc', 'ec'",
        "driver": "Found keywords: 'driver', 'module', 'kmod'",
        "kernel": "Found keywords: 'kernel', 'scheduler', 'syscall'",
        "other": "No specific component keywords matched"
    }

    CATEGORY_RULES = {
        "security": "Has CVE/CVSS/CWE identifier OR keywords like 'vulnerability', 'exploit'",
        "stability": "Found keywords: 'crash', 'hang', 'freeze', 'panic'",
        "performance": "Found keywords: 'slow', 'latency', 'throughput'",
        "other": "No specific category matched"
    }

    def __init__(self):
        self.engine = ClassificationEngine()

    def explain_severity(self, bug: Bug, result: ClassificationResult) -> dict:
        """Explain why this severity was assigned."""
        value = result.severity.value

        if bug.cvss_score is not None:
            if bug.cvss_score >= 9.0:
                reasoning = f"CVSS score {bug.cvss_score} >= 9.0 indicates CRITICAL severity. This vulnerability could allow complete system compromise."
            elif bug.cvss_score >= 7.0:
                reasoning = f"CVSS score {bug.cvss_score} >= 7.0 indicates HIGH severity. This is a significant security vulnerability."
            elif bug.cvss_score >= 4.0:
                reasoning = f"CVSS score {bug.cvss_score} >= 4.0 indicates MEDIUM severity. This has moderate security impact."
            else:
                reasoning = f"CVSS score {bug.cvss_score} < 4.0 indicates LOW severity. This has limited security impact."
        else:
            reasoning = f"No CVSS score. Classified based on keyword analysis: {result.severity_indicators}"

        return {
            "value": value.upper(),
            "confidence": f"{result.severity_confidence:.0%}",
            "evidence": result.severity_indicators,
            "rule": self.SEVERITY_RULES.get(value, "Unknown rule"),
            "reasoning": reasoning
        }

    def explain_chip_family(self, bug: Bug, result: ClassificationResult) -> dict:
        """Explain why this chip family was assigned."""
        value = result.chip_family.value if result.chip_family else "UNKNOWN"

        if result.chip_family_indicators:
            reasoning = f"Found chip-related keywords in bug text: {result.chip_family_indicators}. These match the {value} chip family pattern."
        else:
            reasoning = "No chip family keywords detected in bug title or description."

        return {
            "value": value,
            "confidence": f"{result.chip_family_confidence:.0%}",
            "evidence": result.chip_family_indicators,
            "rule": self.CHIP_RULES.get(value, "No matching pattern"),
            "reasoning": reasoning
        }

    def explain_component(self, bug: Bug, result: ClassificationResult) -> dict:
        """Explain why this component was assigned."""
        value = result.component.value

        if result.component_indicators and result.component_indicators != ["no matches"]:
            reasoning = f"Found component keywords: {result.component_indicators}. These indicate the {value.upper()} subsystem is affected."
        else:
            reasoning = "No hardware component keywords found. Classified as OTHER - needs manual review."

        return {
            "value": value.upper(),
            "confidence": f"{result.component_confidence:.0%}",
            "evidence": result.component_indicators,
            "rule": self.COMPONENT_RULES.get(value, "No matching pattern"),
            "reasoning": reasoning
        }

    def explain_category(self, bug: Bug, result: ClassificationResult) -> dict:
        """Explain why this category was assigned."""
        value = result.category.value

        if bug.cvss_score is not None or bug.cwe_id is not None:
            reasoning = f"Bug has security identifiers (CVSS: {bug.cvss_score}, CWE: {bug.cwe_id}). Automatically classified as SECURITY."
        elif "cve" in bug.title.lower():
            reasoning = "Bug title contains 'CVE', indicating a security vulnerability."
        else:
            reasoning = f"Classified based on keyword analysis: {result.category_indicators}"

        return {
            "value": value.upper(),
            "confidence": f"{result.category_confidence:.0%}",
            "evidence": result.category_indicators,
            "rule": self.CATEGORY_RULES.get(value, "No matching pattern"),
            "reasoning": reasoning
        }

    def explain_bug(self, bug: Bug) -> dict:
        """Generate complete explanation for a bug."""
        result = self.engine.classify(bug)

        return {
            "bug_id": bug.id,
            "bug_title": bug.title,
            "description": bug.description[:200] + "..." if len(bug.description) > 200 else bug.description,
            "source": bug.source.value,
            "cvss_score": bug.cvss_score,
            "severity": self.explain_severity(bug, result),
            "chip_family": self.explain_chip_family(bug, result),
            "component": self.explain_component(bug, result),
            "category": self.explain_category(bug, result),
            "is_security_bug": result.is_security,
            "needs_review": result.needs_review,
            "review_reason": "Low confidence in one or more classifications" if result.needs_review else None
        }

    async def explain_all_bugs(self) -> list[dict]:
        """Explain all bugs in the database."""
        async with get_db_connection() as db:
            repo = BugRepository(db)
            bugs = await repo.list_bugs(limit=50)
            return [self.explain_bug(bug) for bug in bugs]

    async def explain_bug_by_id(self, bug_id: str) -> dict:
        """Explain a specific bug by ID."""
        async with get_db_connection() as db:
            repo = BugRepository(db)
            bug = await repo.get_by_id(bug_id)
            if bug:
                return self.explain_bug(bug)
            return {"error": f"Bug {bug_id} not found"}


def print_explanation(exp: dict):
    """Pretty print a bug explanation."""
    print(f"\n{'='*80}")
    print(f"BUG: {exp['bug_title']}")
    print(f"{'='*80}")
    print(f"ID: {exp['bug_id'][:8]}...")
    print(f"Source: {exp['source']}")
    print(f"CVSS: {exp['cvss_score']}")
    print(f"Description: {exp['description']}")

    print(f"\n--- SEVERITY: {exp['severity']['value']} ({exp['severity']['confidence']}) ---")
    print(f"  Evidence: {exp['severity']['evidence']}")
    print(f"  Rule: {exp['severity']['rule']}")
    print(f"  Reasoning: {exp['severity']['reasoning']}")

    print(f"\n--- CHIP FAMILY: {exp['chip_family']['value']} ({exp['chip_family']['confidence']}) ---")
    print(f"  Evidence: {exp['chip_family']['evidence']}")
    print(f"  Rule: {exp['chip_family']['rule']}")
    print(f"  Reasoning: {exp['chip_family']['reasoning']}")

    print(f"\n--- COMPONENT: {exp['component']['value']} ({exp['component']['confidence']}) ---")
    print(f"  Evidence: {exp['component']['evidence']}")
    print(f"  Rule: {exp['component']['rule']}")
    print(f"  Reasoning: {exp['component']['reasoning']}")

    print(f"\n--- CATEGORY: {exp['category']['value']} ({exp['category']['confidence']}) ---")
    print(f"  Evidence: {exp['category']['evidence']}")
    print(f"  Rule: {exp['category']['rule']}")
    print(f"  Reasoning: {exp['category']['reasoning']}")

    print(f"\nSecurity Bug: {'YES' if exp['is_security_bug'] else 'NO'}")
    print(f"Needs Review: {'YES' if exp['needs_review'] else 'NO'}")
    if exp['review_reason']:
        print(f"  Reason: {exp['review_reason']}")


async def main():
    """Run the skill."""
    import argparse
    parser = argparse.ArgumentParser(description="Bug Explain Skill")
    parser.add_argument("--bug-id", help="Specific bug ID to explain")
    parser.add_argument("--all", action="store_true", help="Explain all bugs")
    parser.add_argument("--summary", action="store_true", help="Show classification rules")
    args = parser.parse_args()

    skill = BugExplainSkill()

    if args.summary:
        print("\n=== CLASSIFICATION RULES ===\n")
        print("SEVERITY (based on CVSS):")
        for k, v in skill.SEVERITY_RULES.items():
            print(f"  {k.upper()}: {v}")
        print("\nCHIP FAMILY:")
        for k, v in skill.CHIP_RULES.items():
            print(f"  {k}: {v}")
        print("\nCOMPONENT:")
        for k, v in skill.COMPONENT_RULES.items():
            print(f"  {k.upper()}: {v}")
        print("\nCATEGORY:")
        for k, v in skill.CATEGORY_RULES.items():
            print(f"  {k.upper()}: {v}")
    elif args.bug_id:
        exp = await skill.explain_bug_by_id(args.bug_id)
        if "error" in exp:
            print(exp["error"])
        else:
            print_explanation(exp)
    else:
        explanations = await skill.explain_all_bugs()
        for exp in explanations:
            print_explanation(exp)


if __name__ == "__main__":
    asyncio.run(main())
