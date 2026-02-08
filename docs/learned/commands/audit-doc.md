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

## Collateral Findings

The Read Referenced Source Code phase of the audit command collects collateral findings — issues in _other_ files discovered while reading source code for the primary audit. See the Read Referenced Source Code and Verify System Descriptions phases in `.claude/commands/local/audit-doc.md` for full collection logic.

### Two Tiers

**Conceptual (highest danger — actively misleads agents):**

| Category           | Abbrev | Found In   | Description                                         |
| ------------------ | ------ | ---------- | --------------------------------------------------- |
| `OBSOLETE_SYSTEM`  | OS     | Other docs | Doc describes a system that was replaced or removed |
| `CONCEPTUAL_DRIFT` | CF     | Other docs | Doc uses terms whose meaning has changed            |
| `STALE_FLOW`       | SF     | Other docs | Multi-step flow where steps have changed            |

Conceptual findings are **discovery-only**. They are never auto-fixed — the agent outputs a recommendation to run a separate `/local:audit-doc` on the affected file. These are too significant for inline correction because they require a full audit pass to fix correctly.

**Mechanical (lower danger — wrong details in otherwise-correct context):**

| Category            | Abbrev | Found In     | Description                                    |
| ------------------- | ------ | ------------ | ---------------------------------------------- |
| `STALE_COMMENT`     | SC     | Source files | Comment doesn't match code behavior            |
| `STALE_DOCSTRING`   | SD     | Source files | Docstring doesn't match signatures/behavior    |
| `BROKEN_CROSS_REF`  | BX     | Other docs   | Link points to renamed/deleted file            |
| `CONTRADICTING_DOC` | CD     | Other docs   | Cross-referenced doc claims conflict with code |

Mechanical findings can be auto-fixed directly.

### Report Format

Collateral findings appear after the primary audit summary, grouped by severity (conceptual first, then mechanical). Each entry shows the abbreviated category tag, file path, and a one-line description with suggested action. See the Generate Report phase in `.claude/commands/local/audit-doc.md` for the exact output format.

### Auto-apply vs Interactive

See the Determine Action phase in `.claude/commands/local/audit-doc.md` for authoritative auto-apply and interactive mode behavior.

## Related Documentation

- [Frontmatter Tripwire Format](../documentation/frontmatter-tripwire-format.md) - YAML schema for tripwires
- [Documentation Methodology](../documentation/) - Complete documentation guide
