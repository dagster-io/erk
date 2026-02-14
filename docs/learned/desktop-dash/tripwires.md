---
title: Desktop Dash Tripwires
read_when:
  - "working on desktop-dash code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from desktop-dash/*.md frontmatter -->

# Desktop Dash Tripwires

Rules triggered by matching actions in code.

**Introduce a status color outside the five-color palette** → Read [Visual Status Indicators](visual-status-indicators.md) first. Map to the canonical five colors (green/amber/purple/red/gray) rather than adding new ones. See the color semantics table in this doc.

**Never expose ipcRenderer directly** → Read [Preload Bridge Patterns](preload-bridge-patterns.md) first. only wrap individual channels as named methods

**Render status indicators from backend-provided display strings** → Read [Visual Status Indicators](visual-status-indicators.md) first. Status indicators must derive from raw state fields via pure functions, not pre-rendered strings. See state-derivation-pattern.md.

**Tests mock window.erkdesk, not ipcRenderer** → Read [Preload Bridge Patterns](preload-bridge-patterns.md) first. the bridge is the test boundary

**adding IPC handler without updating all 4 locations** → Read [erkdesk IPC Action Pattern](ipc-actions.md) first. Every IPC handler requires updates in main/index.ts (handler), main/preload.ts (bridge), types/erkdesk.d.ts (types), and tests. Missing any location compiles fine but fails at runtime.

**adding IPC handlers** → Read [Main Process Startup](main-process-startup.md) first. Every new IPC handler needs matching cleanup in mainWindow.on("closed") — use removeAllListeners for ipcMain.on, removeHandler for ipcMain.handle

**adding a new IPC channel in createWindow** → Read [WebContentsView Lifecycle](webcontentsview-lifecycle.md) first. Every ipcMain.on() or ipcMain.handle() registration MUST have a matching removal in the mainWindow.on('closed') handler. on() uses removeAllListeners(channel), handle() uses removeHandler(channel). Add both in the same commit.

**adding a new action outside the ACTIONS array** → Read [erkdesk Action Toolbar](action-toolbar.md) first. All actions must be entries in the ACTIONS array in ActionToolbar.tsx. Don't create standalone action definitions elsewhere.

**adding a new action without a test case** → Read [erkdesk Action Toolbar](action-toolbar.md) first. ActionToolbar.test.tsx tests every action's availability predicate AND generated command. New actions need both.

**adding a persistent server process for erkdesk** → Read [Backend Communication Pattern Decision](backend-communication.md) first. CLI shelling was chosen deliberately. Python startup (~200ms) is noise compared to GitHub API latency (~1.5-2s). Don't optimize the wrong bottleneck.

**adding state to child components** → Read [erkdesk App Architecture](app-architecture.md) first. PlanList, ActionToolbar, and LogPanel are fully controlled (stateless). All state lives in App.tsx. Pass props down, callbacks up.

**changing right pane size** → Read [SplitPane Renderer-Native Coordination](split-pane-implementation.md) first. every code path that changes the right pane's rendered size must trigger a bounds report to the main process

**choosing subprocess patterns for IPC** → Read [Main Process Startup](main-process-startup.md) first. Use execFile for request/response IPC, spawn for streaming IPC — do not mix the patterns

**configuring Vite preload externals** → Read [Forge Vite Setup](forge-vite-setup.md) first. Do NOT remove external electron from the preload config — bundling electron causes runtime failures

**configuring Vite renderer targets** → Read [Forge Vite Setup](forge-vite-setup.md) first. Do NOT add Node.js builtins or electron to the renderer Vite config — renderer is a browser environment

**configuring erkdesk as workspace member** → Read [Erkdesk Project Structure](erkdesk-project-structure.md) first. Do NOT add erkdesk as a pnpm workspace member — it is intentionally standalone

**configuring vitest globals** → Read [Vitest Configuration for erkdesk](vitest-setup.md) first. globals and tsconfig types must stay in sync — `globals: true` in vitest.config.ts without "vitest/globals" in tsconfig.json causes type errors at edit time but tests still pass, creating a confusing split

**consolidating Vite configs** → Read [Forge Vite Setup](forge-vite-setup.md) first. Do NOT put all three targets in one Vite config — each targets a different JavaScript runtime

**debugging module resolution errors in Electron** → Read [pnpm Hoisting Pattern for Electron](pnpm-hoisting-pattern.md) first. Do NOT assume 'Cannot find module' errors mean a missing dependency — in Electron with pnpm, check .npmrc first

