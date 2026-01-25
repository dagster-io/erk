# Plan: Add Longer Timeout Guidance for Background Agents

## Summary

The `/erk:replan` skill launches background Explore agents for deep investigation but the instructions for waiting on them don't specify timeout values. The default TaskOutput timeout is 30 seconds, which is too short for comprehensive codebase investigation.

## Root Cause

The TaskOutput tool has:
- Default timeout: 30,000ms (30 seconds)
- Maximum timeout: 600,000ms (10 minutes)

Step 4e of `/erk:replan` says to use `TaskOutput` with `block: true` but doesn't specify a timeout, so agents hit the 30-second default.

## Implementation

### File 1: `.claude/commands/erk/replan.md`

Update Step 4e to specify longer timeouts when waiting for background agents.

**Location:** Lines 171-174, in the "How to wait" section

**Change:** Add explicit timeout guidance:

```markdown
**How to wait:**

For each background agent task_id, use TaskOutput tool with:
- `block: true` to wait for completion
- `timeout: 600000` (10 minutes)

Only after ALL agents have completed should you proceed to Step 5.
```

### File 2: `.claude/commands/local/replan-learn-plans.md`

Update the IMPORTANT note at line 137 to reinforce the timeout guidance.

**Location:** Line 137-138

**Change:** Add timeout reminder:

```markdown
**IMPORTANT:** The `/erk:replan` skill will launch background Explore agents for deep investigation. Per Step 4e of that skill, you MUST wait for ALL background agents to complete before creating the consolidated plan. Use `timeout: 600000` (10 minutes) when calling TaskOutput. Do not proceed to plan creation until every investigation agent has returned its findings.
```

## Verification

1. Run `/local:replan-learn-plans` with multiple plans
2. Observe that TaskOutput calls use 5-minute timeouts
3. Confirm agents complete without timeout warnings