---
title: Erkdesk Breaking Change Migration Guide
read_when:
  - "updating erkdesk components after API changes"
  - "fixing ActionToolbar integration after streaming migration"
  - "understanding erkdesk breaking changes"
---

# Erkdesk Breaking Change Migration Guide

This document tracks breaking changes in erkdesk component APIs and provides migration paths.

## ActionToolbar Props: Batch to Streaming Migration

**PR:** #6541
**Affected:** Components using ActionToolbar

### Breaking Change

The ActionToolbar component API changed to support streaming action execution.

**Before (Batch Pattern):**

```typescript
<ActionToolbar
  executeAction={async (action) => {
    const result = await window.erkdesk.executeAction(action, worktreePath);
    // Result contains all output after completion
    return result;
  }}
/>
```

**After (Streaming Pattern):**

```typescript
<ActionToolbar
  onActionStart={(actionId) => {
    // Parent manages streaming state
    setRunningActionId(actionId);
    setShowLogPanel(true);
    // Register streaming listeners
  }}
  runningActionId={runningActionId}
/>
```

### Rationale

The old pattern blocked until action completion, providing no real-time feedback during long-running operations. The new pattern enables:

- Real-time output display in LogPanel
- Non-blocking UI during action execution
- Ability to cancel/monitor long-running actions
- Better UX for operations that take >5 seconds

### Migration Steps

1. **Remove `executeAction` prop** from ActionToolbar
2. **Add state for streaming** in parent component:
   ```typescript
   const [showLogPanel, setShowLogPanel] = useState(false);
   const [actionLogs, setActionLogs] = useState<LogLine[]>([]);
   const [actionStatus, setActionStatus] = useState<
     "running" | "success" | "error"
   >("running");
   const [runningActionId, setRunningActionId] = useState<string | null>(null);
   ```
3. **Add `onActionStart` handler**:

   ```typescript
   const handleActionStart = (actionId: string) => {
     setRunningActionId(actionId);
     setShowLogPanel(true);
     setActionLogs([]);
     setActionStatus("running");

     // Register streaming listeners
     window.erkdesk.onActionOutput((event) => {
       setActionLogs((prev) => [...prev, event]);
     });

     window.erkdesk.onActionCompleted((event) => {
       setActionStatus(event.success ? "success" : "error");
       setRunningActionId(null);
     });

     // Start the action
     const action = actions.find((a) => a.id === actionId);
     if (action) {
       window.erkdesk.startStreamingAction(action, worktreePath);
     }
   };
   ```

4. **Pass `onActionStart` and `runningActionId` to ActionToolbar**:
   ```typescript
   <ActionToolbar
     onActionStart={handleActionStart}
     runningActionId={runningActionId}
   />
   ```
5. **Add LogPanel component**:
   ```typescript
   {showLogPanel && (
     <LogPanel
       logs={actionLogs}
       status={actionStatus}
       onDismiss={() => setShowLogPanel(false)}
     />
   )}
   ```
6. **Add cleanup on unmount**:
   ```typescript
   useEffect(() => {
     return () => {
       window.erkdesk.removeActionListeners();
     };
   }, []);
   ```

### Testing Migration

After migrating:

1. Trigger a long-running action (e.g., submit, land)
2. Verify LogPanel appears with "running" status
3. Verify logs stream in real-time as action executes
4. Verify status changes to "success" or "error" on completion
5. Verify dismiss button hides LogPanel
6. Verify starting second action doesn't accumulate listeners (no memory leak)

### Related Documentation

- [Erkdesk IPC Streaming Architecture](../architecture/erkdesk-ipc-streaming.md) - Streaming event patterns
- [Desktop Dash Interaction Model](interaction-model.md) - Phase 2 implementation details
- [Erkdesk Components](erkdesk-components.md) - LogPanel reference
