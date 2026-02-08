<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->

# Desktop Dash Documentation

- **[action-toolbar.md](action-toolbar.md)** — adding new actions to the erkdesk toolbar, modifying action availability predicates, understanding how toolbar actions connect to IPC streaming
- **[app-architecture.md](app-architecture.md)** — modifying App.tsx state or effects, understanding the WebView overlay approach, adding new state or auto-refresh behavior to erkdesk
- **[backend-communication.md](backend-communication.md)** — choosing how erkdesk communicates with the Python backend, evaluating whether to add a persistent backend server, understanding why erkdesk shells out to CLI commands
- **[defensive-bounds-handling.md](defensive-bounds-handling.md)** — working with WebContentsView bounds in erkdesk, debugging Electron crashes related to setBounds, adding new IPC handlers that pass coordinates to Electron APIs
- **[erkdesk-auto-refresh-patterns.md](erkdesk-auto-refresh-patterns.md)** — building auto-refreshing UI components in erkdesk, adding periodic data fetching with IPC-backed webview loading, debugging duplicate webview loads or stale data after refresh
- **[erkdesk-project-structure.md](erkdesk-project-structure.md)** — working on erkdesk codebase, adding new erkdesk features or components, debugging erkdesk build or packaging issues, understanding why erkdesk is structured differently from the Python codebase
- **[forge-vite-setup.md](forge-vite-setup.md)** — debugging Vite build errors in erkdesk, adding a new Vite build target or renderer window, understanding why a config setting exists in a specific Vite config
- **[framework-evaluation.md](framework-evaluation.md)** — choosing a framework for the desktop dashboard, embedding GitHub pages in an application, evaluating Electron alternatives for erkdesk, understanding why Electron was chosen over Tauri or web-only approaches
- **[interaction-model.md](interaction-model.md)** — designing new erkdesk UX features, deciding whether to port a TUI feature to the desktop dashboard, adding action discovery mechanisms (context menus, shortcuts), planning notification or badge features for erkdesk
- **[ipc-actions.md](ipc-actions.md)** — adding new IPC handlers to erkdesk, choosing between streaming and blocking execution, debugging IPC event flow or memory leaks
- **[main-process-startup.md](main-process-startup.md)** — adding IPC handlers to the main process, debugging window recreation or listener leak issues on macOS, choosing between execFile and spawn for a new IPC handler
- **[pnpm-hoisting-pattern.md](pnpm-hoisting-pattern.md)** — setting up new Electron projects with pnpm, encountering cryptic Electron module resolution errors, debugging 'Cannot find module' errors in Electron, configuring pnpm for Electron compatibility
- **[preload-bridge-patterns.md](preload-bridge-patterns.md)** — exposing Node.js APIs to Electron renderer, implementing IPC communication in erkdesk, understanding context bridge security, adding new erkdesk capabilities
- **[security.md](security.md)** — implementing Electron context bridge, working with erkdesk frontend-backend communication, handling GitHub tokens in desktop app, setting up Electron security settings
- **[split-pane-implementation.md](split-pane-implementation.md)** — working on split-pane layout, debugging bounds reporting, implementing resizable panels in erkdesk
- **[visual-status-indicators.md](visual-status-indicators.md)** — implementing visual status indicators in erkdesk, designing CSS-only status dots with color semantics, understanding the backend data contract for status derivation
- **[vitest-setup.md](vitest-setup.md)** — setting up test infrastructure for erkdesk, adding new tests to erkdesk, understanding erkdesk test environment
- **[webcontentsview-lifecycle.md](webcontentsview-lifecycle.md)** — working with WebContentsView in erkdesk, implementing split-pane with embedded webview, setting up IPC for bounds updates
- **[webview-api.md](webview-api.md)** — working with WebContentsView in erkdesk, implementing split-pane layout, debugging bounds updates or URL loading
