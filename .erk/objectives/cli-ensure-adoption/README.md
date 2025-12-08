# Objective: cli-ensure-adoption

## Type

completable

## Desired State

All CLI error handling in `src/erk/cli/` uses the `Ensure` class from `src/erk/cli/ensure.py` instead of directly raising `SystemExit`. This means:

1. **No direct `raise SystemExit(1)` calls** outside of `ensure.py` itself
2. **Consistent error message formatting** - All errors use the red "Error: " prefix pattern
3. **Type narrowing where applicable** - Methods like `Ensure.not_none()` and `Ensure.not_detached_head()` provide type-safe returns
4. **Domain-specific validation methods** - Common validation patterns are encapsulated as reusable methods

The `Ensure` class provides:

- `invariant(condition, message)` - Generic condition check
- `truthy(value, message)` - Returns value if truthy
- `not_none(value, message)` - Type-narrowing None check
- `path_exists(ctx, path, message)` - Path validation
- `not_empty(value, message)` - String/collection emptiness
- And many more domain-specific methods for git, worktree, and CLI validation

## Rationale

**Consistency**: Standardizing error handling ensures users see consistent error messages across all CLI commands.

**Maintainability**: Having error checking patterns in one place makes it easier to modify error formatting, add logging, or change exit behavior globally.

**Type Safety**: Methods like `Ensure.not_none()` provide type narrowing, allowing downstream code to work with non-null values without additional checks.

**LBYL Compliance**: The Ensure pattern aligns with our "Look Before You Leap" coding standards - checking conditions proactively rather than catching exceptions.

**Discoverability**: New developers can look at `ensure.py` to understand all the validation patterns available, rather than hunting through scattered error handling code.

## Examples

### Before: Direct SystemExit

```python
# Found throughout CLI commands
if not ctx.git.get_current_branch(ctx.cwd):
    user_output(click.style("Error: ", fg="red") + "Not on a branch")
    raise SystemExit(1)

# Or without consistent formatting
if branch is None:
    click.echo("Branch not found", err=True)
    raise SystemExit(1)
```

### After: Using Ensure

```python
from erk.cli.ensure import Ensure

# Using existing methods
Ensure.not_none(ctx.git.get_current_branch(ctx.cwd), "Not on a branch")

# Using domain-specific method (to be implemented)
branch = Ensure.not_detached_head(ctx, ctx.cwd)  # Returns str (type narrowed)
```

### Pattern: Mutually Exclusive Flags

Before:

```python
flag_count = sum([bool(up), bool(down), bool(to)])
if flag_count > 1:
    user_output(click.style("Error: ", fg="red") + "Only one of --up, --down, --to can be specified")
    raise SystemExit(1)
```

After:

```python
Ensure.mutually_exclusive_flags(
    [("--up", up), ("--down", down), ("--to", to)],
    "Only one navigation flag can be specified"
)
```

## Scope

### In Scope

- All files in `src/erk/cli/` directory
- All CLI commands that currently raise `SystemExit(1)` directly
- Creating new `Ensure` methods for common patterns not yet covered
- Migration of existing error handling to use `Ensure` methods

### Out of Scope

- The `ensure.py` module itself (internal `SystemExit` raises are correct)
- Exit code 0 cases (successful early returns)
- Non-CLI code (libraries, shared modules)
- Subprocess error handling in wrapper functions (these are error boundaries)

## Turn Configuration

### Evaluation Prompt

Search the codebase for direct `raise SystemExit(1)` calls in `src/erk/cli/` that are NOT inside `ensure.py`. For each occurrence:

1. Identify the validation pattern being performed
2. Determine if an existing `Ensure` method can handle it
3. If not, note what new `Ensure` method would be needed

Report:

- Total count of direct SystemExit(1) raises remaining
- Breakdown by file
- List of validation patterns not yet covered by Ensure methods
- Recommendation for highest-impact next conversion

### Plan Sizing

Plans generated from this objective should:

1. **Be bounded to 2-4 hours of work** - Either implement 1-2 new Ensure methods OR convert 2-3 files
2. **Prioritize high-frequency patterns first** - Methods like `mutually_exclusive_flags` that appear in 8+ places should come before one-off patterns
3. **Include tests** - Each new Ensure method needs unit tests; file conversions need regression testing
4. **Be independently valuable** - Each plan should reduce direct SystemExit count and be mergeable on its own

Suggested plan granularity:

- **Small**: Convert 1 file with <5 direct SystemExit calls
- **Medium**: Implement 1 new Ensure method + convert files using it
- **Large**: Implement 2 new Ensure methods OR convert 1 large file (15+ occurrences)
