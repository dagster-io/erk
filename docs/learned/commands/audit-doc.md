---
title: /local:audit-doc Command
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

The `/local:audit-doc` command audits a `docs/learned/` markdown file against erk's documentation standards, providing structured recommendations for improvement.

## When to Use

Use `/local:audit-doc` when:

- **Creating new documentation** - Verify the file meets standards before committing
- **Updating existing docs** - Check that updates maintain quality
- **Identifying improvement areas** - Find specific issues to address
- **Learning doc patterns** - Understand what makes good erk documentation

## Typical Workflow

### 1. Write or Update Documentation

Create or modify a file in `docs/learned/`:

```bash
vim docs/learned/architecture/my-new-pattern.md
```

### 2. Run Audit

```bash
/local:audit-doc my-new-pattern.md
# or with full path
/local:audit-doc docs/learned/architecture/my-new-pattern.md
```

### 3. Review Findings

The command generates a compliance scorecard with:

- **PASS** - Fully compliant with standards
- **WARN** - Minor issues or room for improvement
- **FAIL** - Does not meet standards, needs correction

### 4. Apply Recommendations

Follow the numbered, prioritized recommendations to fix issues.

### 5. Re-Audit (Optional)

Run the audit again to verify improvements:

```bash
/local:audit-doc my-new-pattern.md
```

## Value Categories

The audit evaluates documentation across multiple dimensions:

### 1. Frontmatter Quality

- **read_when** triggers - Clear, specific conditions for loading the doc
- **tripwires** - Critical action-triggered warnings with CRITICAL: prefix
- **title** - Appropriate title when needed
- **Structure** - Valid YAML format

**Value:** Ensures documentation is discovered at the right time via `erk docs sync` indexing.

### 2. Content Structure

- **Headings hierarchy** - Proper H2/H3/H4 nesting
- **Code examples** - Realistic, complete examples
- **Before/After comparisons** - When documenting anti-patterns
- **Decision frameworks** - When documenting "when to use X vs Y"

**Value:** Makes documentation easy to scan and navigate.

### 3. Writing Style

- **Concise** - No unnecessary verbosity
- **Imperative** - "Use X" not "You should use X"
- **Specific** - Code references with line numbers (e.g., `file.py:123`)
- **Actionable** - Clear next steps

**Value:** Enables fast comprehension and immediate application.

### 4. Cross-References

- **Related Documentation** section - Links to related docs
- **Code references** - Paths to canonical implementations
- **Examples** - Links to real-world usage

**Value:** Connects documentation into a navigable knowledge graph.

### 5. Completeness

- **Tripwires for anti-patterns** - If documenting what NOT to do, add tripwire
- **Examples for all patterns** - Every pattern has at least one code example
- **Coverage of edge cases** - Common pitfalls documented

**Value:** Prevents users from hitting known issues.

## Audit Output Format

The command generates a structured report:

```markdown
## Doc Audit: <filename>

### Summary

[1-2 sentence overview of doc health and main areas for improvement]

### Compliance Scorecard

| Criterion        | Status         | Notes               |
| ---------------- | -------------- | ------------------- |
| Frontmatter      | PASS/WARN/FAIL | [Brief explanation] |
| Structure        | PASS/WARN/FAIL | [Brief explanation] |
| Writing Style    | PASS/WARN/FAIL | [Brief explanation] |
| Cross-References | PASS/WARN/FAIL | [Brief explanation] |
| Completeness     | PASS/WARN/FAIL | [Brief explanation] |

### Recommendations

1. [Most critical issue and how to fix it]
2. [Second priority item]
   ...

### Detailed Findings

[Expanded analysis for each criterion]
```

## Typical Issues Found

Based on PR #6625 analysis, common issues include:

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

**Problem:** Tripwire doesn't start with `CRITICAL:` or is too vague.

**Fix:** Make tripwires action-triggered and specific:

```yaml
tripwires:
  - "CRITICAL: Before creating a gateway without all 5 implementation layers"
```

### Missing Code Examples

**Problem:** Pattern described in text but no code example.

**Fix:** Add concrete before/after examples from the codebase.

### Broken Cross-References

**Problem:** Links to files that don't exist or are in wrong category.

**Fix:** Verify all links with `Read` tool before committing.

## Integration with Workflow

The audit command is designed to fit into the documentation creation workflow:

1. **Plan mode** - Decide what to document
2. **Write draft** - Create initial markdown file
3. **Audit** - Run `/local:audit-doc` to find issues
4. **Revise** - Apply recommendations
5. **Re-audit** - Verify improvements
6. **Commit** - Add to PR with `erk docs sync`

## Command Location

The command is implemented on branch PR #6625. Once merged, it will be available at:

```
.claude/commands/local/audit-doc.md
```

The implementation likely follows the `/local:audit-skill` pattern (see `.claude/commands/local/audit-skill.md` for reference structure).

## Related Documentation

- [Slash Command to Exec Migration](../cli/slash-command-exec-migration.md) - How slash commands work
- [Frontmatter Tripwire Format](../documentation/frontmatter-tripwire-format.md) - YAML schema for tripwires
- [Documentation Methodology](../documentation/) - Complete documentation guide
