---
title: GitHub Actions Workflow Gating Patterns
read_when:
  - adding conditional execution to GitHub Actions workflows
  - implementing label-based CI skipping
  - understanding why CI was skipped on a PR
tripwires:
  - action: "Use !contains() pattern for label-based gating"
    warning: "Negation is critical — contains() without ! skips all push events"
    score: 5
  - action: "Add branches-ignore for ephemeral branch patterns"
    warning: "Label-based gating doesn't work on push events — use branches-ignore to prevent workflow queuing"
    score: 4
  - action: "using branches-ignore for planned/* branches"
    warning: "planned/ branches contain both metadata AND code. Use paths-ignore instead to skip CI only when commits touch exclusively metadata paths (.erk/impl-context/**, .worker-impl/**)."
    score: 4
last_audited: "2026-02-16 14:20 PT"
audit_result: edited
---

# GitHub Actions Workflow Gating Patterns

GitHub Actions offers multiple mechanisms for controlling workflow execution. Choosing the right layer for each gate determines both safety and cost efficiency.

## Why Multiple Gating Layers Exist

GitHub Actions evaluates conditions at different points in the workflow lifecycle:

<!-- Source: .github/workflows/ci.yml, on: triggers, job if: conditions, step if: conditions -->

1. **Trigger filtering** (`on:` section) — GitHub decides whether to queue the workflow at all
2. **Job conditions** (`if:` at job level) — GitHub decides whether to allocate a runner before any steps execute
3. **Step conditions** (`if:` at step level) — Runs after runner allocation and checkout

Each layer exists for a reason: triggers prevent unnecessary workflow runs, job conditions prevent unnecessary runner allocation, and step conditions enable dynamic decisions based on checkout state or earlier step results.

## The Negation Pattern for Label Checks

<!-- Source: .github/workflows/ci.yml, check-submission job -->
<!-- Source: .github/workflows/code-reviews.yml, discover job -->

### Why !contains() Instead of contains()

The pattern `!contains(github.event.pull_request.labels.*.name, 'erk-plan-review')` appears throughout `.github/workflows/ci.yml` and `.github/workflows/code-reviews.yml`. The negation is **not optional**.

**The problem**: Push events have no `github.event.pull_request` context, so `labels.*.name` evaluates to an empty array. The function `contains([], 'label')` returns `false`.

**Why negation fixes it**:

- PR with label → `contains()` returns `true` → negation makes condition `false` → job skips (intended)
- PR without label → `contains()` returns `false` → negation makes condition `true` → job runs (intended)
- Push event (empty array) → `contains()` returns `false` → negation makes condition `true` → job runs (safe default)

Without negation, push events would skip the job entirely because the condition evaluates to `false`. CI would never run on direct branch pushes.

### Anti-Pattern

**WRONG:**

```yaml
if: contains(github.event.pull_request.labels.*.name, 'erk-plan-review')
```

This skips the job for push events (the empty array case), preventing CI from running on local git pushes. Master branch protection would be defeated.

## Combining Draft and Label Checks

<!-- Source: .github/workflows/ci.yml, check-submission job (line 22), downstream jobs (lines 36-128) -->

The combined pattern `github.event.pull_request.draft != true && !contains(...)` appears directly on `check-submission`; downstream jobs delegate the label/submission check via `needs.check-submission.outputs.skip` while retaining the draft check directly. Both checks are necessary because they gate different states:

**Draft check**: Excludes PRs explicitly marked work-in-progress
**Label check**: Excludes PRs containing plan content rather than code

A PR can be:

- Draft + labeled (WIP plan review) → both checks exclude
- Non-draft + labeled (ready plan review) → label check excludes
- Draft + not labeled (WIP code) → draft check excludes
- Non-draft + not labeled (ready code) → both checks pass, job runs

## The ready_for_review Trigger

<!-- Source: .github/workflows/ci.yml, lines 6-7 -->

