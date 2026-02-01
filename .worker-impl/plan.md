# Plan: Merge Step 3 (Fetch Plan Content) into Step 4 (Deep Investigation) in /erk:replan

## Problem

In `/erk:replan` consolidation mode, Step 3 fetches plan content from each issue via sequential `gh issue view` calls, dumping hundreds of lines per issue into the main conversation context. This content is only consumed by Step 4's Explore agents. For 7 issues, this wastes ~1500+ lines of main context tokens.

## Solution

Remove Step 3 as a separate step. Instead, have each Explore agent in Step 4 fetch its own issue's plan content as part of its investigation work.

## File to Modify

`/Users/schrockn/code/erk/.claude/commands/erk/replan.md`

## Changes

### 1. Remove Step 3 content-fetching from main context

Replace the current Step 3 (lines 83-99) instructions that tell the agent to fetch plan content via `gh issue view` in the main conversation. Instead, Step 3 becomes a brief note:

```markdown
### Step 3: Plan Content Fetching (Delegated to Step 4)

Plan content is fetched by each Explore agent in Step 4, not in the main context.
This avoids dumping large plan bodies into the main conversation.

Skip to Step 4.
```

### 2. Update Step 4 Explore agent instructions to fetch their own plan content

In Step 4 (lines 101-178), update the Explore agent prompt template to include fetching plan content as the agent's first action. Each agent's prompt should instruct it to:

1. Fetch its issue's plan content: `gh issue view <number> --comments --json comments --jq '.comments[0].body'`
2. Parse the plan-body metadata block
3. Then proceed with investigation (checking items against codebase, deep investigation, corrections)

The agent returns a structured summary including:
- Plan items and their status (implemented/not/obsolete)
- Corrections to original plan
- Key architectural insights

This keeps the raw plan content inside the subagent's context, and only the synthesized findings flow back to the main conversation.

### 3. Handle the error case

Add to Step 4's agent prompt: if no `plan-body` metadata block is found in the first comment, the agent should check the issue body directly (handles cases like #6431 where content is in the body).

## Verification

- Run `/erk:replan` on 2+ test issues and confirm Step 3 no longer dumps plan content into main context
- Confirm Explore agents successfully fetch and parse plan content themselves
- Confirm consolidated plan quality is unchanged