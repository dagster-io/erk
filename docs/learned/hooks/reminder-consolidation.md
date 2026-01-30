---
title: Reminder Consolidation Pattern
read_when:
  - "adding a new coding standards reminder"
  - "deciding between UserPromptSubmit and PreToolUse hooks for reminders"
  - "debugging duplicate reminder output"
tripwires:
  - action: "adding new coding standards reminders"
    warning: "Check if reminder is already injected via PreToolUse hook before adding to UserPromptSubmit. Duplicate reminders increase noise and waste tokens. Read reminder-consolidation.md first."
---

# Reminder Consolidation Pattern

When injecting coding standards reminders, choose the most specific hook tier to avoid duplication and minimize token waste.

## Problem: Reminder Duplication

Without careful design, the same reminder can be delivered multiple times in a single conversation:

- **Session-wide** (UserPromptSubmit) - Every user message
- **Action-specific** (PreToolUse) - Before each relevant tool call
- **Per-prompt** (Skill load) - Every time a skill is invoked

This creates noise, wastes tokens, and reduces signal-to-noise ratio for the agent.

## Decision Framework

### UserPromptSubmit Hook

**When to use:** Cross-cutting reminders that apply to ANY action in the session

**Examples:**
- Session-specific routing (e.g., "Use devrun agent for pytest/ty/ruff")
- Session ID availability
- Universal tripwires that don't fit a specific tool

**Advantages:**
- Delivered once at session start
- Always visible in context

**Disadvantages:**
- Always present, even when not relevant
- Higher token cost for long sessions

### PreToolUse Hook

**When to use:** Reminders that only apply when a specific tool is about to be used

**Examples:**
- dignified-python rules when editing `.py` files
- Test placement rules when editing test files
- File-specific conventions

**Advantages:**
- Just-in-time delivery (only when relevant)
- Lower token cost (only fires when tool matches)
- Better signal-to-noise (pointed reminder at moment of action)

**Disadvantages:**
- Not visible in context until tool is invoked
- Requires hook implementation and capability detection

## Case Study: dignified-python Consolidation

PR #6278 consolidated dignified-python reminders from 3 tiers to 2 tiers:

### Before (3-tier delivery)

1. **Ambient** - AGENTS.md included quick reference rules
2. **Session-wide** - UserPromptSubmit reminded to load skill
3. **Per-prompt** - Each skill invocation repeated core rules

**Problem:** Core rules appeared 3 times, wasting tokens and creating noise.

### After (2-tier delivery)

1. **Ambient** - AGENTS.md still includes quick reference rules for context
2. **Action-specific** - PreToolUse hook injects core rules when editing `.py` files

**Result:**
- Removed session-wide UserPromptSubmit reminder (line 160 in AGENTS.md)
- Removed per-prompt core rules repetition from skill file
- Skill file now focuses on extended guidance and examples
- Core rules injected exactly when needed (editing Python code)

**Token savings:** ~200 tokens per edit action (core rules only delivered once, not three times)

## Capability-Gated Design

The PreToolUse hook checks for capability markers before injecting reminders:

```python
# Check if capability exists
if not capability_file.exists():
    return None  # Don't inject reminder

# Capability exists - inject reminder
return reminder_content
```

**Capability markers:** `.erk/capabilities/` directory contains marker files that enable/disable features.

**Example:** `.erk/capabilities/dignified-python-pretooluse` enables Python editing reminders.

**Benefits:**
- Gradual rollout (projects opt-in)
- Easy disable (delete marker file)
- Testable (create/remove marker in tests)

## Prevention Checklist

Before adding a new coding standards reminder:

- [ ] Is this reminder already in AGENTS.md ambient context?
- [ ] Is this reminder already in a UserPromptSubmit hook?
- [ ] Is this reminder already in a PreToolUse hook?
- [ ] Does this reminder apply to a specific tool action (Edit, Write)?
- [ ] If action-specific, can I use PreToolUse instead of UserPromptSubmit?
- [ ] If using PreToolUse, does the capability marker exist?
- [ ] Have I verified no duplication by testing the full reminder flow?

## Consolidation Guidelines

When consolidating existing reminders:

1. **Identify duplicates** - Grep for reminder content across hooks, skills, and AGENTS.md
2. **Choose the most specific tier** - Prefer PreToolUse > UserPromptSubmit > Ambient
3. **Remove from broader tiers** - Delete from session-wide if action-specific works
4. **Test the flow** - Verify reminder appears exactly once at the right moment
5. **Document the decision** - Update this doc or add a tripwire

## When NOT to Consolidate

Keep reminders at multiple tiers when:

- **Ambient + Action-specific** - Quick reference (AGENTS.md) + detailed rules (PreToolUse) serve different purposes
- **Different content** - Session-wide routing ("use devrun") vs action-specific rules ("LBYL only")
- **Different audiences** - Some reminders for planning, others for implementation

## Related Documentation

- [PreToolUse Hook Implementation](pretooluse-implementation.md) - Technical pattern for action-specific hooks
- [Context Injection Tiers](../architecture/context-injection-tiers.md) - Full architecture of 3-tier context system
- [Hooks Overview](hooks.md) - Complete guide to erk's hook system
