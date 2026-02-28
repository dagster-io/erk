---
title: Subagent Output Handling
read_when:
  - "working with Task agent output that produces persisted-output markers"
  - "debugging missing JSON from a Task agent result"
  - "building workflows that process structured output from subagents"
tripwires:
  - action: "using Read tool or grep on a persisted-output file path from a Task agent"
    warning: "Persisted output files contain raw agent transcripts, not clean JSON. Use Python JSON parsing on the actual output content, not file reads on the persisted path."
---

# Subagent Output Handling

When Task agents produce large structured output (JSON, long lists), Claude Code may persist the output to a file instead of returning it inline. This creates `persisted-output` markers in the result instead of the expected content.

## When This Occurs

- Commit categorizer agent producing categorized commit lists
- Any Task agent producing more than ~100 lines of structured output
- Agents that return large JSON objects

## The Problem

The persisted-output file contains the full agent transcript, not just the clean output. Trying to `Read` or `grep` the file path treats the raw transcript as data.

## Correct Pattern

Use Python JSON parsing to handle the structured output:

```python
import json
# Parse the JSON content directly from the agent's output
data = json.loads(output_content)
```

Do not use `Read` tool, `cat`, or `grep` on persisted-output file paths — they contain agent transcripts that include tool calls, system messages, and other non-data content.

## Related Documentation

- [Session Inspector](../sessions/) — Understanding session log formats
