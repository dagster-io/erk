# Plan: Restructure learned-docs Skill as Single Source of Truth

## Context

Documentation quality standards are scattered across four files that each embed their own version of "what makes a good learned doc":
- `learned-docs/SKILL.md` — 130 lines of code-in-docs rules
- `audit-doc.md` — value taxonomy (DUPLICATIVE/HIGH VALUE/etc.), code block triage
- `learn.md` — philosophy (token caches, document reality, bias toward capturing)
- `learned-docs.md` (review) — verbatim detection criteria

This creates duplication, inconsistency, and makes it hard to answer "what's the standard?" The goal is a single source of truth modeled after how `dignified-python` works: a core rules doc that consumers reference.

Key decisions from discussion:
- **Rules, not taxonomy** — the value categories are audit-doc's reporting shorthand, not project-wide standards
- **Cornerstone** — learned docs are for cross-cutting insight that can't live next to any single code artifact
- **Knowledge hierarchy** — code comment > docstring > learned doc (escalation path, not default)
- **Simplified code block rules** — one rule + four exceptions
- **GitHub review deferred** — leave `.github/reviews/learned-docs.md` as-is

## Changes

### 1. CREATE `.claude/skills/learned-docs/learned-docs-core.md`

New file, ~100-120 lines. The single source of truth for content quality standards. Structure:

```
# Learned Documentation - Content Quality Standards

## The Cornerstone
- Learned docs exist for cross-cutting insight that can't live next to any single code artifact
- Knowledge placement hierarchy: code comment > docstring > learned doc

## Audience and Purpose
- Docs are for AI agents, not humans ("token caches")
- Document reality, not aspiration
- Bias toward capturing
- Reject dismissiveness

## Content Rules
- Explain why, not what (CORRECT/WRONG examples)
- Cross-cutting insight is the sweet spot
- Anti-patterns earn their keep

## The One Code Rule
- Never reproduce source code
- Four exceptions: data formats, third-party APIs, anti-patterns, input/output examples
- When in doubt: "Could an agent get this by reading the source?" → source pointer
- Reference docs/learned/documentation/source-pointers.md for format

## What Belongs vs What Doesn't
- Belongs: decision tables, anti-patterns, cross-cutting patterns, historical context, tripwires
- Doesn't: import paths, function signatures, docstring paraphrases, file listings, code duplicating source

## See Also
- docs/learned/documentation/source-pointers.md
- docs/learned/documentation/stale-code-blocks-are-silent-bugs.md
```

### 2. MODIFY `.claude/skills/learned-docs/SKILL.md`

- **ADD** `@learned-docs-core.md` under new "Core Knowledge (ALWAYS Loaded)" section (after frontmatter/overview, before Document Registry)
- **REMOVE** "Code in Documentation" section (lines 158-287, ~130 lines) — now replaced by the concise rules in core doc
- **KEEP** everything else: frontmatter requirements, categories, document structure template, index template, reorganization steps, routing tables, validation, generated files

### 3. MODIFY `.claude/commands/local/audit-doc.md`

- **ADD** prerequisite at top of Phase 1: "Load the `learned-docs` skill for content quality standards"
- **Phase 4** (lines 122-182): Keep the category table (DUPLICATIVE/STALE/etc.) as reporting labels. Remove the three verbose "Specific things to flag as..." blocks (~47 lines). Replace each with a one-line reference to the skill's rules
- **Phase 4.5** (lines 184-201): Keep the triage table (ANTI-PATTERN/CONCEPTUAL/VERBATIM/TEMPLATE). Remove the verbose "Default action for VERBATIM blocks" paragraph. Replace with reference to skill's code block rules
- **KEEP** all procedural phases (1-3, 3.5, 5-7b), output formats, collateral findings, design principles

### 4. MODIFY `.claude/commands/erk/learn.md`

- **ADD** prerequisite at top of Agent Instructions: "Load the `learned-docs` skill for content quality standards"
- **REPLACE** "Purpose" section (lines 18-28) with a brief 2-3 line summary referencing the skill for full philosophy
- **KEEP** all 11 procedural steps, agent dependency graph, tips

## Order of Operations

1. Create `learned-docs-core.md` (no dependencies)
2. Modify `SKILL.md` (add @reference, remove code-in-docs section)
3. Modify `audit-doc.md` (add prerequisite, simplify Phase 4/4.5)
4. Modify `learn.md` (add prerequisite, condense Purpose)

## Verification

1. Run `make fast-ci` — catches YAML, markdown formatting, broken links
2. Grep for key phrases to confirm single-source:
   - "token caches" → only in `learned-docs-core.md` (learn.md has brief mention)
   - "bias toward capturing" → only in `learned-docs-core.md`
   - "Never reproduce source code" → only in `learned-docs-core.md`
3. Read each modified file end-to-end to confirm coherence