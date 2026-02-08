---
title: Desktop Dash Tripwires
read_when:
  - "working on desktop-dash code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from desktop-dash/*.md frontmatter -->

# Desktop Dash Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before Introduce a status color outside the five-color palette** → Read [Visual Status Indicators](visual-status-indicators.md) first. Map to the canonical five colors (green/amber/purple/red/gray) rather than adding new ones. See the color semantics table in this doc.

**CRITICAL: Before adding IPC handler without updating all 4 locations** → Read [erkdesk IPC Action Pattern](ipc-actions.md) first. Every IPC handler requires updates in main/index.ts (handler), main/preload.ts (bridge), types/erkdesk.d.ts (types), and tests. Missing any location compiles fine but fails at runtime.

**CRITICAL: Before adding a new action outside the ACTIONS array** → Read [erkdesk Action Toolbar](action-toolbar.md) first. All actions must be entries in the ACTIONS array in ActionToolbar.tsx. Don't create standalone action definitions elsewhere.

**CRITICAL: Before adding a new action without a test case** → Read [erkdesk Action Toolbar](action-toolbar.md) first. ActionToolbar.test.tsx tests every action's availability predicate AND generated command. New actions need both.

**CRITICAL: Before adding a persistent server process for erkdesk** → Read [Backend Communication Pattern Decision](backend-communication.md) first. CLI shelling was chosen deliberately. Python startup (~200ms) is noise compared to GitHub API latency (~1.5-2s). Don't optimize the wrong bottleneck.

**CRITICAL: Before adding state to child components** → Read [erkdesk App Architecture](app-architecture.md) first. PlanList, ActionToolbar, and LogPanel are fully controlled (stateless). All state lives in App.tsx. Pass props down, callbacks up.

**CRITICAL: Before adding IPC handler without updating all 4 locations** → Read [erkdesk IPC Action Pattern](ipc-actions.md) first. Every IPC handler requires updates in main/index.ts (handler), main/preload.ts (bridge), types/erkdesk.d.ts (types), and tests. Missing any location compiles fine but fails at runtime.

**CRITICAL: Before designing notification features** → Read [Desktop Dashboard Interaction Model](interaction-model.md) first. Notification/badge system is planned but NOT implemented. Don't assume infrastructure exists for state-diff detection, OS notifications, or row badges.

**CRITICAL: Before duplicating PlanDataProvider logic in TypeScript** → Read [Backend Communication Pattern Decision](backend-communication.md) first. erkdesk delegates all data fetching to `erk exec dash-data`. The Python side owns data assembly — erkdesk is a thin rendering shell over CLI output.

**CRITICAL: Before forgetting to remove IPC handlers on window close** → Read [erkdesk IPC Action Pattern](ipc-actions.md) first. The mainWindow 'closed' handler must remove every registered handler and kill any active subprocess. Without this, macOS window re-activation double-registers handlers.

**CRITICAL: Before forgetting to remove event listeners on renderer unmount** → Read [erkdesk IPC Action Pattern](ipc-actions.md) first. Call removeActionListeners() in useEffect cleanup. React strict mode double-mounts in development, stacking listeners and causing double-fires.

**CRITICAL: Before forgetting to return cleanup function from useEffect intervals** → Read [Erkdesk Auto-Refresh Patterns](erkdesk-auto-refresh-patterns.md) first. Always return () => clearInterval(intervalId) from useEffect to prevent multiple intervals running simultaneously.

**CRITICAL: Before adding a new IPC channel in createWindow** → Read [WebContentsView Lifecycle](webcontentsview-lifecycle.md) first. Every ipcMain.on() or ipcMain.handle() registration MUST have a matching removal in the mainWindow.on('closed') handler. on() uses removeAllListeners(channel), handle() uses removeHandler(channel). Add both in the same commit.

**CRITICAL: Before adding a new action outside the ACTIONS array** → Read [erkdesk Action Toolbar](action-toolbar.md) first. All actions must be entries in the ACTIONS array in ActionToolbar.tsx. Don't create standalone action definitions elsewhere.

