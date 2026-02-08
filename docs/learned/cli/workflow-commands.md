---
audit_result: clean
last_audited: 2026-02-08 05:59 PT
read_when:
- triggering GitHub Actions workflows from CLI
- adding a new workflow to erk launch
- understanding local vs remote command duality
title: Workflow Commands
tripwires:
- action: WORKFLOW_COMMAND_MAP maps command names to .yml filenames
  warning: command names intentionally diverge from filenames (e.g., pr-fix-conflicts
    → pr-fix-conflicts.yml, but plan-implement → plan-implement.yml via DISPATCH_WORKFLOW_NAME
    constant)
- action: plan-implement exists in WORKFLOW_COMMAND_MAP but erk launch plan-implement
    always raises UsageError
  warning: use erk plan submit instead
- action: using this pattern
  warning: PR workflows automatically update plan issue dispatch metadata when the
    branch follows the P{issue_number} naming pattern
---

# Workflow Commands

## Design Decisions

### Why a Unified Launcher

`erk launch` consolidates all GitHub Actions workflow triggers behind a single command instead of scattering them across subcommand groups (e.g., `erk pr fix-conflicts-remote`, `erk workflow launch`). This was a deliberate migration away from the old pattern where each remote operation had its own command in the relevant noun group.

The trade-off: the launcher uses a flat option namespace shared across all workflows (`--pr`, `--issue`, `--objective`, `--model`, `--no-squash`, `--dry-run`), with per-workflow validation enforcing which options are required. This avoids Click subcommand proliferation but means invalid option combinations are caught at runtime, not by the CLI framework.

### Local vs Remote Duality

Two operations have both local and remote variants — `pr fix-conflicts` and `pr address`. The local commands live under `erk pr` and invoke Claude CLI directly (requiring `--dangerous` flag). The remote commands are accessed via `erk launch` and trigger GitHub Actions workflows instead.

<!-- Source: src/erk/cli/commands/pr/fix_conflicts_cmd.py, fix_conflicts -->
<!-- Source: src/erk/cli/commands/pr/address_cmd.py, address -->

The local variants reference the remote alternatives in their help text, creating discoverability in both directions. See `fix_conflicts()` in `src/erk/cli/commands/pr/fix_conflicts_cmd.py` and `address()` in `src/erk/cli/commands/pr/address_cmd.py`.

### Why plan-implement Is Blocked

`plan-implement` exists in `WORKFLOW_COMMAND_MAP` but `erk launch plan-implement` always raises `UsageError` directing users to `erk plan submit`. The plan-implement workflow requires branch creation, PR setup, and metadata initialization that `erk plan submit` handles as a coordinated sequence. Triggering the workflow directly would skip these prerequisites and produce orphaned workflow runs.

## Adding a New Workflow

When adding a workflow to `erk launch`:

1. Add the command-name → filename mapping to `WORKFLOW_COMMAND_MAP` in `src/erk/cli/constants.py`
2. Create a `_trigger_<name>()` handler function in `src/erk/cli/commands/launch_cmd.py`
3. Add a dispatch branch in the `launch()` Click command body
4. Add any new Click options to the shared option set on the `launch` command

<!-- Source: src/erk/cli/constants.py, WORKFLOW_COMMAND_MAP -->
<!-- Source: src/erk/cli/commands/launch_cmd.py, launch -->

The handler functions follow a consistent pattern: validate inputs → fetch context from GitHub → build `inputs: dict[str, str]` → call `ctx.github.trigger_workflow()`. See `_trigger_pr_fix_conflicts()` and `_trigger_pr_address()` in `src/erk/cli/commands/launch_cmd.py` for the canonical examples.

## Plan Dispatch Metadata Side Effect

PR-related workflows (`pr-fix-conflicts`, `pr-address`) have an automatic side effect: after triggering the workflow, they call `maybe_update_plan_dispatch_metadata()` which checks if the branch name follows the `P{issue_number}-*` pattern. If so, it writes dispatch metadata (run ID, node ID, timestamp) back to the associated plan issue body.

<!-- Source: src/erk/cli/commands/pr/metadata_helpers.py, maybe_update_plan_dispatch_metadata -->

This is a cross-cutting concern — the launch command doesn't know about plans, but the metadata helper silently links workflow runs to their originating plan issues. The function uses multiple LBYL early returns (no matching branch pattern, no node ID available, no plan-header metadata block) to gracefully skip non-plan branches.

## Anti-Patterns

**DON'T trigger plan-implement via `erk launch`** — always use `erk plan submit`, which handles the full branch + PR + metadata setup sequence.

**DON'T add workflow-specific subcommands under noun groups** — use `erk launch <name>` for all remote workflow triggers. The old pattern (`erk pr fix-conflicts-remote`) was migrated away from intentionally.

**DON'T hardcode workflow filenames in handler functions** — always resolve through `WORKFLOW_COMMAND_MAP` via `_get_workflow_file()`, even inside the handler that "knows" its own workflow name. This keeps the mapping authoritative.

## Related Documentation

- [Remote Workflow Template](../erk/remote-workflow-template.md) — Workflow YAML patterns for the Actions side
- [GitHub Actions Workflow Patterns](../ci/github-actions-workflow-patterns.md) — CI best practices
- [Command Organization](command-organization.md) — CLI structure decisions including verb placement
