---
title: Desktop App Framework Evaluation
read_when:
  - "choosing a framework for the desktop dashboard"
  - "embedding GitHub pages in an application"
  - "understanding why Electron was chosen for the desktop dashboard"
---

# Desktop App Framework Evaluation

Analysis of five framework approaches for the erk desktop dashboard, focusing on the critical constraint: embedding GitHub pages that set `X-Frame-Options: deny`.

## The Deciding Constraint

**GitHub sets `X-Frame-Options: deny` on most pages.** This HTTP header instructs browsers to block iframe embedding, preventing GitHub pages from being rendered inside web views.

This constraint eliminates most web-based approaches and forces us toward native browser embedding solutions that operate outside the standard web security model.

## Evaluated Approaches

### 1. Textual-web (Eliminated)

**Concept:** Run Textual TUI in a WebSocket-connected web frontend.

**Pros:**

- Reuse existing TUI code
- Web-based (no desktop app packaging)
- Textual already battle-tested

**Cons:**

- **FATAL:** Cannot embed GitHub pages (X-Frame-Options blocks iframe)
- Would need to open GitHub pages in separate browser tabs (defeats the purpose)
- WebSocket connection adds complexity
- No access to OS-level notifications

**Verdict:** Eliminated due to iframe restriction.

---

### 2. Electron (CHOSEN)

**Concept:** Desktop app using Electron's `WebContentsView` to embed GitHub pages.

**Pros:**

- **SOLVES IFRAME RESTRICTION:** WebContentsView creates a separate browser context that bypasses X-Frame-Options
- Mature ecosystem (React, TypeScript, npm)
- Native OS integration (notifications, menu bar, file system)
- Built-in Chrome DevTools for debugging
- WebContentsView is the recommended approach (successor to BrowserView)
- Active development and documentation

**Cons:**

- Large bundle size (~200MB with Chromium)
- Memory footprint (~150MB idle)
- Electron-specific APIs for main/renderer IPC

**Verdict:** CHOSEN. Only reliable way to embed GitHub pages without iframe restrictions.

---

### 3. Tauri (Viable Alternative)

**Concept:** Rust-based alternative to Electron using system WebView.

**Pros:**

- Smaller bundle size (~10MB, no bundled browser)
- Lower memory footprint (~50MB)
- Native webview bypasses X-Frame-Options (same as Electron)
- Rust backend could be more performant

**Cons:**

- **Adds Rust to the stack** (erk is Python-only today)
- Smaller ecosystem and community compared to Electron
- System webview differences across macOS/Windows/Linux
- Additional language/tooling burden for team

**Verdict:** Viable but adds complexity. Electron preferred for ecosystem maturity and no new languages.

---

### 4. Full Web App (Eliminated)

**Concept:** Browser-based SPA, no desktop packaging.

**Pros:**

- No app packaging or distribution
- Fastest development (just React + API)
- Easy deployment (static hosting)

**Cons:**

- **FATAL:** Cannot embed GitHub pages (X-Frame-Options blocks iframe)
- Would need to open GitHub pages in separate tabs
- No OS-level notifications without service workers
- Can't monitor local Claude sessions directly

**Verdict:** Eliminated due to iframe restriction.

---

### 5. Hybrid Terminal + Browser (Eliminated)

**Concept:** Keep existing Textual TUI, add `erk dash open-pr` command to open browser tabs.

**Pros:**

- Minimal new code
- Reuse all existing TUI infrastructure
- No app packaging

**Cons:**

- **Defeats the purpose:** Embedded view was the goal
- Context switching between terminal and browser
- No unified interface
- Loses notification integration benefits

**Verdict:** Doesn't meet requirements.

## Electron WebContentsView vs `<webview>` Tag vs iframe

Electron offers three ways to embed web content. Only one is recommended.

### WebContentsView (RECOMMENDED)

**How it works:** Managed at the main process level, overlaid on the window as a separate browser context.

**Pros:**

- **Bypasses X-Frame-Options** (separate browser context)
- Recommended approach (successor to BrowserView)
- Better security isolation
- Better performance
- Active development

**Cons:**

- Main process coordination required for layout
- Slightly more complex setup than `<webview>` tag

**Verdict:** Use this.

### `<webview>` Tag (SOFT-DEPRECATED)

**How it works:** Custom HTML element that embeds a guest page in the renderer process.

**Pros:**

- Simple HTML-like API
- Bypasses X-Frame-Options

**Cons:**

- Soft-deprecated (Electron docs recommend WebContentsView)
- Security concerns (guest runs in renderer process)
- Less performant than WebContentsView
- Uncertain future support

**Verdict:** Avoid. WebContentsView is better.

### iframe (DOES NOT WORK)

**How it works:** Standard HTML iframe element.

**Pros:**

- Standard web API
- Simple to use

**Cons:**

- **FATAL:** Respects X-Frame-Options (blocked by GitHub)
- Cannot embed GitHub pages
- Useless for this use case

**Verdict:** Does not work for GitHub embedding.

## Implementation Architecture

Given the choice of Electron + WebContentsView:

```
┌─────────────────────────────────────┐
│     Electron Main Process           │
│  (Node.js + Electron native APIs)   │
│                                     │
│  - Window management                │
│  - WebContentsView overlay          │
│  - CLI shelling to Python backend   │
│  - OS notifications                 │
└─────────────────────────────────────┘
           │                    │
           ↓                    ↓
  ┌────────────────┐   ┌──────────────────┐
  │ Renderer       │   │ WebContentsView  │
  │ (React + TS)   │   │ (GitHub pages)   │
  │                │   │                  │
  │ - Plan list    │   │ - Live PR view   │
  │ - Toolbar      │   │ - Issue view     │
  │ - Filters      │   │ - Actions runs   │
  └────────────────┘   └──────────────────┘
```

**Key Pattern:** WebContentsView is a sibling to the main renderer window, not a child. Main process coordinates layout and positioning.

## Related Documentation

- [Desktop Dashboard Backend Communication](backend-communication.md) - How Electron talks to Python backend
- [Desktop Dashboard Interaction Model](interaction-model.md) - How the desktop UI differs from TUI
