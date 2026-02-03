# Fix: Make config system schema-driven so this can't happen again

## Problem

`erk config list` displays `interactive_claude.*` keys via hard-coded logic, but `erk config set/get/keys` reject them because they're not in the schema. The root cause: `config list` bypassed the schema with hand-written display code.

## Design Principle

**If it's not in a Pydantic schema model, it cannot appear in `config list/get/set/keys`.** All config commands derive behavior from schema metadata. Adding a new config section means adding a schema model — nothing else.

## Implementation

### Step 1: Add `InteractiveClaudeConfigSchema` and section registry to `schema.py`

**File:** `packages/erk-shared/src/erk_shared/config/schema.py`

Add the schema model and a `section` field to `FieldMetadata`:

```python
class InteractiveClaudeConfigSchema(BaseModel):
    """Schema for interactive_claude.* configuration keys.

    Each field's cli_key uses dotted notation: interactive_claude.<subkey>.
    """
    verbose: bool = Field(
        description="Show verbose output in interactive Claude sessions",
        json_schema_extra={"level": ConfigLevel.GLOBAL_ONLY, "cli_key": "interactive_claude.verbose"},
    )
    permission_mode: str = Field(
        description="Claude CLI permission mode (default, acceptEdits, plan, bypassPermissions)",
        json_schema_extra={"level": ConfigLevel.GLOBAL_ONLY, "cli_key": "interactive_claude.permission_mode"},
    )
    dangerous: bool = Field(
        description="Skip permission prompts (--dangerously-skip-permissions)",
        json_schema_extra={"level": ConfigLevel.GLOBAL_ONLY, "cli_key": "interactive_claude.dangerous"},
    )
    allow_dangerous: bool = Field(
        description="Enable --allow-dangerously-skip-permissions flag",
        json_schema_extra={"level": ConfigLevel.GLOBAL_ONLY, "cli_key": "interactive_claude.allow_dangerous"},
    )
    model: str | None = Field(
        description="Claude model to use (e.g., claude-opus-4-5)",
        json_schema_extra={"level": ConfigLevel.GLOBAL_ONLY, "cli_key": "interactive_claude.model"},
    )
```

Add `section` to `FieldMetadata`:

```python
class FieldMetadata:
    def __init__(self, *, field_name, cli_key, description, level, default, default_display, dynamic, section=None):
        ...
        self.section = section  # None for top-level, "interactive_claude" for nested
```

Add a registry pattern — a single function that yields ALL global fields:

```python
# Section registry: (schema_model, section_name, heading)
_GLOBAL_CONFIG_SECTIONS: list[tuple[type[BaseModel], str | None, str]] = [
    (GlobalConfigSchema, None, "Global configuration"),
    (InteractiveClaudeConfigSchema, "interactive_claude", "Interactive Claude configuration"),
]

def get_all_global_config_fields() -> Iterator[FieldMetadata]:
    """Yield ALL global config fields across all sections.

    This is the single source of truth for what keys exist.
    config list, config get, config set, and config keys all use this.
    """
    for schema, section, _heading in _GLOBAL_CONFIG_SECTIONS:
        for meta in iter_displayable_fields(schema):
            meta.section = section
            yield meta

def get_global_config_sections() -> list[tuple[str, Iterator[FieldMetadata]]]:
    """Yield (heading, fields) for each global config section. Used by config list/keys."""
    result = []
    for schema, section, heading in _GLOBAL_CONFIG_SECTIONS:
        fields = list(iter_displayable_fields(schema))
        for f in fields:
            f.section = section
        result.append((heading, fields))
    return result

def is_any_global_config_key(key: str) -> bool:
    """Check if a key (e.g. 'interactive_claude.verbose' or 'use_graphite') is a global config key."""
    return key in {meta.cli_key for meta in get_all_global_config_fields()}
```

Keep existing `get_global_config_fields()` and `is_global_config_key()` for backward compat with the top-level-only logic in `config set` (which does `dataclasses.replace` on `GlobalConfig` directly).

### Step 2: Update `config keys` to use section registry

