---
title: uvx Hook Invocation Pattern
read_when:
  - implementing plugin hooks with uvx
  - understanding erk hook script architecture
  - debugging hook version issues
---

# uvx Hook Invocation Pattern

> **Note:** This documentation was produced in December 2025 based on Claude Code's plugin system at that time. The plugin system is actively evolving; verify against [official Claude Code documentation](https://docs.anthropic.com/en/docs/claude-code) for current behavior.

ERK hooks use `uvx erk@{version} kit exec` for reproducible, version-pinned script execution.

## The Pattern

```json
{
  "type": "command",
  "command": "uvx erk@1.2.3 kit exec erk session-id-injector-hook",
  "timeout": 30
}
```

## How It Works

1. Hook fires in Claude Code
2. uvx downloads/caches erk@1.2.3 if not present
3. `erk kit exec` runs the script from erk package
4. Script has full access to erk_shared context
5. Output returned to Claude Code

## Script Location

Scripts remain in the `erk` package, NOT in plugins:

```
src/erk/
└── kits/
    └── scripts/
        └── erk/
            └── session_id_injector_hook.py
```

Plugins contain only: commands, agents, skills, docs, hooks.json

## Benefits

- **Version pinning**: Exact erk version, reproducible behavior
- **No install required**: uvx resolves and caches automatically
- **Full erk access**: Scripts use erk_shared, Click, type checking
- **Fast**: ~50ms warm start, ~200ms cold start
- **Ubiquitous**: uv is increasingly standard in Python ecosystem

## Version Management

When releasing erk, update hook versions in plugins:

```json
// plugins/erk/hooks/hooks.json
{
  "command": "uvx erk@1.3.0 kit exec erk session-id-injector-hook"
}
```

Consider automating this in the release process.

## Requirements

- **uv**: Must be installed on user's system
- **Network**: First run requires download (cached after)
- **PyPI**: erk must be published to PyPI

## Why Not Other Approaches?

### Bundle Scripts in Plugins

```json
{
  "command": "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/hook.py"
}
```

**Problems:**

- Scripts lose access to `erk_shared` (context, git/github ABCs)
- No Click decorators (`@logged_hook`, `@project_scoped`)
- Must vendor dependencies or require separate install
- No type safety from erk's pyright config

### Require erk Installation

```json
{
  "command": "erk kit exec erk session-id-injector-hook"
}
```

**Problems:**

- Requires erk to be installed globally
- Version drift: user's erk version may differ from plugin expectation
- No reproducibility guarantee

## Tradeoffs

| Aspect          | uvx Approach        | Bundled Scripts           |
| --------------- | ------------------- | ------------------------- |
| Reproducibility | Exact version       | Depends on plugin version |
| Dependencies    | Full erk access     | Must vendor               |
| Portability     | Requires uv         | Self-contained            |
| Cold start      | ~200ms              | Immediate                 |
| Maintenance     | One script location | Duplicated per plugin     |
