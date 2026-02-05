---
title: Schema-Driven Config System
read_when:
  - adding new configuration options to erk
  - understanding config validation
  - working with config commands
tripwires:
  - action: "adding a new config option without defining it in a Pydantic schema"
    warning: "All config keys must be defined in schema.py with proper ConfigLevel. The schema is the single source of truth for field names, descriptions, and validation."
last_audited: "2026-02-05"
audit_result: edited
---

# Schema-Driven Config System

Erk's configuration system uses Pydantic schemas as the single source of truth for configuration fields. Everything derives from these schemas: field names, CLI keys, descriptions, validation rules, and display formatting.

## ConfigLevel Enum

Every configuration field has a level that controls where it can be set. Defined in `packages/erk-shared/src/erk_shared/config/schema.py`:

| Level         | Where Set                 | Examples                                                                       |
| ------------- | ------------------------- | ------------------------------------------------------------------------------ |
| `GLOBAL_ONLY` | Only `~/.erk/config.toml` | `erk_root`, `interactive_claude.verbose`, `interactive_claude.permission_mode` |
| `OVERRIDABLE` | Global, repo, or local    | `use_graphite`, `github_planning`                                              |
| `REPO_ONLY`   | Only in repository config | `trunk_branch`, `pool_max_slots`, `plans_repo` (see `RepoConfigSchema`)        |

## Schema Structure

Configuration schemas are Pydantic `BaseModel` subclasses. Each field specifies its type, description, and config level via `json_schema_extra`. See `schema.py` for the complete definitions:

- `InteractiveClaudeConfigSchema` — `interactive_claude.*` keys (verbose, permission_mode, dangerous, model)
- `GlobalConfigSchema` — Top-level global keys (erk_root, use_graphite, github_planning)
- `RepoConfigSchema` — Repository-level keys (trunk_branch, pool settings, plans_repo)

Pydantic introspection allows config commands to discover fields, types, and descriptions without manual lists.

**Note**: Schema classes must be registered in `_GLOBAL_CONFIG_SECTIONS` in schema.py to be discovered by config commands.

## Adding New Configuration Options

1. **Add field** to the appropriate schema class in `schema.py`
2. **Choose ConfigLevel** (GLOBAL_ONLY, OVERRIDABLE, or REPO_ONLY)
3. **Write description** (appears in `erk config keys` output)
4. **Specify cli_key** in `json_schema_extra` (dotted notation for the config key)
5. **Register** the schema class in `_GLOBAL_CONFIG_SECTIONS` if it's a new section

CLI commands, validation, and documentation update automatically from the schema.

## Related Documentation

- `packages/erk-shared/src/erk_shared/config/schema.py` — Schema definitions
- `src/erk/cli/commands/config.py` — Config CLI commands that use schemas
