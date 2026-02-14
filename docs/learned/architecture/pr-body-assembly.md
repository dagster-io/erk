---
title: PR Body Assembly
read_when:
  - "implementing or modifying PR body construction"
  - "working with PR footer, closing references, or issue discovery"
  - "adding a new PR command that generates or updates PR descriptions"
tripwires:
  - action: "implementing a new `erk pr` command"
    warning: "Compare feature parity with `submit_pipeline.py`. Check: issue discovery, closing reference preservation, learn plan labels, footer construction, and plan details section. Use shared utilities from `shared.py` (`assemble_pr_body`, `discover_issue_for_footer`)."
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

## Consumers

| Command          | Uses                                                                             |
| ---------------- | -------------------------------------------------------------------------------- |
| `erk pr rewrite` | `assemble_pr_body`, `discover_issue_for_footer`, `run_commit_message_generation` |
| `erk pr submit`  | `assemble_pr_body`, `run_commit_message_generation`                              |

## Related Topics

- [PR Rewrite Command](../cli/pr-rewrite.md) — The command that replaced `erk pr summarize`
- [PR Submit Pipeline Architecture](../cli/pr-submit-pipeline.md) — The multi-step submit pipeline
