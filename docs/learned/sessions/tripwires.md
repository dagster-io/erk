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

**CRITICAL: Before checking entry['type'] == 'tool_result' in Claude session JSONL** → Read [Claude Code JSONL Schema Reference](jsonl-schema-reference.md) first. tool_results are content blocks INSIDE user entries, NOT top-level entry types. Check message.content[].type == 'tool_result' within user entries instead. Load session-inspector skill for correct schema.

**CRITICAL: Before working with session-specific data** → Read [Parallel Session Awareness](parallel-session-awareness.md) first. Multiple sessions can run in parallel. NEVER use "most recent by mtime" for session data lookup - always scope by session ID.
