---
audit_result: edited
last_audited: "2026-02-08"
read_when:
  - debugging Vite build errors in erkdesk
  - adding a new Vite build target or renderer window
  - understanding why a config setting exists in a specific Vite config
title: Forge Vite Setup
tripwires:
  - action: Do NOT add Node.js builtins or electron to the renderer Vite config
    warning: renderer is a browser environment
  - action: Do NOT remove external electron from the preload config
    warning: bundling electron causes runtime failures
  - action: Do NOT put all three targets in one Vite config
    warning: each targets a different JavaScript runtime
---

# Forge Vite Setup

Erkdesk's three Vite configs exist because each Electron build target runs in a fundamentally different JavaScript runtime. This doc explains **why** each config has its specific settings — for the three-target architecture overview, see [Erkdesk Project Structure](erkdesk-project-structure.md).

## Why Each Config Differs

<!-- Source: erkdesk/forge.config.ts, VitePlugin configuration -->

The VitePlugin in `forge.config.ts` orchestrates three separate Vite builds. Each config solves a runtime-specific problem:

| Config                        | Key Setting                                       | Why It Exists                                                                 |
| ----------------------------- | ------------------------------------------------- | ----------------------------------------------------------------------------- |
| `vite.main.config.ts`         | `mainFields: ["module", "jsnext:main", "jsnext"]` | Prioritizes ESM entry points over CommonJS for better tree-shaking in Node.js |
| `vite.preload.config.ts`      | `external: ["electron"]`                          | Electron's native modules can't be bundled — they must come from the runtime  |
| `src/renderer/vite.config.ts` | `plugins: [react()]`                              | Browser environment needs JSX transformation and React Fast Refresh for HMR   |

### Preload Externalization Is Critical

<!-- Source: erkdesk/vite.preload.config.ts, rollupOptions.external -->

The preload script **must** externalize `electron` because Electron provides this module at runtime as a native binding. Attempting to bundle it causes two failures: the bundle bloats with unresolvable native code, and `contextBridge`/`ipcRenderer` imports fail at runtime. This is the most common build misconfiguration.

### Main Process ESM Priority

<!-- Source: erkdesk/vite.main.config.ts, resolve.mainFields -->

The main process overrides Vite's default `mainFields` to prefer ESM entry points (`module`, `jsnext:main`, `jsnext`). Electron's Node.js runtime supports both CommonJS and ESM, but ESM enables tree-shaking that significantly reduces bundle size for dependencies with dual module formats.

## Dev vs Production vs Distribution

Three `pnpm` commands map to increasingly complete build pipelines:

| Command            | What It Does                                                           | Output            |
| ------------------ | ---------------------------------------------------------------------- | ----------------- |
| `pnpm start`       | Starts Vite dev servers with HMR + file watching for all three targets | Live Electron app |
| `pnpm run package` | Production Vite builds, then packages into ASAR archive                | `out/` directory  |
| `pnpm run make`    | Runs `package`, then creates platform ZIP archives via MakerZIP        | `out/make/*.zip`  |

In dev mode, Electron Forge injects global constants (`MAIN_WINDOW_VITE_DEV_SERVER_URL`, `MAIN_WINDOW_VITE_NAME`) that the main process uses to load from the Vite dev server instead of bundled files. See [Main Process Startup](main-process-startup.md) for how these globals control loading.

## Debugging Build Failures

Electron Forge log prefixes identify which target failed:

```
[build] [main] ...          → check vite.main.config.ts
[build] [preload] ...       → check vite.preload.config.ts
[build] [renderer:main_window] ... → check src/renderer/vite.config.ts
```

Common failure patterns:

| Symptom                                    | Likely Cause                                                   |
| ------------------------------------------ | -------------------------------------------------------------- |
| Module resolution error in main            | `mainFields` not finding ESM entry for a dependency            |
| `Cannot find module 'electron'` in preload | `electron` missing from `external` array                       |
| JSX/TSX syntax error in renderer           | React plugin not loaded or misconfigured                       |
| `require is not defined` in renderer       | Code accidentally importing Node.js modules in browser context |

## Adding a New Renderer Window

Each renderer entry in `forge.config.ts` gets its own Vite dev server and independent build. To add a second window, add a new entry to the `renderer` array in `forge.config.ts` with a unique `name` and its own Vite config file. The new config follows the same pattern as `src/renderer/vite.config.ts` — browser-targeted with the React plugin.

## Related Documentation

- [Erkdesk Project Structure](erkdesk-project-structure.md) — Three-target architecture overview and standalone project rationale
- [Main Process Startup](main-process-startup.md) — How Forge globals control dev vs production loading
- [Preload Bridge Patterns](preload-bridge-patterns.md) — Why preload needs electron externalized (the security model it enables)
- [pnpm Hoisting Pattern](pnpm-hoisting-pattern.md) — Why hoisted linker is required for Forge's Vite plugin
