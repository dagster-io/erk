---
title: pnpm Hoisting Pattern
read_when:
  - "setting up new Electron projects with pnpm"
  - "encountering cryptic Electron module resolution errors"
  - "debugging 'Cannot find module' errors in Electron"
  - "configuring pnpm for Electron compatibility"
tripwire:
  trigger: "Before creating Electron project with pnpm"
  action: "Read [pnpm Hoisting Pattern](pnpm-hoisting-pattern.md) first. REQUIRED: Add .npmrc with `node-linker = hoisted`. Without this, Electron crashes with cryptic module resolution errors. This one-line config prevents ~30min debugging sessions."
---

# pnpm Hoisting Pattern

Electron applications using pnpm **require** `.npmrc` with `node-linker = hoisted`. Without this one-line configuration, Electron crashes with cryptic module resolution errors.

## The Configuration

**File**: `erkdesk/.npmrc`

```
node-linker = hoisted
```

**Location**: Root of Electron project directory (not repository root)

## Why This is Required

### pnpm Default Behavior

By default, pnpm uses **symlinks** for dependency management:

```
node_modules/
├── .pnpm/                    # Actual packages stored here
│   └── electron@28.0.0/
│       └── node_modules/
│           └── electron/
└── electron -> .pnpm/electron@28.0.0/node_modules/electron
```

Dependencies are **symlinked** from the `.pnpm` store to `node_modules`.

### Electron Module Resolution

Electron's module resolution:

1. Follows symlinks during require() calls
2. Resolves paths relative to the **symlink target**, not the symlink itself
3. Expects node_modules to use traditional flat or nested structure

**Result**: When Electron follows symlinks into `.pnpm` store, it can't resolve peer dependencies or transitive dependencies correctly.

### The Symptom

Without hoisting, Electron crashes with errors like:

```
Error: Cannot find module 'some-peer-dependency'
    at Module._resolveFilename (node:internal/modules/cjs/loader:1075:15)
```

These errors are **cryptic** because:

- The module IS installed (visible in `node_modules/.pnpm/`)
- The error doesn't mention symlinks or resolution issues
- The error appears randomly for different modules depending on load order

## What Hoisting Does

With `node-linker = hoisted`, pnpm uses **traditional flat layout**:

```
node_modules/
├── electron/              # Actual package, not symlink
├── some-dependency/       # Actual package, not symlink
└── peer-dependency/       # Actual package, not symlink
```

**All packages** are physically present in `node_modules`, not symlinked from `.pnpm` store.

**Result**: Electron's module resolution works correctly because there are no symlinks to follow.

## Tripwire

**Missing this configuration causes ~30 minute debugging sessions.**

The symptoms are:

1. Electron starts but crashes immediately
2. Error messages are cryptic and unhelpful
3. Modules appear to be installed (visible in node_modules)
4. Only some modules fail, making it seem like a dependency issue

**Discovery**: Eventually you search "electron pnpm symlink error" and find this is a known compatibility issue.

**Prevention**: Always include `.npmrc` with `node-linker = hoisted` in Electron projects using pnpm.

## Trade-offs

### Benefits

- Electron compatibility (required)
- Simpler node_modules structure (easier to inspect)
- Familiar layout for developers coming from npm/yarn

### Costs

- Larger node_modules directory (no symlink deduplication)
- Slower installs (physical copies instead of symlinks)
- Loses pnpm's default strict dependency graph enforcement

**Verdict**: The trade-off is non-negotiable — Electron requires hoisting to function.

## Verification

After configuring `.npmrc`, verify the node_modules structure:

```bash
cd erkdesk
pnpm install
ls -la node_modules/electron
```

**Expected**: `node_modules/electron` is a **directory**, not a symlink.

If it's a symlink (`lrwxrwxrwx`), the `.npmrc` configuration didn't take effect.

## Related Issues

This is a known Electron + pnpm issue documented in:

- Electron Forge GitHub issues
- pnpm GitHub discussions
- Stack Overflow threads

The pnpm maintainers acknowledge this incompatibility but can't fix it without breaking Electron's module resolution assumptions.

## Related Documentation

- [Erkdesk Project Structure](erkdesk-project-structure.md) - Overall project setup
- [Forge Vite Setup](forge-vite-setup.md) - Build configuration