The trigger list includes `ready_for_review` to complement the draft exclusion:

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
```

Without this trigger, marking a draft PR as ready wouldn't start CI until the next commit. The workflow would remain in a "waiting for CI" state despite being ready for review.

## When Job-Level Conditions Aren't Enough

<!-- Source: .github/workflows/code-reviews.yml, discover job -->

The `code-reviews.yml` workflow demonstrates why some checks must happen at step-level despite job-level gating.

The job-level `if:` can cheaply skip draft PRs and `erk-plan-review` PRs before runner allocation. But the "local review passed" marker lives in the PR body and depends on the current HEAD SHA, so the workflow must:

1. Allocate a runner
2. Read the current PR body
3. Compare the marker against the current `head.sha`
4. Gate checkout and review discovery based on that result

This is the right use of step-level gating: the decision depends on dynamic API state that is not available in the event payload.

## Output-Based Gating

<!-- Source: .github/workflows/ci.yml, check-submission job outputs, format job conditions -->
<!-- Source: .github/workflows/ci.yml, fix-formatting job outputs -->

Two different output patterns control downstream execution in repo CI.

The `check-submission` job declares outputs:

```yaml
outputs:
  skip: ${{ steps.check.outputs.skip }}
```

Downstream jobs reference this output:

```yaml
format:
  needs: check-submission
  if: needs.check-submission.outputs.skip == 'false'
```

**Why this exists**: The `.erk/impl-context/` folder detection can't happen until after checkout, so it can't be a job-level condition based on event context. The check-submission job performs checkout, checks for the folder, and publishes a decision that later jobs consume.

<!-- Source: .github/workflows/ci.yml, fix-formatting job outputs -->

`fix-formatting` exposes a second output (`pushed`) that format-sensitive jobs (`format`, `docs-check`) check alongside `check-submission.outputs.skip`. When `pushed` is `'true'`, these jobs skip because the auto-fix commit will trigger a fresh CI run on the corrected HEAD. Speculative jobs (`lint`, `ty`, `unit-tests`, `integration-tests`, `erk-mcp-tests`) don't check `pushed` — they run immediately and rely on `cancel-in-progress: true` for cancellation.

<!-- Source: .github/workflows/ci.yml, format job if: condition -->

See the `fix-formatting` job's `outputs:` block and the `format` job's `if:` condition in `.github/workflows/ci.yml` for the exact syntax.

This pattern separates:

- "should repo validation run at all?" (`check-submission`)
- "should format-sensitive validation run on this commit, or wait for the auto-fix rerun?" (`fix-formatting.pushed`)
- Speculative jobs skip this second check entirely — they start immediately and get cancelled if fix-formatting pushes

## Plan-Review Branch Gating

Plan-review branches are gated via the `erk-plan-review` **label** on their PRs, not via `branches-ignore`. The label-based gating is handled by the `!contains()` pattern described above.

In the current architecture, the active gates are job-level conditions in `.github/workflows/ci.yml` and `.github/workflows/code-reviews.yml`. If a future push-triggered workflow needs authoritative PR label checks, use the API-query pattern from [GitHub Actions Label Queries](github-actions-label-queries.md).

## Decision Table: Which Layer to Use

| What you're checking                            | Use this layer                      | Why                                                 |
| ----------------------------------------------- | ----------------------------------- | --------------------------------------------------- |
| Event type (PR opened, push, workflow_dispatch) | Trigger filtering (`on:`)           | No point queuing workflow for irrelevant events     |
| PR draft state                                  | Job-level `if:`                     | Fast path — no runner allocation for drafts         |
| PR labels (pull_request events)                 | Job-level `if:`                     | Fast path — no runner allocation for plan reviews   |
| PR-body marker or dynamic API state             | Step-level check                    | Requires live API data not present in event payload |
| File existence after checkout                   | Step-level check → job output       | Can't know until checkout completes                 |
| Upstream auto-fix pushed a commit               | Downstream job `if:` via job output | Skip stale validation and wait for the rerun        |
| Upstream job failure                            | Downstream job `if:`                | Use `needs.job.result` or job outputs               |

## Why Not Use Step-Level Checks For Everything

**Q: Why not use only step-level API queries for all events?**

A: Cost and queue pressure. Job-level conditions prevent runner allocation. If a pull_request event has the `erk-plan-review` label, the job-level condition rejects it before GitHub allocates a runner, saving CI minutes and reducing queue contention.

Step-level queries require runner allocation, API calls, and often checkout. Use them only when the decision genuinely depends on dynamic state that the event payload does not contain.

## Related Documentation

- [GitHub Actions Label Queries](github-actions-label-queries.md) — Deep dive on the push event asymmetry
- [Plan Implement Customization](plan-implement-customization.md) — Why `.erk/impl-context/` detection uses output-based gating
- [GitHub Actions Workflow Patterns](github-actions-workflow-patterns.md) — General workflow design patterns

## Attribution

Pattern implemented in PR #6243.
