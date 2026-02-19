---
title: PR Body Assembly
read_when:
  - "implementing or modifying PR body construction"
  - "working with PR footer, closing references, or issue discovery"
  - "adding a new PR command that generates or updates PR descriptions"
tripwires:
  - action: "implementing a new `erk pr` command"
    warning: "Compare feature parity with `submit_pipeline.py`. Check: issue discovery, closing reference preservation, learn plan labels, footer construction, and plan details section. Use shared utilities from `shared.py` (`assemble_pr_body`, `discover_issue_for_footer`)."
  - action: "calling assemble_pr_body without metadata_prefix for draft-PR plans"
    warning: "Draft-PR plans require metadata_prefix from extract_metadata_prefix(). Without it, plan-header metadata is lost on every PR rewrite."
  - action: "adding Closes #N for draft-PR backend"
    warning: "Set issue_number=None for draft-PR backend. The draft PR IS the plan — Closes #N would be self-referential."
---

# PR Body Assembly

Shared utilities for constructing PR bodies live in `src/erk/cli/commands/pr/shared.py`. Both `rewrite_cmd.py` and `submit_pipeline.py` use these functions to ensure consistent PR body format across all PR commands.

## Key Functions

<!-- Source: src/erk/cli/commands/pr/shared.py, assemble_pr_body -->

**`assemble_pr_body()`** — Consolidates PR body construction. Combines the AI-generated body, optional plan details section, and footer (with checkout command and closing reference) into a complete PR body ready for the GitHub API.

<!-- Source: src/erk/cli/commands/pr/shared.py, discover_issue_for_footer -->

**`discover_issue_for_footer()`** — Two-step issue discovery for the PR footer:

1. **Primary**: Reads `.impl/issue.json` via `read_issue_reference()`, cross-checked against the branch name pattern (`P{N}-{slug}`)
2. **Fallback**: Extracts closing reference from existing PR body via `extract_closing_reference()`

Returns `IssueDiscovery` on success or `IssueLinkageMismatch` if branch name and `.impl/issue.json` disagree on the issue number.

<!-- Source: src/erk/cli/commands/pr/shared.py, build_plan_details_section -->

**`build_plan_details_section()`** — Builds a collapsed `<details>` section embedding the plan content in the PR body. Used when a `PlanContext` is available.

<!-- Source: src/erk/cli/commands/pr/shared.py, run_commit_message_generation -->

**`run_commit_message_generation()`** — Runs the AI commit message generator and collects progress/completion events. Returns `CommitMessageResult` with the generated title and body.

## Data Types

<!-- Source: src/erk/cli/commands/pr/shared.py, IssueDiscovery -->

**`IssueDiscovery`** — Frozen dataclass holding the discovered `issue_number` and `plans_repo` for footer construction.

<!-- Source: src/erk/cli/commands/pr/shared.py, IssueLinkageMismatch -->

**`IssueLinkageMismatch`** — Error type returned when the branch name's leading issue number disagrees with `.impl/issue.json`. Contains a descriptive `message` field.

## Draft-PR Backend: metadata_prefix Parameter

`assemble_pr_body()` accepts a `metadata_prefix` parameter that controls backend-specific behavior:

| Backend                      | `metadata_prefix`      | Plan section format             | `issue_number`                 |
| ---------------------------- | ---------------------- | ------------------------------- | ------------------------------ |
| Issue-based (`github`)       | `""` (empty)           | `build_plan_details_section()`  | Plan issue number              |
| Draft-PR (`github-draft-pr`) | Extracted from PR body | `build_original_plan_section()` | `None` (self-close prevention) |

When `metadata_prefix` is non-empty, the function uses `build_original_plan_section()` (from `draft_pr_lifecycle.py`) instead of `build_plan_details_section()` to format the plan content.

### Backend Detection Pattern

All three consumers detect draft-PR backend the same way:

<!-- Source: src/erk/cli/commands/pr/rewrite_cmd.py:166-171, src/erk/cli/commands/exec/scripts/update_pr_description.py:153-160, src/erk/cli/commands/pr/submit_pipeline.py:625-631 -->

Each consumer checks `ctx.plan_backend.get_provider_name() == "github-draft-pr"`. On match, it extracts `metadata_prefix` from the existing PR body via `extract_metadata_prefix()` and sets `issue_number = None` to prevent self-close.

### Self-Referential Close Prevention

Draft PR IS the plan. Using `Closes #N` in the footer (where N is the PR's own number) would cause the plan to close itself when merged. All consumers set `issue_number=None` for draft-PR backend.

## Consumers

| Command                          | Uses                                                                             |
| -------------------------------- | -------------------------------------------------------------------------------- |
| `erk pr rewrite`                 | `assemble_pr_body`, `discover_issue_for_footer`, `run_commit_message_generation` |
| `erk pr submit`                  | `assemble_pr_body`, `run_commit_message_generation`                              |
| `erk exec update-pr-description` | `assemble_pr_body`                                                               |

## Related Topics

- [Draft PR Lifecycle](../planning/draft-pr-lifecycle.md) — PR body format through lifecycle stages
- [PR Rewrite Command](../cli/pr-rewrite.md) — The command that replaced `erk pr summarize`
- [PR Submit Pipeline Architecture](../cli/pr-submit-pipeline.md) — The multi-step submit pipeline
