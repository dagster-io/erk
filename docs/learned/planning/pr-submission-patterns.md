---
audit_result: edited
last_audited: '2026-02-08'
read_when:
- creating or updating PRs programmatically in erk
- debugging why a duplicate PR or issue was created
- fixing erk pr check validation failures
- understanding the PR number vs issue number distinction
title: PR Submission Patterns
tripwires:
- action: using issue number from .impl/issue.json in a checkout footer
  warning: Checkout footers require the PR number, not the issue number. The issue
    is the plan; the PR is the implementation. See the PR Number vs Issue Number section.
- action: creating a PR without first checking if one already exists for the branch
  warning: The submit pipeline is idempotent — it checks for existing PRs before creating.
    If building PR creation outside the pipeline, replicate this check to prevent
    duplicates.
- action: constructing a PR footer manually instead of using build_pr_body_footer()
  warning: The footer format includes checkout commands and closing references with
    specific patterns. Use the builder function to ensure validation passes.
---

# PR Submission Patterns

Cross-cutting patterns for reliable, idempotent PR creation in erk. The submit pipeline touches git, GitHub API, Graphite, and the `.impl/` metadata system — mistakes in any layer cascade into validation failures or duplicate artifacts.

## Idempotency: Why Every PR Operation Must Be Re-Runnable

PR submission frequently retries due to network failures, hook loops, or agent restarts. Without idempotency, each retry creates duplicate PRs or issues. Erk enforces idempotency at two levels:

**Branch-level:** The submit pipeline checks GitHub for an existing PR on the current branch before creating one. If found, it updates the existing PR rather than creating a duplicate. This is the single most important idempotency guarantee — without it, every retry during the push-and-create phase would spawn a new PR.

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, push_and_create_pr -->

See `push_and_create_pr()` in `src/erk/cli/commands/pr/submit_pipeline.py` — it calls `get_pr_for_branch()` and branches on `PRNotFound` vs existing.

**Session-level:** Plan-save operations use scratch-directory marker files keyed by session ID. Before creating a GitHub issue, the command checks if this session already created one. This prevents the specific failure mode where exit-plan-mode hook retries cause duplicate plan issues.

<!-- Source: src/erk/cli/commands/exec/scripts/plan_save_to_issue.py, _get_existing_saved_issue -->

See `_get_existing_saved_issue()` in `src/erk/cli/commands/exec/scripts/plan_save_to_issue.py`.

## The Two-Phase Footer Problem

The PR footer needs the PR number for the checkout command (`erk pr checkout <N>`), but the PR number doesn't exist until after creation. The pipeline solves this with two API calls:

1. Create PR with `pr_number=0` placeholder in the footer
2. Immediately update the body with the actual PR number

This two-phase pattern only applies to the core git+gh flow. The Graphite-first flow delegates PR creation to `gt submit` and retrieves the PR number afterward.

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, _core_submit_flow -->

See `_core_submit_flow()` in `src/erk/cli/commands/pr/submit_pipeline.py` for the placeholder-then-update sequence.

## PR Number vs Issue Number: The Most Common Agent Confusion

Agents regularly confuse these two identifiers because both are readily available during submission. The distinction is critical:

| Identifier   | Source                | Used for                   |
| ------------ | --------------------- | -------------------------- |
| Issue number | `.impl/issue.json`    | `Closes #N` in PR body     |
| PR number    | `gh pr create` output | `erk pr checkout N` footer |

**Why agents get this wrong:** During plan-based workflows, `.impl/issue.json` is immediately accessible and contains a number. The checkout footer also needs a number. The temptation to use the available number for both purposes is strong — but the checkout footer validator matches the _PR_ number, not the issue number, and `erk pr checkout` only accepts PR numbers.

**The diagnostic signal:** If `erk pr check` reports "PR body missing checkout footer" but the footer visually appears present, the number is probably wrong. Compare the number in the footer against `gh pr view --json number`.

## Iterate-Until-Valid: Fixing PR Validation Failures

When `erk pr check` reports failures, use this workflow:

1. Read the error message — it names the specific check that failed
2. Apply the obvious fix
3. Re-run `erk pr check`
4. **If the second attempt fails:** stop guessing and grep for the validator function name

The escalation to source investigation after two failures is the key discipline. Erk validators use literal regex matching, not semantic equivalence — "close enough" formats fail silently. For the full investigation methodology, see [Source Investigation Over Trial-and-Error](debugging-patterns.md).

## Closing Reference Preservation on Re-Submit

When re-submitting a PR that already has a closing reference but no local `.impl/` folder (e.g., after worktree recreation), the pipeline extracts the existing reference from the PR body rather than losing it. Without this, re-submitting from a fresh worktree would silently drop the issue linkage, causing the plan issue to remain open after PR merge.

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, _extract_closing_ref_from_pr -->

See `_extract_closing_ref_from_pr()` in `src/erk/cli/commands/pr/submit_pipeline.py`.

## Related Documentation

- [Issue-PR Closing Integration](../integrations/issue-pr-closing-integration.md) — Full cross-repo closing reference patterns and issue number discovery
- [PR Validation Rules](../pr-operations/pr-validation-rules.md) — Complete `erk pr check` validation ruleset and regex patterns
- [Source Investigation Over Trial-and-Error](debugging-patterns.md) — When to stop guessing and read validator source
- [Plan Lifecycle](lifecycle.md) — Full plan lifecycle including PR creation phases
- [Submit Branch Reuse](submit-branch-reuse.md) — Branch reuse detection in plan submit
