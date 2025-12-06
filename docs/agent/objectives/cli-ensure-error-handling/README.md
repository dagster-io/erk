# Objective: CLI Error Handling via Ensure

## Desired State

All error handling in the CLI layer uses the `Ensure` class (`src/erk/cli/ensure.py`) rather than manual error checking patterns.

**When this objective is met:**
- No raw `raise SystemExit(1)` with inline error formatting in CLI command files
- All error messages use consistent styling (red "Error:" prefix)
- Type narrowing happens at the validation point, not scattered through code
- Error handling is declarative and concise

## Rationale

**Why this matters:**

1. **Consistency** - Users see the same error format everywhere
2. **Conciseness** - `Ensure.not_none(x, msg)` replaces 4-line if/print/raise blocks
3. **Type narrowing** - Ensure methods return narrowed types, so subsequent code doesn't need None checks
4. **Discoverability** - All validation patterns are documented in one place

**Agent judgment guidance:**
- When you see a validation pattern not covered by Ensure, consider whether to add a new Ensure method or use `Ensure.invariant()`
- Prefer domain-specific methods (e.g., `Ensure.not_detached_head`) over generic ones when the pattern appears 2+ times
- New Ensure methods need tests in `tests/unit/cli/test_ensure.py`

## Examples

### Before (avoid this)

```python
branch = ctx.git.get_current_branch(ctx.cwd)
if branch is None:
    user_output(click.style("Error: ", fg="red") + "Cannot consolidate: you're in detached HEAD state")
    raise SystemExit(1)
# branch is still typed as str | None here - requires ! assertion or re-check
```

### After (what we want)

```python
raw_branch = ctx.git.get_current_branch(ctx.cwd)
branch = Ensure.not_none(raw_branch, "Cannot consolidate: you're in detached HEAD state")
# branch is now typed as str - no None checks needed downstream
```

### Even better (domain-specific)

```python
branch = Ensure.not_detached_head(ctx, ctx.git.get_current_branch(ctx.cwd), "consolidate")
# Clear intent, consistent messaging, proper type narrowing
```

## Scope

**In scope:**
- All files under `src/erk/cli/commands/`
- CLI helper modules: `src/erk/cli/subprocess_utils.py`, etc.
- Error handling that results in `SystemExit(1)` with user-facing messages

**Out of scope:**
- `src/erk/cli/ensure.py` itself (that's the implementation, not a consumer)
- Core library code (`src/erk/core/`) - those should raise exceptions, not SystemExit
- Test files
- `SystemExit(0)` for successful early returns (e.g., `--help` or no-op cases)
- Exception re-raising patterns (`raise SystemExit(1) from e`) - these may need case-by-case consideration

## How to Contribute

### Quick start for agents

1. Read this README
2. Check `work-log.md` for recent context
3. Check `learnings.md` for patterns discovered so far
4. Pick a file or pattern to work on
5. Make changes, run tests, update work log

### Verification

To check progress toward this objective:

```bash
# Count remaining raw SystemExit patterns (lower is better)
rg "raise SystemExit\(1\)" src/erk/cli/commands/ --count | wc -l

# Exclude the ensure.py file itself
rg "raise SystemExit\(1\)" src/erk/cli/commands/ --glob '!**/ensure.py'
```

### Workflow

1. **Pick work** - Find a file with manual error handling patterns
2. **Assess** - Do existing Ensure methods cover this? If not, need new method?
3. **Implement** - Convert patterns, add tests if new method
4. **Verify** - Run affected tests, check types with pyright
5. **Log** - Add entry to `work-log.md` with session ID

## Related Files

- **Implementation**: `src/erk/cli/ensure.py`
- **Tests**: `tests/unit/cli/test_ensure.py`
- **Detailed task tracking**: `src/erk/cli/ensure-conversion-tasks.md` (legacy, may migrate here)

## Status

**Nature**: Achievable - this objective has a finite endpoint when all conversions are complete.

**Current state**: In progress. The Ensure class exists with ~15 methods. Approximately 80+ unconverted patterns remain across CLI files.

**See**: `work-log.md` for session history
