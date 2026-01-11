---
description: Extract insights from plan-associated sessions
argument-hint: "[issue-number]"
---

# /erk:learn

Extract insights from Claude Code sessions associated with a plan implementation.

## Usage

```
/erk:learn           # Infers issue from current branch (P{issue}-...)
/erk:learn 4655      # Explicit issue number
```

## Agent Instructions

### Step 1: Get Session Information

Run the learn command to get session details:

```bash
erk learn <issue-number> --json --no-track
```

Parse the JSON output to get:

- `session_paths`: Paths to readable session files
- `planning_session_id`: Session that created the plan
- `implementation_session_ids`: Sessions that executed the plan
- `local_session_ids`: Fallback sessions found locally (when GitHub has no tracked sessions)

If no sessions are found (both `session_paths` empty and `local_session_ids` empty), inform the user and stop.

### Step 2: Preprocess and Read Session Content

For each session path from Step 1, preprocess it to compressed XML format for efficient reading:

```bash
erk exec preprocess-session <session-path> --stdout
```

This preprocessing:

- Reduces token usage by 50%+ through deduplication and truncation
- Filters warmup noise (pwd, ls ~/.claude/, etc.)
- Outputs clean XML format instead of raw JSONL

Read the preprocessed output and analyze what happened:

- What was the user trying to accomplish?
- What approaches were tried?
- What challenges were encountered?
- What solutions worked?

Focus on the most relevant sessions (usually implementation sessions contain the most actionable insights).

### Step 3: Extract Insights

Based on the session analysis, identify:

- **Patterns worth documenting**: Reusable approaches or architectural decisions
- **Debugging techniques**: Methods that helped solve problems
- **Non-obvious solutions**: "Aha moments" that weren't immediately apparent
- **Gotchas**: Things that caused confusion or wasted time
- **Best practices**: Approaches that worked particularly well

### Step 4: Present Findings

Present a summary of insights to the user with specific examples from the sessions.

Then ask how they'd like to proceed:

- **Create documentation**: Write findings to `docs/learned/` following the learned-docs skill guidelines
- **Update existing docs**: Add insights to relevant existing documentation
- **Create extraction plan**: Create a more thorough extraction plan issue for deeper analysis
- **Just discuss**: Talk through findings without writing anything

### Tips

- Preprocessed sessions are in XML format with `<user>`, `<assistant>`, `<tool_use>`, and `<tool_result>` elements
- Look for `<tool_use>` elements to see what actions were taken
- Look for `<user>` elements to understand what was requested
- `<tool_result>` elements with errors often reveal the most useful insights
- The preprocessing deduplicates repeated content and filters noise for efficient analysis
