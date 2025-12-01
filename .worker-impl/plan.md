# Plan: Rename `erk ls` to `erk dash`

## Summary

Rename the top-level `erk list`/`erk ls` command to `erk dash` with no aliases.

## Changes

### 1. Command Implementation

**File:** `src/erk/cli/commands/plan/list_cmd.py`

- Remove `@alias("ls")` decorator from `list_plans` function
- Rename command from `"list"` to `"dash"` in `@click.command()` decorator
- Optionally rename function from `list_plans` to `dash` for consistency

### 2. CLI Registration

**File:** `src/erk/cli/cli.py`

- Change `register_with_aliases(cli, list_plans, name="list")` to `cli.add_command(dash)` (or `list_plans` if keeping function name)
- Update import if function is renamed

### 3. Help Formatter

**File:** `src/erk/cli/help_formatter.py`

- Update the `PLANS_COMMANDS` list: change `"list"` to `"dash"`

### 4. Tests

**File:** `tests/commands/test_top_level_commands.py`

- Rename `test_ls_command_lists_plans_by_default` to `test_dash_command_lists_plans_by_default`
- Rename `test_ls_command_plan_filters_work` to `test_dash_command_plan_filters_work`
- Update CLI invocations from `["ls", ...]` to `["dash", ...]`

**Files:** `tests/unit/cli/test_alias.py`, `tests/unit/cli/test_aliases.py`

- Update any tests that specifically reference the `list`/`ls` alias pair

### 5. Documentation

**File:** `.claude/skills/erk/SKILL.md`

- Update all `erk ls` references to `erk dash`

**File:** `.claude/skills/erk/references/erk.md`

- Update command documentation from `erk list`/`erk ls` to `erk dash`

**File:** `docs/agent/cli-command-organization.md`

- Update quick reference from `erk ls` to `erk dash`

### 6. Kit Documentation

**File:** `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/mark_impl_started.py`

- Update any `erk ls` references

**File:** `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/plan-implement.md`

- Update any `erk ls` references
