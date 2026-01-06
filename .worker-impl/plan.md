# Plan: Add Required Kwargs to Functions with 6+ Parameters

## Objective

Enforce keyword-only arguments on all functions with 6 or more parameters to improve call-site readability and catch parameter ordering bugs at the type-checker level.

## Related Documentation

- **Skills to load**: `dignified-python` (loaded)
- **Docs**: None additional needed

## Functions to Modify

### 1. `execute_command_streaming` (6 params)
**File**: `src/erk/core/claude_executor.py:48`

**Current signature:**
```python
def execute_command_streaming(
    self,
    command: str,
    worktree_path: Path,
    dangerous: bool,
    verbose: bool = False,
    debug: bool = False,
    model: str | None = None,
) -> Iterator[ClaudeEvent]:
```

**New signature:** Add `*` after `self`

**Callsites to update:**
- `src/erk/cli/output.py:174` - uses positional args for first 3, needs keywords
- `src/erk/cli/output.py:286` - already uses keywords ✅

---

### 2. `execute_interactive_mode` (6 params)
**File**: `src/erk/cli/commands/implement_shared.py:248`

**Current signature:**
```python
def execute_interactive_mode(
    ctx: ErkContext,
    repo_root: Path,
    worktree_path: Path,
    dangerous: bool,
    model: str | None,
    executor: ClaudeExecutor,
) -> None:
```

**New signature:** Add `*` after `ctx`

**Callsites to update:**
- `src/erk/cli/commands/implement.py:468` - positional, needs keywords
- `src/erk/cli/commands/implement.py:565` - positional, needs keywords

---

### 3. `stream_command_with_feedback` (6 params)
**File**: `src/erk/cli/output.py:121`

**Current signature:**
```python
def stream_command_with_feedback(
    executor: ClaudeExecutor,
    command: str,
    worktree_path: Path,
    dangerous: bool,
    model: str | None = None,
    debug: bool = False,
) -> CommandResult:
```

**New signature:** Add `*` after first param

**Callsites:** Already use keyword args ✅
- `src/erk/cli/commands/implement_shared.py:333`
- `src/erk/cli/commands/objective_helpers.py:116`

---

### 4. `context_for_test` (24 params)
**File**: `src/erk/core/context.py:148`

**Current signature:** All params have defaults

**New signature:** Add `*` at start (all params keyword-only)

**Callsites:** All 100+ callsites already use keyword args ✅

---

### 5. `RealCommandExecutor.__init__` (6 params)
**File**: `src/erk/tui/commands/real_executor.py:15`

**Current signature:**
```python
def __init__(
    self,
    browser_launch: Callable[[str], Any],
    clipboard_copy: Callable[[str], Any],
    close_plan_fn: Callable[[int, str], list[int]],
    notify_fn: Callable[[str], None],
    refresh_fn: Callable[[], None],
    submit_to_queue_fn: Callable[[int, str], None],
) -> None:
```

**New signature:** Add `*` after `self`

**Callsites:** Already use keyword args ✅
- `src/erk/tui/app.py` (2 instances)

---

## Implementation Steps

1. **Modify `execute_command_streaming`**
   - Add `*` after `self` in signature
   - Update callsite at `output.py:174` to use keyword args

2. **Modify `execute_interactive_mode`**
   - Add `*` after `ctx` in signature
   - Update 2 callsites in `implement.py` to use keyword args

3. **Modify `stream_command_with_feedback`**
   - Add `*` after first param in signature
   - No callsite changes needed

4. **Modify `context_for_test`**
   - Add `*` at start of params (after none - all become keyword-only)
   - No callsite changes needed

5. **Modify `RealCommandExecutor.__init__`**
   - Add `*` after `self` in signature
   - No callsite changes needed

6. **Run tests** via devrun agent to verify no regressions

## Files to Modify

| File | Changes |
|------|---------|
| `src/erk/core/claude_executor.py` | Add `*` to signature |
| `src/erk/cli/output.py` | Add `*` to signature + update 1 callsite |
| `src/erk/cli/commands/implement_shared.py` | Add `*` to signature |
| `src/erk/cli/commands/implement.py` | Update 2 callsites |
| `src/erk/core/context.py` | Add `*` to signature |
| `src/erk/tui/commands/real_executor.py` | Add `*` to signature |

## Not In Scope

- **Click commands** (`implement`) - Parameters come from Click framework decorators
- **Functions already using `*`** - Already compliant
- **Test files** - Only production code