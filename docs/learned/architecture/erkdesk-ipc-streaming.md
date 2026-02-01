---
title: Erkdesk IPC Streaming Architecture
read_when:
  - "implementing streaming features in erkdesk"
  - "working with real-time action output in Electron"
  - "understanding erkdesk IPC event patterns"
  - "debugging erkdesk streaming action listeners"
tripwires:
  - action: "implementing streaming action listeners in erkdesk"
    warning: "Always pair onActionOutput/onActionCompleted with removeActionListeners() on cleanup. Prevents accumulated listeners causing memory leaks and duplicate event handling."
---

# Erkdesk IPC Streaming Architecture

This document describes the pub/sub pattern for real-time streaming from spawned processes to React components in erkdesk.

## Architecture Overview

The streaming pattern bridges multiple process boundaries:

```
Main Process (spawn) → IPC events → Preload Bridge → React State → LogPanel
```

This architectural shift replaces the older batch callback pattern with real-time event streaming.

## Architectural Shift

### Before: Batch Callback Pattern

```typescript
// Old pattern - blocking, batch output
executeAction() -> Promise<ActionResult>
```

The old pattern collected all output before returning, providing no real-time feedback during long-running operations.

### After: Streaming Event Pattern

```typescript
// New pattern - non-blocking, streaming
startStreamingAction() + event listeners (onActionOutput, onActionCompleted)
```

The new pattern uses a pub/sub model with event listeners for real-time feedback as actions execute.

## API Methods

### startStreamingAction

Spawns a process with streaming listeners attached.

```typescript
window.erkdesk.startStreamingAction(
  action: ActionDefinition,
  worktreePath: string
): void
```

This method:

- Spawns the erk process in the main process
- Attaches streaming listeners to stdout/stderr
- Emits `action:output` events in real-time
- Emits `action:completed` event on process exit

### onActionOutput

Registers a callback for real-time output events.

```typescript
window.erkdesk.onActionOutput(
  callback: (event: ActionOutputEvent) => void
): void
```

**Event type:**

```typescript
type ActionOutputEvent = {
  stream: "stdout" | "stderr";
  data: string;
};
```

The callback receives data as it arrives from the spawned process, with ANSI codes stripped.

### onActionCompleted

Registers a callback for process completion events.

```typescript
window.erkdesk.onActionCompleted(
  callback: (event: ActionCompletedEvent) => void
): void
```

**Event type:**

```typescript
type ActionCompletedEvent = {
  success: boolean;
  error?: string;
};
```

### removeActionListeners

**CRITICAL**: Removes all registered action listeners to prevent memory leaks.

```typescript
window.erkdesk.removeActionListeners(): void
```

This method must be called during cleanup (component unmount, action completion) to prevent accumulated listeners from causing:

- Memory leaks
- Duplicate event handling
- Performance degradation

## Event Lifecycle

1. **Start**: Component calls `startStreamingAction(action, path)`
2. **Stream**: Main process emits `action:output` events as data arrives
3. **Complete**: Main process emits `action:completed` event on exit
4. **Cleanup**: Component calls `removeActionListeners()` to remove all listeners

## ANSI Stripping Implementation

ANSI escape codes are stripped in the main process before emitting `action:output` events.

**Regex pattern:**

```typescript
/\x1B\[[0-9;]*m/g;
```

**Rationale:** CLI tools emit ANSI escape codes for terminal colors. Stripping at the source ensures clean data reaches React components, avoiding the need for per-component sanitization.

## Memory Leak Prevention

The streaming pattern introduces a critical memory management requirement: **listener cleanup**.

**Problem:** Event listeners accumulate if not removed. Each action start adds new listeners without removing old ones, causing:

- Memory growth over time
- Multiple callbacks firing for single events
- Degraded performance

**Solution:** Always call `removeActionListeners()` during cleanup:

- On component unmount
- On action completion
- Before starting a new action

TypeScript does not enforce this cleanup, making it a manual requirement.

## Integration Example

See `desktop-dash/src/App.tsx` for the canonical implementation pattern showing how React state management integrates with the streaming API.

## Related Documentation

- [Erkdesk Types Reference](../reference/erkdesk-types.md) - Type definitions for event structures
- [Erkdesk Component Testing](../testing/erkdesk-component-testing.md) - Testing streaming APIs
- [Desktop Dash Interaction Model](../desktop-dash/interaction-model.md) - State management patterns
