---
title: Erkdesk React Components Reference
read_when:
  - "implementing new erkdesk React components"
  - "understanding LogPanel component behavior"
  - "working with streaming output display in erkdesk"
---

# Erkdesk React Components Reference

This document provides reference documentation for React components in erkdesk, with a focus on components related to the streaming action architecture.

## LogPanel Component

Status-aware component for displaying streaming log output with auto-scroll.

### Props

```typescript
interface LogPanelProps {
  logs: LogLine[];
  status: "running" | "success" | "error";
  onDismiss: () => void;
}
```

**Props:**

- `logs`: Array of log lines to display, each with `stream` ("stdout" | "stderr") and `data` (string)
- `status`: Current action status, determines header color and status indicator
- `onDismiss`: Callback invoked when user clicks the dismiss button

### Features

#### Stream-Specific Styling

The component applies different styles based on the output stream:

- **stdout**: Gray text (`text-gray-300`)
- **stderr**: Red/orange text (`text-red-400` or similar)

This visual distinction helps users quickly identify error messages vs. normal output.

#### Auto-Scroll Behavior

The component automatically scrolls to the bottom as new log lines arrive, keeping the most recent output visible. This is implemented using a ref to the scrollable container and a `useEffect` that triggers on log array changes.

#### Status Indicators

The header changes color based on the action status:

- **running**: Blue background - action in progress
- **success**: Green background - action completed successfully
- **error**: Red background - action failed

#### Fixed Height with Scrollable Overflow

The panel has a fixed height of 200px with scrollable overflow (`overflow-y-auto`). This ensures:

- Consistent layout regardless of log content
- Logs don't push other UI elements off screen
- Long output remains accessible via scrolling

### Dismiss Button

The component includes a dismiss button in the header that calls the `onDismiss` callback when clicked. This allows the parent component to hide the panel when the user is done reviewing logs.

### Usage Example

See `desktop-dash/src/App.tsx` for integration with streaming action state management.

## Component Testing

See [Erkdesk Component Testing Patterns](../testing/erkdesk-component-testing.md) for testing strategies specific to LogPanel and other erkdesk components.

## Related Documentation

- [Erkdesk IPC Streaming Architecture](../architecture/erkdesk-ipc-streaming.md) - IPC event flow to components
- [Desktop Dash Interaction Model](interaction-model.md) - State management patterns
- [Erkdesk Types Reference](../reference/erkdesk-types.md) - TypeScript type definitions
