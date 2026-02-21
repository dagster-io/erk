---
title: Automated Review System
read_when:
  - "understanding what automated reviews run on PRs"
  - "debugging unexpected review comments on a PR"
  - "adding a new automated review bot"
  - "understanding re-review triggers"
tripwires:
  - action: "creating a new review without checking the review types taxonomy"
    warning: "Consult review-types-taxonomy.md first. Creating overlapping reviews wastes CI resources and confuses PR status checks."
---

# Automated Review System

Erk runs automated code reviews on every non-draft PR via the convention-based review discovery system. This document provides a high-level overview of the review bot ecosystem.

## Review Bots Overview

| Bot                       | Review File                                 | What It Checks                                 |
| ------------------------- | ------------------------------------------- | ---------------------------------------------- |
| test-coverage-review      | `.erk/reviews/test-coverage.md`             | Missing test coverage for changed source files |
| dignified-python-review   | `.erk/reviews/dignified-python.md`          | Python coding standard violations              |
| dignified-code-simplifier | `.erk/reviews/dignified-code-simplifier.md` | Code simplification opportunities              |
| tripwires-review          | `.erk/reviews/tripwires.md`                 | Violations of documented tripwire rules        |
| audit-pr-docs             | `.erk/reviews/audit-pr-docs.md`             | Documentation quality in learned docs PRs      |

> **Note:** Authority level (advisory vs enforcing) is a behavioral convention observed in CI, not a machine-readable spec field in the review files. Check the CI workflow behavior for current enforcement status.

## How Reviews Are Triggered

Reviews are triggered by the `code-reviews.yml` GitHub Actions workflow, which runs on:

- `pull_request` events: `opened`, `synchronize`, `reopened`, `ready_for_review`
- Only on **non-draft** PRs (`github.event.pull_request.draft != true`)

The workflow has two phases:

1. **Discovery** (`erk exec discover-reviews`): Scans changed files against review file patterns to determine which reviews apply
2. **Execution** (`erk exec run-review`): Runs each applicable review in parallel, posting results as PR review comments

## Re-Review Triggers

Reviews re-run automatically when:

- New commits are pushed to the PR branch (`synchronize` event)
- The PR is marked ready for review (`ready_for_review` event)
- The PR is reopened (`reopened` event)

Reviews do NOT re-run when:

- PR body or title is edited
- Labels are added or removed
- Comments are posted

## Bot Thread Inflation

Bot-generated review threads inflate the unresolved thread count on PRs. The PR feedback classifier (used by `/erk:pr-address`) categorizes bot threads as informational rather than actionable.

See [PR Address Workflows — Bot Thread Inflation](../erk/pr-address-workflows.md#bot-thread-inflation) for details.

## Related Documentation

- [Convention-Based Code Reviews](convention-based-reviews.md) - How to add and configure reviews
- [Review Types Taxonomy](review-types-taxonomy.md) - Decision framework for extending vs creating reviews
- [PR Address Workflows](../erk/pr-address-workflows.md) - Addressing review comments
- [Reviews Development](../reviews/development.md) - Review development patterns
