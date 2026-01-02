---
title: Context Window Analysis
read_when:
  - "analyzing context consumption"
  - "debugging context window blowout"
  - "understanding why session ran out of context"
---

# Context Window Analysis

Guide for analyzing what consumes context during Claude Code sessions and identifying optimization opportunities.

## What Consumes Context

### Under Your Control

These can be optimized through documentation and command design:

| Consumer      | Typical Size | Optimization Strategy                                                                  |
| ------------- | ------------ | -------------------------------------------------------------------------------------- |
| Command text  | 5-15K chars  | Extract to `@` docs (see [Command Optimization](../commands/optimization-patterns.md)) |
| Skill content | 3-8K chars   | Modular sections, load on demand                                                       |
| Agent prompts | 2-5K chars   | Use subagents for isolation                                                            |
| AGENTS.md     | 2-4K chars   | Keep routing-focused, link to detailed docs                                            |

### Intrinsic to Claude Code

These are determined by Claude Code's implementation:

| Consumer               | Notes                                       |
| ---------------------- | ------------------------------------------- |
| Read tool output       | Returns full file content with line numbers |
| Glob tool output       | Returns all matching paths                  |
| Edit confirmations     | Returns diff-style confirmation             |
| Tool result formatting | XML wrapping, metadata                      |

## Subagent Context Isolation

**Key insight**: Task tool with subagents runs in isolated context. Only the final summary returns to parent.

```
Parent session receives:
  "Agent completed. Found 3 type errors in src/cli.py, fixed all."

NOT the full subprocess output:
  [10KB of ty output]
  [5KB of file reads]
  [3KB of edits]
```

This makes subagents (devrun, Explore, Plan) highly efficient for:

- CI iteration (devrun consumes tool output, returns summary)
- Codebase exploration (Explore consumes reads, returns findings)
- Complex reasoning (Plan consumes exploration, returns plan)

## Quick Analysis: jq Recipe

To analyze a session log for context consumption:

```bash
# Find your session log
SESSION_LOG=~/.claude/projects/-Users-<path>/<session-id>.jsonl

# Sum tool_result content sizes by tool name
cat "$SESSION_LOG" | jq -s '
  [.[] | select(.type == "tool_result") |
   {size: (.message.content[0].text // "" | length)}] |
  group_by(.size) |
  map({count: length, total_chars: (map(.size) | add)}) |
  add
'
```

For detailed breakdown by tool type, look at the preceding assistant message's `tool_use` entries.

## Quick Analysis: /erk:analyze-context

The easiest way to analyze context consumption is the slash command:

```bash
/erk:analyze-context
```

This analyzes all sessions in the current worktree and outputs:

- **Summary metrics**: Sessions analyzed, peak context window, cache hit rate
- **Token breakdown by category**: File reads, assistant responses, tool results, skill expansions, etc.
- **Duplicate file reads**: Files read multiple times across sessions with wasted token estimates

## Analysis Workflow

### 1. Locate Session Log

Session logs live in `~/.claude/projects/<encoded-path>/`:

- Path encoding: `/` → `-`, `.` → `-`, prepend `-`
- Example: `/Users/foo/.erk/repos/erk` → `-Users-foo--erk-repos-erk`

See [layout.md](layout.md) for complete format reference.

### 2. Parse Tool Results

```python
import json
from collections import defaultdict

def analyze_session(session_file: Path) -> dict[str, int]:
    """Sum tool result sizes by tool type."""
    tool_sizes: dict[str, int] = defaultdict(int)

    with open(session_file) as f:
        for line in f:
            entry = json.loads(line)
            if entry.get("type") == "tool_result":
                content = entry.get("message", {}).get("content", [])
                size = sum(len(c.get("text", "")) for c in content)
                # Tool type requires looking at preceding tool_use
                tool_sizes["total"] += size

    return dict(tool_sizes)
```

### 3. Identify Top Consumers

Common patterns and their causes:

| Pattern                   | Likely Cause        | Solution                                  |
| ------------------------- | ------------------- | ----------------------------------------- |
| Large Read results (>50%) | Reading many files  | Use Explore agent, read selectively       |
| Large Glob results (>20%) | Broad patterns      | Narrow patterns, use Task for exploration |
| Command text (>10%)       | Bloated commands    | Extract to `@` docs                       |
| Repeated tool calls       | Same info requested | Cache in working memory                   |

## Common Optimization Patterns

### Pattern: Extract Command Reference Material

Before (13K command):

```markdown
### Step 4: Execute phases

[2000 chars of detailed execution steps]
[700 chars of coding standards table]
[500 chars of testing guidance]
```

After (7K command + 3.5K external doc):

```markdown
### Step 4: Execute phases

@docs/execution-guide.md
```

See [Command Optimization](../commands/optimization-patterns.md) for complete pattern.

### Pattern: Use Subagent for Exploration

Before (50K in parent context):

```
Read file1.py (10K)
Read file2.py (15K)
Grep pattern (5K results)
Read file3.py (20K)
```

After (2K in parent context):

```
Task(subagent_type="Explore", prompt="Find how X is implemented")
→ Returns: "X is implemented in file2.py:45-80, uses Y pattern"
```

### Pattern: Targeted Reads Over Broad Globs

Before:

```
Glob **/*.py → 200 files
Read 10 files looking for pattern
```

After:

```
Grep "specific_pattern" → 3 files
Read those 3 files
```

## Related Documentation

- [layout.md](layout.md) - Session log format reference
- [Command Optimization](../commands/optimization-patterns.md) - The `@` reference pattern
- [tools.md](tools.md) - CLI tools for session inspection
- [Context Optimization](context-optimization.md) - Patterns for reducing context waste