**File:** `src/erk/cli/commands/config.py`

Replace the global section of `config_keys` to iterate all sections:

```python
for heading, fields in get_global_config_sections():
    user_output(click.style(f"\n{heading} keys:", bold=True))
    formatter = click.HelpFormatter()
    rows = [(meta.cli_key, meta.description) for meta in fields]
    formatter.write_dl(rows)
    user_output(formatter.getvalue().rstrip())
```

### Step 3: Update `config list` — remove hard-coded interactive_claude block

**File:** `src/erk/cli/commands/config.py` (lines 220-230)

Replace the hand-coded interactive_claude display with schema-driven iteration. The `config list` function will iterate `get_global_config_sections()`. For each section, it reads values from the appropriate object:

- Section `None` → read from `ctx.global_config.<field_name>`
- Section `"interactive_claude"` → read from `ctx.global_config.interactive_claude.<field_name>`

The `section` field on `FieldMetadata` tells `config list` where to read the value from. This replaces the hand-coded lines 220-230 entirely.

### Step 4: Update `config get` to handle sectioned keys

**File:** `src/erk/cli/commands/config.py` (in `config_get`)

Before the repo-config fallthrough, add:

```python
# Handle sectioned global keys (e.g., interactive_claude.verbose)
if is_any_global_config_key(key) and not is_global_config_key(parts[0]):
    global_config = Ensure.not_none(ctx.global_config, ...)
    section_obj = getattr(global_config, parts[0])  # e.g., global_config.interactive_claude
    value = getattr(section_obj, parts[1])
    machine_output(_format_config_value(value) if value is not None else "")
    return
```

### Step 5: Update `config set` to handle sectioned keys

**File:** `src/erk/cli/commands/config.py` (in `config_set`)

After the `is_global_config_key` block, before repo config:

```python
# Handle sectioned global keys (e.g., interactive_claude.verbose)
if is_any_global_config_key(key) and not is_global_config_key(parts[0]):
    Ensure.invariant(not (local or repo_flag), f"Key '{key}' can only be set at global level")
    global_config = Ensure.not_none(ctx.global_config, ...)

    section_obj = getattr(global_config, parts[0])  # e.g., interactive_claude
    current_value = getattr(section_obj, parts[1])
    parsed_value = _parse_config_value(parts[1], value, type(current_value)) if current_value is not None else value

    new_section = replace(section_obj, **{parts[1]: parsed_value})
    new_config = replace(global_config, **{parts[0]: new_section})
    ctx.erk_installation.save_config(new_config)
    user_output(f"Set {key}={value}")
    return
```

### Step 6: Add tests

**File:** `tests/commands/setup/test_config.py`

- `config set interactive_claude.verbose true` — succeeds, persists
- `config set interactive_claude.permission_mode plan` — succeeds
- `config set interactive_claude.model claude-opus-4-5` — succeeds (string/None type)
- `config get interactive_claude.verbose` — returns correct value
- `config set interactive_claude.verbose true --local` — fails (global-only)
- `config set interactive_claude.bad_key true` — fails (invalid subkey)
- `config keys` — includes interactive_claude keys in output
- `config list` — shows interactive_claude section (output unchanged)

## Files Modified

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/config/schema.py` | Add `InteractiveClaudeConfigSchema`, section registry, `section` on `FieldMetadata` |
| `src/erk/cli/commands/config.py` | `list`/`get`/`set`/`keys` all driven by schema registry |
| `tests/commands/setup/test_config.py` | Tests for interactive_claude set/get/list/keys |

## Why this prevents recurrence

The only way to add a new config section is to:
1. Create a Pydantic schema model
2. Add it to `_GLOBAL_CONFIG_SECTIONS`

That single registration makes it automatically work in `list`, `get`, `set`, and `keys`. There's no hand-coded display logic to forget to update.

## Verification

1. `erk config set interactive_claude.verbose true` — succeeds
2. `erk config get interactive_claude.verbose` — returns `true`
3. `erk config list` — output unchanged from before
4. `erk config keys` — now includes interactive_claude keys
5. Run existing config tests via devrun agent