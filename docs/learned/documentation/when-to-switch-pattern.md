---
title: When to Switch Between Planless and Planning Workflows
read_when:
  - "deciding whether to plan or start coding"
  - "realizing mid-task that you should have planned"
  - "choosing between erk wt create and plan mode"
---

# When to Switch Between Planless and Planning Workflows

Erk supports two workflows: **planless** (direct coding) and **planning** (plan-first). This guide helps you choose the right workflow and recognize when to switch.

## The Two Workflows

### Planless Workflow

**Pattern:** Code → Commit → PR → Land

- Create worktree with `erk wt create`
- Make changes directly in Claude Code
- Submit with `erk pr submit` or `/local:quick-submit`
- Land with `erk pr land`

**Artifacts:** Git commits, PR, no `.impl/` folder

### Planning Workflow

**Pattern:** Plan → Implement → PR → Land → Learn

- Enter plan mode (automatic or manual)
- Create implementation plan with research
- Save plan with `/erk:plan-save`
- Implement with `/erk:plan-implement`
- Learn from session with `erk learn`

**Artifacts:** GitHub issue with plan, `.impl/` folder, session logs, documentation updates

## Decision Matrix

| Factor                   | Planless | Planning                      |
| ------------------------ | -------- | ----------------------------- |
| **Time estimate**        | <2 hours | >2 hours                      |
| **Files affected**       | 1-4      | 5+                            |
| **Approach clarity**     | Obvious  | Uncertain                     |
| **Research needed**      | None     | Codebase exploration required |
| **Architectural impact** | Isolated | Cross-cutting                 |
| **Reusability**          | One-off  | Pattern worth documenting     |

## Signs You Should Be Planning

### During Task Evaluation

❌ **Skip planning when:**

- "Just need to fix this typo"
- "Add one function to handle X"
- "Update the README"
- "Rename this variable consistently"

✅ **Plan first when:**

- "Need to add authentication... not sure how the current system works"
- "Refactor the storage layer... there are multiple approaches"
- "Implement feature X... affects several components"
- "Fix bug Y... need to understand root cause first"

### Mid-Task Warning Signs

If you're coding and notice any of these, **stop and plan**:

1. **Uncertainty accumulating** - "Wait, how does this interact with that?"
2. **Scope creeping** - "Oh, I also need to change these files"
3. **Multiple decisions** - "Should I use approach A or B? What about C?"
4. **Research needed** - "Let me grep for more examples"
5. **Refactoring urge** - "This would be cleaner if I restructured..."

### Time Check Rule

Set a timer when you start planless work:

- **30 minutes in:** Still uncertain? Switch to planning.
- **1 hour in:** Still making decisions? Should have planned.
- **2 hours in:** Stop. Plan the rest.

## How to Switch Mid-Task

### From Planless to Planning

**If you haven't committed yet:**

1. **Discard changes** - `git reset --hard`
2. **Enter plan mode** - Let Claude create plan
3. **Save plan** - `/erk:plan-save`
4. **Implement from plan** - `/erk:plan-implement`

**If you have committed work:**

1. **Commit current state** - Keep what you have
2. **Enter plan mode** - Plan remaining work
3. **Note prerequisite** - Plan should reference your existing PR
4. **Save and implement** - Continue with planning workflow

### From Planning to Planless (Rare)

**Situation:** Plan reveals task is simpler than expected.

1. **Abandon plan implementation** - Close the plan issue
2. **Create worktree** - `erk wt create simple-fix`
3. **Make the simple change** - Direct coding
4. **Submit** - `erk pr submit`

**Note:** This is rare. Usually if you planned, you should implement from the plan.

## Pattern Examples

### Example 1: Bug Fix

**Initial assessment:**

> "API endpoint returns 500 error on specific input"

**Decision:** Start planless - seems straightforward.

**30 minutes in:**

> "Wait, the error is coming from a middleware layer I don't understand. And there are 3 similar middleware functions doing validation. Which one is wrong?"

**Action:** Switch to planning. Create plan that includes:

- Investigation of middleware architecture
- Understanding validation flow
- Determining root cause
- Implementation approach

### Example 2: Feature Addition

**Initial assessment:**

> "Add a --dry-run flag to the command"

**Decision:** Start planless - just a flag.

**1 hour in:**

> "This command uses 5 different gateways, and each needs a dry-run wrapper. And the error handling needs to distinguish between dry-run and real errors. And there's no pattern for this in the codebase."

**Action:** Switch to planning. Create plan that includes:

- Gateway dry-run pattern research
- Determine wrapper architecture
- Plan implementation across all 5 gateways
- Error handling strategy

### Example 3: Documentation

**Initial assessment:**

> "Document the new feature in README"

**Decision:** Planless is fine.

**30 minutes in:**

> "This feature interacts with 4 other features. Need examples showing integration. Should probably create a howto guide instead of just README updates."

**Action:** Switch to planning. Plan should cover:

- Documentation structure decision
- Integration examples to include
- Where to place new docs
- Update existing references

## Anti-Patterns

### Don't Do: Plan Everything

**Problem:** Planning a typo fix wastes more time than the fix.

**Guideline:** If the entire task description fits in one sentence and you know exactly what to do, skip planning.

### Don't Do: Never Plan

**Problem:** Large changes without plans lead to:

- Scope creep
- Missed edge cases
- Poor architectural decisions
- Wasted implementation time

**Guideline:** If you catch yourself saying "I'll figure it out as I go," that's a sign you should plan.

### Don't Do: Switch Too Late

**Problem:** Realizing 4 hours into coding that you should have planned means 4 hours of potentially wrong implementation.

**Guideline:** The 30-minute rule catches this. Check in with yourself early.

## Related Documentation

- [Planless Workflow Guide](../../howto/planless-workflow.md) - How to work without plans
- [Local Planning Workflow](../../howto/local-workflow.md) - Plan-first workflow
- [Plan Lifecycle](../planning/lifecycle.md) - Understanding plan phases
