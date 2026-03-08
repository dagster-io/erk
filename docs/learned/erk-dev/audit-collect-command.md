---
title: Audit Collect Command
read_when:
  - "modifying the erk-dev audit-collect command"
  - "working with branch/worktree/PR audit data"
  - "understanding the /audit-branches slash command data source"
tripwires:
  - action: "adding mutation logic to audit-collect"
    warning: "audit-collect is read-only data collection. It outputs JSON for the /audit-branches command to consume. Never add delete/cleanup operations here."
---

# Audit Collect Command

The `erk-dev audit-collect` command collects branch, worktree, and PR data as structured JSON. It is the data source for the `/audit-branches` slash command, which was simplified from ~620 to ~150 lines by delegating collection to this CLI command.

## Purpose

Separates data collection (deterministic, testable CLI) from decision-making (AI agent in slash command). The command gathers and categorizes data; the slash command interprets it and suggests actions.

## JSON Output Schema

<!-- Source: packages/erk-dev/src/erk_dev/commands/audit_collect/command.py -->

The command outputs a JSON object via `json.dumps(asdict(audit_result))`:

```
AuditResult:
  success: bool
  summary:
    total_local_branches: int
    total_worktrees: int
    total_open_prs: int
  categories:
    blocking_worktrees: [...]    # Worktrees preventing branch cleanup
    auto_cleanup: [...]          # Safe to auto-delete
    closed_pr_branches: [...]    # Branches with closed/merged PRs
    pattern_branches: [...]      # Branches matching cleanup patterns
    stale_open_prs: [...]        # Open PRs with no recent activity
    needs_attention: [...]       # Require manual review
    active: [...]                # Currently in use
  stubs_tracked_by_graphite: [str]
```

All types are frozen dataclasses serialized via `dataclasses.asdict()`.

## ErkDevContext Fields

The command accesses three fields from `ErkDevContext`:

- `git` — Gateway to git operations (branch listing, worktree enumeration)
- `github` — Gateway to GitHub operations (PR listing, status checks)
- `repo_root` — Repository root `Path` for all operations

## Design Decisions

- **Side-effect-free categorization**: `_run_audit_collect()` is a pure function taking pre-fetched data and returning `AuditResult`
- **Testability**: Core logic separated from Click command for unit testing (22+ tests in `test_audit_collect.py`)
- **CLI push-down pattern**: Moved data collection from embedded bash in slash command to tested CLI

## Related Documentation

- [CLI Push-Down Pattern](../refactoring/cli-push-down-pattern.md) — Design principle behind this separation
