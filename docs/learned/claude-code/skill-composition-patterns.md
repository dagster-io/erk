---
title: Skill Composition Patterns
read_when:
  - creating skills that invoke other skills
  - designing skill hierarchies
  - understanding skill loading chains
tripwires:
  - action: "reloading skills already loaded in the session"
    warning: "Skills persist for entire sessions. Check conversation history before loading."
last_audited: "2026-02-16 14:20 PT"
audit_result: clean
---

# Skill Composition Patterns

## The Reusability Trade-Off

Skills can reference other skills to extract domain-specific logic from workflow orchestration. The key insight: **common logic extracted to an inner skill becomes reusable across multiple consumers**.

Without composition, every command duplicating commit message generation must embed the same prompt. When the format changes (e.g., adding a "User Experience" section), all copies need updates.

With composition, the generation logic lives in one skill. Consumers reference it. Format changes affect one file.

## Why Composition Over Duplication

Early PR commands embedded commit message generation prompts inline. When Anthropic's best practices evolved (component-level over function-level detail), 5+ commands needed updates. Extraction to a reusable skill eliminated divergence risk.

**Decision drivers:**

1. **Consistency** — All callers use identical logic (no drift between copies)
2. **Maintenance** — One change propagates to all consumers
3. **Testability** — Inner skills can be invoked independently

**When NOT to extract:**

- Logic is genuinely single-use (no other consumer will ever need it)
- Prompt requires runtime context from parent conversation (use manual Task delegation instead)

## Loading Persistence Semantics

<!-- Source: .claude/commands/erk/git-pr-push.md, Step 3 -->

Skills persist for the **entire session** once loaded. A command saying "Load the `erk-diff-analysis` skill" doesn't re-inject content on every invocation — Claude Code tracks what's already in context.

**Why this matters:** Avoid defensive reloading. If a hook reminder fires every turn saying "load dignified-python", but the skill loaded 10 turns ago, ignore the reminder. Check conversation history for `<command-message>The "{name}" skill is loading</command-message>` before loading again.

**Anti-pattern:** Loading the same skill multiple times per session wastes tokens. The system already knows not to re-inject, but the parent agent still burns API calls checking.

## Two-Layer Composition Example

<!-- Source: .claude/commands/erk/git-pr-push.md, entire file -->
<!-- Source: .claude/skills/erk-diff-analysis/SKILL.md, entire file -->
<!-- Source: .claude/skills/erk-diff-analysis/references/commit-message-prompt.md, entire file -->

See `/erk:git-pr-push` command → `erk-diff-analysis` skill → `commit-message-prompt.md` reference chain.

**Layer 1 (Command):** Orchestrates git workflow (stage, diff, commit, push, PR creation). At commit message generation, loads `erk-diff-analysis`.

**Layer 2 (Analysis Skill):** Loads `commit-message-prompt.md` reference and applies its principles. Returns formatted commit message to parent.

**Layer 3 (Reference):** Pure prompt text defining format, rules, anti-patterns.

Why three layers instead of two?

- `commit-message-prompt.md` is pure content (no skill metadata, no loading logic)
- `erk-diff-analysis` wraps it with "when to use" guidance for agents
- Commands reference the skill, not the raw reference file

This separation means multiple skills (not just commands) can compose the same reference content.

## Composition vs Context Fork

Composition (skills reference each other) and context forking (isolated subagent execution) solve different problems:

| Pattern          | Context Sharing                                  | Use When                                                |
| ---------------- | ------------------------------------------------ | ------------------------------------------------------- |
| **Composition**  | Both skills share conversation history           | Reusing guidelines, building on prior context           |
| **Context Fork** | Isolated — forked skill sees only its own prompt | Reducing token pollution, fetch-and-classify operations |

<!-- Source: docs/learned/claude-code/context-fork-feature.md, entire file -->

See `context-fork-feature.md` for when isolation makes sense. Key distinction: forked skills must have **actionable steps**, not just guidelines. A forked "Python Standards" skill returns empty output because the subagent has no task. A forked "Fetch PR Comments and Classify" skill works because it has concrete steps.

**Composition guideline-only skills work fine** because the parent agent reads them as context and proceeds with its workflow. Forked guideline-only skills fail because subagents execute tasks, not absorb ambient knowledge.

## Related Documentation

- [Context Fork Feature](context-fork-feature.md) — When to isolate skill execution
- [Task Context Isolation Pattern](../architecture/task-context-isolation.md) — Manual Task delegation for dynamic prompts
