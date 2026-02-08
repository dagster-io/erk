---
audit_result: edited
last_audited: "2026-02-08"
read_when:
  - documenting a decision point between two valid approaches
  - writing comparison documentation for agents
  - choosing between decision table, prose, or template format for trade-off docs
title: Two-Option Decision Documentation
tripwires:
  - action: writing a decision doc with only prose 'use X when...' bullets
    warning:
      Add a decision matrix table. Tables let agents scan trade-offs at a glance
      without parsing paragraphs. See two-option-template.md.
  - action: writing a decision doc without concrete examples
    warning:
      Include at least one situation→decision→reasoning example. Abstract criteria
      are hard to apply without concrete illustrations.
  - action: creating a two-option doc where every matrix row favors the same option
    warning: That's a best-practice doc, not a decision doc. Don't create false balance.
---

# Two-Option Decision Documentation

When two approaches are both valid and context-dependent, agents need a structured way to choose between them. Prose descriptions of trade-offs are hard to scan and easy to misapply. This template standardizes how erk documents binary decisions so agents make the right choice quickly.

## Why This Structure Exists

Decision documentation fails in two predictable ways:

1. **Buried trade-offs** — paragraphs of "use X when... but consider Y if..." force agents to mentally reconstruct a comparison matrix. In compressed context windows, these paragraphs get summarized into mush.
2. **Context-free options** — describing two approaches without grounding them in concrete scenarios leaves agents unable to match their situation to the right choice.

The two-option structure addresses both failures by combining three complementary views of the same decision, each catching what the others miss:

- **Named options with "when to use" bullets** — scannable situation-matching
- **Decision matrix table** — factor-by-factor comparison that survives context compression
- **Concrete examples** — scenarios that ground abstract criteria in reality

The decision matrix is the load-bearing section. Without it, agents must re-derive the comparison every time — exactly the re-computation that `docs/learned/` exists to prevent.

## Required Sections

A well-formed two-option doc needs these structural elements in order:

1. **Brief context** — what decision this addresses and why both options exist
2. **Option descriptions** — each named with a short summary and "when to use" bullets
3. **Decision matrix** — table with factors as rows, options as columns
4. **Examples** — at least one situation → decision → reasoning scenario
5. **Anti-patterns** — common mistakes when choosing between the options

## Applicability

This template applies to a specific shape of decision. Using it outside that shape creates misleading documentation.

| Situation                               | Right format                         | Why                                                     |
| --------------------------------------- | ------------------------------------ | ------------------------------------------------------- |
| Two valid, context-dependent approaches | Two-option template                  | Neither is universally better; factors determine choice |
| One clearly superior approach           | Best-practice doc                    | No decision to make — just document the winner          |
| Three or more options                   | Decision tree or multi-option matrix | Two-option structure misleads by excluding alternatives |
| Complementary approaches (use both)     | Integration guide                    | Options aren't competing — they compose                 |

## Anti-Patterns

**Prose-only comparison.** "Use X when performance matters, use Y when readability matters" forces agents to build a mental model from paragraphs. A table externalizes this comparison into a scannable format. Tables also degrade more gracefully under context compression — the structure survives even when surrounding prose gets trimmed.

**No concrete examples.** Abstract criteria like "use when complexity is high" are ambiguous — every developer thinks their task is complex. Ground each criterion with a real scenario: "Scenario: adding --dry-run to a command that touches 5 gateways. Decision: plan first. Reasoning: cross-cutting change with uncertain scope."

**False balance.** If every row in the decision matrix favors the same option, this isn't a decision — it's a best practice wearing a decision template's clothes. Write a best-practice doc instead.

## Existing Examples in Erk

<!-- Source: docs/learned/documentation/when-to-switch-pattern.md -->

[when-to-switch-pattern.md](when-to-switch-pattern.md) documents the planless vs planning workflow decision using this structure, including a decision matrix, mid-task warning signs, and concrete switch-point scenarios.

<!-- Source: docs/learned/architecture/context-injection-tiers.md -->

[context-injection-tiers.md](../architecture/context-injection-tiers.md) applies a multi-option variant with a three-column decision matrix for choosing between ambient, per-prompt, and just-in-time context injection.

## Related Documentation

- [Divio Documentation System](divio-documentation-system.md) — broader framework for choosing documentation types; this template falls under "Explanation" in that taxonomy
- [Source Pointers](source-pointers.md) — format for decision matrix docs that reference erk source code (use pointers, not code blocks)
