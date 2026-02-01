# Plan: Add Streaming Log Panel for Action Buttons

## Goal

When an action button is pressed in the ActionToolbar, show a bottom log panel that streams stdout/stderr from the running erk CLI command in real-time, with success/failure status on completion.

## Current State

- ActionToolbar has 5 buttons that call `execFile` via IPC and **discard the result**
- No feedback to the user beyond a "running" button label

## Architecture

```
ActionToolbar --onActionStart(id, cmd, args)--> App
App --startStreamingAction(cmd, args)--> preload --> main (spawn)
main --action:output{stream, data}--> preload --> App (appends to state)
main --action:completed{success, error?}--> preload --> App (sets final status)
App --logLines, logStatus--> LogPanel
Layout change --> SplitPane ResizeObserver --> reportBounds() --> WebContentsView repositions
```

## Changes

### 1. Types (`erkdesk/src/types/erkdesk.d.ts`)
- Add `ActionOutputEvent { stream: "stdout"|"stderr", data: string }`
- Add `ActionCompletedEvent { success: boolean, error?: string }`
- Add to `ErkdeskAPI`: `startStreamingAction`, `onActionOutput`, `onActionCompleted`, `removeActionListeners`

### 2. Main process (`erkdesk/src/main/index.ts`)
- Import `spawn` from `child_process`
- Add `actions:start-streaming` IPC listener that uses `spawn` instead of `execFile`
- Stream stdout/stderr chunks via `webContents.send("action:output", ...)`
- Send `action:completed` on close/error
- Track `activeAction` to kill previous if a new one starts
- Strip ANSI codes before sending (`/\x1B\[[0-9;]*m/g`)
- Clean up listener + kill process in `mainWindow.on("closed")`

### 3. Preload (`erkdesk/src/main/preload.ts`)
- Add `startStreamingAction`: sends `actions:start-streaming` via `ipcRenderer.send`
- Add `onActionOutput`: registers `ipcRenderer.on("action:output", ...)`
- Add `onActionCompleted`: registers `ipcRenderer.on("action:completed", ...)`
- Add `removeActionListeners`: removes both listeners

### 4. New `LogPanel` component (`erkdesk/src/renderer/components/LogPanel.tsx` + `.css`)
- Props: `lines: LogLine[]`, `status: "running"|"success"|"error"`, `onDismiss: () => void`
- Fixed 200px height, `flex-shrink: 0`, dark theme matching existing palette
- Header bar with status indicator + dismiss button
- Scrollable content area, auto-scrolls to bottom on new lines
- stderr lines in distinct color (orange/red)
- Monospace font

### 5. SplitPane ResizeObserver (`erkdesk/src/renderer/components/SplitPane.tsx`)
- Add `ResizeObserver` on `rightPaneRef` to call `reportBounds()` on any size change
- This ensures WebContentsView repositions when the log panel appears/disappears below

### 6. ActionToolbar refactor (`erkdesk/src/renderer/components/ActionToolbar.tsx`)
- Replace internal `runningAction` state with props from App: `runningActionId: string | null`
- Add `onActionStart(actionId, command, args)` callback prop
- On click, call `onActionStart` instead of `window.erkdesk.executeAction`

### 7. App wiring (`erkdesk/src/renderer/App.tsx`)
- New state: `logLines`, `logStatus`, `logVisible`, `runningActionId`
- `handleActionStart`: clears log, shows panel, calls `window.erkdesk.startStreamingAction`
- `useEffect` to register/cleanup streaming listeners
- Render `LogPanel` below `SplitPane` when `logVisible`

### 8. Tests
- Update `ActionToolbar.test.tsx` for new props
- Update `App.test.tsx` for log panel visibility and streaming behavior
- New `LogPanel.test.tsx` for rendering, auto-scroll, dismiss

## Implementation Order

1. Types
2. Main process (streaming IPC)
3. Preload (bridge)
4. LogPanel + CSS (new component)
5. SplitPane ResizeObserver
6. ActionToolbar refactor
7. App wiring
8. Tests

## Verification

- Run `make -C erkdesk test` (vitest) to verify all tests pass
- Launch erkdesk, select a plan, press an action button, confirm log panel appears with streaming output
- Confirm log panel dismiss button works and WebContentsView repositions correctly
- Confirm stderr appears in distinct color
- Confirm success/failure status shows after command completes