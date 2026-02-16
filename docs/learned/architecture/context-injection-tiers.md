---
title: Context Injection Architecture
read_when:
  - "designing a new hook or reminder system"
  - "understanding how coding standard reminders work"
  - "deciding where to inject context for agent compliance"
  - "choosing between ambient, per-prompt, and just-in-time injection"
tripwires:
  - action: "designing a new hook or reminder system"
    warning: "Consider the three-tier context architecture and consolidation patterns. Read docs/learned/architecture/context-injection-tiers.md first."
last_audited: "2026-02-16 00:00 PT"
audit_result: edited
---

# Context Injection Architecture

Erk uses a three-tier system to inject coding standards and reminders into agent context. Each tier differs in **timing** (when it fires), **token cost** (how often it's paid), and **specificity** (how targeted the reminder is).

## Why Three Tiers?

**The central trade-off:** Ambient context achieves near-100% compliance but costs tokens for the entire session. Just-in-time injection is cheaper but only fires when relevant. Skills achieve ~53% compliance because agents must remember to load them.

The three-tier architecture addresses this by combining broad coverage (Tier 1) with targeted precision (Tier 3), eliminating the need for agents to remember on-demand loading.

## Decision Matrix

Choose the tier based on your reminder's characteristics:

| Factor                       | Tier 1: Ambient | Tier 2: Per-Prompt | Tier 3: Just-in-Time |
| ---------------------------- | --------------- | ------------------ | -------------------- |
| **When it fires**            | Session start   | Every user message | Before specific tool |
| **Token cost**               | High (once)     | Medium (per turn)  | Low (when triggered) |
| **Compliance rate**          | ~100% (if read) | Medium             | High                 |
| **Specificity**              | Broad           | Broad              | Narrow               |
| **Can inspect tool params**  | No              | No                 | Yes                  |
| **Can block tool execution** | No              | No                 | Yes                  |

**Use case heuristic:**

- **Universal rule affecting all tasks** → Tier 1
- **Session-wide routing or cross-cutting reminder** → Tier 2
- **Action-specific guard or tool-specific rule** → Tier 3

## Tier 1: Ambient (AGENTS.md)

**Mechanism:** References in `AGENTS.md` like `@docs/learned/tripwires-index.md` are loaded at session start and remain in context.

**Strengths:**

- Always available — no agent action required
- Highest compliance rate (near-100% for rules agents read)
- No repeated token cost

**Weaknesses:**

- Token cost paid upfront and maintained throughout session
- Cannot be conditional on specific actions
- Cannot inspect tool parameters or block execution

**When to use:**

- Critical rules that apply to every task (e.g., LBYL, no default parameters)
- Universal tripwires (e.g., "never pip install, use uv")
- Quick-reference coding standards

**Example in erk:** The "Python Standards (Ambient Quick Reference)" section in `AGENTS.md` provides compressed coding rules visible throughout the session.

## Tier 2: Per-Prompt (UserPromptSubmit hooks)

**Mechanism:** UserPromptSubmit hooks fire before each user message. Hook stdout becomes a system reminder.

<!-- Source: .claude/settings.json, UserPromptSubmit section -->

See the `UserPromptSubmit` section in `.claude/settings.json` for configuration.

**Strengths:**

- Reinforces reminders on every turn
- Can include dynamic content (session IDs, current state)
- Fires reliably without agent awareness

**Weaknesses:**

- Repeated token cost on every user message
- Always fires, even when not relevant
- Cannot inspect tool parameters

**When to use:**

- Session-wide routing ("use devrun agent for pytest/ty/ruff")
- Dynamic state injection (session IDs, current branch)
- Cross-cutting reminders that don't fit a specific tool

**When NOT to use:** Tool-specific reminders that only apply when editing certain file types (use Tier 3 instead to avoid token waste).

<!-- Source: src/erk/cli/commands/exec/scripts/user_prompt_hook.py -->

**Example in erk:** The `user-prompt-hook` script (see `src/erk/cli/commands/exec/scripts/user_prompt_hook.py`) emits session ID and devrun routing reminders on every prompt.

## Tier 3: Just-in-Time (PreToolUse hooks)

**Mechanism:** PreToolUse hooks fire immediately before a specific tool executes. The hook receives tool parameters via stdin JSON and can inspect them.

<!-- Source: .claude/settings.json, PreToolUse section -->

See the `PreToolUse` section in `.claude/settings.json` for configuration.

**Strengths:**

- Most targeted — fires only when the specific action is about to happen
- Lowest token cost (only when relevant)
- Highest signal-to-noise ratio
- Can inspect tool parameters (file paths, command content)
- Can block execution (exit code 2)

**Weaknesses:**

- Not visible in context until the tool is invoked
- Requires hook implementation and capability detection
- More complex to test

**When to use:**

- File-type-specific coding standards (Python rules when editing `.py` files)
- Command validation (check Bash commands before execution)
- Tool parameter modification (add safety flags)

<!-- Source: src/erk/cli/commands/exec/scripts/pre_tool_use_hook.py -->

**Example in erk:** The `pre-tool-use-hook` script (see `src/erk/cli/commands/exec/scripts/pre_tool_use_hook.py`) checks if a Write/Edit target is a `.py` file and emits dignified-python core rules only for Python edits.

## Consolidation Pattern: Avoid Duplication

**Problem:** The same reminder delivered at multiple tiers wastes tokens and creates noise.

**Solution:** Choose the **most specific tier** that achieves the desired compliance.

**dignified-python case study:**

Prior to PR #6278, dignified-python used all three tiers:

1. Ambient (AGENTS.md quick reference)
2. Per-Prompt (UserPromptSubmit reminder to load skill)
3. Per-Prompt (skill load repeated core rules)

This resulted in ~200 tokens of duplicated rules on every Python edit.

**After consolidation:**

1. Ambient (AGENTS.md quick reference) — retained for context
2. Just-in-Time (PreToolUse on Write|Edit for `.py` files) — core rules only when editing

**Result:** Core rules injected exactly once, at the moment of action, without session-wide duplication.

For the full consolidation pattern, see [Reminder Consolidation](../hooks/reminder-consolidation.md).

## Compliance Data

**Source:** Vercel's AGENTS.md research shows passive ambient context achieves near-100% compliance for rules agents actually read. Skill-based injection (on-demand loading) achieves ~53% compliance because agents must remember to load the skill.

**Design implication:** Critical rules belong in Tier 1 (ambient) or Tier 3 (just-in-time). Tier 2 (per-prompt) is best reserved for session-wide routing and dynamic state, not for rules that could be action-specific.

## Implementation Notes

**Capability-gated reminders:** PreToolUse hooks can check for capability marker files before injecting reminders. This enables gradual rollout and easy disablement.

**Example:** The `dignified-python` reminder capability (tracked via `state.toml`) enables Python editing reminders. If the capability is not installed, the hook exits silently without injecting content.

**Matchers:** PreToolUse hooks use regex patterns to target specific tools. `"matcher": "Write|Edit"` fires before both Write and Edit tool calls.

## Related Topics

- [Hooks Guide](../hooks/hooks.md) — Hook lifecycle and configuration
- [PreToolUse Implementation](../hooks/pretooluse-implementation.md) — Technical implementation details
- [Reminder Consolidation](../hooks/reminder-consolidation.md) — Pattern for avoiding duplication
