---
title: Desktop App Framework Evaluation
read_when:
  - "choosing a framework for the desktop dashboard"
  - "embedding GitHub pages in an application"
  - "evaluating Electron alternatives for erkdesk"
  - "understanding why Electron was chosen over Tauri or web-only approaches"
tripwires:
  - action: "using an iframe to embed GitHub content in erkdesk"
    warning: "GitHub sets X-Frame-Options: deny. Iframes respect this header and will be blocked. Only native browser contexts (WebContentsView) bypass it."
    score: 9
  - action: "using the Electron <webview> tag instead of WebContentsView"
    warning: "<webview> is soft-deprecated. WebContentsView is the recommended successor with better security isolation and performance."
    score: 7
  - action: "proposing a web-only SPA or Textual-web for the dashboard"
    warning: "Browser-based approaches cannot embed GitHub pages due to X-Frame-Options. This constraint was the deciding factor — see the framework evaluation."
    score: 6
---

# Desktop App Framework Evaluation

## The Deciding Constraint: X-Frame-Options

**GitHub sets `X-Frame-Options: deny` on most pages.** This single HTTP header eliminated three of five evaluated approaches, because any approach using standard browser embedding (iframes) cannot render GitHub content inline.

The core requirement — showing GitHub PRs/issues alongside a plan list in a unified interface — demands a native browser context that operates outside the web security model. Only desktop app frameworks with native webview APIs can bypass `X-Frame-Options`.

## Framework Decision

| Framework                 | X-Frame-Options                | Why eliminated / chosen                                  |
| ------------------------- | ------------------------------ | -------------------------------------------------------- |
| **Electron**              | **Bypassed** (WebContentsView) | **CHOSEN.** Mature ecosystem, React/TS, no new languages |
| Tauri                     | Bypassed (system webview)      | Viable, but adds Rust to a Python-only stack             |
| Textual-web               | Blocked (iframe)               | Fatal: can't embed GitHub pages                          |
| Web SPA                   | Blocked (iframe)               | Fatal: can't embed GitHub pages                          |
| Hybrid TUI + browser tabs | N/A (opens tabs)               | Defeats the purpose — no unified interface               |

**Why Electron over Tauri**: Both solve the X-Frame-Options problem. Electron won because it doesn't introduce a new language. Erk is Python + TypeScript today — Tauri would add Rust as a third language with its own toolchain, dependency management, and learning curve. Tauri's advantages (smaller bundle, lower memory) don't justify that cost for a single-user developer tool.

**Why not "just open tabs"**: The hybrid approach (TUI + browser) was the lowest-effort option but defeats the core requirement. The value of erkdesk is the unified view — selecting a plan and immediately seeing its PR/issue without context-switching.

## Electron Embedding Methods

Within Electron, there are three ways to embed external web content. The choice matters because two of the three fail for GitHub:

| Method              | X-Frame-Options         | Status                                 | Process model                              |
| ------------------- | ----------------------- | -------------------------------------- | ------------------------------------------ |
| **WebContentsView** | **Bypassed**            | Recommended (successor to BrowserView) | Main process — separate browser context    |
| `<webview>` tag     | Bypassed                | Soft-deprecated                        | Renderer process — guest page in renderer  |
| `<iframe>`          | **Respected (blocked)** | Standard web                           | Renderer process — subject to web security |

**Why WebContentsView wins**: It creates a separate browser context at the main process level, which means `X-Frame-Options` headers are irrelevant — there's no parent frame to deny. The `<webview>` tag also bypasses the restriction but is soft-deprecated with security concerns (guest runs in the renderer process). Standard iframes simply don't work.

**The architectural cost**: WebContentsView is a native overlay managed by the main process, not a React component. This means layout coordination requires IPC — the renderer measures where the GitHub pane should be and sends bounds to the main process, which positions the native view. This three-way coordination (SplitPane → IPC → main process) is more complex than a simple iframe `src` prop but is the only approach that works.

<!-- Source: erkdesk/src/main/index.ts, WebContentsView creation and webview:update-bounds handler -->
<!-- Source: erkdesk/src/renderer/components/SplitPane.tsx, reportBounds callback -->

See the `WebContentsView` creation in `erkdesk/src/main/index.ts` and the `reportBounds` callback in `SplitPane.tsx` for the overlay coordination pattern.

## When to Reconsider

**Tauri becomes worth revisiting if**:

- Rust is added to the stack for another reason (eliminates the "new language" objection)
- Bundle size becomes a distribution concern (Electron ~200MB vs Tauri ~10MB)
- Cross-platform webview consistency improves (macOS/Windows/Linux webview differences were a concern)

**The X-Frame-Options constraint is unlikely to change** — it's a deliberate security decision by GitHub, not a bug.

## Related Documentation

- [erkdesk App Architecture](app-architecture.md) — WebView overlay mechanics, state ownership, streaming actions
- [Backend Communication](backend-communication.md) — Why CLI shelling instead of a persistent server
- [Forge/Vite Setup](forge-vite-setup.md) — Three-target Vite build configuration
