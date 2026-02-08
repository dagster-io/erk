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

**CRITICAL: Before analyzing large sessions** → Read [Session Preprocessing](preprocessing.md) first. Sessions exceeding 20,000 tokens are automatically chunked into multi-part files. Analysis must detect and handle chunking (.part1.jsonl, .part2.jsonl, etc.). Check for part files when base session file is missing.

**CRITICAL: Before assuming a session ID from metadata corresponds to a file on disk** → Read [Session Discovery and Fallback Patterns](discovery-fallback.md) first. Claude Code manages session lifecycle; old sessions may be cleaned up. Always use LBYL discovery before reading.

**CRITICAL: Before checking entry['type'] == 'tool_result' in Claude session JSONL** → Read [Claude Code JSONL Schema Reference](jsonl-schema-reference.md) first. tool_results are content blocks INSIDE user entries, NOT top-level entry types. Check message.content[].type == 'tool_result' within user entries instead. Load session-inspector skill for correct schema.

**CRITICAL: Before constructing session file paths manually** → Read [Session File Lifecycle and Persistence](lifecycle.md) first. Use ClaudeInstallation ABC methods, not manual path construction. Storage layout is an implementation detail that may change.

**CRITICAL: Before failing a workflow because a session file is missing** → Read [Session File Lifecycle and Persistence](lifecycle.md) first. Missing sessions must never cause hard failure. Degrade through the fallback hierarchy: planning → implementation → gist → local scan → skip.

**CRITICAL: Before looking up session files from metadata** → Read [Session Preprocessing](preprocessing.md) first. Session IDs in metadata may not match available local files. Verify session paths exist before preprocessing. Use LBYL checks and provide clear error messages when sessions are missing.

**CRITICAL: Before reading or extracting data from agent session files** → Read [Agent Session Files](agent-session-files.md) first. Agent session files use `agent-` prefix and require dedicated reading logic. Check `session_id.startswith("agent-")` and route to `_read_agent_session_entries()`. Using generic `_iter_session_entries()` skips agent files silently.

**CRITICAL: Before using get-session-metadata or get-session-for-issue exec commands** → Read [Session Discovery and Fallback Patterns](discovery-fallback.md) first. These commands do not exist. Use 'erk exec list-sessions' for general enumeration or 'erk exec get-learn-sessions' for plan-specific discovery.

**CRITICAL: Before working with session-specific data** → Read [Parallel Session Awareness](parallel-session-awareness.md) first. Multiple sessions can run in parallel. NEVER use "most recent by mtime" for session data lookup - always scope by session ID.
