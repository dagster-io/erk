# Plan: Add `doc-audit` Review to `.github/reviews/`

## Goal

Create a new review file at `.github/reviews/doc-audit.md` that automatically audits any `docs/learned/` document added or edited in a PR for duplicative content.

## Approach: Reference audit-doc as single source of truth

The review will instruct Claude to **read `.claude/commands/local/audit-doc.md`** and apply its Phases 2-4 (Extract Code References, Read Referenced Source Code, Adversarial Analysis) to each changed doc file. The audit-doc command remains the canonical definition of the classification logic. The review is a thin wrapper that adapts the output format to inline PR comments and a summary table.

**No new shared files needed.** Just one new file: `.github/reviews/doc-audit.md`.

## Complements existing `learned-docs` review

The existing `learned-docs.md` review checks for **verbatim source code copies** in code blocks. This new review checks for **duplicative documentation** — sections that restate what code communicates through signatures, docstrings, and structure. Different concerns, no overlap.

## File to create: `.github/reviews/doc-audit.md`

### Frontmatter

```yaml
---
name: Doc Audit Review
paths:
  - "docs/learned/**/*.md"
marker: "<!-- doc-audit-review -->"
model: claude-haiku-4-5
timeout_minutes: 30
allowed_tools: "Bash(gh:*),Bash(erk exec:*),Read(*)"
enabled: true
---
```

### Steps

**Step 1**: Get PR diff, filter to `docs/learned/**/*.md`, read each changed file fully.

**Step 2**: Read `.claude/commands/local/audit-doc.md` to load the audit methodology.

**Step 3**: For each changed doc, apply audit-doc Phases 2-4:
- Phase 2: Extract code references from the doc
- Phase 3: Read referenced source code
- Phase 4: Adversarial section-by-section classification (DUPLICATIVE / DRIFT RISK / HIGH VALUE / CONTEXTUAL / EXAMPLES)

Only analyze sections on `+` lines in the diff (new/modified content).

**Step 4**: Post inline comments for DUPLICATIVE and DRIFT RISK sections:

```
**Doc Audit**: [DUPLICATIVE] — This section restates [what].

Source: `path:line`

Suggested fix: Replace with code reference:
> See `Symbol` in `path:line`.
```

**Step 5**: Post summary comment with per-file verdict table and activity log.

```
### Doc Audit Review

| File | Verdict | Duplicative % | High Value % | Comments |
|------|---------|---------------|-------------|----------|
| `docs/learned/foo.md` | SIMPLIFY | 60% | 30% | 3 |

### Activity Log
- [timestamp] ...
```

### Key design notes

1. Only audit `+` lines — don't flag pre-existing content
2. The audit-doc command is the source of truth for classification logic
3. Verdicts: KEEP / SIMPLIFY / REPLACE WITH CODE REFS / CONSIDER DELETING
4. Each inline comment includes the specific source location making the section redundant

## Verification

- Confirm frontmatter schema matches other reviews (name, paths, marker, model, timeout_minutes, allowed_tools, enabled)
- Confirm marker `<!-- doc-audit-review -->` is unique across all review files
- Confirm inline comment format follows the `**Review Name**: ...` convention