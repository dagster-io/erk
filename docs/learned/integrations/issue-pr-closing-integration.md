---
title: Issue-PR Closing Integration
read_when:
  - linking PRs to issues for auto-close
  - debugging why issues didn't close when PR merged
  - working on issue number discovery in the submit pipeline
  - understanding cross-repo plan issue references
tripwires:
  - action: "putting Closes keyword in PR title or commit message"
    warning: "GitHub only processes closing keywords in the PR body. Title and commit message references are ignored."
  - action: "using issue number from .impl/plan-ref.json for a checkout footer"
    warning: "The checkout footer requires the PR number, not the issue number. These are different values — the issue is the plan, the PR is the implementation."
  - action: "resolving issue number from a single source without checking for mismatches"
    warning: "Both .impl/plan-ref.json and branch name may contain issue numbers. If both exist, they must agree — otherwise the pipeline could silently close the wrong issue."
---

# Issue-PR Closing Integration

GitHub automatically closes issues when a PR merges **only if** the closing keyword (`Closes #N`) appears in the **PR body**. Title and commit message placement has no effect. The PR must also merge to the repository's default branch.

This document covers the cross-cutting pattern of how erk ensures that closing references are correctly discovered, validated, and embedded across the submit pipeline, exec scripts, and footer generation system.

## Issue Number Discovery: Three Sources, One Truth

The submit pipeline resolves issue numbers from three sources with a strict priority hierarchy. The cross-cutting concern is that these sources live in different systems (filesystem, git, GitHub API) and must be validated against each other.

| Source                    | When used                  | Why it exists                                                                  |
| ------------------------- | -------------------------- | ------------------------------------------------------------------------------ |
| `.impl/plan-ref.json`     | Authoritative when present | Created by `erk br co --for-plan` or `erk plan submit` — explicit plan linkage |
| Branch name (`P{N}-slug`) | Fallback when no `.impl/`  | Supports manually-created worktrees from plan branches                         |
| Existing PR footer        | Last resort on re-submit   | Preserves references after worktree recreation                                 |

<!-- Source: packages/erk-shared/src/erk_shared/impl_folder.py, validate_plan_linkage -->

**The mismatch guard is the key design decision.** When both `.impl/plan-ref.json` and the branch name contain issue numbers, they must agree — a mismatch raises `ValueError` and halts the pipeline. This prevents the most dangerous failure mode: silently closing the wrong issue because stale metadata disagrees with the branch. See `validate_plan_linkage()` in `packages/erk-shared/src/erk_shared/impl_folder.py`.

### Auto-Repair: Bridging Manual Worktree Creation

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, prepare_state -->

When `.impl/` exists but lacks `plan-ref.json`, and the branch name contains a valid issue number, `prepare_state()` auto-creates the missing `plan-ref.json`. This bridges the gap when a worktree is created manually from a plan branch (e.g., `git worktree add`) without going through `erk br co --for-plan`, which would normally create the file. See `prepare_state()` in `src/erk/cli/commands/pr/submit_pipeline.py`.

### Closing Reference Preservation on Re-Submit

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, _extract_closing_ref_from_pr -->

When re-submitting a PR that already has a closing reference but no local `.impl/` folder (e.g., after worktree recreation), `finalize_pr` extracts the existing reference from the PR body rather than losing it. Without this, re-submitting from a fresh worktree would silently drop the issue linkage. See `_extract_closing_ref_from_pr()` in `src/erk/cli/commands/pr/submit_pipeline.py`.

## Two-Phase Footer Creation: The Chicken-and-Egg Problem

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, _core_submit_flow -->

The footer needs both the issue number (for `Closes #N`) and the PR number (for the `erk pr checkout` command), but the PR number doesn't exist until after creation. The solution is two API calls:

1. Create PR with `pr_number=0` placeholder in the footer
2. Immediately update the body with the actual PR number

This pattern only applies to the core submit flow (`_core_submit_flow`). The Graphite-first flow delegates PR creation to `gt submit` and retrieves the PR number afterward, then builds the footer in `finalize_pr`. See `_core_submit_flow()` in `src/erk/cli/commands/pr/submit_pipeline.py`.

## Same-Repo vs Cross-Repo Closing References

Plans can live in a separate repository (configured via `plans_repo` in erk config). This changes the closing reference format because GitHub requires fully-qualified references for cross-repo issue closing:

| Scenario         | Reference format        | Why                                               |
| ---------------- | ----------------------- | ------------------------------------------------- |
| Same-repo plans  | `Closes #123`           | GitHub resolves `#N` within the same repo         |
| Cross-repo plans | `Closes owner/repo#123` | GitHub needs the full repo path to find the issue |

<!-- Source: src/erk/cli/commands/exec/scripts/get_closing_text.py, get_closing_text -->
<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/pr_footer.py, build_pr_body_footer -->

This distinction is handled in two places: `build_pr_body_footer()` in the footer generator (used by the submit pipeline) and `get_closing_text()` in the exec script (used by Claude Code skills that construct PR bodies outside the pipeline). Both read `plans_repo` from erk config. See `build_pr_body_footer()` in `packages/erk-shared/src/erk_shared/gateway/github/pr_footer.py` and `get_closing_text()` in `src/erk/cli/commands/exec/scripts/get_closing_text.py`.

## Debugging Auto-Close Failures

Check these conditions in order — the first failure found is almost always the cause:

```bash
# 1. Is the closing keyword in the PR body?
gh pr view <pr> --json body --jq .body

# 2. Did the PR merge to the default branch?
gh pr view <pr> --json baseRefName --jq .baseRefName

# 3. Was the PR actually merged (not just closed)?
gh pr view <pr> --json merged --jq .merged
```

The most common failure: the keyword is absent from the body because the PR was created outside erk's submit pipeline (e.g., via `gh pr create` directly), bypassing footer generation entirely.

## Related Documentation

- [PR Footer Format Validation](../architecture/pr-footer-validation.md) — Footer format contract and migration strategy
- [Issue-PR Linkage Storage Model](../erk/issue-pr-linkage-storage.md) — `.impl/plan-ref.json` structure and `willCloseTarget` timing
- [PR Submission Decision Framework](../cli/pr-submission.md) — Choosing between git-pr-push and pr-submit workflows
- [PR Validation Rules](../pr-operations/pr-validation-rules.md) — `erk pr check` validates closing references and checkout footers
