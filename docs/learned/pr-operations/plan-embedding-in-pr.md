---
title: Plan Embedding in PR Body
read_when:
  - "implementing PR body formatting with HTML"
  - "understanding how plans are embedded in PRs"
  - "debugging plan visibility in pull requests"
  - "working with <details> collapsible sections in PR bodies"
last_audited: "2026-02-05"
audit_result: edited
---

# Plan Embedding in PR Body

When submitting a PR from a plan implementation (`.impl/` folder), erk embeds the full plan content in the PR body using a collapsible `<details>` section. This provides reviewers with complete context without cluttering the PR description.

## Two-Target Body Pattern

The implementation uses **two separate body strings**:

- `pr_body` - Plain text for git commit messages (no HTML)
- `pr_body_for_github` - Enhanced version with plan embedding (GitHub-specific HTML)

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, _build_plan_details_section -->

See `_build_plan_details_section()` in `src/erk/cli/commands/pr/submit_pipeline.py:587-601` for the implementation. The function wraps the plan in a `<details>` tag with a `<summary>` referencing the plan issue number.

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, finalize_pr -->

See `finalize_pr()` in `src/erk/cli/commands/pr/submit_pipeline.py:603` for how the plan embedding integrates with the PR body assembly.

## Key Invariants

1. **HTML only in PR body**: The `<details>` block never appears in git commit messages
2. **Conditional embedding**: Plan content only embedded when `state.plan_context is not None`
3. **Immutable plan content**: The embedded plan is read-only markdown text, not editable

The test at `tests/unit/cli/commands/pr/submit_pipeline/test_finalize_pr.py` verifies the separation between PR body (with plan) and commit message (without plan).

## Related Documentation

- [PR Body Formatting](../architecture/pr-body-formatting.md) - Two-target pattern explanation
- [PR Submit Phases](pr-submit-phases.md) - Phase 6 integration details
- [Plan Implementation Workflow](../planning/workflow.md) - When plan context is available
