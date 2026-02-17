---
title: System Reminder Composition Patterns
read_when:
  - "writing hook output that becomes a system reminder"
  - "composing reminder text for workflow checkpoints"
  - "debugging why agents ignore or partially follow a reminder"
tripwires:
  - action: "writing a system reminder longer than 5 lines"
    warning: "Long reminders get skimmed or ignored. Apply the three-property test: concise (2-3 sentences or 4-5 bullets), specific (exact step/file/action references), verifiable (agent can self-check completion). Read replan-context-reminders.md."
last_audited: "2026-02-16 14:20 PT"
audit_result: clean
---

# System Reminder Composition Patterns

Hook stdout that exits 0 becomes a system reminder in agent context. Where to _place_ reminders across tiers is covered in [Context Injection Architecture](../architecture/context-injection-tiers.md) and [Reminder Consolidation](reminder-consolidation.md). This document covers the complementary problem: how to **compose** reminder text that agents actually follow.

## Why Composition Matters

A reminder in the right tier but with poor text still fails. Agents process system reminders the way humans process warning labels — they skim, extract the actionable part, and move on. Reminders that bury the action in prose get ignored regardless of delivery mechanism.

This was discovered during the replan workflow (Steps 6a-6b in `/erk:replan`). Investigation context was being lost between Steps 4-5 (investigation) and Step 6 (plan creation) because the original reminders were verbose paragraphs that agents glossed over. The fix wasn't changing _when_ reminders fired — it was changing _how_ they were written.

## The Three-Property Test

Every effective system reminder satisfies all three properties:

| Property       | Test                                                | Failure mode when missing                          |
| -------------- | --------------------------------------------------- | -------------------------------------------------- |
| **Concise**    | 2-3 sentences max, or 4-5 bullet points             | Agent skims wall of text, misses requirements      |
| **Specific**   | References exact steps, file types, or actions      | Agent interprets generically, does the wrong thing |
| **Verifiable** | Agent can self-check whether the requirement is met | Agent believes it complied when it didn't          |

**Priority ordering matters.** Conciseness is the gatekeeper: a concise but vague reminder still nudges behavior; a specific but long reminder gets skimmed before the specifics are reached; a verifiable but verbose reminder never reaches the verification step. When you can't achieve all three, sacrifice verifiability first, then specificity — never conciseness.

## Anti-Pattern: The Wall of Text

The single most common reminder failure mode:

```
WRONG — 175-word wall of text:
"Before you proceed with creating the plan, please make sure that you have thoroughly
gathered all of the investigation context from the previous steps, including but not
limited to: the investigation status for each of the plans you analyzed (with completion
percentages like '4/11 items implemented'), specific discoveries you made while exploring
the codebase (such as file paths, and not just generic 'the documentation files' but
actual full paths like docs/learned/architecture/foo.md, and also line numbers...) [continues]"
```

This fails all three properties: too long to parse, buries specific items in prose, provides no self-check mechanism. The same content restructured effectively:

```
CORRECT — 52 words, numbered, self-checking:
Context Gathering Checkpoint (Step 6a):

Required before Plan Mode:
1. Investigation status (e.g., "4/11 items implemented")
2. File paths with line numbers (docs/learned/foo.md:45)
3. Corrections to original plans (wrong files, outdated APIs)
4. Actual names from codebase (parse_session_file_path(), not guessed)

Verify: Can you answer "which files, which lines, what changes"?
```

The restructured version is 70% shorter, uses numbered items for scanning, and ends with a self-check question. This is the pattern that fixed context loss in the replan workflow.

## Anti-Pattern: The Vague Nudge

The opposite failure — too brief to be actionable:

```
WRONG: "Make sure to collect context before planning."
```

This passes conciseness but fails specificity and verifiability. The agent "collects context" by noting "I looked at the code" and moves on. Compare:

```
CORRECT: "Step 6a: Collect completion percentages, file paths (line numbers),
corrections, and codebase evidence before entering Plan Mode."
```

Same brevity, but the four required items create a checklist the agent can verify against.

## Checkpoint Timing

Multi-step workflows benefit from reminders at _transitions_, not during steps:

| Position               | Purpose                               | Why this moment                                       |
| ---------------------- | ------------------------------------- | ----------------------------------------------------- |
| Before investigation   | Prime the agent to preserve findings  | Sets intent before the work begins                    |
| Before Plan Mode entry | Verify context was gathered (Step 6a) | Last moment before findings must be structured        |
| After plan creation    | Verify plan has specifics             | Catches sparse plans before they reach an implementer |

**Key insight:** Reminders _before_ an action set intent. Reminders _after_ an action verify outcome. Both are needed for high-stakes transitions, but never more than one reminder per checkpoint — multiple reminders at the same point compete for attention and dilute each other.

## Formatting Guidelines

| Guideline                           | Rationale                                                                                    |
| ----------------------------------- | -------------------------------------------------------------------------------------------- |
| Lead with a label/title             | "Context Gathering Checkpoint:" signals what the reminder is about before the agent reads it |
| Use numbered lists for requirements | Agents track numbered items more reliably than prose lists                                   |
| Include one concrete example inline | "File paths (docs/learned/foo.md:45)" prevents abstract interpretation                       |
| End with a verification question    | "Can you answer X from your context?" forces self-assessment                                 |
| One reminder per checkpoint         | Multiple reminders at the same point compete for attention                                   |

## Related Documentation

- [Context Injection Architecture](../architecture/context-injection-tiers.md) — Where reminders are delivered (tier selection)
- [Reminder Consolidation](reminder-consolidation.md) — Avoiding duplicate reminders across tiers
- [PreToolUse Hook Design](pretooluse-implementation.md) — Technical patterns for hooks that emit reminders
- [Context Preservation in Replan](../planning/context-preservation-in-replan.md) — The sparse plan problem that drove these composition patterns