**designing notification features** → Read [Desktop Dashboard Interaction Model](interaction-model.md) first. Notification/badge system is planned but NOT implemented. Don't assume infrastructure exists for state-diff detection, OS notifications, or row badges.

**duplicating PlanDataProvider logic in TypeScript** → Read [Backend Communication Pattern Decision](backend-communication.md) first. erkdesk delegates all data fetching to `erk exec dash-data`. The Python side owns data assembly — erkdesk is a thin rendering shell over CLI output.

**exposing ipcRenderer directly through context bridge** → Read [erkdesk Security Architecture](security.md) first. NEVER expose ipcRenderer as a whole object. Wrap each channel as a named method on window.erkdesk. Direct exposure gives the renderer unrestricted access to all IPC channels.

**forgetting to remove IPC handlers on window close** → Read [erkdesk IPC Action Pattern](ipc-actions.md) first. The mainWindow 'closed' handler must remove every registered handler and kill any active subprocess. Without this, macOS window re-activation double-registers handlers.

**forgetting to remove event listeners on renderer unmount** → Read [erkdesk IPC Action Pattern](ipc-actions.md) first. Call removeActionListeners() in useEffect cleanup. React strict mode double-mounts in development, stacking listeners and causing double-fires.

**forgetting to return cleanup function from useEffect intervals** → Read [Erkdesk Auto-Refresh Patterns](erkdesk-auto-refresh-patterns.md) first. Always return () => clearInterval(intervalId) from useEffect to prevent multiple intervals running simultaneously.

**implementing WebView IPC channels** → Read [WebView IPC Design Decisions](webview-api.md) first. WebView IPC channels (bounds, URL) must be fire-and-forget (send/on), never request-response (invoke/handle) — invoke serializes high-frequency updates and causes visible lag

**implementing blocking action execution** → Read [erkdesk Action Toolbar](action-toolbar.md) first. Actions use streaming execution via IPC (startStreamingAction). Never await or block the UI thread on action completion. App.tsx owns the streaming lifecycle.

**implementing split pane cleanup** → Read [SplitPane Renderer-Native Coordination](split-pane-implementation.md) first. cleanup lives in the main process window-close handler, not in the SplitPane component

**loading URLs on every render without deduplication** → Read [Erkdesk Auto-Refresh Patterns](erkdesk-auto-refresh-patterns.md) first. Use useRef to track lastLoadedUrl. Compare against ref before calling loadWebViewURL() — IPC calls are expensive and cause visible webview flicker.

**loading URLs without deduplication** → Read [erkdesk App Architecture](app-architecture.md) first. lastLoadedUrlRef prevents redundant IPC calls. Always check if the URL actually changed before calling loadWebViewURL.

**making GitHub API calls from the Electron main process** → Read [erkdesk Security Architecture](security.md) first. Token isolation depends on CLI shelling. If the main process calls GitHub directly, tokens must transit through Electron, breaking the three-layer security model.

**modifying CI job dependencies** → Read [Erkdesk Project Structure](erkdesk-project-structure.md) first. Do NOT add erkdesk-tests to the autofix job's needs list in CI

**modifying erkdesk/.npmrc configuration** → Read [pnpm Hoisting Pattern for Electron](pnpm-hoisting-pattern.md) first. Do NOT remove erkdesk/.npmrc or change node-linker away from hoisted — Electron cannot resolve pnpm's symlinked node_modules layout

**passing GitHub tokens through IPC or storing them in the renderer** → Read [erkdesk Security Architecture](security.md) first. GitHub tokens must NEVER reach the renderer or main process. All GitHub API calls happen in the Python backend via CLI shelling.

**performing this action** → Read [Preload Bridge Patterns](preload-bridge-patterns.md) first. Check the relevant documentation.

**performing this action** → Read [Preload Bridge Patterns](preload-bridge-patterns.md) first. Check the relevant documentation.

**porting a TUI modal or overlay to erkdesk** → Read [Desktop Dashboard Interaction Model](interaction-model.md) first. The right pane (WebContentsView showing live GitHub) replaces all TUI modals. Don't build detail modals — the embedded GitHub page provides richer context than any custom UI.

**preserving selection by array index across refresh** → Read [erkdesk App Architecture](app-architecture.md) first. Auto-refresh reorders plans. Selection must be preserved by issue_number, not by index. See the setInterval effect in App.tsx.

