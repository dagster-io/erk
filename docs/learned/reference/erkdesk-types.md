---
title: Erkdesk Type Definitions Reference
read_when:
  - "working with erkdesk TypeScript interfaces"
  - "implementing streaming action features in erkdesk"
  - "understanding erkdesk IPC event structures"
---

# Erkdesk Type Definitions Reference

This document provides reference documentation for TypeScript interfaces and types used in erkdesk, particularly those related to the streaming action architecture.

## Action Event Types

### ActionOutputEvent

Discriminated union for real-time output from streaming actions.

```typescript
type ActionOutputEvent = {
  stream: "stdout" | "stderr";
  data: string;
};
```

**Fields:**

- `stream`: Identifies which output stream the data came from
  - `"stdout"`: Standard output (typically gray in UI)
  - `"stderr"`: Standard error (typically red/orange in UI)
- `data`: The text content, with ANSI escape codes already stripped

**Usage:** Received via `window.erkdesk.onActionOutput()` callback as actions execute.

### ActionCompletedEvent

Discriminated union for action completion status.

```typescript
type ActionCompletedEvent = {
  success: boolean;
  error?: string;
};
```

**Fields:**

- `success`: `true` if the action completed with exit code 0, `false` otherwise
- `error`: Optional error message if `success` is `false`

**Usage:** Received via `window.erkdesk.onActionCompleted()` callback when spawned process exits.

## UI Component Types

### LogLine

Individual log entry for display in LogPanel component.

```typescript
type LogLine = {
  stream: "stdout" | "stderr";
  data: string;
};
```

**Note:** This is structurally identical to `ActionOutputEvent` but semantically distinct - `ActionOutputEvent` represents IPC events, while `LogLine` represents UI state.

## API Interface Extensions

### ElkdeskAPI Streaming Methods

The `window.erkdesk` API exposes these streaming-related methods:

```typescript
interface ElkdeskAPI {
  // Existing methods omitted for brevity

  // Streaming action methods
  startStreamingAction(action: ActionDefinition, worktreePath: string): void;
  onActionOutput(callback: (event: ActionOutputEvent) => void): void;
  onActionCompleted(callback: (event: ActionCompletedEvent) => void): void;
  removeActionListeners(): void;
}
```

**See also:** [Erkdesk IPC Streaming Architecture](../architecture/erkdesk-ipc-streaming.md) for usage patterns and lifecycle details.

## Type-First Development Pattern

The streaming feature implementation followed a type-first approach:

1. Define TypeScript interfaces for IPC events (`ActionOutputEvent`, `ActionCompletedEvent`)
2. Extend `ElkdeskAPI` interface with method signatures
3. Implement main process event emitters conforming to event types
4. Implement preload bridge conforming to API interface
5. Implement React components consuming typed events

This pattern ensures type-safe event handling across Electron process boundaries, catching mismatches at compile time rather than runtime.

## Related Documentation

- [Erkdesk IPC Streaming Architecture](../architecture/erkdesk-ipc-streaming.md) - Streaming architecture and API usage
- [Desktop Dash Interaction Model](../desktop-dash/interaction-model.md) - State management patterns
