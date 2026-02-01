---
title: Erkdesk Project Structure
read_when:
  - "working on erkdesk codebase"
  - "understanding Electron Forge Vite setup"
  - "adding new erkdesk features"
  - "debugging erkdesk build issues"
---

# Erkdesk Project Structure

Erkdesk is a standalone pnpm project implementing an Electron desktop application using Electron Forge with Vite. It is **not** a pnpm workspace — it's a self-contained Electron app within the erk repository.

## Directory Layout

```
erkdesk/
├── src/
│   ├── main/          # Electron main process (Node.js)
│   │   ├── index.ts   # Main process entry point
│   │   └── preload.ts # Preload script (context bridge)
│   └── renderer/      # Renderer process (React)
│       ├── App.tsx    # React application
│       ├── index.tsx  # Renderer entry point
│       └── vite.config.ts  # Renderer-specific Vite config
├── forge.config.ts    # Electron Forge configuration
├── vite.main.config.ts     # Main process Vite config
├── vite.preload.config.ts  # Preload script Vite config
├── package.json       # Dependencies and scripts
├── .npmrc             # pnpm configuration (hoisted mode)
└── tsconfig.json      # TypeScript configuration
```

## Build System Architecture

### Three Vite Build Targets

Erkdesk uses **three separate Vite configurations** orchestrated by Electron Forge's VitePlugin:

1. **Main Process** (`vite.main.config.ts`)
   - Target: Node.js environment
   - Entry: `src/main/index.ts`
   - ESM module resolution
   - Creates the Electron main process bundle

2. **Preload Script** (`vite.preload.config.ts`)
   - Target: Renderer process (but with Node.js access)
   - Entry: `src/main/preload.ts`
   - Externalizes `electron` dependency
   - Minimal bundle for context bridge

3. **Renderer Process** (`src/renderer/vite.config.ts`)
   - Target: Browser environment
   - Entry: `src/renderer/index.tsx`
   - React plugin enabled
   - HMR (Hot Module Replacement) in development

### Forge Configuration

The `forge.config.ts` file orchestrates the build:

```typescript
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
});
```

**Key insight**: Electron Forge coordinates all three builds, ensuring they work together correctly.

## Makefile Targets

Three make targets provide erkdesk operations:

### erkdesk-start

```bash
make erkdesk-start
```

**Action**: `cd erkdesk && pnpm start`

Launches the Electron app in development mode with:

- HMR for renderer process
- Auto-reload for main process changes
- DevTools auto-open

### erkdesk-package

```bash
make erkdesk-package
```

**Action**: `cd erkdesk && pnpm run package`

Creates a packaged application (no installer):

- Bundles app for current platform
- ASAR archive enabled
- Ready for local testing

### erkdesk-make

```bash
make erkdesk-make
```

**Action**: `cd erkdesk && pnpm run make`

Creates distributable artifacts:

- ZIP archives via MakerZIP
- Supports: darwin, linux, win32
- Output in `out/make/` directory

## Standalone vs Workspace

**Erkdesk is NOT a pnpm workspace member**:

- Has its own `package.json` and `pnpm-lock.yaml`
- Dependencies managed independently
- No shared workspace dependencies

**Why standalone?**:

- Electron dependency tree is large and isolated
- Avoids pnpm workspace hoisting complications
- Simpler build and packaging configuration

## Distribution Strategy

The project uses **MakerZIP** for cross-platform distribution:

```typescript
makers: [new MakerZIP({}, ["darwin", "linux", "win32"])];
```

**Benefits**:

- Simple cross-platform distribution (no platform-specific installers yet)
- Users unzip and run
- Future: Can add MakerDMG (macOS), MakerDeb (Linux), MakerSquirrel (Windows)

## Development Workflow

1. **Start development server**:

   ```bash
   make erkdesk-start
   ```

2. **Make changes**:
   - Main process: Edit `src/main/index.ts`, auto-reload triggers
   - Renderer: Edit `src/renderer/App.tsx`, HMR updates instantly
   - Preload: Edit `src/main/preload.ts`, auto-reload triggers

3. **Test packaging**:

   ```bash
   make erkdesk-package
   ```

4. **Build distributables**:
   ```bash
   make erkdesk-make
   ```

## Testing

Erkdesk uses **Vitest + React Testing Library + jsdom** for component testing.

### Test Stack

- **Vitest**: Fast test runner with native ESM support
- **React Testing Library**: Component testing with user-centric queries
- **jsdom**: Simulated DOM environment for Node.js

### Running Tests

```bash
# Via pnpm
cd erkdesk && pnpm test

# Via make
make erkdesk-test
```

### CI Integration

The `erkdesk-tests` job in `.github/workflows/ci.yml` runs the test suite on every push. Tests must pass before merge.

**Key CI property**: The `erkdesk-tests` job is **excluded** from the `autofix` job's needs list. Why? The autofix job can only fix linting/formatting issues, not test failures. Including test jobs would cause the entire pipeline to block on test failures that autofix cannot resolve.

### Configuration

See [Vitest Setup](vitest-setup.md) for detailed configuration patterns, including:

- Test file patterns and discovery
- jsdom environment configuration
- Coverage setup
- Mock patterns for window/DOM APIs

## Related Documentation

- [Forge Vite Setup](forge-vite-setup.md) - Detailed Vite configuration patterns
- [Main Process Startup](main-process-startup.md) - Main process architecture
- [Preload Bridge Patterns](preload-bridge-patterns.md) - Context bridge setup
- [pnpm Hoisting Pattern](pnpm-hoisting-pattern.md) - Critical .npmrc configuration
- [Vitest Setup](vitest-setup.md) - Testing configuration and patterns
- [erkdesk Component Testing](../testing/erkdesk-component-testing.md) - React component testing guide
- [erkdesk Makefile Targets](../cli/erkdesk-makefile-targets.md) - Complete make targets reference
