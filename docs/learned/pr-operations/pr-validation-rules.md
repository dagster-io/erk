---
title: PR Validation Rules
read_when:
  - "debugging 'erk pr check' failures"
  - "building or modifying PR submission pipelines"
  - "generating PR bodies with checkout footers"
tripwires:
  - action: "using issue number from .impl/plan-ref.json in a checkout footer"
    warning: "Checkout footers require the PR number (from create_pr return value), NOT the plan issue number. See pr-validation-rules.md."
last_audited: "2026-02-26 00:00 PT"
audit_result: edited
---

# PR Validation Rules

`erk pr check` enforces structural invariants on every PR: a checkout footer containing the correct PR number. Understanding **why** these checks exist and **where** the data comes from prevents the most common agent mistakes.

## The Checks

<!-- Source: src/erk/cli/commands/pr/check_cmd.py, pr_check -->

See `pr_check()` in `src/erk/cli/commands/pr/check_cmd.py` for the orchestration logic. The command runs checks in sequence:

| Check             | What it validates                                                | Why it exists                                         |
| ----------------- | ---------------------------------------------------------------- | ----------------------------------------------------- |
| Plan-ref presence | `.impl/plan-ref.json` exists and contains a valid plan ID        | Confirms the PR is linked to a tracked plan           |
| Checkout footer   | PR body contains `erk pr checkout <pr_number>` with exact number | Lets reviewers check out the PR into a fresh worktree |
| Header position   | Plan-header metadata is at bottom, not legacy top position       | Ensures PR body follows current formatting standards  |

## The PR Number vs Issue Number Trap

This is the single most common validation failure for agents, and it stems from a data source confusion:

| Data source                | Contains              | Use for                                    |
| -------------------------- | --------------------- | ------------------------------------------ |
| `.impl/plan-ref.json`      | Plan **issue** number | Identifying the plan (not used in PR body) |
| `create_pr()` return value | **PR** number         | `erk pr checkout N` footer                 |

**Why agents get confused:** During the submit workflow, `.impl/plan-ref.json` is readily available and contains a number. The checkout footer needs a number. Agents grab the accessible one — but it's the wrong one. The PR number doesn't exist until `create_pr()` returns.

## Validation Matching Details

<!-- Source: packages/erk-shared/src/erk_shared/gateway/pr/submit.py, has_checkout_footer_for_pr -->

The `has_checkout_footer_for_pr()` function (in `packages/erk-shared/src/erk_shared/gateway/pr/submit.py`) uses regex with word boundaries (`\b`) to prevent partial number matches — PR #12 won't falsely match a footer containing `erk pr checkout 123`.

There is also a less strict `has_body_footer()` function that only checks for the presence of _any_ `erk pr checkout` string without validating the number. This is used during PR creation to detect whether a footer already exists, while the stricter per-number check is used during validation.

## Debugging Validation Failures

When `erk pr check` fails, the resolution pattern is:

1. Read the specific validation function to understand the exact regex
2. Compare the regex against the actual PR body content
3. Fix the mismatch (usually a wrong number or missing footer)

Common failure modes:

- **"PR body missing checkout footer"** — Footer was never appended, or uses wrong PR number
- **Missing plan reference** — `.impl/plan-ref.json` is absent or unreadable

## Stage-Specific Checks

### `--stage=impl`

When `erk pr check --stage=impl` is run, an additional validation check is included:

| Check                        | What it validates                    | Why it exists                                              |
| ---------------------------- | ------------------------------------ | ---------------------------------------------------------- |
| `.erk/impl-context/` cleanup | Directory must not exist in the repo | Transient artifacts cause CI formatter failures (Prettier) |

This check verifies that the `.erk/impl-context/` staging directory was properly removed after implementation.

**Source:** `src/erk/cli/commands/pr/check_cmd.py` — the `--stage` option accepts `click.Choice(["impl"])`.

## Related Documentation

- [Checkout Footer Syntax](checkout-footer-syntax.md) — Footer format details
- [PR Body Formatting](../architecture/pr-body-formatting.md) — Overall PR body structure (header/content/footer)
- [Plan Embedding in PR](plan-embedding-in-pr.md) — How plans are embedded in PR bodies
