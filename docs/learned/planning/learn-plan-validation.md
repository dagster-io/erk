---
title: Learn Plan Validation
read_when:
  - "creating or modifying erk-learn plans"
  - "working on the learn workflow pipeline"
  - "debugging learn-on-learn cycle errors"
tripwires:
  - action: "creating erk-learn plan for an issue that already has erk-learn label"
    warning: "Validate target issue has erk-plan label, NOT erk-learn. Learn plans analyze implementation plans, not other learn plans (cycle prevention)."
last_audited: "2026-02-16 14:20 PT"
audit_result: clean
---

# Learn Plan Validation

## Core Rule: No Learn-on-Learn

Learn plans exist to extract insights from **implementation work** (erk-plan issues). A learn plan must never target another learn plan — this would create documentation cycles where plans endlessly analyze each other instead of analyzing real code changes.

The cycle risk is real because the learn pipeline is automated: after a PR lands, the system can automatically create a learn plan. If learn plans could target other learn plans, the pipeline would generate infinite chains (learn A analyzes learn B which analyzes learn A).

## Where Validation Lives

Cycle prevention is enforced at multiple points because learn plans flow through several different code paths. Each enforcement point serves a different workflow entry:

| Enforcement Point                 | What It Checks                                   | Why There                                                             |
| --------------------------------- | ------------------------------------------------ | --------------------------------------------------------------------- |
| `/erk:learn` skill (Step 1)       | Target issue labels include `erk-learn` → reject | Primary entry: agent-driven learn invocation                          |
| `erk land` pre-flight             | Issue has `erk-learn` label → skip learn prompt  | Prevents "did you learn from this?" prompt for learn plans themselves |
| `is_issue_learn_plan()` in submit | Label check helper                               | Shared utility for branch/submit workflows                            |

<!-- Source: .claude/commands/erk/learn.md:38-53 -->

The `/erk:learn` skill performs the authoritative check in its Step 1 by fetching the issue via `erk exec get-issue-body` and inspecting the `labels` array. If `erk-learn` is present, the skill halts with a cycle prevention error.

<!-- Source: src/erk/cli/commands/land_cmd.py, _check_learn_before_land -->

The land command's learn check skips entirely for issues bearing the `erk-learn` label, since learn plans are not themselves subject to the "did you learn?" prompt.

## The Two-Label System

Understanding why this validation matters requires understanding the label-based workflow stages:

| Label       | Role                | Direction                                                    |
| ----------- | ------------------- | ------------------------------------------------------------ |
| `erk-plan`  | Implementation plan | Looks **forward** — code changes to make                     |
| `erk-learn` | Documentation plan  | Looks **backward** — insights to extract from completed work |

<!-- Source: src/erk/cli/constants.py, ERK_PLAN_LABEL and ERK_LEARN_LABEL -->

Both labels are defined as constants and used throughout the CLI for label checks, issue creation, and filtering.

The flow is strictly one-directional: `erk-plan` → implement → land PR → `erk-learn` → extract docs → done. Learn plans are terminal nodes in this pipeline, never sources for further learn plans.

## Anti-Patterns

**Creating a learn plan that targets another learn plan.** Even if the goal is "meta-analysis of the learn workflow itself," the correct approach is to create an `erk-plan` issue for improving the learn workflow's code, not an `erk-learn` issue analyzing another `erk-learn` issue.

**Skipping the label check when adding new learn entry points.** Any new code path that creates or triggers learn plans must check for the `erk-learn` label on the target issue. The validation is intentionally distributed across entry points rather than centralized, so new entry points need their own check.
