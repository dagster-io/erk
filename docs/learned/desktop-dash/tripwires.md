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

**CRITICAL: Before adding IPC handler without updating all 4 locations** → Read [erkdesk IPC Action Pattern](ipc-actions.md) first. Every IPC handler requires updates in 4 files: main/index.ts (handler), main/preload.ts (bridge), types/erkdesk.d.ts (types), tests (mock). Missing any location breaks type safety or tests.

**CRITICAL: Before adding a new action without updating ACTIONS array** → Read [erkdesk Action Toolbar](action-toolbar.md) first. ACTIONS is exported and can be reused in context menus. Add new ActionDef entries to the ACTIONS array, not as separate one-offs.

**CRITICAL: Before breaking the auto-refresh selection preservation logic** → Read [erkdesk App Component Architecture](app-architecture.md) first. Auto-refresh preserves selection by issue_number, not by array index. Always use issue_number to find the new index after refresh.

**CRITICAL: Before creating WebContentsView or setting bounds** → Read [WebContentsView Lifecycle](webcontentsview-lifecycle.md) first. Initialize with zero bounds {x: 0, y: 0, width: 0, height: 0}, wait for renderer to report measurements. Always apply defensive clamping: Math.max(0, Math.floor(value)) to prevent fractional/negative coordinates that cause Electron crashes. Clean up IPC listeners on window close.

**CRITICAL: Before forgetting to remove IPC handlers on window close** → Read [erkdesk IPC Action Pattern](ipc-actions.md) first. Call removeHandler() and removeAllListeners() in mainWindow.on('closed') handler. See main/index.ts:190-201 for the pattern. Prevents memory leaks and dangling handlers.

**CRITICAL: Before forgetting to remove event listeners on renderer unmount** → Read [erkdesk IPC Action Pattern](ipc-actions.md) first. Call removeActionListeners() in useEffect cleanup to prevent memory leaks. See App.tsx lines 124-126 for the pattern.

**CRITICAL: Before forgetting to return cleanup function from useEffect intervals** → Read [Erkdesk Auto-Refresh Patterns](erkdesk-auto-refresh-patterns.md) first. Always return () => clearInterval(intervalId) from useEffect to prevent memory leaks and multiple intervals running.

**CRITICAL: Before handling GitHub tokens in frontend code** → Read [erkdesk Security Architecture](security.md) first. GitHub tokens must NEVER reach the renderer process. Keep all GitHub API calls in the Python backend layer.

**CRITICAL: Before implementing Electron IPC without context bridge** → Read [erkdesk Security Architecture](security.md) first. NEVER expose Node.js APIs directly to renderer. Use context bridge with preload script. Set contextIsolation: true, nodeIntegration: false.

**CRITICAL: Before implementing blocking action execution** → Read [erkdesk Action Toolbar](action-toolbar.md) first. Actions use streaming execution (startStreamingAction), not blocking. Never await or block the UI thread on action completion.

**CRITICAL: Before loading URLs on every render without deduplication** → Read [Erkdesk Auto-Refresh Patterns](erkdesk-auto-refresh-patterns.md) first. Use useRef to track lastLoadedUrl. Compare url !== lastLoadedUrlRef.current before calling loadWebViewURL() to prevent redundant IPC calls.

**CRITICAL: Before replacing good data with error states during refresh** → Read [Erkdesk Auto-Refresh Patterns](erkdesk-auto-refresh-patterns.md) first. Return early from refresh on error (if (!result.success) return). Keep showing last good data instead of empty state.

**CRITICAL: Before storing derived state in useState** → Read [erkdesk App Component Architecture](app-architecture.md) first. App.tsx follows state lifting: only store plan data, selectedIndex, loading, error, and log state. Derived values like selectedPlan are computed inline.

**CRITICAL: Before updating state directly instead of using functional setState** → Read [Erkdesk Auto-Refresh Patterns](erkdesk-auto-refresh-patterns.md) first. Use setPlans((prevPlans) => ...) and setSelectedIndex((prevIndex) => ...) to ensure reading latest state when multiple updates are queued.

**CRITICAL: Before using blocking execution for long-running actions** → Read [erkdesk IPC Action Pattern](ipc-actions.md) first. Use streaming (startStreamingAction + events) for actions >1s. Blocking execution (executeAction) freezes the UI.