**CRITICAL: Before implementing blocking action execution** → Read [erkdesk Action Toolbar](action-toolbar.md) first. Actions use streaming execution via IPC (startStreamingAction). Never await or block the UI thread on action completion. App.tsx owns the streaming lifecycle.

**CRITICAL: Before loading URLs on every render without deduplication** → Read [Erkdesk Auto-Refresh Patterns](erkdesk-auto-refresh-patterns.md) first. Use useRef to track lastLoadedUrl. Compare against ref before calling loadWebViewURL() — IPC calls are expensive and cause visible webview flicker.

**CRITICAL: Before loading URLs without deduplication** → Read [erkdesk App Architecture](app-architecture.md) first. lastLoadedUrlRef prevents redundant IPC calls. Always check if the URL actually changed before calling loadWebViewURL.

**CRITICAL: Before porting a TUI modal or overlay to erkdesk** → Read [Desktop Dashboard Interaction Model](interaction-model.md) first. The right pane (WebContentsView showing live GitHub) replaces all TUI modals. Don't build detail modals — the embedded GitHub page provides richer context than any custom UI.

**CRITICAL: Before preserving selection by array index across refresh** → Read [erkdesk App Architecture](app-architecture.md) first. Auto-refresh reorders plans. Selection must be preserved by issue_number, not by index. See the setInterval effect in App.tsx.

**CRITICAL: Before proposing a web-only SPA or Textual-web for the dashboard** → Read [Desktop App Framework Evaluation](framework-evaluation.md) first. Browser-based approaches cannot embed GitHub pages due to X-Frame-Options. This constraint was the deciding factor — see the framework evaluation.

**CRITICAL: Before replacing good data with error states during refresh** → Read [Erkdesk Auto-Refresh Patterns](erkdesk-auto-refresh-patterns.md) first. Return early from refresh on error. Keep showing last good data instead of flashing an error state that auto-resolves on next successful refresh.

**CRITICAL: Before requiring keyboard shortcuts for actions** → Read [Desktop Dashboard Interaction Model](interaction-model.md) first. Erkdesk uses discoverability-first design. Toolbar buttons and (future) context menus are primary. Keyboard shortcuts are secondary convenience, not required paths.

**CRITICAL: Before storing derived state in useState** → Read [erkdesk App Architecture](app-architecture.md) first. selectedPlan is computed inline from plans[selectedIndex], not stored in state. Never cache derived values — compute them on render.

**CRITICAL: Before updating state directly instead of using functional setState in interval callbacks** → Read [Erkdesk Auto-Refresh Patterns](erkdesk-auto-refresh-patterns.md) first. Interval closures capture stale state. Use functional setState (setPrevState => ...) to read latest values inside setInterval callbacks.

**CRITICAL: Before using an iframe to embed GitHub content in erkdesk** → Read [Desktop App Framework Evaluation](framework-evaluation.md) first. GitHub sets X-Frame-Options: deny. Iframes respect this header and will be blocked. Only native browser contexts (WebContentsView) bypass it.

**CRITICAL: Before using blocking execution for long-running actions** → Read [erkdesk IPC Action Pattern](ipc-actions.md) first. Use streaming for actions >1s. Blocking execution freezes the entire Electron renderer (single-threaded) — no scrolling, no input, no feedback.

**CRITICAL: Before using ipcMain.handle for streaming or ipcMain.on for blocking** → Read [erkdesk IPC Action Pattern](ipc-actions.md) first. handle for streaming = Promise that never resolves. on for blocking = renderer gets no result. Match the Electron API to the communication pattern.

**CRITICAL: Before using the Electron <webview> tag instead of WebContentsView** → Read [Desktop App Framework Evaluation](framework-evaluation.md) first. <webview> is soft-deprecated. WebContentsView is the recommended successor with better security isolation and performance.
