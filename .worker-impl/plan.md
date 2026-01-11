# Plan: Delete `erk plan start` Command

## Summary

Remove the `erk plan start` command, which starts a planning session in an assigned pool slot without requiring a pre-existing plan file.

## Files to Delete

1. **`src/erk/cli/commands/plan/start_cmd.py`** - Main command implementation (403 lines)
2. **`tests/commands/plan/test_start.py`** - Test suite (447 lines)

## Files to Modify

### 1. `src/erk/cli/commands/plan/__init__.py`

Remove import and command registration:
- Remove: `from erk.cli.commands.plan.start_cmd import plan_start`
- Remove: `plan_group.add_command(plan_start, name="start")`

### 2. `docs/learned/erk/slot-pool-architecture.md`

Update the entry points table to remove `erk plan start` reference (line 157).

## Not Modified

- `tests/unit/status/test_orchestrator.py` - Uses `"plan_start"` as a local execution-order tracking string, unrelated to this command.

## Verification

1. Run `devrun` agent with `ty check src/erk/cli/commands/plan/`
2. Run `devrun` agent with `pytest tests/commands/plan/ -v`
3. Run `erk plan --help` to confirm `start` is no longer listed