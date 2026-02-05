---
title: Erkdesk Project Structure
read_when:
  - "working on erkdesk codebase"
  - "understanding Electron Forge Vite setup"
  - "adding new erkdesk features"
  - "debugging erkdesk build issues"
last_audited: "2026-02-05 09:45 PT"
audit_result: edited
---

# Erkdesk Project Structure

Erkdesk is a standalone pnpm project implementing an Electron desktop application using Electron Forge with Vite. It is **not** a pnpm workspace — it's a self-contained Electron app within the erk repository.

## Directory Layout

See `erkdesk/` for current structure. Key locations:

- `src/main/` — Electron main process (Node.js)
- `src/renderer/` — Renderer process (React)
- `forge.config.ts` — Electron Forge configuration

## Build System Architecture

### Three Vite Build Targets

Erkdesk uses **three separate Vite configurations** orchestrated by Electron Forge's VitePlugin:

1. **Main Process** (`vite.main.config.ts`) — Node.js environment, creates the Electron main process bundle
2. **Preload Script** (`vite.preload.config.ts`) — Renderer with Node.js access, minimal bundle for context bridge
3. **Renderer Process** (`src/renderer/vite.config.ts`) — Browser environment with React and HMR

**Key insight**: Electron Forge coordinates all three builds via `forge.config.ts`, ensuring they work together correctly. See `erkdesk/forge.config.ts` for the VitePlugin configuration.

## Makefile Targets

Run `make erkdesk-<target>` for development operations. See `Makefile` for exact commands:

- `erkdesk-start` — Launch in dev mode (HMR, auto-reload, DevTools)
- `erkdesk-package` — Create packaged app (no installer)
- `erkdesk-make` — Create distributables (ZIP for darwin/linux/win32)
- `erkdesk-test` — Run test suite

## Standalone vs Workspace

**Erkdesk is NOT a pnpm workspace member**:

- Has its own `package.json` and `pnpm-lock.yaml`
- Dependencies managed independently

**Why standalone?**:

- Electron dependency tree is large and isolated
- Avoids pnpm workspace hoisting complications
- Simpler build and packaging configuration

## Distribution Strategy

Uses **MakerZIP** for cross-platform distribution (simple unzip-and-run). Future options: MakerDMG (macOS), MakerDeb (Linux), MakerSquirrel (Windows).

## CI Integration

The `erkdesk-tests` job in `.github/workflows/ci.yml` runs tests on every push.

**Key CI property**: The `erkdesk-tests` job is **excluded** from the `autofix` job's needs list. Why? Autofix can only fix linting/formatting issues, not test failures. Including test jobs would block the pipeline on failures autofix cannot resolve.

## Related Documentation

- [Forge Vite Setup](forge-vite-setup.md) - Detailed Vite configuration patterns
- [Main Process Startup](main-process-startup.md) - Main process architecture
- [Preload Bridge Patterns](preload-bridge-patterns.md) - Context bridge setup
- [pnpm Hoisting Pattern](pnpm-hoisting-pattern.md) - Critical .npmrc configuration
- [Vitest Setup](vitest-setup.md) - Testing configuration and patterns
- [erkdesk Component Testing](../testing/erkdesk-component-testing.md) - React component testing guide
- [erkdesk Makefile Targets](../cli/erkdesk-makefile-targets.md) - Complete make targets reference
