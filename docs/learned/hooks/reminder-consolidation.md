---
title: Reminder Consolidation Pattern
read_when:
  - "adding a new coding standards reminder to any hook, skill, or AGENTS.md section"
  - "debugging why a reminder appears multiple times in agent context"
  - "deciding which tier (ambient, per-prompt, just-in-time) a new reminder belongs in"
  - "removing or reducing reminder duplication across tiers"
tripwires:
  - action: "adding new coding standards reminders"
    warning: "Grep for the reminder text across AGENTS.md, hooks, and skills first — it may already exist at another tier. Duplicate reminders waste tokens and teach agents to ignore them. Read reminder-consolidation.md first."
---

# Reminder Consolidation Pattern

This document covers **how to decide where a reminder belongs** and **how to eliminate duplication** across erk's three-tier context injection system. For the tier architecture itself (what each tier is, when it fires, token costs), see [Context Injection Architecture](../architecture/context-injection-tiers.md).

## Why Consolidation Matters

The same coding standard delivered at multiple tiers creates three compounding problems:

1. **Token waste** — Identical content repeated per-turn or per-tool-call accumulates across a session
2. **Signal dilution** — Agents learn to skim repeated text, reducing compliance on the parts that actually matter
3. **Maintenance drift** — Updates must be synchronized across multiple locations, and stale copies silently diverge from the canonical version

The goal: every reminder appears **exactly once**, at the **most specific tier** that achieves the desired compliance.

## Tier Selection Decision Table

| Reminder characteristic | Correct tier | Why |
|---|---|---|
| Applies to every task regardless of tool | Tier 1 (Ambient / AGENTS.md) | Always in context, no action-specific trigger exists |
| Cross-cutting session routing (e.g., "use devrun") | Tier 2 (UserPromptSubmit) | Needs per-turn reinforcement, not tool-specific |
| Dynamic state injection (session IDs, branch names) | Tier 2 (UserPromptSubmit) | Value changes per-session, needs dynamic computation |
| Applies only when editing certain file types | Tier 3 (PreToolUse) | Can inspect `file_path` in tool params, fires only when relevant |
| Applies only to a specific tool (Bash, Write) | Tier 3 (PreToolUse) | Matcher targets the exact tool, zero cost when tool isn't used |

**Default to the most specific tier.** The temptation is to put everything in UserPromptSubmit "just in case" — but Tier 3 achieves equal compliance at a fraction of the token cost because it fires only when the action is imminent.

## The Ambient + JIT Pattern

The most common correct multi-tier pattern is **compressed awareness at Tier 1** combined with **pointed nudge at Tier 3**. These are not duplicates — they serve different cognitive purposes:

- **Ambient (AGENTS.md)** provides the "why" context that makes standards legible throughout the session. Without it, agents encounter JIT reminders with no framework for understanding them.
- **Just-in-time (PreToolUse)** provides the "remember right now" nudge at the exact moment the agent is about to take the relevant action. Without it, ambient rules fade from attention.

### Case Study: dignified-python (PR #6278)

Before consolidation, dignified-python core rules were delivered three times per Python edit:

1. **Ambient** — AGENTS.md "Python Standards" quick reference
2. **Per-prompt** — UserPromptSubmit hook reminded agent to load the skill
3. **Skill load** — Skill file repeated core rules in its preamble

After consolidation, Tier 2 and the skill preamble repetition were removed. Only two tiers remain, each delivering **different content**:

1. **Ambient** — AGENTS.md retains the compressed quick reference (background awareness)
2. **Just-in-time** — PreToolUse hook emits a one-line pointed reminder only when Write/Edit targets a `.py` file

<!-- Source: src/erk/cli/commands/exec/scripts/pre_tool_use_hook.py, build_pretool_dignified_python_reminder -->

See `build_pretool_dignified_python_reminder()` in `src/erk/cli/commands/exec/scripts/pre_tool_use_hook.py` for how the JIT reminder is deliberately compressed to a single sentence, distinct from the ambient quick reference.

## Capability Gating Enables Gradual Rollout

Reminders are opt-in per project via the `[reminders] installed` list in `.erk/state.toml`. Both UserPromptSubmit and PreToolUse hooks check this before emitting anything.

<!-- Source: src/erk/core/capabilities/detection.py, is_reminder_installed -->

See `is_reminder_installed()` in `src/erk/core/capabilities/detection.py` for the detection logic.

This gating directly serves consolidation: adding a new reminder to a hook doesn't force it on every project. You can roll out gradually, observe compliance in one project, and remove broader-tier duplicates only after confirming the more specific tier achieves equivalent compliance.

## Prevention Checklist

Before adding a new coding standards reminder:

1. **Grep for duplicates** — Search AGENTS.md, all hook scripts in `src/erk/cli/commands/exec/scripts/`, and skill files for the reminder's core content
2. **Check existing tiers** — Is this knowledge already delivered at Tier 1 (ambient), Tier 2 (per-prompt), or Tier 3 (JIT)?
3. **Choose the most specific tier** — Can the reminder be scoped to a specific tool or file type? If so, Tier 3 is almost always correct.
4. **Verify no overlap** — If keeping content at multiple tiers, confirm each tier delivers **different content** serving **different purposes** (the Ambient + JIT pattern above)
5. **Gate on capability** — Add the reminder name to the `is_reminder_installed()` checks so projects can opt in/out
6. **Test the full flow** — Trigger the relevant action in a session and verify the reminder appears exactly once at the right moment

## When NOT to Consolidate

Keep reminders at multiple tiers when:

- **Different content at each tier** — Compressed awareness (ambient) vs pointed nudge (JIT) serve different cognitive purposes. The dignified-python pattern above is the canonical example.
- **Different scopes** — A session-wide routing reminder ("use devrun for pytest") and an action-specific reminder ("LBYL when editing Python") address different concerns even though they're both about "coding standards."
- **Different audiences** — Planning-phase reminders vs implementation-phase reminders may both reference the same standard but guide different agent behaviors.

## Anti-Patterns

**Consolidating down to zero ambient context.** If you remove a standard from AGENTS.md entirely and rely solely on JIT hooks, the agent has no awareness of the standard until the moment it's about to violate it. The ambient tier provides the conceptual framework that makes JIT reminders actionable rather than confusing.

**Putting file-type-specific rules in UserPromptSubmit.** The PreToolUse hook can inspect `file_path` in tool params and fire only when relevant. Putting "LBYL when editing Python" in UserPromptSubmit means every non-Python turn pays the token cost for no benefit. Tier 3 achieves equal compliance because the reminder arrives at the moment of action.

**Skipping the grep before adding a reminder.** The single most common source of duplication is adding a reminder without checking whether it already exists at another tier. The reminder's wording may differ slightly, but if the core instruction is the same, it's a duplicate.

## Consolidation Process

When reducing existing duplication:

1. **Audit** — Grep for the reminder text across all tiers to find every instance
2. **Classify** — For each instance, determine whether it provides unique value at that tier or is pure repetition
3. **Remove repetitions** — Delete instances that duplicate content already delivered at a more specific tier
4. **Preserve ambient awareness** — Keep compressed references in AGENTS.md unless the standard is truly niche
5. **Verify** — Run a session, trigger the relevant action, and confirm the reminder appears once at the right moment

## Related Documentation

- [Context Injection Architecture](../architecture/context-injection-tiers.md) — The three-tier system this pattern operates within
- [PreToolUse Hook Design Patterns](pretooluse-implementation.md) — How to build JIT hooks with pure functions and capability gating
- [Hooks Guide](hooks.md) — Hook lifecycle, matchers, and configuration
