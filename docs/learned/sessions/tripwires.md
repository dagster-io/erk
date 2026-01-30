---
title: Sessions Tripwires
read_when:
  - "working on sessions code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from sessions/*.md frontmatter -->

# Sessions Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before accessing planning session in learn workflow** → Read [Session File Lifecycle and Persistence](lifecycle.md) first. Session files are session-scoped, not persistent across Claude Code sessions. If planning session is unavailable, implement fallback strategy using available sessions.

**CRITICAL: Before analyzing large sessions** → Read [Session Preprocessing](preprocessing.md) first. Sessions exceeding 20,000 tokens are automatically chunked into multi-part files. Analysis must detect and handle chunking (.part1.jsonl, .part2.jsonl, etc.). Check for part files when base session file is missing.

**CRITICAL: Before checking entry['type'] == 'tool_result' in Claude session JSONL** → Read [Claude Code JSONL Schema Reference](jsonl-schema-reference.md) first. tool_results are content blocks INSIDE user entries, NOT top-level entry types. Check message.content[].type == 'tool_result' within user entries instead. Load session-inspector skill for correct schema.

**CRITICAL: Before looking up session files from metadata** → Read [Session Preprocessing](preprocessing.md) first. Session IDs in metadata may not match available local files. Verify session paths exist before preprocessing. Use LBYL checks and provide clear error messages when sessions are missing.

**CRITICAL: Before reading or extracting data from agent session files** → Read [Agent Session Files](agent-session-files.md) first. Agent session files use `agent-` prefix and require dedicated reading logic. Check `session_id.startswith("agent-")` and route to `_read_agent_session_entries()`. Using generic `_iter_session_entries()` skips agent files silently.

**CRITICAL: Before working with session-specific data** → Read [Parallel Session Awareness](parallel-session-awareness.md) first. Multiple sessions can run in parallel. NEVER use "most recent by mtime" for session data lookup - always scope by session ID.
