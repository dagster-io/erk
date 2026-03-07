---
title: Workflow Run List
read_when:
  - "modifying workflow run list display"
  - "working with erk workflow run list"
  - "understanding run-name format parsing"
  - "modifying workflow run display"
---

# Workflow Run List

The `erk workflow run list` command displays GitHub Actions workflow runs in a PR-centric table view.

## Command Hierarchy

Moved from top-level `erk run` to `erk workflow run list` and `erk workflow run logs` in PR #8549.

## Source Files

- `src/erk/cli/commands/run/list_cmd.py` -- Main list command (192 lines)
- `src/erk/cli/commands/run/shared.py` -- Shared utilities (42 lines)
- `src/erk/cli/commands/doctor_workflow.py:253` -- Registration point

## PR-Centric Display

Runs are displayed with PR numbers extracted from run-name format. The table columns are: run-id, status, submitted, workflow, pr, title, chks.

## Run-Name Format Parsing

<!-- Source: src/erk/cli/commands/run/shared.py:6-23 -->

`extract_pr_number()` in `shared.py` uses regex `r"#(\d+)"` to extract PR numbers from `display_title`:

Supported formats:

- `"pr-address:#456:abc123"` -> 456
- `"8559:#460:abc123"` -> 460
- `"one-shot:#458:abc123"` -> 458
- `"rebase:#456:abc123"` -> 456
- `"plnd/fix-auth-bug-01-15-1430 (#460):abc456"` -> 460 (plan-implement branch-name format)

The plan-implement workflow uses a `run-name` template of `"${{ inputs.branch_name }} (#${{ inputs.pr_number }}):${{ inputs.distinct_id }}"`, which includes the branch name for easier identification. The `#(\d+)` regex works with both old and new formats because it matches the `#NNN` pattern regardless of surrounding context.

Formats without `#` return None and fall back to plan-PR linkage via `extract_plan_number()` which parses `"NUMBER:HASH"` format.

## Workflow Source Column

<!-- Source: src/erk/cli/commands/run/list_cmd.py:42-45 -->

Iterates `WORKFLOW_COMMAND_MAP` (maps command names to .yml filenames) and tags each run with its source workflow.

## Constants

<!-- Source: src/erk/cli/commands/run/list_cmd.py:27-29 -->

| Constant              | Value | Purpose                      |
| --------------------- | ----- | ---------------------------- |
| `_MAX_DISPLAY_RUNS`   | 50    | Maximum runs shown in output |
| `_PER_WORKFLOW_LIMIT` | 20    | Runs fetched per workflow    |
| `_MAX_TITLE_LENGTH`   | 50    | Title truncation threshold   |

## Deduplication

<!-- Source: src/erk/cli/commands/run/list_cmd.py:47-52 -->

Uses dict-based `seen[run_id]` pattern for O(n) deduplication across all workflows.

## learn.yml Exception

The learn workflow has no PR number in run-name because learn runs execute post-merge and don't receive a `pr_number` input.

## Related Documentation

- [Workflow Commands](workflow-commands.md) -- WORKFLOW_COMMAND_MAP and dispatch patterns
