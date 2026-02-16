---
title: Batch File Editing Threshold
description: When to use sed/Bash for bulk file changes vs Edit tool
read_when:
  - more than 30 files need identical changes
  - mechanical find-replace across many files
  - batch format updates
last_audited: "2026-02-16 00:00 PT"
audit_result: clean
---

# Batch File Editing Threshold

## The Rule

When **>30 files** need identical mechanical changes, delegate to Bash subagent with sed/awk/find.

## Why

- 122 files via sed: ~21 seconds
- 122 files via Edit tool: ~122 individual tool calls, several minutes, clutters conversation

## Pattern

```bash
# Example: Update date format in all markdown files
find docs/learned -name "*.md" -exec sed -i 's/YYYY-MM-DD$/YYYY-MM-DD HH:MM PT/g' {} +
```

## Verification

After bulk edits, always verify:

1. Zero matches for old pattern: `grep -r "old_pattern" docs/`
2. Expected matches for new pattern: `grep -r "new_pattern" docs/ | wc -l`

## Threshold Justification

- <10 files: Edit tool is fine
- 10-30 files: Edit tool acceptable, sed optional
- \>30 files: sed strongly preferred for efficiency

## Example

<!-- Source: src/erk/agent_docs/operations.py, _validate_last_audited_format -->

See `_validate_last_audited_format()` migration in `src/erk/agent_docs/operations.py` for an example of a format migration applied across 100+ files.
