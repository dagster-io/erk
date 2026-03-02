---
title: Workflow Run List
read_when:
  - "workflow run list"
  - "erk run"
  - "workflow runs"
  - "run-name format"
tripwires:
  - action: "changing run-name format in workflow files"
    warning: "extract_pr_number() in shared.py parses '#NNN' from run-name. Changing the format breaks PR number extraction in the run list display."
---

# Workflow Run List

The `erk workflow run list` command displays GitHub Actions workflow runs with a PR-centric view.

## Command Hierarchy

Moved from top-level `erk run` in PR #8549 to:

- `erk workflow run list` — List recent workflow runs
- `erk workflow run logs` — View logs for a specific run

<!-- Source: src/erk/cli/commands/run/__init__.py -->

The `run_group` is registered in `doctor_workflow.py:253` via `workflow_group.add_command(run_group)`.

## PR-Centric Display

<!-- Source: src/erk/cli/commands/run/list_cmd.py -->

Each run is displayed with its associated PR number, extracted from the run-name format.

### Run-Name Format Parsing

<!-- Source: src/erk/cli/commands/run/shared.py -->

Two extraction functions in `shared.py`:

**`extract_pr_number(display_title)`** — Uses regex `r"#(\d+)"` to find PR numbers:

- New format: `"pr-address:#456:abc123"` → 456
- New format: `"8559:#460:abc123"` → 460
- Old format without `#`: returns None

**`extract_plan_number(display_title)`** — Parses colon-based format:

- Format: `"123:abc456"` → 123 (plan number is first segment before colon)
- Falls back when `extract_pr_number` returns None

PR numbers are preferred; plan numbers are used as fallback for plan→PR linkage via `get_prs_linked_to_issues()`.

## Workflow Source Column

Iterates `WORKFLOW_COMMAND_MAP` (defined in `src/erk/cli/constants.py`) to tag each run with its source workflow:

| Command Name     | Workflow File      |
| ---------------- | ------------------ |
| `plan-implement` | plan-implement.yml |
| `pr-rebase`      | pr-rebase.yml      |
| `pr-address`     | pr-address.yml     |
| `pr-rewrite`     | pr-rewrite.yml     |
| `learn`          | learn.yml          |
| `one-shot`       | one-shot.yml       |

## Constants

| Constant              | Value | Purpose                           |
| --------------------- | ----- | --------------------------------- |
| `_MAX_DISPLAY_RUNS`   | 50    | Maximum total runs displayed      |
| `_PER_WORKFLOW_LIMIT` | 20    | Maximum runs fetched per workflow |
| `_MAX_TITLE_LENGTH`   | 50    | Truncation limit for title column |

## Deduplication

Uses dict-based deduplication keyed by `run_id`:

<!-- Source: src/erk/cli/commands/run/list_cmd.py, _deduplicate_runs -->

See `_deduplicate_runs()` in `src/erk/cli/commands/run/list_cmd.py` — it uses dict-based deduplication keyed by `run_id`, which is O(n) and handles the case where a run matches multiple workflows.

## learn.yml Exception

The `learn` workflow has no PR number in its run-name because learn runs execute post-merge (no `pr_number` input). The `extract_pr_number()` function returns None, and the plan number fallback is used for display linkage.

## Source Files

- `src/erk/cli/commands/run/list_cmd.py` — Main list command implementation
- `src/erk/cli/commands/run/shared.py` — Shared extraction utilities
- `src/erk/cli/commands/doctor_workflow.py:253` — Registration point

## Related Documentation

- [Workflow Commands](workflow-commands.md) — WORKFLOW_COMMAND_MAP and dispatch patterns
