"""Bug Report Skill - Generate reports and analytics."""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# Add project root to path (4 levels up: Scripts -> bug-report -> skills -> .claude -> project)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.bug_tracker.database.connection import get_database
from src.bug_tracker.database.repositories import BugRepository


console = Console()


def parse_period(period_str: str) -> datetime:
    """Parse period parameter to start datetime."""
    if period_str.endswith("d"):
        days = int(period_str[:-1])
        return datetime.utcnow() - timedelta(days=days)
    elif period_str.endswith("h"):
        hours = int(period_str[:-1])
        return datetime.utcnow() - timedelta(hours=hours)
    else:
        return datetime.fromisoformat(period_str)


async def summary_report(period: str = "30d") -> dict:
    """Generate summary report."""
    db = await get_database()
    bug_repo = BugRepository(db)

    by_status = await bug_repo.count_by_status()
    by_severity = await bug_repo.count_by_severity()

    total = sum(by_status.values())
    open_count = (
        by_status.get("new", 0) +
        by_status.get("triaged", 0) +
        by_status.get("in_progress", 0) +
        by_status.get("reopened", 0)
    )
    closed_count = by_status.get("closed", 0)

    console.print(Panel(
        f"[bold]Bug Tracking Summary Report[/bold]\n"
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
        f"Period: Last {period}",
        title="Summary"
    ))

    stats_table = Table(title="Overview")
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Count", style="green")
    stats_table.add_column("Percentage", style="yellow")

    stats_table.add_row("Total Bugs", str(total), "100%")
    stats_table.add_row("Open", str(open_count), f"{open_count/total*100:.1f}%" if total else "0%")
    stats_table.add_row("Closed", str(closed_count), f"{closed_count/total*100:.1f}%" if total else "0%")

    console.print(stats_table)

    severity_table = Table(title="By Severity")
    severity_table.add_column("Severity", style="cyan")
    severity_table.add_column("Count", style="green")
    severity_table.add_column("Percentage", style="yellow")

    severity_order = ["critical", "high", "medium", "low", "info"]
    for sev in severity_order:
        count = by_severity.get(sev, 0)
        pct = f"{count/total*100:.1f}%" if total else "0%"
        severity_table.add_row(sev.capitalize(), str(count), pct)

    console.print(severity_table)

    status_table = Table(title="By Status")
    status_table.add_column("Status", style="cyan")
    status_table.add_column("Count", style="green")

    for status, count in sorted(by_status.items(), key=lambda x: -x[1]):
        status_table.add_row(status.replace("_", " ").title(), str(count))

    console.print(status_table)

    return {
        "total": total,
        "open": open_count,
        "closed": closed_count,
        "by_status": by_status,
        "by_severity": by_severity
    }


async def security_report(cvss_min: float = 0.0) -> dict:
    """Generate security-focused report."""
    db = await get_database()
    bug_repo = BugRepository(db)

    security_bugs = await bug_repo.get_security_bugs(min_cvss=cvss_min)

    console.print(Panel(
        f"[bold]Security Bug Report[/bold]\n"
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
        f"CVSS Minimum: {cvss_min}",
        title="Security Report"
    ))

    console.print(f"\n[bold]Total Security Bugs: {len(security_bugs)}[/bold]\n")

    severity_counts = {}
    cwe_counts = {}
    for bug in security_bugs:
        sev = bug.severity.value
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

        if bug.cwe_id:
            cwe_counts[bug.cwe_id] = cwe_counts.get(bug.cwe_id, 0) + 1

    severity_table = Table(title="By Severity")
    severity_table.add_column("Severity", style="cyan")
    severity_table.add_column("Count", style="red")

    for sev in ["critical", "high", "medium", "low"]:
        count = severity_counts.get(sev, 0)
        severity_table.add_row(sev.capitalize(), str(count))

    console.print(severity_table)

    if cwe_counts:
        cwe_table = Table(title="Top CWEs")
        cwe_table.add_column("CWE ID", style="cyan")
        cwe_table.add_column("Count", style="green")

        for cwe, count in sorted(cwe_counts.items(), key=lambda x: -x[1])[:10]:
            cwe_table.add_row(cwe, str(count))

        console.print(cwe_table)

    critical_bugs = [b for b in security_bugs if b.severity.value == "critical"]
    if critical_bugs:
        console.print("\n[bold red]Critical Vulnerabilities:[/bold red]")
        for bug in critical_bugs[:10]:
            cvss = f" (CVSS: {bug.cvss_score})" if bug.cvss_score else ""
            console.print(f"  - {bug.external_id or bug.id[:8]}: {bug.title[:60]}{cvss}")

    return {
        "total": len(security_bugs),
        "by_severity": severity_counts,
        "top_cwes": dict(sorted(cwe_counts.items(), key=lambda x: -x[1])[:10])
    }


