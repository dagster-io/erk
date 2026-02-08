---
audit_result: edited
last_audited: "2026-02-08"
read_when:
  - writing a learned doc whose topic overlaps with AGENTS.md or another learned doc
  - consolidating scattered knowledge about the same topic into one document
  - resolving conflicts between two docs that describe the same pattern differently
tripwires:
  - action: "declaring canonical authority in a learned doc"
    warning: "Authority without substance misleads. Only declare canonical authority if the doc is the comprehensive deep-dive, not a summary. If AGENTS.md has the abbreviated version and this doc has the full treatment, that's the right split."
  - action: "two learned docs claiming canonical authority over the same topic"
    warning: "Contradicts the purpose. Consolidate into one doc, or differentiate scope explicitly (e.g., 'canonical for hook patterns' vs 'canonical for command patterns')."
last_audited: "2026-02-08"
audit_result: regenerated
---

# Canonical Authority Declarations

## The Problem: Ambiguous Authority

Erk's documentation is layered: AGENTS.md has compressed quick-reference tables, skills provide on-demand deep dives, learned docs hold cross-cutting insight, and code has comments and docstrings. When the same topic appears at multiple layers, agents can't tell which version is definitive when they disagree. They waste tokens reading all sources and still guess wrong.

A canonical authority declaration resolves this by telling the reading agent "stop searching — this is the authoritative source for topic X." The abbreviated version in AGENTS.md is intentional; it's a routing pointer, not a competing document.

**Most docs don't need declarations.** The typical learned doc covers a topic that only appears in one place, making authority implicit. Declarations matter only when genuine ambiguity exists.

## Two Directions of Authority

Documentation authority flows in two directions, and conflating them causes confusion:

| Direction             | Meaning                                                                 | When to use                                                                                                           |
| --------------------- | ----------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| **Doc is canonical**  | This document is the definitive reference; other mentions are summaries | Topic spans multiple files, has nuance that code alone doesn't convey, or consolidates previously scattered knowledge |
| **Code is canonical** | The source code is authoritative; this doc just helps agents find it    | Pattern is stable, well-structured, and best understood by reading the implementation directly                        |

Most learned docs fall into the first category — they exist precisely because the insight can't live next to any single code artifact. The second category is for docs whose primary value is directing agents to the right source file rather than explaining the pattern itself.

## When to Declare Authority

Declare canonical authority when **all three** conditions hold:

1. **Multiple sources document the topic** — the pattern appears in AGENTS.md, code comments, and/or other learned docs
2. **The doc provides comprehensive treatment** — not a summary or stub, but the full deep-dive with edge cases and decision rationale
3. **Ambiguity would cost tokens** — without the declaration, an agent would reasonably keep searching

**Skip the declaration when:**

- The topic is unique to one document (no competing sources exist)
- The document is a reference list or index (authority is implicit from structure)
- The content is exploratory or observational, not definitive

## Placement and Phrasing

Place the declaration after the main explanation, before the "Related Documentation" section, as its own sentence or short paragraph. **Not in frontmatter** — frontmatter handles routing (`read_when`), not authority claims.

The distinction matters: `read_when` tells an agent _when to load_ the doc. A canonical authority declaration tells an agent that's _already reading_ to trust this source over alternatives.

## Relationship to Source Pointers

Canonical authority declarations and source pointers solve complementary problems:

- **Canonical authority** answers "which document should I trust?" — routing agents to the right doc
- **Source pointers** answer "where is the code?" — routing agents from docs to implementation

A well-structured doc declares its own authority over the cross-cutting insight, then uses source pointers to reference the implementations it discusses. The two mechanisms work together: the doc owns the "why," the code owns the "what." See [source-pointers.md](source-pointers.md) for pointer format.

## Anti-Patterns

### Authority Without Substance

A canonical declaration is a promise of comprehensive treatment. Three lines of explanation plus a canonical claim is worse than no declaration — agents stop searching and trust incomplete coverage, missing the real documentation elsewhere.

### Competing Declarations

Two docs each claiming to be "the canonical reference for session ID patterns" forces agents to read both and guess which is current. Fix by consolidating into one doc, or by explicitly differentiating scope (e.g., one doc owns hook-side patterns, the other owns command-side patterns).

### Declaration Inflation

When every document declares itself canonical, the signal loses meaning. Reserve declarations for topics where agents would otherwise reasonably search multiple locations. If a topic only lives in one doc, the doc is already authoritative by default.

## Related Documentation

- [source-pointers.md](source-pointers.md) — format for referencing source code without reproducing it
- [stale-code-blocks-are-silent-bugs.md](stale-code-blocks-are-silent-bugs.md) — why source pointers prevent documentation drift
- [simplification-patterns.md](simplification-patterns.md) — duplication removal patterns that often require authority decisions
