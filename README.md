# Bug Tracker Plugin for Claude Code

A Claude Code plugin for semiconductor bug tracking with MCP integration, AI-powered triage, and multi-source data import.

## Features

- **4 Skills**: Bug triage, data import, bug reports, classification explanations
- **4 Agents**: Triage, classification, explainer, routing agents
- **MCP Server**: 14+ tools for bug CRUD, queries, and workflow
- **Chip Detection**: Intel, AMD, ARM, NVIDIA, Qualcomm

## Installation

```bash
/plugin install Raman11-1/bug-tracker-plugin
```

## Skills

| Skill | Command | Description |
|-------|---------|-------------|
| Bug Triage | `/bug-tracker:bug-triage` | Classify bugs by severity, component, chip family |
| Data Import | `/bug-tracker:data-import` | Import from NVD (CVE) or GitHub Issues |
| Bug Report | `/bug-tracker:bug-report` | Generate summary, security, component reports |
| Bug Explain | `/bug-tracker:bug-explain` | Explain classification decisions |

## Agents

| Agent | Description |
|-------|-------------|
| `@triage-agent` | Analyzes bugs, assigns severity/component/team |
| `@classification-agent` | Pattern matching with keywords |
| `@explainer-agent` | Explains classification reasoning |
| `@routing-agent` | Routes bugs to appropriate teams |

## MCP Tools

- `create_bug`, `get_bug`, `update_bug`, `delete_bug`
- `list_bugs`, `search_bugs`, `get_bug_stats`
- `transition_bug`, `assign_bug`, `add_comment`
- `get_untriaged_bugs`, `get_security_bugs`
- `get_bug_history`, `get_bug_comments`

## Requirements

This plugin requires the Bug Tracking System project to be set up:
- Clone: https://github.com/Raman11-1/Bug_Traking_System
- Run: `uv sync && uv run python main.py init`

## License

MIT
