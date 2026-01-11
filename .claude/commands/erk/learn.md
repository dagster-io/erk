---
description: Extract insights from plan-associated sessions
argument-hint: "<issue-number>"
---

# /erk:learn

Extract insights from Claude Code sessions associated with a plan implementation.

## Usage

```
/erk:learn 4655
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

If no readable sessions are found, inform the user and stop.

### Step 2: Read Session Content

For each readable session path, read the session log to understand what happened during that session:

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

- Session files are JSONL format - each line is a JSON object representing a message or tool call
- Look for `type: "assistant"` entries with tool calls to see what actions were taken
- Look for `type: "user"` entries to understand what was requested
- Error messages and retries often reveal the most useful insights
