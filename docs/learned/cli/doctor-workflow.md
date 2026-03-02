---
title: Doctor Workflow Subcommand
read_when:
  - "modifying doctor command or workflow diagnostics"
  - "adding health checks to doctor"
tripwires:
  - action: "adding doctor subcommand without invoke_without_command=True"
    warning: "Doctor uses Click group with invoke_without_command=True so bare 'erk doctor' preserves original behavior."
---

# Doctor Workflow Subcommand

## Architecture

`erk doctor` is a Click group with `invoke_without_command=True`, preserving backward compatibility (bare `erk doctor` still runs the original health checks). `erk doctor workflow` is a subgroup for workflow-specific diagnostics.

## Subcommands

| Command                          | Purpose                                                  |
| -------------------------------- | -------------------------------------------------------- |
| `erk doctor workflow check`      | Static health checks (GitHub auth, secrets, permissions) |
| `erk doctor workflow smoke-test` | Production dispatch test with configurable `--wait`      |
| `erk doctor workflow cleanup`    | Remove `plnd/smoke-test-*` branches and associated PRs   |
| `erk doctor workflow list`       | List installed workflows                                 |

## Health Checks

`erk doctor workflow check` validates:

- GitHub CLI authentication
- Queue PAT secret
- Anthropic API secret
- Workflow permissions
- `CLAUDE_ENABLED` variable
- Workflow artifacts

## Smoke Test

Dispatches through the production one-shot code path with a test plan. The `--wait` flag controls how long to wait for the workflow to complete before reporting results.

## Key Types

All frozen dataclasses:

- `SmokeTestResult`: Success outcome with run details
- `SmokeTestError`: Failure with error context
- `CleanupItem`: Branch/PR pair for cleanup

## Files

- `src/erk/cli/commands/doctor_workflow.py` - CLI subcommands
- `src/erk/core/workflow_smoke_test.py` - Smoke test logic
