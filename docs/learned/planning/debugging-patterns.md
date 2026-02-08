---
title: "Source Investigation Over Trial-and-Error"
last_audited: "2026-02-08"
audit_result: regenerated
read_when:
  - Debugging validation failures after an initial fix attempt fails
  - Encountering errors where the required format is unclear from the error message alone
  - Deciding whether to guess at another fix or read the validator source
tripwires:
  - action: "making a third trial-and-error attempt at a validation fix"
    warning: "After 2 failed attempts, stop guessing. Grep for the validator function and read the source to understand the exact requirement."
  - action: "grepping only for the error message text"
    warning: "Also grep for function names extracted from the error (e.g., 'checkout_footer' from 'Missing checkout footer'). Validator function names are more stable search targets than error message strings."
sources:
  - "[Impl 5d99bc36]"
title: Source Investigation Over Trial-and-Error
tripwires:
  - action: making a third trial-and-error attempt at a validation fix
    warning:
      After 2 failed attempts, stop guessing. Grep for the validator function
      and read the source to understand the exact requirement.
  - action: grepping only for the error message text
    warning:
      Also grep for function names extracted from the error (e.g., 'checkout_footer'
      from 'Missing checkout footer'). Validator function names are more stable search
      targets than error message strings.
---

# Source Investigation Over Trial-and-Error

## The Core Insight

When an erk validation error is unclear about its exact requirements, reading the validator source code is faster and more reliable than iterating through guesses. This is a cross-cutting debugging strategy — it applies to PR validation, plan validation, config validation, and any other erk subsystem that enforces format rules.

**Why this matters for agents specifically:** Agents are biased toward action — trying another fix is faster than investigating. But erk validators often enforce literal patterns (regex matches, exact string formats) where semantic equivalents fail silently. An agent can waste many turns guessing at variations when a single grep-and-read cycle would reveal the exact requirement.

## Decision Table: Investigate vs Retry

| Signal                                                                         | Action                                                         |
| ------------------------------------------------------------------------------ | -------------------------------------------------------------- |
| Error message specifies the exact fix (e.g., "Missing required field 'title'") | Apply the fix directly — no investigation needed               |
| Error message names what's wrong but not the required format                   | Grep for the validator function, read the regex/logic          |
| First reasonable fix attempt fails                                             | Try one more obvious variation                                 |
| Second attempt also fails                                                      | **Stop guessing. Read the source.**                            |
| Error involves regex, pattern matching, or format validation                   | Investigate source immediately — don't guess at regex patterns |
| Validation is new or undocumented                                              | Investigate source immediately                                 |

## The Investigation Workflow

1. **Extract search terms from the error message.** Convert the human-readable error into likely function/variable names. "Missing checkout footer" → `checkout_footer`, `has_checkout`, `footer`.

2. **Grep for the validator, not the error string.** Function names are more stable search targets. Erk validators follow naming conventions: `validate_*`, `check_*`, `has_*`, `is_valid_*`.

3. **Read the validator and its caller.** The validator reveals the exact requirement; the caller reveals the context (what inputs it receives, what error it raises). Understanding both prevents fixing the symptom while missing the cause.

4. **Apply the fix and verify in one step.** Source understanding should yield a correct fix on the first attempt.

## Why Erk Validators Reward Investigation

Erk validation functions frequently use literal regex matching rather than semantic equivalence. This is a deliberate design choice for consistency and parseability across the codebase, but it means that "close enough" fixes fail.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/pr/submit.py, has_checkout_footer_for_pr -->

**Example:** The checkout footer validator matches `erk pr checkout <number>` as a literal regex. Running `erk wt from-pr 123` produces the same result but fails validation. An agent that tries command variations will fail repeatedly; an agent that reads `has_checkout_footer_for_pr()` in `packages/erk-shared/src/erk_shared/gateway/pr/submit.py` discovers the exact pattern in seconds. For full details on this specific validator, see [PR Checkout Footer Validation](../erk/pr-commands.md) and [PR Validation Rules](../pr-operations/pr-validation-rules.md).

## Integration with Iterate-Until-Valid

This pattern complements the iterate-until-valid workflow documented in [PR Submission Patterns](pr-submission-patterns.md). The two strategies combine:

1. **First validation failure** → Try the obvious fix
2. **Second failure** → Investigate source, then fix with full understanding
3. **Success** → Pattern is now understood

The anti-pattern is waiting until 5-6 failures before investigating. The two-attempt threshold exists because the first attempt tests whether the fix is obvious; the second tests whether a reasonable variation works. After that, further guessing has diminishing returns while source investigation has near-guaranteed payoff.

## Related Documentation

- [PR Submission Patterns](pr-submission-patterns.md) — Iterate-until-valid workflow
- [PR Checkout Footer Validation](../erk/pr-commands.md) — Specific checkout footer validation details
- [PR Validation Rules](../pr-operations/pr-validation-rules.md) — Complete `erk pr check` validation ruleset
