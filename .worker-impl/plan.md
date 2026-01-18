# Plan: Add `-d` alias to all `--dangerous` flags

## Summary

Add the `-d` short form alias to all `--dangerous` CLI option flags for consistency and ease of use.

## Files to Modify

### 1. `src/erk/cli/commands/prepare.py` (line 17-21)
**Current:**
```python
@click.option(
    "--dangerous",
    is_flag=True,
    help="Include --dangerous flag to skip permission prompts during implementation",
)
```
**Change to:**
```python
@click.option(
    "-d",
    "--dangerous",
    is_flag=True,
    help="Include --dangerous flag to skip permission prompts during implementation",
)
```

### 2. `src/erk/cli/commands/branch/create_cmd.py` (line 40-44)
**Current:**
```python
@click.option(
    "--dangerous",
    is_flag=True,
    help="Include --dangerous flag to skip permission prompts during implementation",
)
```
**Change to:**
```python
@click.option(
    "-d",
    "--dangerous",
    is_flag=True,
    help="Include --dangerous flag to skip permission prompts during implementation",
)
```

### 3. `src/erk/cli/commands/learn/learn_cmd.py` (line 70-74)
**Current:**
```python
@click.option(
    "--dangerous",
    is_flag=True,
    help="Launch Claude with --dangerously-skip-permissions (skip all permission prompts)",
)
```
**Change to:**
```python
@click.option(
    "-d",
    "--dangerous",
    is_flag=True,
    help="Launch Claude with --dangerously-skip-permissions (skip all permission prompts)",
)
```

### 4. `src/erk/cli/commands/implement_shared.py` (line 90-95)
**Current:**
```python
fn = click.option(
    "--dangerous",
    is_flag=True,
    default=False,
    help="Skip permission prompts by passing --dangerously-skip-permissions to Claude",
)(fn)
```
**Change to:**
```python
fn = click.option(
    "-d",
    "--dangerous",
    is_flag=True,
    default=False,
    help="Skip permission prompts by passing --dangerously-skip-permissions to Claude",
)(fn)
```

### 5. `src/erk/cli/commands/pr/fix_conflicts_cmd.py` (line 15-20)
**Current:** (incorrectly uses `-f` which should be reserved for `--force`)
```python
@click.option(
    "-f",
    "--dangerous",
    is_flag=True,
    help="Acknowledge that this command invokes Claude with --dangerously-skip-permissions.",
)
```
**Change to:**
```python
@click.option(
    "-d",
    "--dangerous",
    is_flag=True,
    help="Acknowledge that this command invokes Claude with --dangerously-skip-permissions.",
)
```

### 6. `src/erk/cli/commands/pr/sync_cmd.py` (line 125-129)
**Current:**
```python
@click.option(
    "--dangerous",
    is_flag=True,
    help="Required for Graphite mode (invokes Claude with --dangerously-skip-permissions).",
)
```
**Change to:**
```python
@click.option(
    "-d",
    "--dangerous",
    is_flag=True,
    help="Required for Graphite mode (invokes Claude with --dangerously-skip-permissions).",
)
```

## Verification

1. Run `make fast-ci` to ensure all tests pass
2. Verify help text shows `-d` alias: `erk implement --help`, `erk pr sync --help`, etc.