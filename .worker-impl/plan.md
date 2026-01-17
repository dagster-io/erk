# Plan: Pass Through Flags to Shell Integration Message

## Problem

When running `erk land -f` without shell integration, the error message shows:
```
Run: source .../land.sh
```

But it should show:
```
Run: source .../land.sh -f
```

The original flags are lost, requiring the user to remember and re-type them.

## Solution

Reconstruct the CLI arguments from the function parameters and include them in the shell integration error message.

## Implementation

### File: `src/erk/cli/commands/land_cmd.py`

**Change location:** Lines 652-661 (the shell integration validation block)

**Current code:**
```python
if not script and not ctx.dry_run:
    land_script = ensure_land_script(repo.root)
    user_output(
        click.style("Error: ", fg="red")
        + "This command requires shell integration.\n\n"
        + f"Run: source {land_script}\n"
    )
    raise SystemExit(1)
```

**New code:**
```python
if not script and not ctx.dry_run:
    land_script = ensure_land_script(repo.root)

    # Reconstruct CLI args from parameters
    args: list[str] = []
    if target is not None:
        args.append(target)
    if up_flag:
        args.append("--up")
    if force:
        args.append("-f")
    if not pull_flag:
        args.append("--no-pull")
    if no_delete:
        args.append("--no-delete")

    args_str = " " + " ".join(args) if args else ""

    user_output(
        click.style("Error: ", fg="red")
        + "This command requires shell integration.\n\n"
        + f"Run: source {land_script}{args_str}\n"
    )
    raise SystemExit(1)
```

**Note:** `--dry-run` is not passed through because when `dry_run=True`, the code path sets `script=False` and shows human-readable output (lines 643-645), so it won't reach this error block anyway.

## Verification

1. Run `erk land -f` → should show `source .../land.sh -f`
2. Run `erk land --up` → should show `source .../land.sh --up`
3. Run `erk land -f --no-pull` → should show `source .../land.sh -f --no-pull`
4. Run `erk land 123 -f` → should show `source .../land.sh 123 -f`
5. Run `erk land` → should show `source .../land.sh` (no extra args)
6. Run devrun agent for pytest/ty/ruff checks