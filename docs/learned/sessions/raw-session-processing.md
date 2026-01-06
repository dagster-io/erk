---
title: Raw Session Issue Processing
read_when:
  - "processing issues with erk-raw-session label"
  - "extracting documentation from landed PR sessions"
  - "understanding raw session issue format"
---

# Raw Session Issue Processing

Raw session issues capture session context from landed PRs for future documentation extraction.

## What Are Raw Session Issues?

When a PR is landed with `erk pr land --extract`, the session context is:

1. Preprocessed into XML format
2. Uploaded to a GitHub issue as comments
3. Labeled with `erk-raw-session` and `erk-plan`

## Issue Structure

The issue body contains:

- Session metadata (branch name, session IDs)
- Instructions for processing

The issue comments contain:

- `<!-- erk:metadata-block:session-content -->` blocks
- Collapsible `<details>` sections with session XML
- Key implementation highlights (if truncated)

## Processing Workflow

### Option 1: Automated via /erk:create-extraction-plan

Run from a worktree created for the issue:

```bash
/erk:create-extraction-plan
```

This analyzes the session XML and generates documentation suggestions.

### Option 2: Manual via /erk:system:impl-execute

If an implementation plan already exists:

```bash
/erk:system:impl-execute
```

This executes the extraction analysis framework directly.

## Extraction Analysis Framework

Apply two-category analysis:

**Category A (Learning Gaps):**

- Documentation that would have made the original session faster
- Usually skills, patterns, or architectural guidance

**Category B (Teaching Gaps):**

- Documentation for what was built in the session
- Usually reference docs, command documentation, glossary entries

## Related Documentation

- [Session Logs](tools.md) - Understanding session log format
- [Parallel Session Awareness](parallel-session-awareness.md) - Session ID scoping
