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

> **Source:** `erkdesk/src/types/erkdesk.d.ts:45-53`

### ActionOutputEvent

Discriminated union for real-time output from streaming actions. Has two fields: `stream` (`"stdout"` | `"stderr"`) identifying the output source, and `data` (string) containing text with ANSI escape codes already stripped.

**Usage:** Received via `window.erkdesk.onActionOutput()` callback as actions execute. Stdout is typically rendered gray in the UI, stderr in red/orange.

### ActionCompletedEvent

Discriminated union for action completion status. Has `success` (boolean, true if exit code 0) and optional `error` (string, present when `success` is false).

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

> **Source:** `erkdesk/src/types/erkdesk.d.ts:55-65`

The `window.erkdesk` API exposes four streaming-related methods: `startStreamingAction` to spawn a process, `onActionOutput` / `onActionCompleted` to register callbacks for output events and completion, and `removeActionListeners` to clean up IPC listeners.

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
