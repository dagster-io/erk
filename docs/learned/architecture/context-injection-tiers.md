---
title: Three-Tier Context Injection Architecture
read_when:
  - "designing a new hook or reminder system"
  - "understanding how dignified-python reminders work"
  - "deciding where to inject context for agent compliance"
tripwires:
  - action: "designing a new hook or reminder system"
    warning: "Consider the three-tier context architecture. Read docs/learned/architecture/context-injection-tiers.md first."
---

# Three-Tier Context Injection Architecture

Erk uses three tiers of context injection to ensure agents follow coding standards. Each tier serves a different purpose and fires at a different point in the agent lifecycle.

## The Three Tiers

### Tier 1: Ambient (AGENTS.md / CLAUDE.md)

**When**: Loaded at session start, always present in context.

**Mechanism**: `@docs/learned/...` references in AGENTS.md that Claude reads automatically.

**Characteristics**:

- Always available — 100% compliance for agents that read it
- Token cost is paid upfront for the entire session
- Best for critical rules that apply to all tasks
- Cannot be conditional on task type

**Example**: The "Python Standards (Ambient Quick Reference)" section in AGENTS.md provides compressed coding rules visible in every session.

### Tier 2: Per-Prompt (UserPromptSubmit hooks)

**When**: Fires before each user prompt is processed.

**Mechanism**: UserPromptSubmit hook outputs appear as system reminders.

**Characteristics**:

- Fires on every turn, reinforcing rules
- Can include dynamic content (session IDs, current state)
- Moderate token cost (repeated each turn)
- Good for reminders that need regular reinforcement

**Example**: The `user-prompt-hook` emits session ID and devrun routing reminders on every prompt.

### Tier 3: Just-in-Time (PreToolUse hooks)

**When**: Fires immediately before a specific tool executes.

**Mechanism**: PreToolUse hook checks tool input and emits targeted reminder.

**Characteristics**:

- Most targeted — fires only when the specific action is about to happen
- Lowest token cost (only when relevant)
- Highest signal-to-noise ratio
- Can inspect tool parameters (file paths, command content)

**Example**: The `pre-tool-use-hook` checks if a Write/Edit target is a `.py` file and emits a dignified-python reminder only for Python edits.

## Decision Matrix

| Factor                 | Ambient        | Per-Prompt    | Just-in-Time   |
| ---------------------- | -------------- | ------------- | -------------- |
| Token cost             | High (once)    | Medium (each) | Low (targeted) |
| Compliance rate        | High (if read) | Medium        | High           |
| Specificity            | Broad          | Broad         | Narrow         |
| Can inspect tool input | No             | No            | Yes            |
| Can block tool         | No             | No            | Yes (exit 2)   |

## When to Use Each Tier

- **New universal rule** → Tier 1 (Ambient) — add to AGENTS.md
- **Session-wide reminder** → Tier 2 (Per-Prompt) — UserPromptSubmit hook
- **Action-specific guard** → Tier 3 (Just-in-Time) — PreToolUse hook

## Integration Example: dignified-python

The dignified-python coding standards use all three tiers:

1. **Ambient**: AGENTS.md "Python Standards" section provides compressed rules always in context
2. **Per-Prompt**: UserPromptSubmit hook emits "dignified-python: CRITICAL RULES" reminder each turn
3. **Just-in-Time**: PreToolUse hook on `Write|Edit` detects `.py` files and emits targeted reminder

This layered approach means an agent writing Python code receives the standards at session start, gets reminded each turn, and gets a final targeted reminder at the exact moment of editing.

## Compliance Observations

From Vercel's AGENTS.md research: passive ambient context achieves near-100% compliance for rules agents read. Skill-based injection (on-demand loading) achieves ~53% compliance because agents must remember to load the skill. The three-tier architecture addresses this gap by ensuring critical rules are always present (Tier 1) while reserving detailed guidance for on-demand loading.

## Related Topics

- [Hooks Guide](../hooks/hooks.md) — Hook lifecycle and configuration
- [PreToolUse Implementation](../hooks/pretooluse-implementation.md) — Tier 3 implementation details
