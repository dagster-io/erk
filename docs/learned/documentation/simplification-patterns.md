---
title: Documentation Simplification Patterns
read_when:
  - auditing or cleaning up documentation
  - removing duplication from docs
  - deciding how to simplify an oversized or redundant doc
  - replacing code blocks with source pointers
tripwires:
  - action: "documenting implementation details that are derivable from code"
    warning: "Use source pointers instead of duplication. See simplification-patterns.md for the three simplification patterns."
  - action: "restructuring or deleting doc content"
    warning: "Run 'erk docs sync' after structural changes to regenerate indexes and fix broken cross-references."
last_audited: "2026-02-08"
audit_result: edited
---

# Documentation Simplification Patterns

Three patterns for reducing documentation maintenance burden, each targeting a different root cause of doc decay.

## Pattern Decision Table

| Symptom                                                                      | Pattern             | Core Action                                                         |
| ---------------------------------------------------------------------------- | ------------------- | ------------------------------------------------------------------- |
| Doc lists fields, methods, config options, or enum values that exist in code | Static → Dynamic    | Replace enumeration with source pointer                             |
| Same conceptual knowledge appears in 2+ docs                                 | Duplication Removal | Choose canonical location, replace others with cross-references     |
| Doc covers multiple distinct topics or exceeds ~100 lines                    | Scope Reduction     | Extract peripheral details into focused docs, keep cross-references |

## Pattern 1: Static → Dynamic Replacement

**Root cause**: Documentation enumerates things that code already defines — config fields, dataclass members, gateway methods, enum values.

**Why this decays**: Every code change silently invalidates the doc. No tooling detects the drift until an agent trusts the doc and uses an outdated field name or missing option.

**Fix**: Replace the enumeration with a source pointer to the authoritative definition. Point to the stable interface where the items are defined, not to an implementation that may change.

**Pointer target priority** (most stable first):

1. ABC classes and abstract methods
2. Schema/config model definitions (Pydantic, dataclasses)
3. Enum definitions
4. Concrete implementations (avoid unless no abstraction exists)

<!-- Source: packages/erk-shared/src/erk_shared/config/schema.py, GlobalConfigSchema -->

For example, listing config fields should become a pointer to `GlobalConfigSchema` in the config schema module rather than enumerating each field. Similarly, gateway method lists should point to the relevant ABC files under the gateway package.

See [source-pointers.md](source-pointers.md) for the exact pointer format.

### When the Code Artifact Doesn't Exist Yet

Pattern 1 assumes the code artifact already exists. When it doesn't — and the
learn pipeline proposes documenting an enumerable catalog — the correct action
is to **create the code artifact first**, then point to it. Don't document what
should be typed.

Examples of catalogs that belong as code artifacts:

- Error type catalogs → `Literal["type1", "type2", ...]` or Enum with docstring comments
- Status values → Literal or Enum
- Config option names → typed constants or TypedDict fields

A learn plan should propose a code change for these, not a documentation table.

## Pattern 2: Duplication Removal

**Root cause**: The same conceptual knowledge gets written independently in multiple docs because authors don't find the existing doc before writing.

**Why this decays**: When reality changes, some copies get updated and others don't. Agents find the stale copy and act on contradictory information — strictly worse than the information being absent entirely.

**Fix**: Choose one canonical location for the knowledge. Replace all other occurrences with a single-line cross-reference. The canonical location should be the doc where the topic is the _primary_ subject, not a supporting detail.

**Deduplication checklist**:

1. Grep `docs/learned/` for the duplicated concept before writing new content
2. If found, add a cross-reference to the existing doc instead of re-explaining
3. If multiple copies already exist, consolidate into the most topically appropriate doc
4. Replace all other occurrences with one-line pointers to the canonical doc

## Pattern 3: Scope Reduction

**Root cause**: A document accumulates coverage of adjacent topics over time, becoming a mini-encyclopedia rather than a focused reference.

**Why this decays**: Broad docs are expensive to maintain (changes to any covered topic require updating the omnibus doc) and expensive to read (agents searching for one topic load five unrelated sections, wasting context tokens).

**Fix**: Identify the doc's core topic. Extract peripheral sections into their own focused docs (or confirm they already exist elsewhere). Replace extracted content with cross-references.

**Scope test**: If a doc needs multiple headings at the "topic" level rather than the "subtopic" level, it's probably covering too much. Each doc should have one clear purpose that its title communicates.

## Anti-Patterns

**Over-simplifying**: Deleting "why" explanations because they aren't code-derived. Conceptual reasoning is the entire purpose of learned docs — only remove content that restates what code already communicates. See [audit-methodology.md](audit-methodology.md) for the classification distinction between HIGH VALUE and DUPLICATIVE.

**Pointing to volatile code**: Source pointers to implementation files that change frequently create a different maintenance problem. Always prefer pointing to ABCs, schemas, and config models — these stable interfaces survive refactoring.

**Simplifying without fixing references**: Removing or restructuring content breaks links from other docs, the index, and tripwires files. Always run `erk docs sync` after structural changes to regenerate cross-references.

## Related Documentation

- [audit-methodology.md](audit-methodology.md) — Audit process and classification framework
- [source-pointers.md](source-pointers.md) — Format for replacing code blocks with references
- [stale-code-blocks-are-silent-bugs.md](stale-code-blocks-are-silent-bugs.md) — The deeper case against embedded code
- [tripwires.md](tripwires.md) — Documentation category tripwires
