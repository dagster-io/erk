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
---

# TypeScript Multi-Config Project Checking

When a project has multiple `tsconfig.json` files in different directories, running `tsc --noEmit` from the root directory does NOT check all configurations. You must check each config separately.

## The Problem

Consider this structure:

```
erkdesk/
├── tsconfig.json          # Root config
├── main/
│   └── tsconfig.json      # Main process config (extends root)
└── renderer/
    └── tsconfig.json      # Renderer process config (extends root)
```

Running `tsc --noEmit` from `erkdesk/` only checks the root config, ignoring `main/` and `renderer/`.

## The Solution

Check each config explicitly:

```bash
# From erkdesk/ directory
tsc -p . --noEmit              # Check root config
tsc -p main --noEmit           # Check main process
tsc -p renderer --noEmit       # Check renderer process
```

## Why This Matters

Multi-config setups exist when different parts of the project have different TypeScript requirements:

- **Electron main process**: Node.js environment, different types
- **Electron renderer process**: Browser environment, React types
- **Shared code**: Common types and utilities

Each config has different:

- `compilerOptions.target` (ES version)
- `compilerOptions.lib` (available APIs)
- `include`/`exclude` patterns
- Type definitions (`@types/*`)

A single `tsc --noEmit` can't check all these contexts.

## erkdesk Example

The erkdesk project has three TypeScript configs:

```bash
# Check all TypeScript in erkdesk
cd erkdesk/
tsc -p . --noEmit          # Root shared code
tsc -p main --noEmit       # Electron main process
tsc -p renderer --noEmit   # React renderer
```

**Common mistake**:

```bash
# ❌ This only checks root config
tsc --noEmit

# ✅ Must check each config
tsc -p . --noEmit && tsc -p main --noEmit && tsc -p renderer --noEmit
```

## CI Integration

In CI workflows, check all configs:

```yaml
- name: TypeScript check
  run: |
    cd erkdesk/
    tsc -p . --noEmit
    tsc -p main --noEmit
    tsc -p renderer --noEmit
```

Or use a Makefile target:

```makefile
.PHONY: typecheck
typecheck:
	cd erkdesk && tsc -p . --noEmit
	cd erkdesk && tsc -p main --noEmit
	cd erkdesk && tsc -p renderer --noEmit
```

## How to Detect Multi-Config Projects

Look for multiple `tsconfig.json` files:

```bash
find . -name "tsconfig.json"
```

If you see more than one, you need to check each separately.

## Related Documentation

- [erkdesk Security](../desktop-dash/security.md) - Why main and renderer need separate configs
- [CI Tripwires](../ci/tripwires.md) - CI-specific type checking patterns
