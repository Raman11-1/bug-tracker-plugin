"""Data Import Skill - Import bugs from external sources."""

import asyncio
import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# Add project root to path (4 levels up: Scripts -> data-import -> skills -> .claude -> project)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, TaskID

from src.bug_tracker.database.connection import get_database
from src.bug_tracker.database.repositories import BugRepository
from api.github.client import GitHubClient
from api.nvd.client import NVDClient


console = Console()


def parse_since(since_str: str) -> datetime:
    """Parse since parameter to datetime."""
    if since_str.endswith("d"):
        days = int(since_str[:-1])
        return datetime.utcnow() - timedelta(days=days)
    elif since_str.endswith("h"):
        hours = int(since_str[:-1])
        return datetime.utcnow() - timedelta(hours=hours)
    else:
        return datetime.fromisoformat(since_str)


async def import_from_nvd(
    keywords: Optional[list[str]] = None,
    since: Optional[str] = None,
    limit: int = 100,
    dry_run: bool = False,
    offset: int = 0
) -> dict:
    """Import from NVD.

    Args:
        keywords: Search keywords
        since: Time range
        limit: Max bugs to import
        dry_run: Preview without importing
        offset: Skip this many results (auto-calculated if 0)
    """
    client = NVDClient()
    db = await get_database()
    bug_repo = BugRepository(db)

    since_dt = parse_since(since) if since else None

    if keywords is None:
        keywords = ["Intel"]

    # Auto-calculate offset from existing NVD bugs if not specified
    if offset == 0:
        existing_bugs = await bug_repo.list_bugs(limit=1000)
        nvd_count = sum(1 for b in existing_bugs if b.source.value == "nvd")
        offset = nvd_count
        if nvd_count > 0:
            console.print(f"[yellow]Found {nvd_count} existing NVD bugs, starting from offset {offset}[/yellow]")

    results = {"fetched": 0, "created": 0, "duplicates": 0, "samples": []}

    console.print(f"[cyan]Fetching CVEs from NVD with keywords: {keywords} (offset: {offset})[/cyan]")

    with Progress() as progress:
        task = progress.add_task("Importing from NVD...", total=limit)

        async for bug in client.fetch_cves(keywords=keywords, since=since_dt, limit=limit, offset=offset):
            results["fetched"] += 1
            progress.update(task, advance=1)

            existing = await bug_repo.get_by_external_id(bug.external_id, bug.source.value)
            if existing:
                results["duplicates"] += 1
                continue

            if not dry_run:
                await bug_repo.create(bug)

            results["created"] += 1
            if len(results["samples"]) < 5:
                results["samples"].append({
                    "id": bug.external_id,
                    "title": bug.title[:60],
                    "severity": bug.severity.value,
                    "cvss": bug.cvss_score
                })

    return results


async def import_from_github(
    repo: str = "torvalds/linux",
    since: Optional[str] = None,
    state: str = "all",
    limit: int = 100,
    dry_run: bool = False,
    offset: int = 0
) -> dict:
    """Import from GitHub Issues.

    Args:
        repo: GitHub repo (owner/name)
        since: Time range
        state: Issue state filter
        limit: Max bugs to import
        dry_run: Preview without importing
        offset: Skip this many results (auto-calculated if 0)
    """
    client = GitHubClient()
    db = await get_database()
    bug_repo = BugRepository(db)

    owner, repo_name = repo.split("/")
    since_dt = parse_since(since) if since else None

    # Auto-calculate offset from existing GitHub bugs if not specified
    if offset == 0:
        existing_bugs = await bug_repo.list_bugs(limit=1000)
        github_count = sum(1 for b in existing_bugs if b.source.value == "github")
        offset = github_count
        if github_count > 0:
            console.print(f"[yellow]Found {github_count} existing GitHub bugs, starting from offset {offset}[/yellow]")

    results = {"fetched": 0, "created": 0, "duplicates": 0, "samples": []}

    console.print(f"[cyan]Fetching issues from GitHub: {repo} (offset: {offset})[/cyan]")

    with Progress() as progress:
        task = progress.add_task(f"Importing from {repo}...", total=limit)

        async for bug in client.fetch_issues(owner, repo_name, state=state, since=since_dt, limit=limit, offset=offset):
            results["fetched"] += 1
            progress.update(task, advance=1)

            existing = await bug_repo.get_by_external_id(bug.external_id, bug.source.value)
            if existing:
                results["duplicates"] += 1
                continue

            if not dry_run:
                await bug_repo.create(bug)

            results["created"] += 1
            if len(results["samples"]) < 5:
                results["samples"].append({
                    "id": bug.external_id,
                    "title": bug.title[:60],
                    "severity": bug.severity.value
                })

    return results


async def run_import(
    source: str,
    keywords: Optional[str] = None,
    repo: Optional[str] = None,
    since: str = "30d",
    limit: int = 100,
    dry_run: bool = False
):
    """Run the data import workflow."""
    all_results = {}

    if source in ["nvd", "all"]:
        kw_list = keywords.split(",") if keywords else None
        results = await import_from_nvd(
            keywords=kw_list,
            since=since,
            limit=limit,
            dry_run=dry_run
        )
        all_results["NVD"] = results

    if source in ["github", "all"]:
        repo_to_use = repo or "intel/linux-intel-lts"
        results = await import_from_github(
            repo=repo_to_use,
            since=since,
            limit=limit,
            dry_run=dry_run
        )
        all_results["GitHub"] = results

    for src_name, results in all_results.items():
        table = Table(title=f"Import Results: {src_name}")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green")

        table.add_row("Fetched", str(results["fetched"]))
        table.add_row("Created", str(results["created"]))
        table.add_row("Duplicates", str(results["duplicates"]))

        console.print(table)

        if results["samples"]:
            console.print("\n[bold]Sample imports:[/bold]")
            for sample in results["samples"]:
                cvss = f" (CVSS: {sample.get('cvss', 'N/A')})" if sample.get('cvss') else ""
                console.print(f"  - {sample['id']}: {sample['title']} [{sample['severity']}]{cvss}")

        console.print()

    if dry_run:
        console.print("[yellow]DRY RUN - No data was imported[/yellow]")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Data Import Skill")
    parser.add_argument("source", choices=["nvd", "github", "all"], help="Data source")
    parser.add_argument("--keywords", help="Search keywords (NVD)")
    parser.add_argument("--repo", help="GitHub repository (owner/repo)")
    parser.add_argument("--since", default="30d", help="Time range (7d, 30d, or date)")
    parser.add_argument("--limit", type=int, default=100, help="Maximum bugs to import")
    parser.add_argument("--dry-run", action="store_true", help="Preview without importing")
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    asyncio.run(run_import(
        source=args.source,
        keywords=args.keywords,
        repo=args.repo,
        since=args.since,
        limit=args.limit,
        dry_run=args.dry_run
    ))


if __name__ == "__main__":
    main()
