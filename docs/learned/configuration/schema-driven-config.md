---
audit_result: edited
last_audited: '2026-02-08'
read_when:
- adding new configuration options to erk
- modifying config CLI commands (get, set, list, keys)
- understanding why config commands don't need manual field lists
title: Schema-Driven Config System
tripwires:
- action: adding a new config option without defining it in a Pydantic schema
  warning: All config keys must be defined in schema.py with proper ConfigLevel. The
    schema is the single source of truth — CLI commands discover fields via Pydantic
    introspection, so manual lists are unnecessary and will diverge.
---

# Schema-Driven Config System

## Why Schema-Driven?

Erk's config system uses Pydantic schemas as the **single source of truth** for all configuration metadata. The alternative — maintaining separate lists of field names, descriptions, and validation rules in CLI commands — leads to drift when fields are added or renamed. Instead, `erk config keys`, `erk config list`, `erk config get`, and `erk config set` all introspect the schema at runtime.

This means adding a new config option is a **one-place change** (the schema) rather than updating multiple CLI command files.

## ConfigLevel: Where a Key Can Live

<!-- Source: packages/erk-shared/src/erk_shared/config/schema.py, ConfigLevel -->

Every field carries a `ConfigLevel` that controls which config files can set it:

| Level         | Meaning                          | Why This Level Exists                                                          |
| ------------- | -------------------------------- | ------------------------------------------------------------------------------ |
| `GLOBAL_ONLY` | Only `~/.erk/config.toml`        | Settings that are inherently user-wide (e.g., `erk_root`, permission modes)    |
| `OVERRIDABLE` | Global, repo, or local           | Settings where teams want a default but individuals may need to diverge        |
| `REPO_ONLY`   | Only in repo config (not global) | Settings that are meaningless outside a specific repository (e.g., pool slots) |

The `config set` command enforces these levels — attempting to write a `GLOBAL_ONLY` key with `--repo` or `--local` flags is rejected.

For how config files are layered and merged, see [Configuration Layers](config-layers.md).

## The json_schema_extra Convention

Each Pydantic field stores its config metadata in `json_schema_extra`. This is the mechanism that bridges Pydantic's type system with erk's config semantics:

- **`level`**: Which `ConfigLevel` applies
- **`cli_key`**: The user-facing dotted key (e.g., `interactive_claude.verbose`, `pool.max_slots`)
- **`special`**: Marks fields stored outside TOML (e.g., `trunk_branch` lives in `pyproject.toml`)
- **`dynamic`**: Marks open-ended keys like `env.<name>` that accept arbitrary subkeys
- **`default_display`**: Override for display when no value is configured
- **`internal`**: If `True`, field is excluded from `erk config keys` output

This convention matters because `iter_displayable_fields()` and `get_field_metadata()` in `schema.py` extract these extras to drive all CLI behavior. Adding a new extra key here is how you extend the config system's capabilities.

## Section Registration

<!-- Source: packages/erk-shared/src/erk_shared/config/schema.py, _GLOBAL_CONFIG_SECTIONS -->

Schema classes must be registered in `_GLOBAL_CONFIG_SECTIONS` to be discovered by config commands. This is the one coupling point — if you create a new schema class and forget to register it, the fields will exist in the type system but be invisible to `erk config keys/list/get/set`.

## CLI Key vs Attribute Name Mismatch

<!-- Source: src/erk/cli/commands/config.py, _CLI_KEY_TO_ATTR -->

The user-facing CLI key prefix `interactive_claude` maps to the `GlobalConfig` attribute `interactive_agent`. This mismatch exists because the internal attribute name was generalized while the CLI key kept the user-friendly name. See `_CLI_KEY_TO_ATTR` in `config.py` for the mapping. When adding new sectioned schemas, you may need to add a similar mapping if the CLI prefix differs from the dataclass attribute.

## Adding a New Config Option — Checklist

1. **Add field** to the appropriate schema class in `schema.py` with `json_schema_extra` containing `level` and `cli_key`
2. **Choose ConfigLevel** based on the decision table above
3. **Register** the schema class in `_GLOBAL_CONFIG_SECTIONS` if it's a new section
4. **Add `_CLI_KEY_TO_ATTR` mapping** if the CLI prefix differs from the `GlobalConfig` attribute name
5. **Handle in `config set`** if the key needs special parsing (repo keys with custom types require a `match` case in `config_set`)

Steps 1-3 are always required. Steps 4-5 are only needed for sectioned or repo-level keys with non-standard types.

**What updates automatically from the schema alone:** `erk config keys` output, `erk config list` display, `erk config get` for global keys.

**What does NOT auto-update:** `config set` for repo-level keys (these use a `match` statement that must be extended manually), and `config list` for repo-level keys (displayed with hand-written logic).

## Anti-Patterns

**Adding a config key to config.py without a schema field** — The config commands will work initially but the key won't appear in `erk config keys`, won't be validated, and won't have a description. Always start from the schema.

**Using `internal=True` to hide unfinished fields** — This is intended for fields that are genuinely internal (used by code but not user-facing). Don't use it as a feature flag for work-in-progress config options.