async def component_report(chip_filter: Optional[str] = None) -> dict:
    """Generate component breakdown report."""
    db = await get_database()
    bug_repo = BugRepository(db)

    bugs = await bug_repo.list_bugs(chip_family=chip_filter, limit=10000)

    component_counts = {}
    component_severity = {}

    for bug in bugs:
        comp = bug.component.value
        component_counts[comp] = component_counts.get(comp, 0) + 1

        if comp not in component_severity:
            component_severity[comp] = {}
        sev = bug.severity.value
        component_severity[comp][sev] = component_severity[comp].get(sev, 0) + 1

    console.print(Panel(
        f"[bold]Component Breakdown Report[/bold]\n"
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
        f"Chip Filter: {chip_filter or 'All'}",
        title="Component Report"
    ))

    comp_table = Table(title="Bugs by Component")
    comp_table.add_column("Component", style="cyan")
    comp_table.add_column("Total", style="green")
    comp_table.add_column("Critical", style="red")
    comp_table.add_column("High", style="yellow")
    comp_table.add_column("Medium", style="blue")

    for comp, count in sorted(component_counts.items(), key=lambda x: -x[1]):
        sevs = component_severity.get(comp, {})
        comp_table.add_row(
            comp.upper(),
            str(count),
            str(sevs.get("critical", 0)),
            str(sevs.get("high", 0)),
            str(sevs.get("medium", 0))
        )

    console.print(comp_table)

    return {
        "by_component": component_counts,
        "component_severity": component_severity
    }


async def chip_report() -> dict:
    """Generate chip family breakdown report."""
    db = await get_database()
    bug_repo = BugRepository(db)

    bugs = await bug_repo.list_bugs(limit=10000)

    chip_counts = {}
    chip_component = {}

    for bug in bugs:
        chip = bug.chip_family.value if bug.chip_family else "Unknown"
        chip_counts[chip] = chip_counts.get(chip, 0) + 1

        if chip not in chip_component:
            chip_component[chip] = {}
        comp = bug.component.value
        chip_component[chip][comp] = chip_component[chip].get(comp, 0) + 1

    console.print(Panel(
        f"[bold]Chip Family Breakdown Report[/bold]\n"
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
        title="Chip Report"
    ))

    chip_table = Table(title="Bugs by Chip Family")
    chip_table.add_column("Chip Family", style="cyan")
    chip_table.add_column("Total Bugs", style="green")
    chip_table.add_column("Top Component", style="yellow")

    for chip, count in sorted(chip_counts.items(), key=lambda x: -x[1]):
        components = chip_component.get(chip, {})
        top_comp = max(components.items(), key=lambda x: x[1])[0] if components else "N/A"
        chip_table.add_row(chip, str(count), top_comp.upper())

    console.print(chip_table)

    return {
        "by_chip": chip_counts,
        "chip_component": chip_component
    }


async def run_report(
    report_type: str,
    period: str = "30d",
    cvss_min: float = 0.0,
    chip: Optional[str] = None,
    output_format: str = "text",
    output_file: Optional[str] = None
):
    """Run the requested report."""
    if report_type == "summary":
        result = await summary_report(period)
    elif report_type == "security":
        result = await security_report(cvss_min)
    elif report_type == "component":
        result = await component_report(chip)
    elif report_type == "chip":
        result = await chip_report()
    else:
        console.print(f"[red]Unknown report type: {report_type}[/red]")
        return

    if output_file:
        with open(output_file, "w") as f:
            if output_format == "json":
                json.dump(result, f, indent=2, default=str)
            else:
                f.write(str(result))
        console.print(f"\n[green]Report saved to: {output_file}[/green]")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Bug Report Skill")
    parser.add_argument(
        "report_type",
        choices=["summary", "security", "component", "chip", "trends"],
        help="Type of report"
    )
    parser.add_argument("--period", default="30d", help="Time period")
    parser.add_argument("--cvss-min", type=float, default=0.0, help="Minimum CVSS score")
    parser.add_argument("--chip", help="Filter by chip family")
    parser.add_argument("--format", dest="output_format", default="text", choices=["text", "json"])
    parser.add_argument("--output", dest="output_file", help="Output file path")
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    asyncio.run(run_report(
        report_type=args.report_type,
        period=args.period,
        cvss_min=args.cvss_min,
        chip=args.chip,
        output_format=args.output_format,
        output_file=args.output_file
    ))


if __name__ == "__main__":
    main()
