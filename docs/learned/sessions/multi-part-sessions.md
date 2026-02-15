---
title: Multi-Part Sessions
read_when:
  - "working with session JSONL files"
  - "preprocessing long sessions"
  - "session files split across multiple parts"
  - "concatenating session data"
---

# Multi-Part Sessions

Long Claude Code sessions may split into multiple JSONL files. This affects session preprocessing and analysis.

## File Naming

Sessions are stored in `~/.claude/projects/` with this naming pattern:

| File                       | Description          |
| -------------------------- | -------------------- |
| `{session-id}.jsonl`       | Primary session file |
| `{session-id}.part2.jsonl` | Second part          |
| `{session-id}.part3.jsonl` | Third part, etc.     |

## Impact on Preprocessing

The `erk exec preprocess-session` command and the learn pipeline's `_preprocess_session_direct()` must handle multi-part sessions:

1. **Discovery:** Look for all files matching `{session-id}*.jsonl` pattern
2. **Concatenation:** Parts must be joined in order before analysis
3. **Token counts:** Total token usage spans all parts

## Impact on Session Analysis

- Session analysis agents receive concatenated content, not individual parts
- The preprocessing pipeline handles concatenation transparently
- Downstream agents don't need to know about multi-part splitting

## Detection

To check if a session has multiple parts:

```bash
ls ~/.claude/projects/*/sessions/{session-id}*.jsonl
```

If multiple files match, the session is multi-part.

## Related Documentation

- [Session Preprocessing Architecture](../planning/session-preprocessing.md) - Preprocessing pipeline
- [Learn Workflow](../planning/learn-workflow.md) - How sessions feed into learn pipeline
