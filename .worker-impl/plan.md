# Plan: Make land.sh Accept Arguments for Transparency

## Goal

Change `land.sh` script generation so users run:
```bash
source land.sh 5278 "P5277-fix-documentation-warning-01-19-1520"
```

Instead of:
```bash
source land.sh
```

This makes the PR number and branch name visible in the command itself, improving transparency.

## Current Behavior

**Generated script** (hardcoded values):
```bash
# erk land deferred execution
erk exec land-execute --pr-number=5278 --branch=P5277-fix... --use-graphite
cd /path/to/repo
```

**User sees**:
```
To land the PR:
  source /path/.erk/bin/land.sh  (copied to clipboard)
```

## New Behavior

**Generated script** (parameterized):
```bash
# erk land deferred execution
# Usage: source land.sh <pr_number> <branch>
PR_NUMBER="${1:?Error: PR number required}"
BRANCH="${2:?Error: Branch name required}"

erk exec land-execute --pr-number="$PR_NUMBER" --branch="$BRANCH" --use-graphite
cd /path/to/repo
```

**User sees**:
```
To land the PR:
  source /path/.erk/bin/land.sh 5278 "P5277-fix..."  (copied to clipboard)
```

## Files to Modify

### 1. `src/erk/cli/commands/land_cmd.py`

**Function: `render_land_execution_script()`** (lines 613-676)

Change from building hardcoded command to using shell variables:
- Add usage comment
- Define `PR_NUMBER="${1:?Error: PR number required}"`
- Define `BRANCH="${2:?Error: Branch name required}"`
- Use `"$PR_NUMBER"` and `"$BRANCH"` in the erk exec command

Return signature unchanged (still returns `str`).

**Callers of `print_temp_script_instructions()`** (3 locations):
- `_land_current_branch()` ~line 1077
- `_land_specific_pr()` ~line 1197
- `_land_by_branch()` ~line 1322

Each needs to pass the PR number and branch to build the full source command.

### 2. `src/erk/cli/activation.py`

**Function: `print_temp_script_instructions()`** (lines 364-393)

Add optional `args` parameter to include in the source command:
```python
def print_temp_script_instructions(
    script_path: Path,
    *,
    instruction: str,
    copy: bool,
    args: Sequence[str] | None,  # NEW
) -> None:
```

Build source command as:
```python
if args:
    quoted_args = " ".join(shlex.quote(str(a)) for a in args)
    source_cmd = f"source {script_path} {quoted_args}"
else:
    source_cmd = f"source {script_path}"
```

### 3. Tests

### New: `tests/unit/cli/commands/land/test_render_land_script.py`

Test `render_land_execution_script()`:
- Verify script includes `PR_NUMBER="${1:?...}"` and `BRANCH="${2:?...}"`
- Verify `erk exec land-execute` uses `"$PR_NUMBER"` and `"$BRANCH"`
- Verify optional flags are still hardcoded (e.g., `--use-graphite`)

### New: `tests/unit/cli/test_activation.py`

Test `print_temp_script_instructions()` with args parameter:
- Verify source command includes quoted arguments when provided
- Verify source command is plain when args is None

## Verification

1. Run `erk land` on a test branch with open PR
2. Verify the output shows `source land.sh <pr> <branch>`
3. Verify the generated script uses `$1` and `$2`
4. Run the full CI: `make all-ci`