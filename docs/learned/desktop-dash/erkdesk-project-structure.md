---
title: Erkdesk Project Structure
read_when:
  - working on erkdesk codebase
  - adding new erkdesk features or components
  - debugging erkdesk build or packaging issues
  - understanding why erkdesk is structured differently from the Python codebase
tripwires:
  - action: "configuring erkdesk as workspace member"
    warning: "Do NOT add erkdesk as a pnpm workspace member — it is intentionally standalone"
  - action: "using Electron view components"
    warning: "Do NOT use BrowserView — use WebContentsView (BrowserView is deprecated)"
  - action: "running pnpm commands for erkdesk"
    warning: "Do NOT run pnpm commands from the repo root — always cd into erkdesk/ first"
  - action: "modifying CI job dependencies"
    warning: "Do NOT add erkdesk-tests to the autofix job's needs list in CI"
last_audited: "2026-02-08 00:00 PT"
audit_result: clean
---

# Erkdesk Project Structure

Erkdesk is a standalone Electron desktop app within the erk repository. Understanding _why_ it's structured this way prevents common mistakes when adding features or debugging builds.

## Why Standalone (Not a Workspace)

Erkdesk has its own `package.json` and `pnpm-lock.yaml` — it is **not** a pnpm workspace member. Three reasons drove this decision:

1. **Dependency isolation** — Electron's dependency tree is massive and entirely unrelated to the Python codebase. Workspace hoisting would pull these into the root, creating confusion and potential conflicts.
2. **Build simplicity** — Electron Forge expects a self-contained project. Workspace member resolution adds a layer of indirection that complicates packaging and distribution.
3. **Independent lifecycle** — erkdesk dependencies update on a different cadence than the Python tooling. Separate lockfiles prevent one from blocking the other.

**Consequence**: All pnpm/npm commands must run from within `erkdesk/`. The root Makefile wraps this with `erkdesk-*` targets — see `Makefile` for the current set.

## Three-Target Build Architecture

Electron apps require three distinct bundles that target different JavaScript runtimes. Erkdesk uses three separate Vite configs orchestrated by Electron Forge's VitePlugin:

| Target         | Runtime                   | Config                        | Purpose                                      |
| -------------- | ------------------------- | ----------------------------- | -------------------------------------------- |
| Main process   | Node.js                   | `vite.main.config.ts`         | Window management, IPC, subprocess spawning  |
| Preload script | Node.js + renderer bridge | `vite.preload.config.ts`      | Context bridge exposing `window.erkdesk` API |
| Renderer       | Browser (React)           | `src/renderer/vite.config.ts` | UI with HMR in dev mode                      |

<!-- Source: erkdesk/forge.config.ts, VitePlugin configuration -->

The VitePlugin in `forge.config.ts` wires these three configs together. This is the central coordination point — when adding a new entry point or changing build behavior, start there.

**Why three configs matter**: Each target has different module resolution, externalization rules, and output formats. The main process needs Node.js builtins; the preload must externalize `electron`; the renderer must not access Node.js APIs. Mixing these up causes cryptic runtime errors.

## Distribution: MakerZIP Only

Erkdesk uses MakerZIP for all platforms (darwin, linux, win32) — simple unzip-and-run distribution. This was chosen over platform-specific installers (DMG, DEB, Squirrel) because erkdesk is developer-only tooling where installation ceremony adds no value.

<!-- Source: erkdesk/forge.config.ts, makers array -->

## CI: Intentionally Excluded from Autofix

The `erkdesk-tests` job in `.github/workflows/ci.yml` runs tests in parallel with Python CI, but it is **excluded** from the `autofix` job's `needs` list.

**Why**: The autofix job can only remediate linting/formatting failures. Test failures require code changes that autofix cannot make. If erkdesk-tests were in the needs list, any test failure would block autofix from running — preventing it from fixing the very lint issues it _can_ handle.

## Hoisted Node Linker

<!-- Source: erkdesk/.npmrc -->

Erkdesk uses `node-linker=hoisted` in `.npmrc`. See [pnpm Hoisting Pattern](pnpm-hoisting-pattern.md) for why this is required — Electron Forge's Vite plugin has compatibility issues with pnpm's default symlinked `node_modules` layout.

**Anti-pattern**: Removing the `.npmrc` or switching to `isolated` linker. This will cause Electron Forge builds to fail with module resolution errors that are difficult to diagnose.

## Related Documentation

- [Forge Vite Setup](forge-vite-setup.md) — Detailed Vite configuration patterns
- [Main Process Startup](main-process-startup.md) — Main process architecture and window creation
- [Preload Bridge Patterns](preload-bridge-patterns.md) — Context bridge and IPC type safety
- [pnpm Hoisting Pattern](pnpm-hoisting-pattern.md) — Why hoisted linker is required
- [Vitest Setup](vitest-setup.md) — Testing configuration with jsdom
- [App Architecture](app-architecture.md) — Component hierarchy and state flow
- [erkdesk Component Testing](../testing/erkdesk-component-testing.md) — React component testing patterns
- [erkdesk Makefile Targets](../cli/erkdesk-makefile-targets.md) — Complete make targets reference
