---
title: Forge Vite Setup
last_audited: "2026-02-03 15:30 PT"
audit_result: clean
read_when:
  - "configuring Electron Forge with Vite"
  - "understanding erkdesk build configuration"
  - "debugging Vite build issues in Electron"
  - "adding new build targets or configs"
---

# Forge Vite Setup

Erkdesk uses Electron Forge's VitePlugin to orchestrate three separate Vite builds: main process, preload script, and renderer process. Each has its own configuration file with specific settings for its execution environment.

## Overview

**Orchestrator**: `forge.config.ts` defines the VitePlugin configuration

**Build targets**:

1. Main process → `vite.main.config.ts`
2. Preload script → `vite.preload.config.ts`
3. Renderer process → `src/renderer/vite.config.ts`

## forge.config.ts

**File**: `erkdesk/forge.config.ts`

```typescript
import type { ForgeConfig } from "@electron-forge/shared-types";
import { VitePlugin } from "@electron-forge/plugin-vite";
import { MakerZIP } from "@electron-forge/maker-zip";

const config: ForgeConfig = {
  packagerConfig: {
    asar: true, // Package app into ASAR archive
  },
  makers: [new MakerZIP({}, ["darwin", "linux", "win32"])],
  plugins: [
    new VitePlugin({
      build: [
        {
          entry: "src/main/index.ts",
          config: "vite.main.config.ts",
          target: "main",
        },
        {
          entry: "src/main/preload.ts",
          config: "vite.preload.config.ts",
          target: "preload",
        },
      ],
      renderer: [
        {
          name: "main_window",
          config: "src/renderer/vite.config.ts",
        },
      ],
    }),
  ],
};
```

**Key settings**:

- `asar: true` — Packages app into archive for distribution
- `makers: [MakerZIP]` — Cross-platform distribution via ZIP archives
- `build` array — Main and preload process configurations
- `renderer` array — Renderer process configurations (can have multiple windows)

## vite.main.config.ts

**Target**: Node.js environment (Electron main process)

**File**: `erkdesk/vite.main.config.ts`

```typescript
import { defineConfig } from "vite";

export default defineConfig({
  resolve: {
    mainFields: ["module", "jsnext:main", "jsnext"],
  },
});
```

**Settings**:

- `mainFields` — ESM module resolution priority
  - Prefers `module` field in package.json (ESM entry point)
  - Falls back to `jsnext:main` and `jsnext` (legacy ESM fields)
  - Ensures main process uses ESM modules when available

**Why this matters**: Node.js in Electron supports both CommonJS and ESM. Prioritizing ESM improves tree-shaking and reduces bundle size.

## vite.preload.config.ts

**Target**: Preload script (bridge between main and renderer)

**File**: `erkdesk/vite.preload.config.ts`

```typescript
import { defineConfig } from "vite";

export default defineConfig({
  build: {
    rollupOptions: {
      external: ["electron"],
    },
  },
});
```

**Settings**:

- `external: ["electron"]` — Electron module NOT bundled
  - Preload script runs in renderer with Node.js access
  - `electron` module provided by Electron runtime, not bundled
  - Prevents bundling Electron's massive native modules

**Why this matters**: Bundling `electron` into preload would bloat the bundle and cause runtime errors (can't bundle native modules).

**Result**: Minimal preload bundle containing only application-specific bridge code.

## src/renderer/vite.config.ts

**Target**: Browser environment (React renderer process)

**File**: `erkdesk/src/renderer/vite.config.ts`

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
});
```

**Settings**:

- `plugins: [react()]` — React plugin enabled
  - JSX transformation
  - React Fast Refresh (HMR)
  - Development optimizations

**Why this matters**: Renderer process is a web environment running React. The React plugin provides the standard React development experience.

**HMR in dev**: Changes to React components update instantly without full reload.

## Build Process Flow

### Development Mode (`pnpm start`)

1. Electron Forge starts Vite dev servers for all three targets
2. Main process: Watches `src/main/index.ts`, rebuilds on change
3. Preload: Watches `src/main/preload.ts`, rebuilds on change
4. Renderer: Starts dev server with HMR for React app
5. Electron launches with dev server URLs
6. DevTools auto-open for debugging

### Production Build (`pnpm run package`)

1. Vite builds main process (ESM bundle)
2. Vite builds preload script (minimal bundle, `electron` external)
3. Vite builds renderer (React production build)
4. Electron Forge packages all three into ASAR archive
5. Output in `out/` directory

### Distribution (`pnpm run make`)

1. Runs production build
2. MakerZIP creates platform-specific ZIP archives
3. Outputs to `out/make/`:
   - `erkdesk-darwin-arm64-{version}.zip` (macOS)
   - `erkdesk-linux-x64-{version}.zip` (Linux)
   - `erkdesk-win32-x64-{version}.zip` (Windows)

## MakerZIP Configuration

```typescript
makers: [new MakerZIP({}, ["darwin", "linux", "win32"])];
```

**Platforms**: Builds for macOS (darwin), Linux, and Windows (win32)

**Why ZIP**: Simple cross-platform distribution without platform-specific installers.

**Future**: Can add:

- `MakerDMG` for macOS disk images
- `MakerDeb` for Debian/Ubuntu packages
- `MakerSquirrel` for Windows installers

## Common Patterns

### Adding a New Renderer Window

To add a second window:

```typescript
renderer: [
  {
    name: "main_window",
    config: "src/renderer/vite.config.ts",
  },
  {
    name: "settings_window",
    config: "src/settings/vite.config.ts", // New config
  },
];
```

Each renderer gets its own Vite dev server and build.

### Debugging Build Issues

**Problem**: Build fails with module resolution error

**Solution**: Check which target is failing:

- Main process errors → Check `vite.main.config.ts` mainFields
- Preload errors → Check `external` configuration
- Renderer errors → Check React plugin setup

**Logs**: Electron Forge shows which Vite config is building:

```
[build] [main] Building main process...
[build] [preload] Building preload script...
[build] [renderer:main_window] Building renderer...
```

## Related Documentation

- [Erkdesk Project Structure](erkdesk-project-structure.md) - Overall architecture
- [Main Process Startup](main-process-startup.md) - Main process implementation
- [Preload Bridge Patterns](preload-bridge-patterns.md) - Preload script patterns
