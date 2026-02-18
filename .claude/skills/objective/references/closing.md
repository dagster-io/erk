# Closing an Objective

This document covers when and how to close objectives, including proactive triggers that should prompt the agent to ask about closing.

## Proactive Closing Triggers

**CRITICAL**: When any of these conditions are detected, the agent MUST ask the user about closing the objective. Do not let objectives linger in a "ready to close" state.

### Trigger 1: All Nodes Complete

When updating an objective and ALL roadmap nodes show `done` or `skipped` status:

```
All roadmap nodes are complete. Should I close objective #<number> now?
- Yes, close with final summary
- Not yet, there may be follow-up work
- I'll close it manually later
```

### Trigger 2: Final PR Landed

When the user says they're landing/merging the final PR for an objective:

- "Landing this PR"
- "Merging the last PR"
- "This completes the objective"

Ask before or immediately after the merge:

```
This PR completes objective #<number>. Should I close it now?
```

### Trigger 3: Post-Update Check

After any objective update that marks the last pending node as done, proactively check:

1. Are all nodes now done/skipped?
2. If yes, ask about closing

## When to Close

Close an objective when:

- All roadmap nodes are done or explicitly skipped
- The goal has been achieved
- The objective is abandoned (document why)

Do NOT close if:

- There's follow-up work that should be tracked
- The user indicates more phases may be added
- PRs are merged but verification is pending

## Pre-Closing Checklist

Before closing, verify:

- [ ] All roadmap nodes are `done` or `skipped` (with reasons for skipped)
- [ ] All related PRs are merged
- [ ] Action comments capture key lessons learned
- [ ] Issue body reflects final state

## The Two-Step Close

### Step 1: Post Final Action Comment

```bash
gh issue comment <issue-number> --body "$(cat <<'EOF'
## Action: Objective Complete

**Date:** $(date +%Y-%m-%d)

### Summary
[What was achieved overall - 1-2 sentences]

### Key Outcomes
- [Concrete outcome 1]
- [Concrete outcome 2]

### Lessons for Future Objectives
- [Meta-lesson about the process]
EOF
)"
```

### Step 2: Close the Issue

```bash
gh issue close <issue-number>
```

## Abandoning an Objective

If abandoning rather than completing, document why:

```bash
gh issue comment <issue-number> --body "$(cat <<'EOF'
## Action: Objective Abandoned

**Date:** $(date +%Y-%m-%d)

### Reason
[Why the objective is being abandoned]

### Completed Work
- [What was done before abandoning]

### Lessons Learned
- [Insights from the work]

### Disposition
- [What happens to any in-progress work]
EOF
)"

gh issue close <issue-number> --reason "not planned"
```

## Example: Complete Close Flow

User: "I'm about to land PR #3491 which completes the objective"

Agent should:

1. Recognize this as Trigger 3 (final PR)
2. Ask: "This PR completes objective #3472. Should I close it after landing?"
3. If yes:
   - Post final action comment summarizing the work
   - Update issue body if needed (ensure all nodes marked done)
   - Close the issue
   - Report: "Objective #3472 closed successfully"

## Anti-Pattern: Lingering Objectives

**Don't leave objectives in limbo.** These states indicate a missed closing opportunity:

- All nodes are done but no final summary posted
- Last update was days ago with completion language

If you notice these states, proactively ask about closing.
