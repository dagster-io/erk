# Plan: Migrate navigation_helpers.py to Ensure Pattern

**Part of Objective #5185, Step 1A.1**

## Goal

Migrate error-handling patterns in `navigation_helpers.py` to use the Ensure class where there's a **clear boolean condition to express**. Establish criteria for what makes a good Ensure candidate.

## Current State Analysis

**File:** `src/erk/cli/commands/navigation_helpers.py`

**Already using Ensure (3 patterns):**
- Line 63-67: `Ensure.invariant()` for clean working tree check
- Line 321: `Ensure.path_exists()` for worktree path check
- Lines 392-395: `Ensure.truthy()` for children check

**Candidates for migration (5 instances in 4 locations):**

| Location | Lines | Condition | Migrate? |
|----------|-------|-----------|----------|
| `check_pending_learn_marker` | 50-55 | "reached end of function" | **No** - no clear condition |
| `verify_pr_closed_or_merged` | 110-117 | After interactive prompts | **No** - side effects before error |
| `resolve_up_navigation` | 398-404 | `len(children) > 1` | **Yes** - clear condition |
| `resolve_down_navigation` | 450-451 | `current_branch == detected_trunk` | **Yes** - clear condition |
| `resolve_down_navigation` | 453-454 | "reached else branch" | **No** - no clear condition |

## Design Decisions

1. **Only migrate clear conditions**: Ensure provides value when the invariant is explicit and readable
2. **Anti-pattern: `Ensure.invariant(False, ...)`**: This is just obfuscated error handling - provides no clarity about what's being checked
3. **Leave complex flows as-is**: Patterns with early returns, side effects, or "fallthrough to error" don't benefit from Ensure
4. **Document criteria**: This steelthread establishes what makes a good migration candidate

### Migration Criteria

**Good Ensure candidate:**
- Has a clear boolean condition that can be inverted (e.g., `if len(x) > 1:` → `Ensure.invariant(len(x) <= 1, ...)`)
- No side effects before the error
- Condition is meaningful when read (tells you what the code expects)

**Skip migration:**
- "Reached end of function after early returns" - no condition to express
- "Reached else branch" - the condition is implicit in control flow
- Has warnings, prompts, or other side effects before the error

## Implementation

### Step 1: Migrate `resolve_up_navigation` (lines 398-404)

**Before:**
```python
if len(children) > 1:
    children_list = ", ".join(f"'{child}'" for child in children)
    user_output(
        f"Error: Branch '{current_branch}' has multiple children: {children_list}.\n"
        f"Please create worktree for specific child: erk create <branch-name>"
    )
    raise SystemExit(1)
```

**After:**
```python
Ensure.invariant(
    len(children) <= 1,
    f"Branch '{current_branch}' has multiple children: "
    f"{', '.join(f\"'{c}'\" for c in children)}.\n"
    f"Please create worktree for specific child: erk create <branch-name>",
)
```

### Step 2: Migrate `resolve_down_navigation` first error (lines 446-451)

**Before:**
```python
if parent_branch is None:
    detected_trunk = ctx.git.detect_trunk_branch(repo.root)
    if current_branch == detected_trunk:
        user_output(f"Already at the bottom of the stack (on trunk branch '{detected_trunk}')")
        raise SystemExit(1)
    else:
        user_output("Error: Could not determine parent branch from Graphite metadata")
        raise SystemExit(1)
```

**After:**
```python
if parent_branch is None:
    detected_trunk = ctx.git.detect_trunk_branch(repo.root)
    Ensure.invariant(
        current_branch != detected_trunk,
        f"Already at the bottom of the stack (on trunk branch '{detected_trunk}')",
    )
    # Not on trunk but no parent - keep as direct error (no clear condition to express)
    user_output(
        click.style("Error: ", fg="red")
        + "Could not determine parent branch from Graphite metadata"
    )
    raise SystemExit(1)
```

### Patterns NOT migrated (with rationale)

1. **`check_pending_learn_marker` (lines 50-55)**: The "condition" is "reached this point after early returns" - no boolean to express
2. **`verify_pr_closed_or_merged` (lines 110-117)**: Has interactive `ctx.console.confirm()` prompts before the error
3. **`resolve_down_navigation` second error (lines 453-454)**: The "condition" is "reached else branch" - implicit in control flow

## Files to Modify

- `src/erk/cli/commands/navigation_helpers.py`

## Verification

1. Run type checker: `ty check src/erk/cli/commands/navigation_helpers.py`
2. Run tests: `pytest tests/unit/cli/commands/ -k navigation -v`
3. Verify migrations:
   ```bash
   grep -n "Ensure\." src/erk/cli/commands/navigation_helpers.py
   ```
   Expected: 5 Ensure calls (3 existing + 2 new)

## Outcome

- 2 patterns migrated to Ensure (clear boolean conditions)
- 3 patterns documented as not suitable (no clear condition or has side effects)
- Establishes migration criteria for subsequent phases
- Anti-pattern documented: never use `Ensure.invariant(False, ...)`