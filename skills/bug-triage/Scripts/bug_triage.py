"""Bug Triage Skill - Interactive bug triage workflow."""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Optional

# Add project root to path (4 levels up: Scripts -> bug-triage -> skills -> .claude -> project)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from src.bug_tracker.database.connection import get_database
from src.bug_tracker.database.repositories import BugRepository
from scripts.agents.triage_agent import TriageAgent


console = Console()


async def run_triage(
    bug_id: Optional[str] = None,
    auto: bool = False,
    batch: int = 10,
    min_confidence: float = 0.7,
    dry_run: bool = False
):
    """Run the bug triage workflow."""
    db = await get_database()
    bug_repo = BugRepository(db)
    agent = TriageAgent()

    if bug_id:
        bug = await bug_repo.get_by_id(bug_id)
        if not bug:
            console.print(f"[red]Bug {bug_id} not found[/red]")
            return
        bugs = [bug]
    else:
        bugs = await bug_repo.get_untriaged(limit=batch)

    if not bugs:
        console.print("[yellow]No untriaged bugs found[/yellow]")
        return

    console.print(f"\n[bold]Found {len(bugs)} bug(s) to triage[/bold]\n")

    results = {
        "processed": 0,
        "auto_triaged": 0,
        "manual_review": 0,
        "skipped": 0
    }

    for bug in bugs:
        console.print(Panel(
            f"[bold]{bug.title}[/bold]\n\n"
            f"ID: {bug.id}\n"
            f"Source: {bug.source.value}\n"
            f"External ID: {bug.external_id or 'N/A'}\n\n"
            f"Description:\n{bug.description[:500]}{'...' if len(bug.description) > 500 else ''}",
            title=f"Bug: {bug.id[:8]}...",
            expand=False
        ))

        triage_result = await agent.triage_bug(bug, auto_apply=False)

        table = Table(title="Triage Suggestions")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Confidence", style="yellow")

        table.add_row(
            "Severity",
            triage_result.suggested_severity.value,
            f"{triage_result.confidence_score:.0%}"
        )
        table.add_row(
            "Priority",
            triage_result.suggested_priority.value,
            "-"
        )
        table.add_row(
            "Component",
            triage_result.suggested_component.value,
            "-"
        )
        table.add_row(
            "Chip Family",
            triage_result.suggested_chip_family.value if triage_result.suggested_chip_family else "Unknown",
            "-"
        )
        table.add_row(
            "Category",
            triage_result.suggested_category.value,
            "-"
        )
        table.add_row(
            "Suggested Team",
            triage_result.suggested_team or "Unassigned",
            "-"
        )

        console.print(table)
        console.print(f"\n[dim]Reasoning:[/dim]\n{triage_result.reasoning}\n")

        if dry_run:
            console.print("[yellow]DRY RUN - No changes applied[/yellow]")
            results["processed"] += 1
            continue

        if auto:
            if triage_result.confidence_score >= min_confidence:
                await agent._apply_triage(bug.id, triage_result)
                console.print(f"[green]Auto-triaged (confidence: {triage_result.confidence_score:.0%})[/green]")
                results["auto_triaged"] += 1
            else:
                console.print(f"[yellow]Skipped - confidence too low ({triage_result.confidence_score:.0%} < {min_confidence:.0%})[/yellow]")
                results["manual_review"] += 1
        else:
            if Confirm.ask("Apply these triage decisions?"):
                await agent._apply_triage(bug.id, triage_result)
                console.print("[green]Triage applied[/green]")
                results["auto_triaged"] += 1
            else:
                if Confirm.ask("Mark for manual review?"):
                    results["manual_review"] += 1
                else:
                    results["skipped"] += 1

        results["processed"] += 1
        console.print("\n" + "=" * 50 + "\n")

    console.print(Panel(
        f"[bold]Triage Summary[/bold]\n\n"
        f"Processed: {results['processed']}\n"
        f"Auto-triaged: {results['auto_triaged']}\n"
        f"Needs manual review: {results['manual_review']}\n"
        f"Skipped: {results['skipped']}",
        title="Results"
    ))


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Bug Triage Skill")
    parser.add_argument("--bug-id", help="Triage specific bug by ID")
    parser.add_argument("--auto", action="store_true", help="Auto-triage mode")
    parser.add_argument("--batch", type=int, default=10, help="Number of bugs to process")
    parser.add_argument("--min-confidence", type=float, default=0.7, help="Minimum confidence for auto-apply")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    asyncio.run(run_triage(
        bug_id=args.bug_id,
        auto=args.auto,
        batch=args.batch,
        min_confidence=args.min_confidence,
        dry_run=args.dry_run
    ))


if __name__ == "__main__":
    main()
