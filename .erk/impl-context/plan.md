# Plan: Add `erk release-notes` top-level command

## Context

The release notes viewer currently lives at `erk info release-notes`, which is buried and hard to discover. Claude Code has a top-level `/release-notes` command that's much more accessible. We want to match that pattern by promoting release notes to a top-level `erk release-notes` command.

## Changes

### 1. Create top-level command file

**New file:** `src/erk/cli/commands/release_notes_cmd.py`

- Import `release_notes_cmd` from the existing `info/release_notes_cmd.py` module and re-export it as a top-level command
- Actually, simpler: just import the existing click command directly — it's already a standalone `@click.command("release-notes")` with all the options

### 2. Register as top-level command in `cli.py`

**File:** `src/erk/cli/cli.py`

- Import `release_notes_cmd` from `erk.cli.commands.info.release_notes_cmd`
- Add `cli.add_command(release_notes_cmd)` alongside other top-level commands

### 3. Add to help formatter top-level list

**File:** `src/erk/cli/help_formatter.py`

- Add `"release-notes"` to the `top_level_commands` list (line 244) so it shows in the "Top-Level Commands" section of `erk --help`

### 4. Remove from info group (or keep as hidden alias)

**File:** `src/erk/cli/commands/info/__init__.py`

- Remove `release_notes_cmd` from the `info_group` since it's now top-level
- If `info_group` has no other commands, remove the group entirely from `cli.py` and `help_formatter.py`

## Files to modify

- `src/erk/cli/cli.py` — register top-level command, possibly remove info_group
- `src/erk/cli/help_formatter.py` — add to top-level list, possibly remove "info" from groups
- `src/erk/cli/commands/info/__init__.py` — remove command (or delete file if empty)

## Verification

1. Run `erk release-notes` — should show current version's notes
2. Run `erk release-notes --all` — should show all releases
3. Run `erk release-notes --version 0.9.5` — should show specific version
4. Run `erk --help` — should show `release-notes` in Top-Level Commands
5. Run existing tests if any exist for the info group
