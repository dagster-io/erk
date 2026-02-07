---
title: Claude Code JSONL Schema Reference
read_when:
  - "parsing Claude Code session files"
  - "understanding JSONL entry types"
  - "extracting data from session logs"
  - "building tools that process session transcripts"
  - "debugging session parsing issues"
redirect_to: "/.claude/skills/session-inspector/"
tripwires:
  - action: "checking entry['type'] == 'tool_result' in Claude session JSONL"
    warning: "tool_results are content blocks INSIDE user entries, NOT top-level entry types. Check message.content[].type == 'tool_result' within user entries instead. Load session-inspector skill for correct schema."
---

# Claude Code JSONL Schema Reference

**Source of Truth:** Load the `session-inspector` skill for authoritative JSONL schema documentation.

```
Skill: session-inspector
Location: .claude/skills/session-inspector/
Reference: .claude/skills/session-inspector/references/format.md
```

## Why This Redirect?

The JSONL schema documentation has been consolidated into the `session-inspector` skill because:

1. **Agents need it when working** - Skills are loaded on-demand when agents are actively parsing sessions
2. **Single source of truth** - Prevents documentation drift between learned docs and skills
3. **Operational guidance** - The skill includes code examples and common patterns

## Quick Reference

**⚠️ CRITICAL: Tool results are NOT top-level entries.**

Tool results appear as `content[].type = "tool_result"` blocks INSIDE `user` entries:

```json
{
  "type": "user",
  "message": {
    "content": [
      {
        "type": "tool_result",
        "tool_use_id": "toolu_abc123",
        "content": "Tool output..."
      }
    ]
  }
}
```

**Common mistake:** Code that checks `entry["type"] == "tool_result"` will never match.

## Entry Types (Summary)

| Type                    | Description                                      |
| ----------------------- | ------------------------------------------------ |
| `user`                  | Human input AND tool results (as content blocks) |
| `assistant`             | Claude responses with text and tool_use blocks   |
| `summary`               | Context compaction markers                       |
| `system`                | Notifications and system events                  |
| `file-history-snapshot` | File state tracking                              |
| `queue-operation`       | Message queue manipulations                      |

For complete schema details, load the `session-inspector` skill.

## Related Documentation

- [Session Layout](./layout.md) - Directory structure and file organization
- [Session Hierarchy](./session-hierarchy.md) - Understanding session relationships
