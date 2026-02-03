---
title: /local:audit-doc Command
last_audited: "2026-02-03 03:56 PT"
audit_result: edited
tripwires:
  - action: "creating or modifying docs/learned/ markdown files without checking quality"
    warning: "Run /local:audit-doc to verify frontmatter, structure, and completeness before committing."
read_when:
  - "Running the /local:audit-doc command"
  - "Understanding documentation quality standards"
  - "Auditing docs/learned/ files for compliance"
---

# /local:audit-doc Command

## Overview

The `/local:audit-doc` command audits a `docs/learned/` markdown file against erk's documentation standards. The command itself is defined in `.claude/commands/local/audit-doc.md`.

## Usage

```bash
/local:audit-doc docs/learned/architecture/my-pattern.md
/local:audit-doc architecture/my-pattern.md   # relative to docs/learned/
```

## Typical Issues Found

Based on real audit experience, common issues include:

### Missing read_when Triggers

**Problem:** Frontmatter has no `read_when` field, making the doc hard to discover.

**Fix:** Add specific triggers:

```yaml
---
read_when:
  - "implementing gateway abstractions"
  - "working with 5-layer gateway pattern"
---
```

### Weak Tripwires

**Problem:** Tripwire doesn't use structured format or is too vague.

**Fix:** Make tripwires action-triggered and specific. See [Frontmatter Tripwire Format](../documentation/frontmatter-tripwire-format.md) for the required schema.

### Missing Code Examples

**Problem:** Pattern described in text but no code example.

**Fix:** Add concrete before/after examples from the codebase.

### Broken Cross-References

**Problem:** Links to files that don't exist or are in wrong category.

**Fix:** Verify all links with `Read` tool before committing.

## Related Documentation

- [Frontmatter Tripwire Format](../documentation/frontmatter-tripwire-format.md) - YAML schema for tripwires
- [Documentation Methodology](../documentation/) - Complete documentation guide
