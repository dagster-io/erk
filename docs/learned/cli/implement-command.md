---
title: Implement Command
read_when:
  - "running erk implement without arguments"
  - "auto-detecting plans from current branch"
  - "understanding how erk implement selects which plan to execute"
tripwires:
  - action: "assuming erk implement always requires a plan number argument"
    warning: "erk implement supports auto-detection from .erk/impl-context/ and from branch PRs. Read this doc first."
---

# Implement Command

The `erk implement` command sets up an implementation environment and executes a plan. When called without arguments, it uses a two-strategy auto-detection system to find the plan.

## Auto-Detection Strategies

<!-- Source: src/erk/cli/commands/implement.py, implement() command -->

When `TARGET` is omitted, `erk implement` tries two strategies in order:

### Strategy 1: Resolve from `.erk/impl-context/`

Calls `resolve_impl_dir()` (from `erk_shared.impl_folder`) to check if an impl directory already exists under `.erk/impl-context/` for the current branch. If found, the plan is loaded from that directory without any network calls.

### Strategy 2: Extract from Branch PR

Calls `extract_plan_from_current_branch()` to look up the current branch's associated GitHub PR and extract the plan number from it. This handles the case where a plan branch has been checked out but the impl directory hasn't been set up yet.

If neither strategy finds a plan, the command exits with an error.

## Execution Modes

<!-- Source: src/erk/cli/commands/implement.py, _execute() -->

The shared execution function supports multiple execution modes:

| Mode            | Flag               | Behavior                                          |
| --------------- | ------------------ | ------------------------------------------------- |
| Interactive     | (default)          | Opens Claude Code for interactive implementation  |
| Non-interactive | `--no-interactive` | Runs implementation without user interaction      |
| Script          | `--script <path>`  | Executes a custom script against the impl context |
| Dry-run         | `--dry-run`        | Shows what would happen without side effects      |

## Usage Examples

```bash
# Auto-detect from impl-context or branch PR
erk implement

# Implement a specific plan by number
erk implement 42

# Implement from a local markdown file
erk implement ./my-plan.md

# Non-interactive execution
erk implement 42 --no-interactive
```

## Related Documentation

- [Impl Context](../planning/impl-context.md) - How `.erk/impl-context/` directories work
- [Plan Lifecycle](../planning/lifecycle.md) - Plan states and transitions
