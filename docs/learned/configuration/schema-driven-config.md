---
title: Schema-Driven Config System
read_when:
  - adding new configuration options to erk
  - understanding config validation
  - working with config commands
tripwires:
  - action: "adding a new config option without defining it in a Pydantic schema"
    warning: "All config keys must be defined in schema.py with proper ConfigLevel. The schema is the single source of truth for field names, descriptions, and validation."
---

# Schema-Driven Config System

Erk's configuration system uses Pydantic schemas as the single source of truth for configuration fields. This ensures consistency between CLI keys, validation logic, documentation, and display formatting.

## Core Concept

**Single Source of Truth**: Configuration fields are defined once in Pydantic models. Everything else derives from these schemas:

- Field names and CLI keys
- Descriptions (used by `erk config keys`)
- Configuration levels (where the key can be set)
- Validation rules
- Display formatting

**No duplication**: You don't separately maintain field lists, validation logic, and documentation. The schema defines it all.

## ConfigLevel Enum

Every configuration field has a level that controls where it can be set:

```python
class ConfigLevel(str, Enum):
    """Defines where a configuration key can be set."""

    GLOBAL_ONLY = "global_only"    # Only in ~/.erk/config.toml
    OVERRIDABLE = "overridable"    # Global, repo, or local
    REPO_ONLY = "repo_only"        # Only in repository config
```

See `packages/erk-shared/src/erk_shared/config/schema.py:18-28` for implementation.

### GLOBAL_ONLY

Settings that apply across all repositories and cannot be overridden per-repo.

**Examples**:

- `erk_root` - Where erk stores global data
- `interactive_claude.verbose` - Claude CLI verbosity
- `interactive_claude.permission_mode` - Permission mode for Claude

**Why global-only**: These settings affect tool behavior at a level above individual repositories.

### OVERRIDABLE

Settings that can be set globally but overridden per-repository or even per-branch.

**Examples**:

- `use_graphite` - Enable Graphite integration
- `github_planning` - Enable GitHub issues integration

**Why overridable**: Different repositories may have different workflows. One repo uses Graphite, another doesn't.

### REPO_ONLY

Settings that only make sense at repository level.

**Examples**: (Currently none, but pattern is available)

**Why repo-only**: Settings intrinsic to a specific repository that shouldn't have global defaults.

## Schema Structure

Configuration schemas are Pydantic `BaseModel` subclasses with metadata in `json_schema_extra`:

```python
class InteractiveClaudeConfigSchema(BaseModel):
    """Schema for interactive_claude.* configuration keys."""

    verbose: bool = Field(
        description="Show verbose output in interactive Claude sessions",
        json_schema_extra={
            "level": ConfigLevel.GLOBAL_ONLY,
            "cli_key": "interactive_claude.verbose",
        },
    )
```

See `packages/erk-shared/src/erk_shared/config/schema.py:31-69` for complete example.

### Field Components

Each field definition has:

1. **Type annotation** (`bool`, `str`, `str | None`): Enforces validation
2. **Description**: Used by `erk config keys` to explain what the field does
3. **json_schema_extra**: Metadata dictionary containing:
   - `level`: ConfigLevel enum value
   - `cli_key`: Dotted notation for CLI commands (e.g., `interactive_claude.verbose`)

## Section Registry Pattern

The config system uses a registry pattern to discover all schema sections:

```python
# In schema.py - define schema classes
class InteractiveClaudeConfigSchema(BaseModel):
    """Schema for interactive_claude.* configuration keys."""
    ...

class GlobalConfigSchema(BaseModel):
    """Schema for global configuration keys."""
    ...

# Config commands automatically discover and use all schema classes
# No manual registration needed
```

**Key insight**: By using Pydantic models, the config commands can introspect field definitions, types, descriptions, and metadata without manual lists or mappings.

## Concrete Example: interactive_claude Section

The `interactive_claude` section demonstrates the pattern:

**Schema definition** (`schema.py:31-69`):

```python
class InteractiveClaudeConfigSchema(BaseModel):
    verbose: bool = Field(...)
    permission_mode: str = Field(...)
    dangerous: bool = Field(...)
    allow_dangerous: bool = Field(...)
    model: str | None = Field(default=None, ...)
```

**CLI usage** (automatically derived from schema):

```bash
# List all interactive_claude keys with descriptions
erk config keys interactive_claude

# Set a value (validates against schema type)
erk config set interactive_claude.verbose true

# Get current value
erk config get interactive_claude.verbose
```

**Validation** (automatic from Pydantic):

- `verbose` must be boolean
- `permission_mode` must be string
- `model` can be string or null

## Adding New Configuration Options

To add a new configuration option:

1. **Add field to appropriate schema** in `schema.py`
2. **Choose ConfigLevel** (GLOBAL_ONLY, OVERRIDABLE, or REPO_ONLY)
3. **Write description** (appears in `erk config keys` output)
4. **Specify cli_key** (dotted notation for the config key)

That's it. The CLI commands, validation, and documentation update automatically.

**Example**: Adding a new `interactive_claude.timeout` field:

```python
class InteractiveClaudeConfigSchema(BaseModel):
    # ... existing fields ...

    timeout: int | None = Field(
        default=None,
        description="Timeout in seconds for Claude operations (null = no timeout)",
        json_schema_extra={
            "level": ConfigLevel.GLOBAL_ONLY,
            "cli_key": "interactive_claude.timeout",
        },
    )
```

Now users can:

```bash
erk config set interactive_claude.timeout 300
erk config get interactive_claude.timeout
```

And validation ensures the value is an integer or null.

## Benefits of Schema-Driven Approach

1. **No duplication**: Field definitions exist in one place
2. **Type safety**: Pydantic validates types at runtime
3. **Self-documenting**: Descriptions in schema appear in CLI output
4. **Consistent**: CLI keys, validation, and display all derive from same source
5. **Discoverable**: `erk config keys` shows all options with descriptions

## Migration from Manual Config

Before schema-driven config, adding a field required:

1. Updating hardcoded field list in CLI commands
2. Adding validation logic
3. Updating documentation separately
4. Keeping all three in sync

After schema-driven config:

1. Add field to schema
2. Done

The schema is the single source of truth, eliminating synchronization burden.

## Related Documentation

- `packages/erk-shared/src/erk_shared/config/schema.py` - Schema definitions
- `src/erk/cli/commands/config/` - Config CLI commands that use schemas
- [configuration.md](configuration.md) - User-facing config documentation
