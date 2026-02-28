---
title: PR Body Assembly
read_when:
  - "implementing or modifying PR body construction"
  - "working with PR footer or checkout command"
  - "adding a new PR command that generates or updates PR descriptions"
tripwires:
  - action: "implementing a new `erk pr` command"
    warning: "Compare feature parity with `submit_pipeline.py`. Check: learn plan labels, footer construction, and plan details section. Use shared utilities from `shared.py` (`assemble_pr_body`)."
  - action: "calling assemble_pr_body without metadata_prefix for planned-PR plans"
    warning: "Planned PR plans require metadata_prefix from find_metadata_block(). Without it, plan-header metadata is lost on every PR rewrite."
---

# PR Body Assembly

Shared utilities for constructing PR bodies live in `src/erk/cli/commands/pr/shared.py`. Both `rewrite_cmd.py` and `submit_pipeline.py` use these functions to ensure consistent PR body format across all PR commands.

## Key Functions

<!-- Source: src/erk/cli/commands/pr/shared.py, assemble_pr_body -->

**`assemble_pr_body()`** — Consolidates PR body construction. Combines the AI-generated body, optional plan details section, and footer (with checkout command) into a complete PR body ready for the GitHub API.

<!-- Source: src/erk/cli/commands/pr/shared.py, build_plan_details_section -->

**`build_plan_details_section()`** — Builds a collapsed `<details>` section embedding the plan content in the PR body. Used when a `PlanContext` is available.

<!-- Source: src/erk/cli/commands/pr/shared.py, run_commit_message_generation -->

**`run_commit_message_generation()`** — Runs the AI commit message generator and collects progress/completion events. Returns `CommitMessageResult` with the generated title and body.

## Planned PR Backend: plan-header metadata

`assemble_pr_body()` detects whether the existing PR body contains a plan-header metadata block. When present, it uses `build_original_plan_section()` (from `planned_pr_lifecycle.py`) instead of `build_plan_details_section()` to format the plan content.

| Backend                        | Plan section format             |
| ------------------------------ | ------------------------------- |
| Issue-based (`github`)         | `build_plan_details_section()`  |
| Planned PR (`github-draft-pr`) | `build_original_plan_section()` |

## No "Closes #N" References

PR bodies no longer contain `Closes #N` references. Plan issue closure is handled directly via the GitHub API in `erk land` (see `objective_helpers.py`). This avoids unreliable GitHub auto-close behavior.

## Consumers

| Command                          | Uses                                                |
| -------------------------------- | --------------------------------------------------- |
| `erk pr rewrite`                 | `assemble_pr_body`, `run_commit_message_generation` |
| `erk pr submit`                  | `assemble_pr_body`, `run_commit_message_generation` |
| `erk exec update-pr-description` | `assemble_pr_body`, `run_commit_message_generation` |

## Related Topics

- [Planned PR Lifecycle](../planning/planned-pr-lifecycle.md) — PR body format through lifecycle stages
- [PR Rewrite Command](../cli/pr-rewrite.md) — The command that replaced `erk pr summarize`
- [PR Submit Pipeline Architecture](../cli/pr-submit-pipeline.md) — The multi-step submit pipeline
