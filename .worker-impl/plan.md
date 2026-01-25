# Plan: Add Background Agent Completion Requirement to Replan Commands

## Problem

During `/local:replan-learn-plans` execution, background Explore agents are launched for deep investigation but the plan is created before all agents complete. This leads to incomplete investigation data in the consolidated plan.

## Solution

Update the `/erk:replan` skill to add an explicit step requiring all background agents to complete before proceeding to plan creation.

## Files to Modify

### 1. `.claude/commands/erk/replan.md`

**Change:** Add new Step 4e after Step 4d (around line 154)

Insert between Step 4d (Consolidation Analysis) and Step 5 (Post Investigation):

```markdown
### Step 4e: Wait for All Background Investigations (CRITICAL)

**BEFORE proceeding to Step 5 or Step 6, you MUST wait for ALL background agents to complete.**

If you launched agents with `run_in_background: true`:

1. **Check agent status**: Use TaskOutput with `block: true` to wait for each background agent
2. **Collect all results**: Do not proceed until every agent has returned its findings
3. **Synthesize findings**: Combine results from all agents into a unified investigation summary

**Why this matters:**

- Background agents may discover critical corrections or implementation details
- Creating the plan before investigations complete leads to incomplete or inaccurate plans
- The consolidated plan quality depends on having ALL investigation data

**How to wait:**

For each background agent task_id, use TaskOutput tool with `block: true` to wait for completion, then read the agent's findings from the output.

Only after ALL agents have completed should you proceed to Step 5.
```

### 2. `.claude/commands/local/replan-learn-plans.md`

**Change:** Add note after Step 3's skill invocation (after line 117)

Insert after the line `Use the Skill tool with skill: "erk:replan"...`:

```markdown
**IMPORTANT:** The `/erk:replan` skill will launch background Explore agents for deep investigation. Per Step 4e of that skill, you MUST wait for ALL background agents to complete before creating the consolidated plan. Do not proceed to plan creation until every investigation agent has returned its findings.
```

## Verification

1. Read both files after editing to confirm changes are in place
2. The changes are documentation-only - no code tests needed