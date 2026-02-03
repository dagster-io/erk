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
last_audited: "2026-02-03 04:00 PT"
audit_result: edited
---

# Claude Code JSONL Schema Reference

This document redirects to the `session-inspector` skill, which is the single source of truth for JSONL schema documentation.

**Load:** `session-inspector` skill | **Reference:** `.claude/skills/session-inspector/references/format.md`

## Related Documentation

- [Session Layout](./layout.md) - Directory structure and file organization
- [Session Hierarchy](./session-hierarchy.md) - Understanding session relationships
