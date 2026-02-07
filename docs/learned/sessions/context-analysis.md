---
title: Context Window Analysis
read_when:
  - "analyzing context consumption"
  - "debugging context window blowout"
  - "understanding why session ran out of context"
last_audited: "2026-02-07 18:30 PT"
audit_result: edited
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

## Quick Analysis

The easiest way to analyze context consumption is the `/local:analyze-context` slash command, which analyzes all sessions in the current worktree and reports token breakdown by category, duplicate file reads, and cache hit rates.

For manual analysis with jq or CLI tools, see [tools.md](tools.md) which has complete recipes for counting tool calls by type, finding large tool results, and debugging session blowouts.

For session log format and location details, see [layout.md](layout.md).

## Identifying Top Consumers

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
