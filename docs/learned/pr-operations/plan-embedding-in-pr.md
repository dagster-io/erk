---
title: Plan Embedding in PR Body
read_when:
  - "embedding plan content in a PR body"
  - "debugging missing or malformed plan sections in pull requests"
  - "modifying how plan context flows through PR submission"
tripwires:
  - action: "adding plan HTML to the pr_body variable instead of pr_body_for_github"
    warning: "Plan embedding uses <details> HTML which must never enter git commit messages. Append only to pr_body_for_github. See pr-body-formatting.md for the two-target pattern."
last_audited: "2026-02-08"
audit_result: edited
---

# Plan Embedding in PR Body

## Why Embed Plans

When a PR originates from an erk-plan issue, reviewers need the original plan for context — it explains the _intent_ behind the code, not just the diff. Embedding the plan directly in the PR body means reviewers don't have to chase cross-references to a separate GitHub issue. A collapsible `<details>` section keeps this context available without overwhelming the PR description.

## Data Flow: Plan to PR

Plan content arrives at the PR through a multi-system chain:

1. **Branch name** → `PlanContextProvider` extracts the issue number from the `P{number}-{slug}` convention
2. **GitHub API** → fetches the plan issue body, then the plan comment containing the actual plan markdown
3. **Phase 3** of the submit pipeline populates `state.plan_context` (a `PlanContext` with issue number, plan markdown, and optional objective summary)
4. **Phase 6** (`finalize_pr`) conditionally appends the plan HTML to the GitHub-only body string

<!-- Source: src/erk/core/plan_context_provider.py, PlanContextProvider.get_plan_context -->

See `PlanContextProvider.get_plan_context()` in `src/erk/core/plan_context_provider.py` for the extraction chain (branch name → issue → comment → plan content).

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, _build_plan_details_section -->

See `_build_plan_details_section()` in `src/erk/cli/commands/pr/submit_pipeline.py` for the HTML assembly.

The embedding is **conditional** — `finalize_pr` only appends the plan section when `state.plan_context is not None`. Branches that don't follow the plan naming convention, or plans that fail to fetch, gracefully produce PRs with no plan section. Every step in `PlanContextProvider` returns `None` on failure rather than raising, so the embedding is always best-effort.

## Critical Invariant: Two-Target Body Separation

Plan embedding is an application of the two-target body pattern documented in [PR Body Formatting](../architecture/pr-body-formatting.md). The plan `<details>` HTML is appended **only** to `pr_body_for_github`, never to `pr_body`. This ensures:

- **Git commit messages** remain plain text (no HTML pollution in `git log`)
- **GitHub PR body** includes the collapsible plan section

This separation is verified by a dedicated test that asserts `<details>` appears in the GitHub body but not in the amended commit message.

## Related Documentation

- [PR Body Formatting](../architecture/pr-body-formatting.md) — The two-target pattern this feature depends on
- [PR Submit Phases](pr-submit-phases.md) — Phase 3 (plan fetch) and Phase 6 (embedding) context
- [Plan Implementation Workflow](../planning/workflow.md) — When `.impl/` context is available
