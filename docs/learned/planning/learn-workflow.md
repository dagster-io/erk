---
title: Learn Workflow
read_when:
  - "using /erk:learn skill"
  - "understanding learn status tracking"
  - "auto-updating parent plans when learn plans land"
tripwires:
  - action: "modifying learn command to add/remove/reorder agents"
    warning: "Verify tier placement before assigning model. Parallel extraction uses haiku, sequential synthesis may need opus for quality-critical output."
  - action: "adding new agents to learn workflow"
    warning: "Document input/output format and test file passing. Learn workflow uses stateless agents with file-based composition."
---

# Learn Workflow

This guide explains the learn workflow in erk: how `/erk:learn` creates documentation plans, tracks status on parent plans, and enables automatic updates when learn plans are landed.

## Overview

The learn workflow extracts insights from implementation sessions and creates documentation plans. It's part of erk's knowledge capture system.

```
┌─────────────────┐     /erk:learn      ┌─────────────────┐
│  Parent Plan    │ ─────────────────→  │  Learn Plan     │
│  (erk-plan)     │                     │  (erk-learn)    │
│                 │                     │                 │
│ learn_status:   │                     │ learned_from:   │
│ completed_with_ │ ←─────────────────  │ <parent-issue>  │
│ plan            │      backlink       │                 │
│ learn_plan_     │                     │                 │
│ issue: <N>      │                     │                 │
└─────────────────┘                     └─────────────────┘
         │                                      │
         │                                      │
         │         erk land                     │
         │     ←───────────────────────         │
         │      auto-update on land             │
         ▼                                      ▼
┌─────────────────┐                     ┌─────────────────┐
│ learn_status:   │                     │  PR merged      │
│ plan_completed  │                     │                 │
│ learn_plan_pr:  │                     │                 │
│ <PR-number>     │                     │                 │
└─────────────────┘                     └─────────────────┘
```

## Key Concepts

### Parent Plan

The original implementation plan that `/erk:learn` is invoked on. After learn completes, the parent plan's metadata is updated with:

- `learn_status`: Status of the learning workflow
- `learn_plan_issue`: Issue number of the created learn plan (if any)
- `learn_plan_pr`: PR number that implemented the learn plan (after landing)

### Learn Plan

A documentation plan created by `/erk:learn`. It has the `erk-learn` label and contains:

- `learned_from_issue`: Backlink to the parent plan issue number

This backlink enables automatic status updates when the learn plan is landed.

### Learn Status Values

| Status                | Description                                 |
| --------------------- | ------------------------------------------- |
| `completed_no_plan`   | Learn completed, no documentation needed    |
| `completed_with_plan` | Learn completed, documentation plan created |
| `plan_completed`      | Learn plan was implemented and PR landed    |

## Agent Tier Architecture

The learn workflow orchestrates 5 agents across 3 tiers:

### Parallel Tier (Haiku)

Run simultaneously via `run_in_background: true`:

- **SessionAnalyzer** - Extracts patterns from preprocessed session XML
- **CodeDiffAnalyzer** - Inventories PR changes
- **ExistingDocsChecker** - Searches for duplicates/contradictions

### Sequential Tier 1 (Haiku)

Depends on parallel tier outputs:

- **DocumentationGapIdentifier** - Synthesizes and deduplicates candidates

### Sequential Tier 2 (Opus)

Depends on Sequential Tier 1:

- **PlanSynthesizer** - Creates narrative context and draft content

### Model Selection Rationale

| Tier         | Model | Rationale                                                      |
| ------------ | ----- | -------------------------------------------------------------- |
| Parallel     | Haiku | Mechanical extraction tasks - pattern matching, classification |
| Sequential 1 | Haiku | Rule-based deduplication and prioritization                    |
| Sequential 2 | Opus  | Creative authoring, narrative generation, quality-critical     |

See [Agent Delegation](agent-delegation.md#model-selection) for general model selection guidance.

## The Learn Flow

### Step 1: Run /erk:learn on Parent Plan

```bash
/erk:learn <parent-issue-number>
```

The skill:

1. Analyzes sessions associated with the parent plan
2. Identifies documentation gaps
3. Creates a learn plan issue (if needed)

### Step 2: Track Learn Result

After creating the learn plan, the skill calls:

```bash
erk exec track-learn-result \
    --issue <parent-issue-number> \
    --status completed_with_plan \
    --plan-issue <learn-plan-issue-number>
```

This sets `learn_status` and `learn_plan_issue` on the parent plan.

If no documentation was needed:

```bash
erk exec track-learn-result \
    --issue <parent-issue-number> \
    --status completed_no_plan
```

### Step 3: Learn Plan Links Back

When creating the learn plan, the `--learned-from-issue` flag is passed:

```bash
erk exec plan-save-to-issue \
    --plan-type learn \
    --learned-from-issue <parent-issue-number> \
    ...
```

This sets `learned_from_issue` in the learn plan's metadata, creating a bidirectional link.

### Step 4: Implement and Land Learn Plan

When the learn plan is implemented and the PR is landed via `erk land`:

1. The land command detects `learned_from_issue` in the plan header
2. It calls `_update_parent_plan_on_learn_plan_land()`
3. The parent plan's status is updated:
   - `learn_status` → `plan_completed`
   - `learn_plan_pr` → PR number

## TUI Integration

The TUI shows learn status in the "lrn" column:

| Display | Meaning                     |
| ------- | --------------------------- |
| (empty) | Not learned yet             |
| `#N`    | Learn created plan issue #N |
| `✓ #PR` | Learn plan landed in PR #PR |

Clicking the cell opens the learn plan issue or PR.

## Related Commands

- `/erk:learn` - Run learn workflow on a plan
- `erk exec track-learn-result` - Update parent plan's learn status
- `erk exec track-learn-evaluation` - Track that learn was invoked
- `erk land` - Land PR with automatic parent plan updates

## Metadata Fields

### On Parent Plans

```yaml
learn_status: completed_with_plan # or completed_no_plan, plan_completed
learn_plan_issue: 123 # Issue number of learn plan
learn_plan_pr: 456 # PR number (after landing)
last_learn_at: 2025-01-21T... # Timestamp of last learn invocation
last_learn_session: abc123 # Session ID that ran learn
```

### On Learn Plans

```yaml
learned_from_issue: 100 # Parent plan issue number
```

## CI Environment Behavior

The learn workflow automatically detects CI environments and adjusts its behavior:

### Environment Detection

The command checks for CI mode using these environment variables:

- `$CI` - Set by most CI systems including GitHub Actions
- `$GITHUB_ACTIONS` - GitHub-specific indicator

### Behavioral Differences

| Context     | Detection                                 | Step 5 Behavior                                    |
| ----------- | ----------------------------------------- | -------------------------------------------------- |
| Interactive | Neither `$CI` nor `$GITHUB_ACTIONS` set   | Prompts user to confirm which items to include     |
| CI Mode     | Either `$CI` or `$GITHUB_ACTIONS` is set  | Auto-proceeds with all HIGH/MEDIUM priority items  |

### Detection Pattern

```bash
[ -n "$CI" ] || [ -n "$GITHUB_ACTIONS" ] && echo "CI_MODE" || echo "INTERACTIVE"
```

This pattern is used in Step 5 (Present Findings) to determine whether to prompt the user or auto-proceed.
