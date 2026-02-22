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

<!-- Source: .github/workflows/ci.yml, autofix job steps 166-397 -->

The autofix job demonstrates why some checks must happen at step-level despite job-level gating:

**For push events**, `github.event.pull_request` doesn't exist at job evaluation time. Job-level label checks are impossible. The workflow must:

1. Allocate a runner (job-level condition passes for push events)
2. Query GitHub API to find associated PR
3. Fetch labels via API
4. Gate subsequent steps based on result

This asymmetry exists because push events are branch operations. GitHub doesn't implicitly resolve "what PR uses this branch?" until you ask via the API.

See the autofix job in `.github/workflows/ci.yml` for the multi-step implementation: discover PR (via `github.event.pull_request.number` for PR events or `gh api` for push events), check for label, consolidate all conditions into a single boolean output, gate all subsequent steps on that output.

For the deep dive on why this asymmetry exists and the defense-in-depth solution, see [GitHub Actions Label Queries](github-actions-label-queries.md).

## Output-Based Gating

<!-- Source: .github/workflows/ci.yml, check-submission job outputs, format job conditions -->

A different pattern: one job's results control whether downstream jobs execute.

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

**Why this exists**: The `.worker-impl/` folder detection can't happen until after checkout, so it can't be a job-level condition based on event context. The check-submission job performs checkout, checks for the folder, and publishes a decision that later jobs consume.

This pattern separates "should this workflow run?" (event-based, job-level) from "should this job run?" (state-based, after checkout). For full context on why `.worker-impl/` folders are special, see [Plan Implement Customization](plan-implement-customization.md).

## Autofix Safety Pattern

<!-- Source: .github/workflows/ci.yml, autofix job condition lines 152-163 -->

The autofix job combines event type checks with label/draft checks:

```yaml
if: |
  always() &&
  github.ref_name != 'master' &&
  github.ref_name != 'main' &&
  (github.event_name == 'pull_request' || github.event_name == 'push') &&
  (github.event_name != 'pull_request' || github.event.pull_request.draft != true) &&
  (github.event_name != 'pull_request' || !contains(..., 'erk-plan-review')) &&
  (needs.format.result == 'failure' || ...)
```

**Why event type guards**: The label/draft checks reference `github.event.pull_request`, which only exists for `pull_request` events. Without the guard `github.event_name != 'pull_request' ||`, the checks would fail for push events.

The guard pattern `(event != X || check_that_only_works_for_X)` creates safe evaluation: if the event type doesn't match, the guard short-circuits to `true` without evaluating the check.

**Why `always()`**: Autofix must evaluate its condition even when upstream jobs fail (that's the point — fix the failures). Without `always()`, a failed format job would prevent autofix from even considering whether to run.

## Path-Based Filtering (paths-ignore)

<!-- Source: .github/workflows/ci.yml, on: push: paths-ignore -->

The CI workflow uses `paths-ignore` on push events to skip CI when commits only touch ephemeral metadata directories:

```yaml
on:
  push:
    paths-ignore:
      - ".erk/impl-context/**"
      - ".worker-impl/**"
```

**Why paths-ignore instead of branches-ignore**: Branches like `planned/*` contain both metadata commits AND code commits. Using `branches-ignore` would skip CI for ALL pushes to those branches, including code changes. `paths-ignore` only skips CI when the push exclusively modifies the listed paths.

| Directory            | Purpose                                   |
| -------------------- | ----------------------------------------- |
| `.erk/impl-context/` | Plan content committed during plan-save   |
| `.worker-impl/`      | Worker implementation submission metadata |

**When both metadata and code change in the same push**: `paths-ignore` allows CI to run because the push touches paths outside the ignore list.

## Plan-Review Branch Gating

Plan-review branches are gated via the `erk-plan-review` **label** on their PRs, not via `branches-ignore`. The label-based gating is handled by the `!contains()` pattern described above.

**Defense-in-depth** for plan-review PRs:

1. **Label-based job conditions** (`!contains(...)`) — blocks pull_request events at job level
2. **Step-level API queries** — blocks push events at step level in the autofix job

## Decision Table: Which Layer to Use

| What you're checking                            | Use this layer                        | Why                                                   |
| ----------------------------------------------- | ------------------------------------- | ----------------------------------------------------- |
| Known ephemeral branch patterns (push events)   | Trigger filtering (`branches-ignore`) | Prevents workflow from queuing — zero cost            |
| Branches with both metadata AND code            | Trigger filtering (`paths-ignore`)    | Skips CI only when push is metadata-only              |
| Event type (PR opened, push, workflow_dispatch) | Trigger filtering (`on:`)             | No point queuing workflow for irrelevant events       |
| PR draft state                                  | Job-level `if:`                       | Fast path — no runner allocation for drafts           |
| PR labels (pull_request events)                 | Job-level `if:`                       | Fast path — no runner allocation for plan reviews     |
| PR labels (push events)                         | Step-level API query                  | Required path — PR context doesn't exist at job level |
| File existence after checkout                   | Step-level check → job output         | Can't know until checkout completes                   |
| Upstream job failure                            | Downstream job `if:`                  | Use `needs.job.result` or job outputs                 |

## Why Both Job-Level and Step-Level Label Checks

**Q: Why not use only step-level API queries for all events?**

A: Cost and queue pressure. Job-level conditions prevent runner allocation. If a pull_request event has the `erk-plan-review` label, the job-level condition rejects it before GitHub allocates a runner, saving CI minutes and reducing queue contention.

Step-level queries require: runner allocation, checkout, API calls. This burns resources for cases that could be rejected immediately.

The defense-in-depth approach uses the fast path when available (job-level for pull_request) and the required path when necessary (step-level for push).

## Related Documentation

- [GitHub Actions Label Queries](github-actions-label-queries.md) — Deep dive on the push event asymmetry
- [Plan Implement Customization](plan-implement-customization.md) — Why `.worker-impl/` detection uses output-based gating
- [GitHub Actions Workflow Patterns](github-actions-workflow-patterns.md) — General workflow design patterns

## Attribution

Pattern implemented in PR #6243.
