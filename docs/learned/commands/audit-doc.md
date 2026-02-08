---
title: Audit-Doc Design Decisions
read_when:
  - "understanding why audit-doc works the way it does"
  - "modifying the /local:audit-doc command"
  - "understanding collateral finding tiers"
  - "debugging unexpected audit verdicts"
tripwires:
  - action: "modifying collateral finding categories or auto-apply behavior in audit-doc"
    warning: "CRITICAL: Read this doc first to understand the conceptual vs mechanical finding distinction"
last_audited: "2026-02-08 11:48 PT"
audit_result: clean
---

# Audit-Doc Design Decisions

<!-- Source: .claude/commands/local/audit-doc.md -->

This document captures cross-cutting design decisions behind the `/local:audit-doc` command that aren't obvious from reading the command source alone. For the command definition itself, see `.claude/commands/local/audit-doc.md`.

## Why Two Tiers of Collateral Findings

The collateral finding system splits into **conceptual** (OS, CF, SF) and **mechanical** (SC, SD, BX, CD) tiers because they require fundamentally different remediation strategies.

**Conceptual findings are discovery-only** — they are never auto-fixed, even in `--auto-apply` mode. The reason: a conceptual problem (e.g., a doc describing a system that was replaced) means the entire doc's premise is wrong. Fixing individual claims would create a Frankenstein document that's partially updated but still misleading. The correct action is always a full audit pass on the affected file.

**Mechanical findings can be auto-fixed** because they're localized: a stale comment, a broken link, a wrong return type in a docstring. The surrounding context remains valid; only the specific detail needs correction.

This distinction matters for `--auto-apply` in CI: mechanical fixes are safe to batch-apply, but conceptual findings must produce audit recommendations (not inline edits) to avoid silent corruption.

## Verdict Threshold Design

The verdict system uses percentage-based thresholds (not absolute counts) to account for documents of varying length. A 3-section doc with 1 duplicative section looks very different from a 20-section doc with 1 duplicative section.

Key threshold decisions:

| Verdict                | Threshold                            | Why                                 |
| ---------------------- | ------------------------------------ | ----------------------------------- |
| KEEP                   | ≥50% high-value                      | Majority of content earns its place |
| SIMPLIFY               | ≥30% duplicative but has high-value  | Worth preserving after trimming     |
| REPLACE WITH CODE REFS | ≥60% duplicative, minimal high-value | More noise than signal              |
| CONSIDER DELETING      | ≥80% duplicative, no high-value      | Almost entirely redundant with code |

**INACCURATE is treated as at least as severe as DUPLICATIVE** in all threshold calculations. This prevents a doc with many inaccurate sections from receiving a lenient verdict just because it's not "duplicative" per se.

## The "Missing Code Examples" Trap

A common audit instinct is to flag docs for "missing code examples" and recommend adding them. This directly contradicts the One Code Rule from the content quality standards. The correct recommendation is almost always a source pointer, not a new code block.

The only exceptions where audit-doc should recommend adding code: data format examples, third-party API patterns, anti-patterns marked WRONG, and I/O examples (CLI commands with expected output).

## CI Auto-Detection

The command auto-enables `--auto-apply` when `$CI` or `$GITHUB_ACTIONS` is set. This exists because the batch regeneration workflow (`scripts/batch_regenerate_docs.py`) runs audit-doc in a non-interactive context where prompting would hang the pipeline.

In CI mode, `CONSIDER DELETING` verdicts are stamped as clean (not auto-deleted) because deletion is a destructive action that requires human judgment about whether the content should be preserved elsewhere.

## Adversarial Framing

The audit is intentionally adversarial: the burden of proof is on the document to justify its existence over just reading code. This framing prevents the natural tendency to rate documentation as "good enough" — most docs accumulate duplicative content over time as the code they describe evolves, and a generous audit misses that drift.

## Related Documentation

- [Content Quality Standards](.claude/skills/learned-docs/learned-docs-core.md) — the rules audit-doc enforces
- [Source Pointers](../documentation/source-pointers.md) — format for replacing verbatim code with references
- [Frontmatter Tripwire Format](../documentation/frontmatter-tripwire-format.md) — YAML schema for tripwires
