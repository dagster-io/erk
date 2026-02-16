---
title: erkdesk Security Architecture
read_when:
  - adding IPC methods or context bridge APIs to erkdesk
  - handling credentials or tokens in the desktop app
  - configuring BrowserWindow security settings
  - reviewing erkdesk for security concerns
tripwires:
  - action: "exposing ipcRenderer directly through context bridge"
    warning: "NEVER expose ipcRenderer as a whole object. Wrap each channel as a named method on window.erkdesk. Direct exposure gives the renderer unrestricted access to all IPC channels."
  - action: "passing GitHub tokens through IPC or storing them in the renderer"
    warning: "GitHub tokens must NEVER reach the renderer or main process. All GitHub API calls happen in the Python backend via CLI shelling."
  - action: "making GitHub API calls from the Electron main process"
    warning: "Token isolation depends on CLI shelling. If the main process calls GitHub directly, tokens must transit through Electron, breaking the three-layer security model."
last_audited: "2026-02-16 08:00 PT"
audit_result: clean
---

# erkdesk Security Architecture

Erkdesk's security model emerges from three architectural decisions reinforcing each other: Electron's context isolation, the CLI shelling backend pattern, and the named-method bridge contract. These are documented separately in [preload bridge patterns](preload-bridge-patterns.md), [backend communication](backend-communication.md), and [framework evaluation](framework-evaluation.md) — this doc explains how they combine into a coherent security posture.

## The Three-Layer Trust Model

Most Electron apps have two layers (main + renderer). Erkdesk's CLI shelling architecture creates a third, and this shapes the entire security model:

| Layer                       | Trust Level             | Has Token Access | Talks To                                |
| --------------------------- | ----------------------- | ---------------- | --------------------------------------- |
| Renderer (React)            | Untrusted               | No               | Preload bridge only (`window.erkdesk`)  |
| Main process (Node.js)      | Trusted for IPC routing | No               | Renderer via IPC, Python via subprocess |
| Python backend (`erk exec`) | Fully trusted           | Yes              | GitHub API, local filesystem            |

**The key insight**: The main process is a _router_, not a _consumer_ of GitHub tokens. It forwards requests to Python via CLI shelling and returns results. Even a compromised main process cannot leak tokens — they never transit through Electron at all.

This is a stronger guarantee than "we don't pass the token" — the architecture _cannot_ pass it because the main process never has it. The guarantee exists as an emergent property of the [CLI shelling decision](backend-communication.md), not because of explicit prevention code.

**When this would break**: If erkdesk ever made direct GitHub API calls from the main process (e.g., for lower latency), tokens would need to transit through Electron. The [backend communication doc](backend-communication.md) discusses when the CLI shelling model might be reconsidered — any such change would require revisiting this security model.

## Why Both Electron Security Settings Are Required

Every `BrowserWindow` and `WebContentsView` must use `contextIsolation: true` and `nodeIntegration: false`. Either setting alone is insufficient:

- **Without `contextIsolation`**: Renderer code can reach into the preload script's scope to access `ipcRenderer` directly, bypassing the named-method bridge entirely.
- **Without `nodeIntegration: false`**: Renderer code can `require('electron')` and access Node.js APIs, making the bridge irrelevant.

<!-- Source: erkdesk/src/main/index.ts, BrowserWindow webPreferences -->

See the `BrowserWindow` constructor and `WebContentsView` constructor in `erkdesk/src/main/index.ts` — both apply identical security settings.

## Named-Method Bridge as Security Allowlist

The preload bridge pattern is documented in [preload bridge patterns](preload-bridge-patterns.md) for its development implications. The security dimension is distinct: each bridge method is an **explicit capability grant**. If a new IPC channel is added to the main process, the renderer _cannot_ access it until someone adds a corresponding bridge method. This is an allowlist, not a denylist.

The alternative — exposing `ipcRenderer` as a whole object — would give the renderer access to every channel, including channels added in the future. Any XSS vulnerability in the renderer would escalate to arbitrary IPC invocations.

## WebContentsView Isolation

The GitHub content pane uses `WebContentsView`, which creates a separate browser context managed by the main process. The security implications go beyond the [X-Frame-Options bypass](framework-evaluation.md) that motivated its use:

- **Separate context**: The WebContentsView's browsing context is isolated from the React renderer. A compromised GitHub page cannot access the `window.erkdesk` bridge.
- **No script injection path**: The main process loads URLs into the WebContentsView but never injects scripts. The view is read-only from erkdesk's perspective.
- **Minimal IPC surface**: The only IPC channels touching the WebContentsView are geometry updates (`webview:update-bounds`) and URL loading (`webview:load-url`). No data flows from the GitHub page back into erkdesk.

## Security Checklist for New Features

When adding erkdesk features, verify:

- BrowserWindow `webPreferences` include both `contextIsolation: true` and `nodeIntegration: false`
- New IPC methods are exposed as named bridge methods, not raw channel access
- No GitHub tokens or credentials appear in IPC messages or renderer code
- All GitHub API calls route through Python backend via CLI subprocess
- Main process handlers validate IPC payloads before acting (currently minimal — `webview:load-url` validates URL type but `actions:execute` does not validate command/args)
- Streaming IPC listeners have cleanup methods to prevent accumulation (see [preload bridge patterns](preload-bridge-patterns.md))

## Related Documentation

- [Preload Bridge Patterns](preload-bridge-patterns.md) — Four-place rule and IPC style selection
- [Backend Communication](backend-communication.md) — Why CLI shelling, and when it might change
- [Framework Evaluation](framework-evaluation.md) — Why Electron, and WebContentsView vs alternatives
- [App Architecture](app-architecture.md) — State ownership and streaming action lifecycle
