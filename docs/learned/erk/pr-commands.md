---
title: "PR Checkout Footer Validation Pattern"
read_when:
  - generating or modifying PR body footers
  - debugging `erk pr check` footer validation failures
tripwires:
  - action: "constructing a checkout footer string manually"
    warning: "Use build_pr_body_footer() from the gateway layer. Manual construction risks format drift from the validator regex."
  - action: "using issue number in checkout footer instead of PR number"
    warning: "Checkout footer requires the PR number (from gh pr create output), NOT the plan issue number from .impl/issue.json."
last_audited: "2026-02-16 14:20 PT"
audit_result: clean
---

# PR Checkout Footer Validation Pattern

This document covers the cross-package contract between footer generation and validation, and the most common agent mistake when constructing footers. For the full footer format specification, see [PR Footer Format Validation](../architecture/pr-footer-validation.md). For the complete `erk pr check` validation ruleset, see [PR Validation Rules](../pr-operations/pr-validation-rules.md).

## Why Literal Matching, Not Semantic Equivalence

<!-- Source: packages/erk-shared/src/erk_shared/gateway/pr/submit.py, has_checkout_footer_for_pr -->

The checkout footer validator matches `erk pr checkout <number>` as a literal regex pattern. It does **not** understand command semantics — `erk wt from-pr 123` produces the same result but fails validation.

This is deliberate:

- **Consistency** — Every PR displays the same checkout command format, making footers scannable across dozens of PRs
- **Parseable** — The literal pattern is trivially greppable by scripts, CI, and future tooling
- **Canonical command** — `erk pr checkout` is the user-facing command; alternative syntaxes should not appear in PR bodies

See `has_checkout_footer_for_pr()` in `packages/erk-shared/src/erk_shared/gateway/pr/submit.py`.

## The Cross-Package Generator-Validator Split

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/pr_footer.py, build_pr_body_footer -->
<!-- Source: packages/erk-shared/src/erk_shared/gateway/pr/submit.py, has_checkout_footer_for_pr -->

Footer generation and validation live in **different packages** that must agree on format:

| Component     | Package                     | Function                       |
| ------------- | --------------------------- | ------------------------------ |
| **Generator** | `erk_shared.gateway.github` | `build_pr_body_footer()`       |
| **Validator** | `erk_shared.gateway.pr`     | `has_checkout_footer_for_pr()` |

**Why this matters:** There is no compile-time or type-level guarantee that these agree. The generator produces a markdown string; the validator applies a regex to it. Changing the generator's output format without updating the validator regex (or vice versa) creates silent failures where `erk pr submit` generates footers that `erk pr check` rejects. The split exists because footer generation is a GitHub concern (PR body construction) while validation is a PR submission concern (pre-flight checks), but it requires manual coordination on any format change.

For the full three-part contract (generator, parser, validator) and migration strategy, see [PR Footer Format Validation](../architecture/pr-footer-validation.md).

## PR Number vs Issue Number — The Common Agent Mistake

The most frequent footer validation failure comes from confusing two different numbers:

| Number           | Source                | Used In                    |
| ---------------- | --------------------- | -------------------------- |
| **Issue number** | `.impl/issue.json`    | `Closes #N` reference      |
| **PR number**    | `gh pr create` output | `erk pr checkout N` footer |

These are never the same number. The issue is created during planning; the PR is created during submission.

**Why agents make this mistake:** During footer construction, `.impl/issue.json` is readily available — the issue was created before implementation started. The PR number only exists after the PR creation API call returns. This temporal gap makes the issue number tempting to reach for. The submit pipeline solves this via a two-phase approach: create the PR with a placeholder footer (`pr_number=0`), then immediately update with the real PR number.

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, _core_submit_flow -->

See `_core_submit_flow()` in `src/erk/cli/commands/pr/submit_pipeline.py` for the two-phase creation pattern.

## Related Documentation

- [PR Footer Format Validation](../architecture/pr-footer-validation.md) — Full format specification and migration strategy
- [PR Validation Rules](../pr-operations/pr-validation-rules.md) — Complete validation orchestration and regex patterns
- [PR Submission Decision Framework](../cli/pr-submission.md) — When to use git-pr-push vs pr-submit
