<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->

# Desktop Dash Documentation

- **[action-toolbar.md](action-toolbar.md)** — adding new actions to the erkdesk toolbar, modifying action availability predicates, understanding how toolbar actions connect to IPC streaming
- **[app-architecture.md](app-architecture.md)** — modifying App.tsx state or effects, understanding the WebView overlay approach, adding new state or auto-refresh behavior to erkdesk
- **[backend-communication.md](backend-communication.md)** — choosing how erkdesk communicates with the Python backend, evaluating whether to add a persistent backend server, understanding why erkdesk shells out to CLI commands
- **[erkdesk-auto-refresh-patterns.md](erkdesk-auto-refresh-patterns.md)** — building auto-refreshing UI components in erkdesk, adding periodic data fetching with IPC-backed webview loading, debugging duplicate webview loads or stale data after refresh
- **[framework-evaluation.md](framework-evaluation.md)** — choosing a framework for the desktop dashboard, embedding GitHub pages in an application, evaluating Electron alternatives for erkdesk, understanding why Electron was chosen over Tauri or web-only approaches
- **[interaction-model.md](interaction-model.md)** — designing new erkdesk UX features, deciding whether to port a TUI feature to the desktop dashboard, adding action discovery mechanisms (context menus, shortcuts), planning notification or badge features for erkdesk
- **[ipc-actions.md](ipc-actions.md)** — adding new IPC handlers to erkdesk, choosing between streaming and blocking execution, debugging IPC event flow or memory leaks
- **[security.md](security.md)** — adding IPC methods or context bridge APIs to erkdesk, handling credentials or tokens in the desktop app, configuring BrowserWindow security settings, reviewing erkdesk for security concerns
- **[visual-status-indicators.md](visual-status-indicators.md)** — implementing visual status indicators in erkdesk, adding color-coded status to the erkdesk plan list, migrating erkdesk from pre-rendered display strings to derived status
