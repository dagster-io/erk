---
title: TypeScript Multi-Config Project Checking
read_when:
  - "setting up TypeScript type checking for multi-config projects"
  - "encountering TypeScript errors in subdirectories with separate configs"
  - "working with erkdesk TypeScript configuration"
  - "running tsc --noEmit from project root"
tripwires:
  - action: "running tsc --noEmit from root in multi-config TypeScript project"
    warning: "tsc --noEmit from root breaks subdirectory configs. Use tsc -p <path> --noEmit for each tsconfig.json separately."
last_audited: "2026-02-07 21:48 PT"
audit_result: clean
---

# TypeScript Multi-Config Project Checking

## The Core Issue

TypeScript's `tsc` command **only processes one configuration at a time**. When you run `tsc --noEmit` from a directory containing `tsconfig.json`, it checks that config and ignores any nested configs in subdirectories — even if those nested configs extend the root config.

This is TypeScript's deliberate design: each `tsconfig.json` defines a compilation context with distinct compiler options, included files, and type definitions. There is no "check all configs recursively" mode.

## Why Multi-Config Projects Exist

<!-- Source: erkdesk/tsconfig.json, erkdesk/src/main/tsconfig.json, erkdesk/src/renderer/tsconfig.json -->

Multi-config setups emerge when different parts of a codebase need incompatible compiler settings. Electron projects are the canonical example:

- **Main process** runs in Node.js: needs `module: "commonjs"`, `types: ["node"]`
- **Renderer process** runs in browser: needs `module: "ESNext"`, `lib: ["DOM"]`, JSX support
- **Shared root** provides base settings inherited by both contexts

See erkdesk's three-config structure: root `erkdesk/tsconfig.json`, main-specific `erkdesk/src/main/tsconfig.json`, renderer-specific `erkdesk/src/renderer/tsconfig.json`.

Each context has different module resolution, target environments, and available global types. A single `tsc --noEmit` run cannot check both Node.js and browser code simultaneously.

## The Solution Pattern

Check each configuration explicitly with `tsc -p <path> --noEmit`:

```bash
# From erkdesk/ directory
tsc -p . --noEmit              # Root config (if it includes any files)
tsc -p src/main --noEmit       # Main process
tsc -p src/renderer --noEmit   # Renderer process
```

The `-p` flag tells TypeScript which `tsconfig.json` to use. Each invocation is an isolated type-checking run with its own compiler options.

## Detection Strategy

Find all `tsconfig.json` files:

```bash
find . -name "tsconfig.json"
```

If you see more than one, you must check each separately. Grep for `"extends"` to understand the inheritance hierarchy, but remember: **extension is for sharing settings, not for aggregating type checks**.

## Anti-Pattern: Relying on Root Check

```bash
# ❌ WRONG: Only checks root config, misses main/renderer
cd erkdesk/
tsc --noEmit

# ✅ CORRECT: Check each config explicitly
tsc -p . --noEmit && tsc -p src/main --noEmit && tsc -p src/renderer --noEmit
```

The first command succeeds even if `src/main/` or `src/renderer/` have type errors. This creates a false sense of type safety and breaks CI reliability.

## CI Integration

In GitHub Actions or other CI, chain all checks:

```yaml
- name: TypeScript check
  run: |
    cd erkdesk/
    tsc -p . --noEmit
    tsc -p src/main --noEmit
    tsc -p src/renderer --noEmit
```

Or use a Makefile target to centralize the command list:

```makefile
.PHONY: typecheck
typecheck:
	cd erkdesk && tsc -p . --noEmit
	cd erkdesk && tsc -p src/main --noEmit
	cd erkdesk && tsc -p src/renderer --noEmit
```

The key insight: **there is no TypeScript feature to automate this**. You must maintain the list of configs manually and ensure CI checks all of them.

## Historical Context

Why doesn't TypeScript have a "check all configs" mode? Because TypeScript views each `tsconfig.json` as defining a distinct compilation unit. Multi-config projects are compositions of separate projects, not a single project with multiple facets.

TypeScript's project references feature (`"references": [...]`) can express dependencies between configs, but it doesn't eliminate the need to check each one — it just enables incremental builds.

## Related Patterns

- Monorepos with multiple packages: each package has its own `tsconfig.json`, each must be checked separately
- Build vs. test configs: `tsconfig.json` for source, `tsconfig.test.json` for tests with additional types — both must be checked
- Strict vs. loose configs during migration: incremental `strictNullChecks` adoption uses multiple configs — each must be checked

The lesson: **TypeScript type checking is per-config, always**. Structure your CI accordingly.
