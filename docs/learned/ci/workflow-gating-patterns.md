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
---

# GitHub Actions Workflow Gating Patterns

Erk uses multiple layers of workflow gating to control when CI runs. This guide covers the patterns used in `.github/workflows/ci.yml` and `.github/workflows/code-reviews.yml`.

## Overview: Multiple Layers of Workflow Gating

Erk's CI uses a compositional gating strategy with three layers:

1. **Trigger filtering**: `on:` section filters which events start the workflow
2. **Job conditions**: `if:` clauses on jobs determine whether they execute
3. **Output-based skipping**: Jobs check outputs to decide whether to run downstream work

Each layer serves a different purpose and they work together to create flexible, safe workflow control.

## Label-Based Gating Pattern

### The Core Pattern

```yaml
if: github.event.pull_request.draft != true && !contains(github.event.pull_request.labels.*.name, 'plan-review')
```

This pattern appears in:

- `.github/workflows/ci.yml:20` - check-submission job
- `.github/workflows/ci.yml:135` - autofix job
- `.github/workflows/code-reviews.yml:11` - discover job

### Why Negation is Critical

The `!contains()` pattern uses **negation** to exclude labeled PRs. This design is critical because of how GitHub Actions handles push events:

- **Pull request events**: `github.event.pull_request.labels` is an array of label objects
- **Push events**: `github.event.pull_request` is `null`, so `labels.*.name` evaluates to an empty array
- **contains() with empty array**: Always returns `false`

**WRONG (skips all push events):**

```yaml
if: contains(github.event.pull_request.labels.*.name, 'plan-review')
```

This evaluates to `false` for push events (empty array), so the job is skipped.

**CORRECT (runs for push events):**

```yaml
if: !contains(github.event.pull_request.labels.*.name , 'plan-review')
```

This evaluates to `true` for push events (empty array doesn't contain 'plan-review'), so the job runs.

### Safe Defaults

The negation pattern creates a safe default behavior:

- **PR with 'plan-review' label**: Job is skipped (intended)
- **PR without 'plan-review' label**: Job runs (intended)
- **Push event (no PR context)**: Job runs (safe default - don't skip CI on direct pushes)

This ensures that CI always runs on direct pushes to branches, which is important for protecting the main branch.

## Draft PR Exclusion Pattern

### The Pattern

```yaml
if: github.event.pull_request.draft != true
```

This pattern appears in all job conditions that also check labels. It excludes draft PRs from running CI.

### Why Check Both Draft and Labels

Draft and label checks serve different purposes:

- **Draft check**: Excludes PRs that are explicitly marked as work-in-progress
- **Label check**: Excludes PRs that contain plan content rather than code

Both checks are needed because:

1. A PR can be both draft and labeled (e.g., a draft plan review)
2. A PR can be non-draft but labeled (e.g., a ready plan review)
3. A PR can be draft but not labeled (e.g., a work-in-progress code change)

The combined condition ensures CI only runs on PRs that are both:

- Ready for review (not draft)
- Contain code changes (not labeled 'plan-review')

## ready_for_review Trigger Complement

### The Pattern

```yaml
on:
  pull_request:
    types: [opened, synchronize, ready_for_review]
```

The `ready_for_review` trigger complements the draft exclusion by ensuring CI runs when a draft PR is marked ready:

- **opened**: PR created as ready (draft check passes)
- **synchronize**: PR updated with new commits (draft check evaluates current state)
- **ready_for_review**: Draft PR marked ready (draft check now passes)

Without `ready_for_review`, CI wouldn't run when a draft PR transitions to ready until the next push.

## Compositional Gating: How Layers Interact

### Layer 1: Trigger Filtering

```yaml
on:
  pull_request:
    types: [opened, synchronize, ready_for_review]
  push:
    branches: [master, main]
```

**Purpose**: Control which events start the workflow at all.

**Effect**: The workflow runs for PR events and pushes to main branches. Other events (e.g., pull_request.closed) don't trigger the workflow.

### Layer 2: Job Conditions

```yaml
jobs:
  check-submission:
    if: github.event.pull_request.draft != true && !contains(github.event.pull_request.labels.*.name, 'plan-review')
```

**Purpose**: Decide whether individual jobs execute within the triggered workflow.

**Effect**: The job is skipped if the PR is a draft or has the 'plan-review' label. Other jobs in the workflow can still run.

### Layer 3: Output-Based Skipping

```yaml
jobs:
  check-submission:
    outputs:
      skip: ${{ steps.check.outputs.skip }}

  format:
    needs: check-submission
    if: needs.check-submission.outputs.skip == 'false'
```

**Purpose**: Let one job's results control whether downstream jobs execute.

**Effect**: The check-submission job determines if the PR has a `.worker-impl/` folder. If not, downstream jobs are skipped. See [Plan Implement Customization](plan-implement-customization.md) for details.

### Why Three Layers?

Each layer solves a different problem:

1. **Triggers**: "Should this event start CI at all?" (e.g., don't run on PR close)
2. **Job conditions**: "Is this PR in a state where this job makes sense?" (e.g., don't run code checks on plan-only PRs)
3. **Output checks**: "Did earlier checks determine this work is unnecessary?" (e.g., no code changes to test)

The layers compose: a job only runs if all three conditions are satisfied.

## Autofix Safety Pattern

The autofix job uses **both** event type and label checks to ensure safe execution:

```yaml
autofix:
  if: |
    always() &&
    github.ref_name != 'master' &&
    github.ref_name != 'main' &&
    (github.event_name == 'pull_request' || github.event_name == 'push') &&
    (github.event_name != 'pull_request' || github.event.pull_request.draft != true) &&
    (github.event_name != 'pull_request' || !contains(github.event.pull_request.labels.*.name, 'plan-review')) &&
    (needs.format.result == 'failure' ||
     needs.lint.result == 'failure' ||
     needs.prettier.result == 'failure' ||
     needs.docs-check.result == 'failure' ||
     needs.typecheck.result == 'failure')
```

This pattern ensures autofix:

- Runs even if earlier jobs failed (`always()`)
- Never runs on main branches (prevents accidental commits)
- Only runs for PR or push events (not for other event types)
- Respects draft and label exclusions (same safety as other jobs)
- Only runs if at least one format/lint job failed (no unnecessary commits)

The event type check prevents autofix from running in contexts where `github.event.pull_request` would be null, which would break the label check.

## Decision Table: When to Use Each Pattern

| Scenario                    | Pattern                                                       | Example                                       |
| --------------------------- | ------------------------------------------------------------- | --------------------------------------------- |
| Exclude labeled PRs         | `!contains(github.event.pull_request.labels.*.name, 'label')` | Skip CI for plan-review PRs                   |
| Exclude draft PRs           | `github.event.pull_request.draft != true`                     | Don't run CI until PR is ready                |
| Both draft and label        | Combine both conditions with `&&`                             | Skip CI for draft plan reviews                |
| Allow workflow but skip job | Job-level `if:` condition                                     | Skip code checks but run metadata checks      |
| Skip based on job output    | `needs.job.outputs.var == 'value'`                            | Skip tests if no code changes                 |
| Safety for push commits     | Check event type before accessing PR fields                   | Prevent autofix from running in wrong context |

## Related Documentation

- [Plan Implement Customization](plan-implement-customization.md) - Output-based skipping pattern
- [GitHub Actions Workflow Patterns](github-actions-workflow-patterns.md) - General workflow design
- [Convention-Based Reviews](convention-based-reviews.md) - How label checks affect code reviews

## Attribution

Pattern implemented in PR #6243.