**proposing a web-only SPA or Textual-web for the dashboard** → Read [Desktop App Framework Evaluation](framework-evaluation.md) first. Browser-based approaches cannot embed GitHub pages due to X-Frame-Options. This constraint was the deciding factor — see the framework evaluation.

**registering IPC handlers** → Read [Main Process Startup](main-process-startup.md) first. Register IPC handlers inside createWindow(), not at module scope — macOS activate re-calls createWindow, causing duplicate listeners

**rendering content in right pane** → Read [SplitPane Renderer-Native Coordination](split-pane-implementation.md) first. the right pane div is a positioning placeholder only — it renders no content, the WebContentsView overlays it

**replacing good data with error states during refresh** → Read [Erkdesk Auto-Refresh Patterns](erkdesk-auto-refresh-patterns.md) first. Return early from refresh on error. Keep showing last good data instead of flashing an error state that auto-resolves on next successful refresh.

**requiring keyboard shortcuts for actions** → Read [Desktop Dashboard Interaction Model](interaction-model.md) first. Erkdesk uses discoverability-first design. Toolbar buttons and (future) context menus are primary. Keyboard shortcuts are secondary convenience, not required paths.

**running erkdesk tests** → Read [Vitest Configuration for erkdesk](vitest-setup.md) first. erkdesk tests run separately from the Python suite — `make fast-ci` and `make all-ci` do NOT include them; use `make erkdesk-test`

**running pnpm commands for erkdesk** → Read [Erkdesk Project Structure](erkdesk-project-structure.md) first. Do NOT run pnpm commands from the repo root — always cd into erkdesk/ first

**setting WebContentsView bounds** → Read [Main Process Startup](main-process-startup.md) first. WebContentsView starts at zero bounds — renderer must report bounds before it becomes visible

**setting WebContentsView initial bounds** → Read [WebView IPC Design Decisions](webview-api.md) first. the WebContentsView starts at zero bounds intentionally; do not set initial bounds in createWindow — see defensive-bounds-handling.md

**spawning streaming processes** → Read [Main Process Startup](main-process-startup.md) first. Kill activeAction before spawning a new streaming process — concurrent subprocess conflicts cause interleaved output

**storing derived state in useState** → Read [erkdesk App Architecture](app-architecture.md) first. selectedPlan is computed inline from plans[selectedIndex], not stored in state. Never cache derived values — compute them on render.

**updating ErkdeskAPI interface** → Read [Vitest Configuration for erkdesk](vitest-setup.md) first. the window.erkdesk mock in setup.ts must match the ErkdeskAPI interface — adding a new IPC method requires updating both the type definition and the mock or TypeScript will catch the mismatch

**updating state directly instead of using functional setState in interval callbacks** → Read [Erkdesk Auto-Refresh Patterns](erkdesk-auto-refresh-patterns.md) first. Interval closures capture stale state. Use functional setState (setPrevState => ...) to read latest values inside setInterval callbacks.

**using Electron view components** → Read [Erkdesk Project Structure](erkdesk-project-structure.md) first. Do NOT use BrowserView — use WebContentsView (BrowserView is deprecated)

**using an iframe to embed GitHub content in erkdesk** → Read [Desktop App Framework Evaluation](framework-evaluation.md) first. GitHub sets X-Frame-Options: deny. Iframes respect this header and will be blocked. Only native browser contexts (WebContentsView) bypass it.

**using blocking execution for long-running actions** → Read [erkdesk IPC Action Pattern](ipc-actions.md) first. Use streaming for actions >1s. Blocking execution freezes the entire Electron renderer (single-threaded) — no scrolling, no input, no feedback.

**using ipcMain.handle for streaming or ipcMain.on for blocking** → Read [erkdesk IPC Action Pattern](ipc-actions.md) first. handle for streaming = Promise that never resolves. on for blocking = renderer gets no result. Match the Electron API to the communication pattern.

**using the Electron <webview> tag instead of WebContentsView** → Read [Desktop App Framework Evaluation](framework-evaluation.md) first. <webview> is soft-deprecated. WebContentsView is the recommended successor with better security isolation and performance.

**using this pattern** → Read [Defensive Bounds Handling](defensive-bounds-handling.md) first. never pass renderer-reported bounds directly to Electron setBounds() without clamping

**using this pattern** → Read [Defensive Bounds Handling](defensive-bounds-handling.md) first. always clamp at the main process trust boundary, not only in the renderer
