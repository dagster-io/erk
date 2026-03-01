---
title: Check State Classification
read_when:
  - "modifying how CI check states are counted or displayed"
  - "understanding why planned PRs show 0/0 checks"
  - "working with PASSING_CHECK_RUN_STATES or SKIPPED_CHECK_RUN_STATES"
tripwires:
  - action: "counting SKIPPED checks in the total"
    warning: "SKIPPED checks must be excluded from BOTH passing and total counts. They are subtracted from total_count at return time in parse_aggregated_check_counts()."
  - action: "treating NEUTRAL the same as SKIPPED"
    warning: "NEUTRAL counts as PASSING (it's in PASSING_CHECK_RUN_STATES). Do not confuse with SKIPPED. NEUTRAL checks are real checks that completed successfully with no opinion."
---

# Check State Classification

GitHub check runs report various conclusion states. Erk classifies these states to produce accurate passing/total counts for PR displays.

## State Constants

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/parsing.py -->

Three frozenset constants define the classification (see source file for current values):

- `PASSING_CHECK_RUN_STATES` — SUCCESS, NEUTRAL
- `SKIPPED_CHECK_RUN_STATES` — SKIPPED
- `PASSING_STATUS_CONTEXT_STATES` — SUCCESS

**CheckRun** (modern GitHub checks) and **StatusContext** (legacy commit statuses) use different passing criteria:

| Source        | Passing States   | Skipped States |
| ------------- | ---------------- | -------------- |
| CheckRun      | SUCCESS, NEUTRAL | SKIPPED        |
| StatusContext | SUCCESS          | (none)         |

## Two-Layer Counting

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/parsing.py, parse_aggregated_check_counts -->

`parse_aggregated_check_counts(check_run_counts, status_context_counts, total_count)` processes both layers:

1. Iterates `check_run_counts` — adds to `passing` if state in `PASSING_CHECK_RUN_STATES`, adds to `skipped` if in `SKIPPED_CHECK_RUN_STATES`
2. Iterates `status_context_counts` — adds to `passing` if state in `PASSING_STATUS_CONTEXT_STATES`
3. Returns `(passing, total_count - skipped)`

The `total_count` parameter comes from GitHub's `statusCheckRollup.contexts.totalCount` which includes all checks. Skipped checks are subtracted from it.

## Skipped Check Handling

Skipped checks are excluded from **both** the numerator and denominator:

- **Passing count**: Skipped states are not in `PASSING_CHECK_RUN_STATES`, so they never increment `passing`
- **Total count**: The accumulated `skipped` count is subtracted from `total_count` at return time

This means a PR with 10 SUCCESS and 3 SKIPPED checks shows `10/10` (not `10/13`). A PR with only SKIPPED checks shows `0/0`.

## Display Flow

```
parse_aggregated_check_counts()  ->  PullRequestInfo.checks_counts  ->  format_checks_cell()
     (passing, total)                  tuple[int, int] | None              "✅ 10/10"
```

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/emoji.py, format_checks_cell -->

`format_checks_cell()` renders the counts with emoji:

| Condition                  | Output   |
| -------------------------- | -------- |
| No PR                      | `-`      |
| Checks pending / no checks | `🔄`     |
| All passing (with counts)  | `✅ 5/5` |
| Some failing (with counts) | `🚫 2/5` |
| All passing (no counts)    | `✅`     |

## Impact on Planned PRs

Before skipped-check exclusion was added, planned PRs (which have no real checks to run) showed `13/13` because all checks were SKIPPED but counted in the total. Now they correctly show `0/0`, which `format_checks_cell()` renders as `✅ 0/0`.

## Related Documentation

- [CI Failure Summarization](ci-failure-summarization.md) - How failing checks get summarized
- [GitHub Token Scopes](github-token-scopes.md) - Token requirements for CI operations
