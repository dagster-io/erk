# Plan: Scaffold erkdesk Electron + React + TypeScript App

**Objective:** #6423, Step 1.2
**Goal:** Create a minimal working Electron app in `erkdesk/` that launches a window and renders a React component. No plan data, no WebContentsView, no split pane — just the scaffold.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Bundler | Vite | Fast HMR, excellent React/TS support, modern |
| Electron tooling | electron-forge | Official recommendation, built-in Vite plugin |
| Package manager | npm | Simple, no extra tooling, CI already uses Node 20 |
| TypeScript | Strict mode, separate configs for main/renderer | Main = Node types, renderer = DOM types |

## Project Structure

```
erkdesk/
├── package.json
├── tsconfig.json              # Root TS config
├── forge.config.ts            # electron-forge config
├── vite.main.config.ts        # Vite config for main process
├── vite.preload.config.ts     # Vite config for preload script
├── .gitignore                 # Node-specific ignores
├── src/
│   ├── main/
│   │   ├── index.ts           # Electron entry: create BrowserWindow
│   │   ├── preload.ts         # Preload script (contextBridge stub)
│   │   └── tsconfig.json      # Node.js types
│   └── renderer/
│       ├── index.html         # HTML entry
│       ├── index.tsx          # React entry (createRoot)
│       ├── App.tsx            # Placeholder component
│       ├── vite.config.ts     # Vite config for renderer
│       └── tsconfig.json      # DOM types, jsx: react-jsx
```

## Implementation Steps

### 1. Create `erkdesk/` directory and `package.json`

Initialize with npm. Set `"private": true`, name `"erkdesk"`, version `"0.1.0"`.

### 2. Install dependencies

**devDependencies:**
- `electron`, `@electron-forge/cli`, `@electron-forge/plugin-vite`, `@electron-forge/maker-zip`
- `typescript`, `vite`, `@vitejs/plugin-react`
- `@types/react`, `@types/react-dom`

**dependencies:**
- `react`, `react-dom`

### 3. Create TypeScript configs

- **Root `tsconfig.json`**: ES2020 target, strict, esModuleInterop
- **`src/main/tsconfig.json`**: Extends root, commonjs module, Node types
- **`src/renderer/tsconfig.json`**: Extends root, ESNext module, DOM lib, jsx: react-jsx, bundler moduleResolution

### 4. Create electron-forge config (`forge.config.ts`)

Configure VitePlugin with:
- Build entries for `src/main/index.ts` and `src/main/preload.ts`
- Renderer entry for `src/renderer/` named `main_window`
- Single maker: `@electron-forge/maker-zip` (macOS/Linux/Windows)

### 5. Create Vite configs

- **`vite.main.config.ts`**: Node-oriented resolve settings (browserField: false)
- **`vite.preload.config.ts`**: External electron module
- **`src/renderer/vite.config.ts`**: React plugin

### 6. Create main process files

**`src/main/index.ts`:**
- Create BrowserWindow (1200x800)
- Preload script with contextIsolation: true
- Load from Vite dev server (dev) or built files (prod)
- Standard macOS activate/window-all-closed handlers
- DevTools open in dev mode

**`src/main/preload.ts`:**
- contextBridge stub exposing `erkdesk.version`
- Placeholder for future IPC (dash-data, exec commands)

### 7. Create renderer files

**`src/renderer/index.html`:** Minimal HTML with `<div id="root">`, module script tag
**`src/renderer/index.tsx`:** createRoot, StrictMode, render App
**`src/renderer/App.tsx`:** Simple placeholder: "erkdesk" heading + scaffold message

### 8. Create `erkdesk/.gitignore`

```
node_modules/
out/
dist/
.vite/
*.tsbuildinfo
.DS_Store
```

### 9. Update root `.gitignore`

Add erkdesk Node.js artifact patterns:
```
# erkdesk Electron app
erkdesk/node_modules/
erkdesk/out/
erkdesk/dist/
erkdesk/.vite/
```

### 10. Update root `.prettierignore`

Add erkdesk build artifact patterns so prettier doesn't process generated files:
```
erkdesk/out/
erkdesk/dist/
erkdesk/.vite/
erkdesk/node_modules/
```

### 11. Skip Makefile targets for now

No Makefile targets in this PR — the erkdesk workflow is `cd erkdesk && npm start`. Can add convenience targets in a later step if warranted.

## Files Modified

| File | Action |
|------|--------|
| `erkdesk/package.json` | Create |
| `erkdesk/tsconfig.json` | Create |
| `erkdesk/forge.config.ts` | Create |
| `erkdesk/vite.main.config.ts` | Create |
| `erkdesk/vite.preload.config.ts` | Create |
| `erkdesk/.gitignore` | Create |
| `erkdesk/src/main/index.ts` | Create |
| `erkdesk/src/main/preload.ts` | Create |
| `erkdesk/src/main/tsconfig.json` | Create |
| `erkdesk/src/renderer/index.html` | Create |
| `erkdesk/src/renderer/index.tsx` | Create |
| `erkdesk/src/renderer/App.tsx` | Create |
| `erkdesk/src/renderer/vite.config.ts` | Create |
| `erkdesk/src/renderer/tsconfig.json` | Create |
| `.gitignore` | Edit — add erkdesk patterns |
| `.prettierignore` | Edit — add erkdesk patterns |

## Verification

1. `cd erkdesk && npm install` — installs without errors
2. `cd erkdesk && npx tsc --noEmit` — type checks clean
3. `cd erkdesk && npm start` — launches Electron window showing "erkdesk" heading
4. Edit `App.tsx` → see hot reload in the window