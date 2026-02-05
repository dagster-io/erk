---
title: TOML File Handling
last_audited: "2026-02-05 16:53 PT"
audit_result: edited
read_when:
  - "reading TOML files"
  - "writing TOML files"
  - "generating TOML configuration"
  - "working with config.toml"
  - "working with pyproject.toml"
tripwires:
  - action: "defining the same skill or command in multiple TOML sections"
    warning: "TOML duplicate key constraint: Each skill/command must have a single canonical destination. See bundled-artifacts.md for portability classification."
---

# TOML File Handling

Standard patterns for reading and writing TOML files in erk.

## Library Choice

- **Reading**: Use `tomllib` (stdlib, Python 3.11+)
- **Writing**: Use `tomlkit` (preserves formatting, adds comments programmatically)

`tomlkit` is a dependency of `erk-shared` (see `packages/erk-shared/pyproject.toml`).

## Why tomlkit over f-strings?

1. **Proper escaping**: Handles special characters correctly
2. **Consistent formatting**: Produces valid TOML with proper quoting
3. **Maintainability**: Structure is explicit in code, not hidden in string templates
4. **Comments**: Can add comments programmatically

## Reference Implementations

For real usage of both libraries, see:

- `src/erk/cli/commands/init/main.py` - tomlkit for generating config files
- `src/erk/cli/commands/project/init_cmd.py` - tomlkit for project initialization
- `src/erk/cli/config.py` - tomllib for reading configuration
- `src/erk/core/context.py` - tomllib for reading TOML data

## TOML Duplicate Key Constraint

TOML prohibits duplicate keys in the same document. Each entity (skill, command, config section) must have exactly ONE canonical location. See [bundled-artifacts.md](../integrations/bundled-artifacts.md) for the complete portability classification pattern.
