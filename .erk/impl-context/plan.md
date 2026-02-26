# Documentation Plan: Add .ensure() to NonIdealState classes and IssueComments wrapper

## Context

This PR (#8258) implements a significant ergonomic improvement to erk's discriminated union error handling pattern. The core innovation is a **two-sided `.ensure()` pattern** where both success and error types in `T | NonIdealState` unions implement an `ensure()` method, enabling one-liner unwrapping: `result = operation().ensure()`. For success types, `ensure()` returns `self`; for error types, it raises `NonIdealStateError`. This eliminates 4+ `_ensure_*` helper functions per module and creates a uniform API for result handling.

The implementation journey across 5 sessions revealed critical Python Protocol semantics that warrant tripwire documentation. Specifically, Protocol concrete methods don't inherit structurally (only via explicit inheritance), and Protocol `@property` declarations create descriptor conflicts with frozen dataclass fields of the same name. The `NonIdealStateMixin` pattern emerged as an architectural solution to the latter constraint.

Future agents need to understand when to use Protocol inheritance vs. the mixin pattern, how to wrap built-in types (like lists) in `EnsurableResult` dataclasses, and why type narrowing assertions after `.ensure()` are NOT dead code despite what automated reviewers may claim. This documentation captures hard-won lessons from implementation iterations that would otherwise need to be re-learned.

## Raw Materials

PR #8258

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 14    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 4     |
| Potential tripwires (score2-3) | 3     |

## Documentation Items

### HIGH Priority

#### 1. Protocol property descriptor conflict with frozen dataclass fields

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Sessions f0087b17, 327598da

**Draft Content:**

```markdown
## Protocol Property Descriptor Conflict

**Trigger:** Before inheriting from a Protocol with `@property` declarations in a frozen dataclass

**Problem:** When a Protocol declares `@property def message(self) -> str` and a frozen dataclass inherits from it while defining `message: str` as a field, Python raises `AttributeError: property 'message' of '...' object has no setter`. The property descriptor's `__set__` method raises AttributeError, blocking even `object.__setattr__` during frozen dataclass `__init__`.

**Warning:** Check if Protocol declares properties matching your dataclass field names. Protocol `@property` creates a descriptor that blocks frozen dataclass field initialization.

**Resolution:** Use the mixin pattern (`NonIdealStateMixin`) to provide shared methods without declaring property descriptors. See `packages/erk-shared/src/erk_shared/non_ideal_state.py` for implementation.

**Severity:** HIGH - causes immediate runtime AttributeError at class instantiation
```

---

#### 2. Protocol concrete methods don't inherit structurally

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Sessions 327598da, f0087b17

**Draft Content:**

```markdown
## Protocol Concrete Method Inheritance

**Trigger:** Before defining a concrete method in a Protocol expecting structural implementations to inherit it

**Problem:** Concrete methods defined in a Protocol body are NOT automatically inherited by classes that structurally match the Protocol. They only inherit when classes explicitly inherit from the Protocol class itself. `@runtime_checkable` `isinstance()` checks verify attribute presence on instances, so if the method isn't physically present, the check fails at runtime.

**Warning:** Protocol concrete methods require explicit inheritance. Classes that structurally match a Protocol don't inherit concrete methods. Add the method to each concrete class OR make all classes explicitly inherit from the Protocol.

**Resolution:** Either:
1. Add method explicitly to each concrete class
2. Use a mixin class for shared implementation
3. Make all classes explicitly inherit from the Protocol

**Severity:** HIGH - causes isinstance checks to fail at runtime, type narrowing fails at compile time
```

---

#### 3. EnsurableResult and two-sided .ensure() pattern

**Location:** `docs/learned/architecture/discriminated-union-error-handling.md`
**Action:** UPDATE (new section)
**Source:** [Impl] Sessions 294a070f, b9666d76, fc5d8669; [PR #8258]

**Draft Content:**

```markdown
## The .ensure() Instance Method Pattern

### Overview

The `.ensure()` pattern enables one-liner unwrapping for `T | NonIdealState` union return types:

```python
# Instead of verbose LBYL:
result = operation()
if isinstance(result, SomeError):
    raise SomeException(result.message)
# Use result...

# One-liner with .ensure():
result = operation().ensure()
# result is now type-narrowed to T
```

### Two-Sided Pattern

Both success and error types implement `ensure()` with different return types:

- **Success types** (inherit `EnsurableResult`): `ensure() -> Self` returns the instance
- **Error types** (implement `NonIdealState`): `ensure() -> NoReturn` raises `NonIdealStateError`

The union `T | NoReturn` simplifies to `T` from the type checker's perspective.

### Implementation

See `packages/erk-shared/src/erk_shared/non_ideal_state.py` for:
- `EnsurableResult` mixin for success types
- `NonIdealStateError` exception raised by error types
- `NonIdealStateMixin` for error types with field/property conflicts

### When to Use

Use `.ensure()` pattern when:
- You have a `T | NonIdealState` return type
- You want to unwrap the success value or fail fast
- The error handling is "raise and exit" (not conditional logic)

Use LBYL `isinstance()` checks when:
- You need custom error handling logic
- The success type is a built-in that can't inherit `EnsurableResult`
- You need to inspect the error before deciding how to handle it
```

---

#### 4. NonIdealStateMixin workaround pattern

**Location:** `docs/learned/architecture/discriminated-union-error-handling.md`
**Action:** UPDATE (new section)
**Source:** [Impl] Sessions 294a070f, f0087b17; [PR #8258]

**Draft Content:**

```markdown
## NonIdealStateMixin for Field-Based Classes

### Problem

When a frozen dataclass defines `message: str` as a field and inherits from `NonIdealState` Protocol (which declares `message` as `@property`), Python raises `AttributeError` at initialization due to property descriptor conflicts.

### Solution

Use `NonIdealStateMixin` instead of Protocol inheritance:

```python
@dataclass(frozen=True)
class GitHubAPIFailed(NonIdealStateMixin):  # NOT NonIdealState
    message: str
    error_type: Literal["github_api_failed"] = "github_api_failed"
```

The mixin provides `ensure()` without declaring properties, avoiding descriptor conflicts.

### Decision Tree

- **Field has same name as Protocol property?** -> Use `NonIdealStateMixin`
- **Field names don't conflict?** -> Can inherit from `NonIdealState` Protocol directly
- **Using `@property` for computed values?** -> Inherit from `NonIdealState` Protocol

### Implementation Reference

See `packages/erk-shared/src/erk_shared/non_ideal_state.py` for the mixin implementation. Note the `type: ignore[arg-type]` comment needed when passing `self` to `NonIdealStateError` (mixin's `self` isn't typed as the full Protocol).
```

---

### MEDIUM Priority

#### 5. Type narrowing assertion pattern after isinstance + ensure()

**Location:** `docs/learned/conventions.md` (add to type narrowing section) OR `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Session fc5d8669; [PR #8258]

**Draft Content:**

```markdown
## Type Narrowing After ensure() in Guards

**Trigger:** After `isinstance(x, ErrorType): x.ensure()` guard blocks

**Problem:** The type checker doesn't automatically narrow the union type after `.ensure()` is called inside an `isinstance()` guard. The code after the guard still sees `T | ErrorType`.

**Pattern:**

```python
branch = get_branch()  # returns str | BranchDetectionFailed
if isinstance(branch, BranchDetectionFailed):
    branch.ensure()  # NoReturn - raises exception
assert not isinstance(branch, BranchDetectionFailed)  # Required for ty
# Now branch is narrowed to str
```

**Warning:** The assert is NOT dead code. It executes on the happy path (when `branch` is `str`, the if block is skipped entirely). It's required for `ty` type narrowing when `.ensure()` doesn't automatically narrow.

**Bot False Positive:** Automated reviewers flag this as "dead code after NoReturn". They misunderstand that the assert is AFTER the if block, not AFTER the `.ensure()` call.

**Severity:** MEDIUM - code works without it, but type checking fails
```

---

#### 6. Built-in type union limitation and wrapper pattern

**Location:** `docs/learned/architecture/discriminated-union-error-handling.md`
**Action:** UPDATE (new section)
**Source:** [Impl] Sessions 294a070f, b9666d76; [PR #8258]

**Draft Content:**

```markdown
## Collection Wrapper Pattern for Built-in Types

### Problem

Built-in types (`list`, `str`, `tuple`) cannot inherit from `EnsurableResult`. Unions like `list[T] | NonIdealState` cannot use the one-liner `.ensure()` pattern because the success type lacks the method.

### Solution: Wrapper Dataclass

Wrap the built-in type in a frozen dataclass that inherits from `EnsurableResult`:

```python
@dataclass(frozen=True)
class IssueComments(EnsurableResult):
    """Wraps tuple[IssueComment, ...] to enable .ensure() unwrapping."""
    comments: tuple[IssueComment, ...]

    def __iter__(self) -> Iterator[IssueComment]:
        return iter(self.comments)
```

### Key Implementation Points

- Use `tuple` internally (immutable, aligns with frozen dataclass)
- Implement `__iter__()` to maintain drop-in compatibility with iteration patterns
- Inherit from `EnsurableResult` to get `ensure() -> Self`
- Return type changes from `list[T] | Error` to `WrapperClass | Error`

### When to Wrap

**Wrap when:**
- The collection is returned from a gateway method
- Callers consistently need the `.ensure()` pattern
- API consistency matters more than avoiding type proliferation

**Accept LBYL when:**
- Single call site that handles errors differently
- The built-in type semantics (slicing, indexing) are heavily used
- Minimal ergonomic benefit from wrapping

### Example

See `packages/erk-shared/src/erk_shared/gateway/github/issues/types.py` for `IssueComments` implementation and `checks.py` for the `issue_comments()` method return type change.
```

---

#### 7. handle_non_ideal_exit decorator pattern

**Location:** `docs/learned/cli/exec-script-patterns.md` OR new `docs/learned/cli/error-handling-patterns.md`
**Action:** UPDATE or CREATE
**Source:** [Impl] Session 327598da; [PR #8258]

**Draft Content:**

```markdown
## @handle_non_ideal_exit Decorator

### Purpose

Centralized error handling at Click command boundaries for exec scripts using `.ensure()`. Catches `NonIdealStateError` and converts to JSON error output via `exit_with_error`.

### Usage

```python
@click.command()
@click.option(...)
@click.pass_context
@handle_non_ideal_exit  # Innermost decorator (closest to function)
def my_command(ctx: click.Context) -> None:
    result = operation().ensure()  # Will be caught by decorator
    # ...
```

### Decorator Ordering

Order matters - `@handle_non_ideal_exit` must be innermost (closest to function definition):

1. `@click.command()` - outermost
2. `@click.option(...)` - options
3. `@click.pass_context` - context injection
4. `@handle_non_ideal_exit` - innermost, catches exceptions from function body
5. Function definition

Wrong order causes exceptions to propagate to Click's error handler instead of JSON output.

### Implementation Reference

See `src/erk/cli/script_output.py` for the decorator implementation.
```

---

#### 8. Migration pattern: _ensure_* helpers to .ensure() one-liners

**Location:** `docs/learned/refactoring/ensure-pattern-migration.md`
**Action:** CREATE
**Source:** [Impl] Session 327598da; [PR #8258] Code Deletions

**Draft Content:**

```markdown
# Migration: _ensure_* Helpers to .ensure() One-Liners

## Overview

This document describes migrating from per-type `_ensure_*` helper functions to the inline `.ensure()` pattern, eliminating boilerplate while maintaining type safety.

## Before/After Pattern

### Before: Helper Function Approach

```python
def _ensure_branch(branch: str | BranchDetectionFailed) -> str:
    if isinstance(branch, BranchDetectionFailed):
        exit_with_error(
            error_type=branch.error_type,
            message=branch.message,
        )
    return branch

def _ensure_pr_for_branch(pr: PRDetails | NoPRForBranch) -> PRDetails:
    if isinstance(pr, NoPRForBranch):
        exit_with_error(...)
    return pr

# Usage
branch = _ensure_branch(GitHubChecks.branch(...))
```

### After: Inline .ensure() Pattern

```python
# Direct unwrap (success types with EnsurableResult)
pr_details = GitHubChecks.pr_by_number(...).ensure()

# Check-then-ensure (when custom logging needed)
branch = GitHubChecks.branch(...)
if isinstance(branch, BranchDetectionFailed):
    branch.ensure()  # Raises NonIdealStateError
assert not isinstance(branch, BranchDetectionFailed)  # Type narrowing
```

## Migration Checklist

1. Add `@handle_non_ideal_exit` decorator to Click command
2. Identify all `_ensure_*` helper functions
3. For each helper:
   - If success type has `EnsurableResult`: replace with direct `.ensure()`
   - If success type is built-in: keep LBYL or create wrapper class
4. Remove helper functions
5. Add type narrowing asserts where needed for `ty`
6. Run tests to verify behavior

## Example Migration

See `src/erk/cli/commands/exec/scripts/get_pr_feedback.py` diff in PR #8258 - removed 4 helper functions (~35 lines) replaced with inline patterns.
```

---

#### 9. Test coverage requirements for architectural refactoring

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [Impl] Session fc5d8669; [PR #8258]

**Draft Content:**

```markdown
## Testing Architectural Abstractions

When introducing architectural abstractions (mixins, decorators, wrappers), comprehensive testing is required:

### What Requires Tests

- **Mixins**: Test that classes inheriting the mixin get expected behavior
- **Decorators**: Unit test the decorator in isolation, then integration test through decorated functions
- **Wrappers**: Test wrapper construction, method delegation, and type satisfaction

### Test Organization

- **Abstraction unit tests**: `tests/unit/` close to the abstraction (e.g., `test_non_ideal_state.py` for `NonIdealStateMixin`)
- **Usage integration tests**: Test files for commands/modules that use the abstraction
- **Gateway wrappers**: `packages/erk-shared/tests/unit/github/` for GitHub gateway types

### Example Coverage Pattern

PR #8258 added 30 tests across 5 files for the `.ensure()` pattern:
- `NonIdealStateError` exception: 3 tests
- `NonIdealState.ensure()`: 7 tests (one per concrete class)
- `EnsurableResult.ensure()`: 1 test
- `IssueComments` wrapper: 6 tests
- `PRDetails` with mixin: 3 tests
- `GitHubChecks.issue_comments()`: 6 tests
- `@handle_non_ideal_exit` decorator: 4 tests
```

---

### LOW Priority

#### 10. IssueComments wrapper as architectural example

**Location:** `docs/learned/architecture/discriminated-union-error-handling.md`
**Action:** UPDATE (within collection wrapper section)
**Source:** [Impl] Session b9666d76, fc5d8669; [PR #8258]

**Draft Content:**

Reference `IssueComments` in the collection wrapper section as the canonical example:
- Wraps `tuple[IssueComment, ...]`
- Provides `__iter__()` for transparent iteration
- Return type change: `list[IssueComment] | GitHubAPIFailed` -> `IssueComments | GitHubAPIFailed`
- Both sides now have `.ensure()`

See `packages/erk-shared/src/erk_shared/gateway/github/issues/types.py` for implementation.

---

#### 11. PRDetails inheritance as success type example

**Location:** `docs/learned/architecture/discriminated-union-error-handling.md`
**Action:** UPDATE (within EnsurableResult section)
**Source:** [PR #8258]

**Draft Content:**

Reference `PRDetails` as example of success type adopting `EnsurableResult`:
- Changed from standalone `@dataclass(frozen=True)` to `class PRDetails(EnsurableResult)`
- Enables: `pr = GitHubChecks.pr_by_number(...).ensure()`
- Pattern for gateway result types that don't need collection wrapping

See `packages/erk-shared/src/erk_shared/gateway/github/types.py` for implementation.

---

#### 12. Bot review false positive handling

**Location:** `docs/learned/review/bot-false-positive-patterns.md`
**Action:** CREATE
**Source:** [Impl] Sessions 294a070f, b9666d76, fc5d8669; [PR #8258]

**Draft Content:**

```markdown
# Bot Review False Positive Patterns

Automated review bots (dignified-python-review, test-coverage-review, tripwires-review) can flag false positives requiring human judgment.

## Common False Positive Patterns

### 1. Type Narrowing Assertions Flagged as Dead Code

**Bot claim:** "assert after NoReturn is dead code"

**Reality:** The assert is AFTER the if block, not AFTER the `.ensure()` call. Happy path skips the if block entirely and executes the assert.

**Example from PR #8258:** 6 instances flagged across `get_pr_feedback.py`

### 2. Architectural Necessity Flagged as Unnecessary

**Bot claim:** "NonIdealStateMixin may be unnecessary, consider removing"

**Reality:** The mixin exists specifically to avoid property descriptor conflict when `message: str` is a frozen dataclass field. It's architecturally required.

### 3. Type Ignore Comments Questioned

**Bot claim:** "`type: ignore[arg-type]` could be clarified"

**Reality:** The ignore is necessary because `self` in the mixin isn't typed as the full Protocol. This is intentional design, not a typing mistake.

## Handling Process

1. **Read the flagged code carefully** - understand what the bot is claiming
2. **Verify against architectural constraints** - check conventions docs, understand the pattern
3. **If false positive**: Dismiss with detailed explanation referencing specific line numbers and architectural reasons
4. **Never blindly implement bot suggestions** - bots lack project context
```

---

#### 13. Click decorator ordering for exception handling

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Session 327598da

**Draft Content:**

```markdown
## @handle_non_ideal_exit Decorator Ordering

**Trigger:** Adding `@handle_non_ideal_exit` to a Click command

**Warning:** Decorator ordering matters. `@handle_non_ideal_exit` must be the innermost decorator (closest to the function definition).

**Correct Order:**
1. `@click.command()` - outermost
2. `@click.option(...)` - options
3. `@click.pass_context` - context
4. `@handle_non_ideal_exit` - innermost
5. Function definition

**Wrong Order Result:** Exceptions propagate to Click's error handler instead of being caught and converted to JSON output.
```

---

#### 14. isinstance() with @runtime_checkable Protocol clarification

**Location:** `docs/learned/architecture/discriminated-union-error-handling.md`
**Action:** UPDATE (clarification in existing Protocol section)
**Source:** [Impl] Sessions 327598da, f0087b17

**Draft Content:**

Add clarification to existing Protocol section:
- `@runtime_checkable` checks for attribute presence on instances
- Only checks protocol members (abstract methods/properties), not concrete methods unless explicit inheritance
- This connects to "Protocol concrete methods don't inherit structurally" tripwire

---

## Stale Documentation Cleanup

No stale documentation identified. All referenced artifacts in existing docs verified as existing.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Protocol Concrete Method Assumption

**What happened:** Initial implementation added `ensure()` as a concrete method to the Protocol only, expecting structural implementations to inherit it.

**Root cause:** Misunderstanding of Python Protocol semantics - structural typing doesn't extend to concrete method inheritance.

**Prevention:** Before adding concrete methods to Protocols, verify whether implementations are structural or explicit inheritors. Use mixin for shared implementation.

**Recommendation:** TRIPWIRE (added above)

### 2. Property Descriptor Conflict with Frozen Dataclass

**What happened:** Made `GitHubAPIFailed` explicitly inherit from `NonIdealState` Protocol. Initialization failed with `AttributeError: property 'message' has no setter`.

**Root cause:** Protocol declares `message` as `@property`. Frozen dataclass defines `message: str` as field. Property descriptor blocks `object.__setattr__` in `__init__`.

**Prevention:** Check Protocol property declarations against dataclass field names before adding inheritance. Use mixin pattern for conflicts.

**Recommendation:** TRIPWIRE (added above)

### 3. Type Narrowing Without Assert

**What happened:** After `isinstance()` check with `.ensure()` call, type checker still saw union type.

**Root cause:** Type checker doesn't understand that code after `.ensure()` (NoReturn) in an if block is unreachable from the error branch.

**Prevention:** Add `assert not isinstance(x, ErrorType)` after guard blocks for type narrowing.

**Recommendation:** TRIPWIRE (added above)

### 4. Built-in Type .ensure() Attempt

**What happened:** Tried to use `.ensure()` on `list[IssueComment] | GitHubAPIFailed` but `list` can't have methods added.

**Root cause:** Built-in types don't support mixin inheritance.

**Prevention:** Recognize the pattern early - wrap built-ins in frozen dataclasses inheriting from `EnsurableResult`.

**Recommendation:** TRIPWIRE (added above)

### 5. Bot False Positive Response

**What happened:** 6 bot threads flagged type narrowing assertions as "dead code". Initial instinct was to investigate removing them.

**Root cause:** Bots misunderstand `NoReturn` + isinstance control flow patterns.

**Prevention:** Always read flagged code carefully, verify bot's claim against actual semantics, dismiss with explanation.

**Recommendation:** ADD_TO_DOC (bot-false-positive-patterns.md)

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Protocol property descriptor conflict with frozen dataclass

**Score:** 8/10 (Non-obvious +2, Cross-cutting +2, Destructive +2, Repeated pattern +1, External tool quirk +1)

**Trigger:** Before inheriting from Protocol with @property in frozen dataclass

**Warning:** Check if Protocol declares properties matching your dataclass field names. Protocol @property creates descriptor that blocks frozen dataclass field initialization (AttributeError: property 'message' has no setter). Use mixin pattern (NonIdealStateMixin) to provide shared methods without property descriptors.

**Target doc:** `docs/learned/architecture/tripwires.md`

This tripwire is critical because the error appears at runtime during class instantiation with a cryptic "no setter" message that doesn't obviously point to the Protocol/dataclass interaction. The session required full implementation -> test failure -> debugging -> revert -> redesign cycle.

### 2. Protocol concrete methods don't inherit structurally

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)

**Trigger:** Before defining concrete method in Protocol expecting structural implementations to inherit it

**Warning:** Protocol concrete methods are NOT inherited by structural implementations - only by explicit inheritance. If you need structural typing, add the method to each concrete class. If you need inheritance, make all classes explicitly inherit from the Protocol.

**Target doc:** `docs/learned/architecture/tripwires.md`

This tripwire prevents a common misunderstanding where developers assume Protocol methods work like ABC methods with structural typing benefits.

### 3. Type narrowing assertion after isinstance + ensure()

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)

**Trigger:** After isinstance(x, ErrorType): x.ensure() guard block

**Warning:** Add 'assert not isinstance(x, ErrorType)' after the guard for type narrowing. Without it, ty cannot narrow T | ErrorType to T and reports type errors. This assert is NOT dead code - it executes on the happy path (when x is T). Bots may flag this as dead code (false positive).

**Target doc:** `docs/learned/conventions.md` OR `docs/learned/architecture/tripwires.md`

This pattern appears wherever the check-then-ensure pattern is used rather than direct `.ensure()` on EnsurableResult types.

### 4. Built-in types in NonIdealState unions

**Score:** 4/10 (Non-obvious +1, Cross-cutting +2, Repeated pattern +1)

**Trigger:** When designing API returning list[T] | NonIdealState or str | NonIdealState

**Warning:** Built-in types can't have .ensure() added. Wrap in frozen dataclass inheriting from EnsurableResult (see IssueComments pattern) OR accept LBYL pattern with isinstance checks. One-liner .ensure() requires custom types.

**Target doc:** `docs/learned/architecture/discriminated-union-error-handling.md` (within tripwires section)

This is an API design decision point that affects downstream ergonomics. Wrapping adds type proliferation but enables uniform patterns.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. handle_non_ideal_exit decorator ordering

**Score:** 3/10 (Non-obvious +2, Cross-cutting +1)

**Notes:** Already covered by existing CLI decorator ordering guidance. Should be updated to include this specific decorator. If more decorator ordering issues emerge, may warrant standalone tripwire.

### 2. Bot false positives on architectural patterns

**Score:** 3/10 (Non-obvious +1, Repeated pattern +1, External tool quirk +1)

**Notes:** 6 instances in this PR alone. May not meet "destructive potential" threshold since code still works - it's a review workflow issue. Document as process pattern rather than tripwire unless it causes actual code damage.

### 3. JSON escaping for complex stdin

**Score:** 3/10 (Non-obvious +1, Repeated pattern +1, Silent failure +1)

**Notes:** Appeared in session b9666d76 when passing JSON to `resolve-review-threads`. Should be added to `docs/learned/pr-operations/tripwires.md` - use temp file approach with `json.dump()` rather than shell escaping of quotes.
