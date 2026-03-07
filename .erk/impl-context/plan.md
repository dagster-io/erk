# Rename `/erk:rebase` to `/erk:pr-rebase`

## Context

The slash command `/erk:rebase` should be renamed to `/erk:pr-rebase` for consistency with the `pr` command group naming convention. Other PR-related slash commands already follow this pattern: `/erk:pr-address`, `/erk:pr-preview-address`, `/erk:pr-dispatch`, `/erk:pr-list`, `/erk:pr-submit`, `/erk:pr-address-remote`, `/erk:pr-incremental-dispatch`. The rebase command is invoked via `erk pr rebase` on the CLI, so the slash command should mirror this as `/erk:pr-rebase`.

## Changes

### 1. Rename the command file

**Rename** `.claude/commands/erk/rebase.md` **to** `.claude/commands/erk/pr-rebase.md`

The file content stays the same. Only the filename changes. Claude Code derives the slash command name from the file path, so renaming the file automatically changes the command from `/erk:rebase` to `/erk:pr-rebase`.

### 2. Update `src/erk/cli/commands/pr/rebase_cmd.py`

This file has 3 references to `/erk:rebase` that need to become `/erk:pr-rebase`:

- **Line 4** (module docstring): `Phase 2: If conflicts arise, launch Claude TUI interactively with /erk:rebase.` → change to `/erk:pr-rebase`
- **Line 42** (function docstring): `launches Claude TUI with /erk:rebase for interactive resolution.` → change to `/erk:pr-rebase`
- **Line 136** (code): `command="/erk:rebase",` → change to `command="/erk:pr-rebase",`

### 3. Update `src/erk/cli/output.py`

This file has 5 references to `/erk:rebase` in the `stream_rebase` function that need updating:

- **Line 281** (docstring): `Handles the /erk:rebase command execution with:` → `/erk:pr-rebase`
- **Line 301** (output marker): `click.echo(click.style("--- /erk:rebase ---", bold=True))` → `"--- /erk:pr-rebase ---"`
- **Line 305** (code): `command="/erk:rebase",` → `command="/erk:pr-rebase",`
- **Line 330** (user-facing hint): `click.echo(click.style("    claude /erk:rebase", fg="cyan"))` → `"    claude /erk:pr-rebase"`
- **Line 366** (error message): `"check hooks or run 'claude /erk:rebase' directly to debug"` → `'claude /erk:pr-rebase'`

### 4. Update `tests/commands/pr/test_rebase.py`

- **Line 66**: `assert call[2] == "/erk:rebase"  # command` → `assert call[2] == "/erk:pr-rebase"  # command`

### 5. Update documentation files

#### `docs/ref/slash-commands.md`
- **Line 21**: `<!-- TODO: /quick-submit, /erk:auto-restack, /erk:rebase -->` → `/erk:pr-rebase`

#### `docs/howto/planless-workflow.md`
- **Line 109**: `` 1. **Use `/erk:rebase`** `` → `` **Use `/erk:pr-rebase`** ``

#### `docs/howto/conflict-resolution.md`
- **Line 35**: `/erk:rebase` → `/erk:pr-rebase`
- **Line 192**: `resolve them with `/erk:rebase`` → `/erk:pr-rebase`

#### `docs/learned/testing/rebase-conflicts.md`
- **Line 13**: `Use the `/erk:rebase` command.` → `` Use the `/erk:pr-rebase` command. ``

#### `docs/learned/architecture/rebase-conflict-patterns.md`
- **Line 62**: `launches Claude Code interactively with `/erk:rebase"` → `/erk:pr-rebase`

## Files NOT Changing

- **`.claude/commands/erk/diverge-fix.md`** — references "rebase" as a git concept, not the slash command
- **`CHANGELOG.md`** — historical reference, should not be modified per project rules
- **`.claude/skills/erk-exec/reference.md`** — references `rebase-with-conflict-resolution` exec script, which is a different thing from the slash command
- **`.claude/skills/gt/`** — references git rebase as a concept, not the slash command
- **`.claude/commands/erk/pr-submit.md`** — references git rebase concept, not the slash command
- **`.github/workflows/`** — no references found to `/erk:rebase`
- **CLI command name** — `erk pr rebase` stays the same (only the slash command is renamed)

## Implementation Details

- The rename is purely a find-and-replace of the string `/erk:rebase` → `/erk:pr-rebase` across all files listed above
- The command file must be renamed (git mv), not just its content updated — Claude Code derives slash command names from file paths
- Use `git mv .claude/commands/erk/rebase.md .claude/commands/erk/pr-rebase.md` to preserve git history

## Verification

1. Run `ruff check src/erk/cli/commands/pr/rebase_cmd.py src/erk/cli/output.py` — no lint errors
2. Run `pytest tests/commands/pr/test_rebase.py` — all tests pass
3. Grep for any remaining `/erk:rebase` references (excluding CHANGELOG.md): `grep -r "/erk:rebase" --include="*.py" --include="*.md" . | grep -v CHANGELOG.md` — should return zero matches
4. Verify the new command file exists: `ls .claude/commands/erk/pr-rebase.md`
5. Verify the old command file is gone: `ls .claude/commands/erk/rebase.md` should fail