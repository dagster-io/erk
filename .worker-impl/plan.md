# Plan: Clarify session ID retrieval in objective-next-plan skill

## Problem

In Step 2.5 of the `/erk:objective-next-plan` skill, the instruction to "get the session ID" is ambiguous. Claude incorrectly tried to use `Grep` on `/dev/stdin` to extract the session ID, when it should simply read it directly from the visible system reminder text.

## Solution

Add explicit clarification that the session ID should be read directly from the conversation context - no tools needed.

## File to Modify

`.claude/commands/erk/objective-next-plan.md`

## Change

**Before (line 70):**
```markdown
**Get the session ID** from the `session:` system reminder in your conversation context (e.g., `session: a8e2cb1d-f658-4184-b359-b84bb67a487d`).
```

**After:**
```markdown
**Get the session ID** by reading the `session:` line from the system reminders in your conversation context (e.g., `session: a8e2cb1d-f658-4184-b359-b84bb67a487d`). This value is already visible in your context - just copy it directly, no tools needed.
```

## Verification

1. Run `/erk:objective-next-plan <issue>`
2. Confirm Claude reads the session ID directly without attempting to use search tools