# Fix land.sh Script Sourcing Error

## Problem Summary

When the user runs `source .erk/bin/land.sh`, the shell reports:
```
no such file or directory:   /var/folders/.../erk-land-72f5c832.sh
```

The temp file is being created but doesn't exist when the shell tries to source it.

## Root Cause

The current approach has a fragile dependency chain:
1. `land.sh` uses `source "$(erk land --script)"`
2. Command substitution `$()` runs erk, captures stdout (a file PATH)
3. Shell tries to `source` that path as a file
4. File doesn't exist (possible race condition or cleanup)

## Solution: Output Script Content Directly

Instead of writing to a temp file and outputting the path, **output the script content directly** and use **process substitution**:

```bash
# Current (fragile - relies on temp file existing):
source "$(erk land --script "$@")"

# Fixed (robust - sources content directly via FIFO):
source <(erk land --script "$@")
```

This eliminates the temp file dependency entirely. Process substitution `<()` creates a named pipe (FIFO) that the shell reads from directly.

## Implementation

### 1. Update `render_land_script()` in `src/erk/cli/activation.py`

Change the land.sh wrapper to use process substitution:

```python
def render_land_script() -> str:
    return """#!/usr/bin/env bash
# erk land wrapper - source this script to land with shell integration
# Usage: source .erk/bin/land.sh [args...]
source <(erk land --script "$@")
"""
```

### 2. Update `activate_root_repo()` in `src/erk/cli/commands/navigation_helpers.py`

Change to output script content instead of path when called from land command:

```python
if script:
    script_content = render_activation_script(...)
    # Output content directly instead of writing to temp file
    machine_output(script_content, nl=False)
```

**Wait** - this would break other commands that use the path pattern. Need a different approach.

### Alternative: Keep temp file but make land.sh more robust

Actually, looking at this more, the cleanest fix is just to change `land.sh` to use process substitution to read the file:

```bash
source <(cat "$(erk land --script "$@")")
```

This:
1. Runs `erk land --script`, captures the path
2. Uses `cat` to read the file immediately
3. Feeds content to `source` via process substitution

Even if the file gets deleted after `cat` reads it, the content is already in the pipe.

## Files to Modify

1. `src/erk/cli/activation.py` - Line 248, `render_land_script()` function

## Change

```python
# Before:
def render_land_script() -> str:
    return """#!/usr/bin/env bash
# erk land wrapper - source this script to land with shell integration
# Usage: source .erk/bin/land.sh [args...]
source "$(erk land --script "$@")"
"""

# After:
def render_land_script() -> str:
    return """#!/usr/bin/env bash
# erk land wrapper - source this script to land with shell integration
# Usage: source .erk/bin/land.sh [args...]
source <(cat "$(erk land --script "$@")")
"""
```

## Verification

1. Run `make py-test` to verify tests pass
2. Test manually in a worktree with a PR:
   - Create a test worktree with a PR
   - Run `source .erk/bin/land.sh`
   - Verify navigation works correctly