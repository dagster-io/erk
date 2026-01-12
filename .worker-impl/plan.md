# Documentation Plan: Standardize session ID retrieval instructions across commands

## Context

During plan #4808 implementation, we discovered that the instruction "Get the session ID from the `SESSION_CONTEXT` reminder" was misinterpreted by an agent as requiring a tool call (grep) to extract the value, when the session ID is already visible in the conversation context.

The fix for `objective-next-plan.md` (PR #4810) added clarifying language: "This value is already visible in your context - just copy it directly, no tools needed."

However, 4 other commands have similar instructions without this clarification.

## Raw Materials

https://gist.github.com/schrockn/c57a8389d925c2737f75d1fa59fe1f13

## Documentation Items

### Item 1: Update plan-save.md

**Location**: `.claude/commands/erk/plan-save.md:45`
**Action**: Update
**Current**: 
```
Get the session ID from the `SESSION_CONTEXT` reminder in your conversation context.
```
**New**:
```
Get the session ID by reading the `session:` line from the `SESSION_CONTEXT` reminder in your conversation context (e.g., `session: a8e2cb1d-...`). This value is already visible - just copy it directly, no tools needed.
```
**Source**: [Plan] Session analysis of plan #4808

### Item 2: Update plan-update.md

**Location**: `.claude/commands/local/plan-update.md:34`
**Action**: Update
**Current**: 
```
Get the session ID from the `SESSION_CONTEXT` reminder in your conversation context.
```
**New**:
```
Get the session ID by reading the `session:` line from the `SESSION_CONTEXT` reminder in your conversation context (e.g., `session: a8e2cb1d-...`). This value is already visible - just copy it directly, no tools needed.
```
**Source**: [Plan] Session analysis of plan #4808

### Item 3: Update incremental-plan-mode.md

**Location**: `.claude/commands/local/incremental-plan-mode.md:23`
**Action**: Update
**Current**: 
```
**Get the session ID** from the `session:` system reminder in your conversation context (e.g., `session: a8e2cb1d-f658-4184-b359-b84bb67a487d`).
```
**New**:
```
**Get the session ID** by reading the `session:` line from the system reminders in your conversation context (e.g., `session: a8e2cb1d-f658-4184-b359-b84bb67a487d`). This value is already visible in your context - just copy it directly, no tools needed.
```
**Source**: [Plan] Session analysis of plan #4808

### Item 4: Update impl-execute.md

**Location**: `.claude/commands/erk/system/impl-execute.md:50`
**Action**: Update
**Current**: 
```
Get the session ID from the `SESSION_CONTEXT` reminder in your conversation context.
```
**New**:
```
Get the session ID by reading the `session:` line from the `SESSION_CONTEXT` reminder in your conversation context (e.g., `session: a8e2cb1d-...`). This value is already visible - just copy it directly, no tools needed.
```
**Source**: [Plan] Session analysis of plan #4808