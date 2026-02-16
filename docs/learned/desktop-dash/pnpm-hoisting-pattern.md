---
title: pnpm Hoisting Pattern for Electron
read_when:
  - setting up a new Electron project with pnpm
  - debugging 'Cannot find module' errors in Electron
  - configuring pnpm for Electron Forge compatibility
tripwires:
  - action: "modifying erkdesk/.npmrc configuration"
    warning: "Do NOT remove erkdesk/.npmrc or change node-linker away from hoisted — Electron cannot resolve pnpm's symlinked node_modules layout"
  - action: "debugging module resolution errors in Electron"
    warning: "Do NOT assume 'Cannot find module' errors mean a missing dependency — in Electron with pnpm, check .npmrc first"
last_audited: "2026-02-08 00:00 PT"
audit_result: clean
---

# pnpm Hoisting Pattern for Electron

## Why Hoisting Is Non-Negotiable

pnpm's default dependency strategy uses a content-addressable store with symlinks into `node_modules/.pnpm/`. Electron's module resolver follows symlinks but resolves paths relative to the **symlink target** (inside `.pnpm/`), not the symlink location. This means peer and transitive dependencies become invisible — Electron resolves `require()` calls from inside the `.pnpm` store where sibling packages don't exist in the expected structure.

The `node-linker = hoisted` setting tells pnpm to use a traditional flat `node_modules` layout (physical copies, no symlinks), which Electron's resolver handles correctly.

<!-- Source: erkdesk/.npmrc -->

See `erkdesk/.npmrc` for the configuration. It belongs in the Electron project root, not the repository root.

## Why This Is a Tripwire

The failure mode is deceptive:

- Errors say `Cannot find module 'X'` but the module **is** installed (visible in `node_modules/.pnpm/`)
- Different modules fail depending on load order, making it look like a dependency version issue
- Nothing in the error message mentions symlinks or resolution paths

Without prior knowledge, this leads to chasing phantom dependency issues rather than recognizing a fundamental pnpm/Electron incompatibility. This is a known issue acknowledged by pnpm maintainers — it can't be fixed without changing Electron's module resolution assumptions.

## Trade-offs Accepted

Hoisting sacrifices pnpm's strict dependency graph enforcement and symlink deduplication (larger `node_modules`, slower installs). This is acceptable because Electron **cannot function** without it — there is no alternative configuration that preserves both pnpm's symlink strategy and Electron compatibility.

## Related Documentation

- [Erkdesk Project Structure](erkdesk-project-structure.md) — overall project setup
- [Forge Vite Setup](forge-vite-setup.md) — build configuration
