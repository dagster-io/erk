# Add --allow-dangerously-skip-permissions and --verbose flags to erk planner connect

## Summary

Add `--allow-dangerously-skip-permissions` and `--verbose` flags to the claude invocation in `erk planner connect`.

## Files to Modify

### 1. `src/erk/cli/commands/planner/connect_cmd.py`

**Current code (line 65):**

```python
claude_command = 'claude "/erk:craft-plan"'
```

**New code:**

```python
claude_command = 'claude --allow-dangerously-skip-permissions --verbose "/erk:craft-plan"'
```

### 2. `tests/commands/planner/test_planner_connect.py`

**Update test assertion (lines 184-188):**

Current:

```python
expected_remote_cmd = (
    "bash -l -c 'git pull && uv sync && source .venv/bin/activate "
    '&& claude "/erk:craft-plan"\''
)
```

New:

```python
expected_remote_cmd = (
    "bash -l -c 'git pull && uv sync && source .venv/bin/activate "
    '&& claude --allow-dangerously-skip-permissions --verbose "/erk:craft-plan"\''
)
```
