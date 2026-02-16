---
title: Stale Code Blocks Are Silent Bugs
read_when:
  - documenting implementation patterns with code examples
  - deciding whether to include verbatim code in docs
  - reviewing docs that contain embedded source code
  - understanding why erk enforces source pointers over code blocks
tripwires:
  - action: "copying erk source code into a docs/learned/ markdown file"
    warning: "Verbatim source in docs silently goes stale. Use a source pointer instead — see source-pointers.md."
  - action: "adding a code block longer than a few lines to a learned doc"
    warning: "Check if this falls under the One Code Rule exceptions (data formats, third-party APIs, anti-patterns, I/O examples). If not, use a source pointer."
last_audited: "2026-02-08 00:00 PT"
audit_result: clean
---

# Stale Code Blocks Are Silent Bugs

This document explains _why_ erk treats embedded source code in `docs/learned/` as a defect — not a style issue. It captures the reasoning behind the One Code Rule and the enforcement system that makes it practical. For the replacement format, see [source-pointers.md](source-pointers.md). For audit classification details, see [audit-methodology.md](audit-methodology.md).

## The Asymmetry That Makes Stale Docs Worse Than No Docs

Code in source files lives inside feedback loops: tests fail, type checkers flag mismatches, linters catch drift, and runtime errors surface problems. Code blocks in markdown have **zero feedback loops**. When the source changes, the doc copy stays frozen, and nothing flags the divergence.

This asymmetry is the crux of the problem. An agent with _no_ documentation will read the source and discover the current pattern. An agent with _stale_ documentation will copy the outdated pattern from the doc, fully confident it's correct because it appeared in an authoritative context. The doc's authority turns from asset to liability the moment its content drifts.

An early audit round found 11 phantom type definitions across 10 documents — classes, dataclasses, and enums that docs referenced but that had been removed from the codebase. Agents importing these phantom types got cryptic failures rather than a clear "this doesn't exist." That discovery motivated the shift from optional best-practice to enforced policy.

## Fail-Loud vs Fail-Silent: The Core Design Choice

The source pointer system exists to convert a silent failure into a loud one:

| Failure mode         | Detection                                   | Agent impact                                         |
| -------------------- | ------------------------------------------- | ---------------------------------------------------- |
| Stale code block     | None — appears correct                      | Agent copies wrong pattern with full confidence      |
| Stale source pointer | Obvious — symbol or file path doesn't match | Agent reads actual source, discovers current pattern |

A source pointer that drifts is a minor inconvenience — the agent navigates to the file and finds the right symbol nearby. A code block that drifts is an active hazard — the agent implements the wrong pattern and believes it's canonical.

This is also why name-based pointers (`ClassName.method_name`) are preferred over line-range pointers: symbol names survive refactoring, while line numbers shift on any edit. The pointer format trades a small readability cost for a large reliability gain.

## When Code Blocks Are Appropriate

Not all code blocks carry this risk. The One Code Rule (defined in `learned-docs-core.md`) grants four exceptions where the content either doesn't exist in erk source or the block's value depends on its exact form:

1. **Data formats** — JSON/YAML/TOML shape examples (structure, not processing logic)
2. **Third-party API patterns** — Click, pytest, Rich (teaching external APIs that aren't in erk source)
3. **Anti-patterns marked WRONG** — the wrongness is the point; these are intentionally incorrect
4. **I/O examples** — CLI commands with expected output (self-contained, stable)

The decision test is mechanical: "Could an agent get this by reading erk source?" If yes, use a pointer regardless of how short the excerpt is. Partial excerpts ("just the interesting lines") create the same staleness problem as copying the whole function.

## The Three-Part Enforcement Loop

This isn't a style guideline — it's an enforced system with three interlocking pieces:

| Component                                                  | Role                                                                    | When it acts                                                |
| ---------------------------------------------------------- | ----------------------------------------------------------------------- | ----------------------------------------------------------- |
| Content quality standards (`learned-docs-core.md`)         | Define the One Code Rule and its exceptions                             | At authoring time — agents consult before writing           |
| Source pointers ([source-pointers.md](source-pointers.md)) | Provide the replacement format with machine-greppable HTML comments     | At authoring time — agents use format when replacing blocks |
| PR review automation (`.erk/reviews/audit-pr-docs.md`)     | Enforce the rule by classifying code blocks and posting inline comments | At PR time — catches violations before merge                |

<!-- Source: .erk/reviews/audit-pr-docs.md -->

The `audit-pr-docs` review audits the **full document** (not just changed lines) on every PR touching `docs/learned/`. It classifies each code block as VERBATIM, ANTI-PATTERN, CONCEPTUAL, or TEMPLATE, and posts inline comments for verbatim blocks with the exact source location and suggested pointer replacement. This "audit on touch" design means stale code blocks surface when docs are being actively worked on — the cheapest time to fix them.

Together the three pieces form a closed loop: standards define what's wrong, pointers define the fix, and automation catches violations before they merge. Any agent writing or reviewing documentation needs to understand all three.

## Related Documentation

- [source-pointers.md](source-pointers.md) — Replacement format specification (two-part HTML comment + prose reference)
- [audit-methodology.md](audit-methodology.md) — How audits classify content and the constants exception
- [simplification-patterns.md](simplification-patterns.md) — Pattern 1 (Static → Dynamic) applies this principle to enumerated lists
