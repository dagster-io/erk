# Plan: `erk admin api-key` toggle command

## Context

You want the ability to quickly disable/enable the `ANTHROPIC_API_KEY` environment variable in your shell RC file by renaming it to `ANTHROPIC_API_KEY_DISABLED` and back. This acts as a local kill switch for Anthropic API access without losing the key value.

## Command UX

Follows the existing `github-pr-setting` pattern (display-or-modify):

```bash
erk admin api-key              # Show current status (enabled/disabled/not found)
erk admin api-key --disable    # Rename ANTHROPIC_API_KEY → ANTHROPIC_API_KEY_DISABLED
erk admin api-key --enable     # Rename ANTHROPIC_API_KEY_DISABLED → ANTHROPIC_API_KEY
```

Auto-detects shell RC file via `ctx.shell.detect_shell()` (zsh → `~/.zshrc`, bash → `~/.bashrc`, fish → `~/.config/fish/config.fish`). Optionally accepts `--file` to override.

## Implementation

### 1. Add command to `src/erk/cli/commands/admin.py`

New `api-key` subcommand on `admin_group`:

```python
@admin_group.command("api-key")
@click.option("--enable", "action", flag_value="enable", help="Enable ANTHROPIC_API_KEY")
@click.option("--disable", "action", flag_value="disable", help="Disable ANTHROPIC_API_KEY")
@click.option("--file", "rc_file", type=click.Path(exists=True, path_type=Path), help="Shell RC file to modify (auto-detected if omitted)")
@click.pass_obj
def api_key(ctx: ErkContext, action: Literal["enable", "disable"] | None, rc_file: Path | None) -> None:
```

**Core logic:**

1. Resolve RC file: use `--file` if provided, otherwise `ctx.shell.detect_shell()`
2. Read file content
3. Search for lines matching `ANTHROPIC_API_KEY=` or `ANTHROPIC_API_KEY_DISABLED=`
4. Display status (no action flag) or perform rename (with flag)
5. Write modified content back

**Replacement strategy** — simple string replacement on each line:
- Disable: replace `ANTHROPIC_API_KEY=` with `ANTHROPIC_API_KEY_DISABLED=` (only on lines that don't already have `_DISABLED`)
- Enable: replace `ANTHROPIC_API_KEY_DISABLED=` with `ANTHROPIC_API_KEY=`

Extract a pure function `toggle_api_key_line(line, action)` for easy unit testing.

### 2. Add tests at `tests/unit/cli/commands/test_admin_api_key.py`

- Use `FakeShell` for shell detection
- Use `tmp_path` for RC file fixtures
- Test cases:
  - Status display: enabled, disabled, not found
  - Disable: renames correctly
  - Enable: renames correctly
  - Already in desired state: shows message, doesn't modify
  - `--file` override works
  - Multiple export formats: `export ANTHROPIC_API_KEY=...`, `ANTHROPIC_API_KEY=...`, quoted values

## Files to modify

- `src/erk/cli/commands/admin.py` — add `api-key` command (~60 lines)
- `tests/unit/cli/commands/test_admin_api_key.py` — new test file

## Verification

1. `erk admin api-key` — should show current status
2. `erk admin api-key --disable` — should rename in RC file, show confirmation
3. `erk admin api-key` — should now show disabled
4. `erk admin api-key --enable` — should rename back
5. Run tests via devrun agent