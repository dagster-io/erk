---
title: PR Validation Rules
read_when:
  - "debugging 'erk pr check' failures"
  - "building or modifying PR submission pipelines"
  - "generating PR bodies with checkout footers or closing references"
tripwires:
  - action: "using issue number from .impl/issue.json in a checkout footer"
    warning: "Checkout footers require the PR number (from create_pr return value), NOT the issue number. Issue numbers go in `Closes` references. See pr-validation-rules.md."
  - action: "adding Closes reference in a PR body update instead of initial creation"
    warning: "GitHub sets willCloseTarget at PR creation time. The Closes reference must be in the initial create_pr body, not a subsequent update. See checkout-footer-syntax.md."
last_audited: "2026-02-08 00:00 PT"
audit_result: edited
---

# PR Validation Rules

`erk pr check` enforces two structural invariants on every PR: a checkout footer containing the correct PR number, and (when `.impl/issue.json` exists) a `Closes` reference linking the PR to its plan issue. Understanding **why** these checks exist and **where** the data comes from prevents the most common agent mistakes.

## The Three Checks

<!-- Source: src/erk/cli/commands/pr/check_cmd.py, pr_check -->

See `pr_check()` in `src/erk/cli/commands/pr/check_cmd.py` for the orchestration logic. The command runs three checks in sequence:

| Check                   | What it validates                                                | Why it exists                                                               |
| ----------------------- | ---------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Branch/issue agreement  | Branch name `P{N}-...` matches `.impl/issue.json` issue number   | Catches stale `.impl/` from a previous plan left behind after branch rename |
| Issue closing reference | PR body contains `Closes #N` (or cross-repo variant)             | GitHub auto-closes the plan issue when the PR merges                        |
| Checkout footer         | PR body contains `erk pr checkout <pr_number>` with exact number | Lets reviewers check out the PR into a fresh worktree                       |

## The PR Number vs Issue Number Trap

This is the single most common validation failure for agents, and it stems from a data source confusion:

| Data source                | Contains              | Use for                          |
| -------------------------- | --------------------- | -------------------------------- |
| `.impl/issue.json`         | Plan **issue** number | `Closes #N` reference in PR body |
| `create_pr()` return value | **PR** number         | `erk pr checkout N` footer       |

**Why agents get confused:** During the submit workflow, `.impl/issue.json` is readily available and contains a number. The checkout footer needs a number. Agents grab the accessible one — but it's the wrong one. The PR number doesn't exist until `create_pr()` returns.

This confusion is also why the footer uses a two-phase create-then-update pattern: the PR must be created first (with `Closes` reference in the initial body), and the footer is appended afterward once the PR number is known. See [Checkout Footer Syntax](checkout-footer-syntax.md) for the full pattern.

## Validation Matching Details

<!-- Source: packages/erk-shared/src/erk_shared/gateway/pr/submit.py, has_checkout_footer_for_pr -->
<!-- Source: packages/erk-shared/src/erk_shared/gateway/pr/submit.py, has_issue_closing_reference -->

Both validation functions in `has_checkout_footer_for_pr()` and `has_issue_closing_reference()` (in `packages/erk-shared/src/erk_shared/gateway/pr/submit.py`) use regex with word boundaries (`\b`) to prevent partial number matches — PR #12 won't falsely match a footer containing `erk pr checkout 123`.

Key matching differences between the two validators:

- **Checkout footer**: Case-sensitive, exact format `erk pr checkout N`
- **Closing reference**: Case-insensitive (`Closes`, `closes`, `CLOSES` all work), flexible whitespace, supports cross-repo syntax `Closes owner/repo#N` when `plans_repo` is configured

There is also a less strict `has_body_footer()` function that only checks for the presence of _any_ `erk pr checkout` string without validating the number. This is used during PR creation to detect whether a footer already exists, while the stricter per-number check is used during validation.

## Cross-Repo Closing References

When `.erk/config.toml` sets a `plans_repo` (for repos that track plans in a separate repository), the closing reference format changes from `Closes #N` to `Closes owner/repo#N`. The checkout footer is unaffected — it always uses the local repo's PR number.

## Debugging Validation Failures

When `erk pr check` fails, the resolution pattern is:

1. Read the specific validation function to understand the exact regex
2. Compare the regex against the actual PR body content
3. Fix the mismatch (usually a wrong number or missing reference)

Common failure modes:

- **"PR body missing checkout footer"** — Footer was never appended, or uses wrong PR number
- **"PR body missing issue closing reference"** — `Closes #N` was omitted from the initial PR body, or the issue number doesn't match `.impl/issue.json`
- **Branch/issue disagreement** — Branch was renamed but `.impl/issue.json` still points to the old issue

## Related Documentation

- [Checkout Footer Syntax](checkout-footer-syntax.md) — Two-phase create-then-update pattern, footer format details
- [PR Body Formatting](../architecture/pr-body-formatting.md) — Overall PR body structure (header/content/footer)
- [Plan Embedding in PR](plan-embedding-in-pr.md) — How plans are embedded in PR bodies
