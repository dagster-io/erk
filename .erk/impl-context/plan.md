# Documentation Plan: Make erk pr sync resilient to other-worktree gt sync failures

## Context

This PR addresses a critical usability issue where `erk pr sync` would fail completely when `gt sync` encountered problems in OTHER worktrees, even though the current branch synced successfully. The root cause is a quirk in Graphite's behavior: `gt sync` is a repo-wide operation that exits with code 1 when ANY worktree has issues, regardless of whether the current branch synced fine.

The implementation introduces `sync_idempotent()`, a new convenience method in the Graphite ABC that follows the established pattern of `restack_idempotent()` and `squash_branch_idempotent()`. This method wraps the primitive `sync()` operation and classifies errors into two categories: "other-branch-conflict" (recoverable, issue is in a different worktree) and "sync-failed" (fatal, actual sync problem). The `pr sync` command now warns and continues on recoverable errors instead of failing completely.

Documentation matters because this is the SECOND occurrence of the idempotent convenience method pattern (after `restack_idempotent`). Documenting it establishes pattern repeatability and provides a template for future similar patterns. Additionally, the error classification strategy (parsing error messages to distinguish recoverable from fatal errors) is a cross-cutting pattern that deserves explicit documentation to prevent future agents from implementing less elegant solutions.

## Raw Materials

PR #8217

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 8     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 1     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. Update git-graphite-quirks.md: Add SyncError Handling Section

**Location:** `docs/learned/architecture/git-graphite-quirks.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8217]

**Draft Content:**

```markdown
## SyncError Handling Patterns

The `gt sync` command has a repo-wide quirk similar to restack: it exits with code 1 when ANY worktree in the repository has issues, even if the current branch synced successfully.

### The Quirk

When running `gt sync` in a worktree where the branch syncs fine, but another worktree has uncommitted changes, Graphite reports "cannot sync: unstaged changes in /path/to/other/worktree" and exits non-zero.

### Solution: sync_idempotent()

The `sync_idempotent()` convenience method wraps the primitive `sync()` operation and classifies errors:

- **"other-branch-conflict"**: Error message contains both "cannot sync" and "unstaged changes" - indicates another worktree has dirty state
- **"sync-failed"**: All other errors - genuine sync failures requiring intervention

See `packages/erk-shared/src/erk_shared/gateway/graphite/abc.py` for the `sync_idempotent` method implementation (parallel to `restack_idempotent` in the same file).

### CLI Behavior

The `pr sync` command uses this classification:
- **other-branch-conflict**: Warns and continues workflow (current branch synced successfully)
- **sync-failed**: Fails fast with error message

See `src/erk/cli/commands/pr/sync_cmd.py` for the sync_idempotent usage in CLI.
```

---

#### 2. Update abc-convenience-methods.md: Add sync_idempotent Example

**Location:** `docs/learned/architecture/abc-convenience-methods.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8217]

**Draft Content:**

```markdown
## sync_idempotent() Example

A second canonical example of the convenience method pattern, parallel to `squash_branch_idempotent()`.

### Pattern Summary

- **Wraps**: `sync()` primitive method
- **Returns**: `SyncSuccess | SyncError` discriminated union
- **Error classification**: Distinguishes "other-branch-conflict" (recoverable) from "sync-failed" (fatal)

### Key Characteristics

1. **Defined once in ABC**: Inherited by all implementations (Real, Fake, DryRun, Printing)
2. **Exception handling at boundary**: Catches RuntimeError from primitive, converts to typed result
3. **Message-based classification**: Parses error message to determine error type
4. **Runtime import**: Uses runtime import for types to avoid circular dependency at ABC boundary

### Source Reference

See `packages/erk-shared/src/erk_shared/gateway/graphite/abc.py` and search for `sync_idempotent`. Compare structure to `restack_idempotent` and `squash_branch_idempotent` in the same file.

### Why This Pattern Matters

Convenience methods enable LBYL in callers: CLI commands can check error type before acting rather than catching generic exceptions. The discriminated union return type makes error handling explicit and type-safe.
```

---

#### 3. Update discriminated-union-error-handling.md: Reference SyncSuccess/SyncError Types

**Location:** `docs/learned/architecture/discriminated-union-error-handling.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8217]

**Draft Content:**

```markdown
## SyncSuccess | SyncError

Added alongside existing `RestackSuccess | RestackError` and `SquashSuccess | SquashError` patterns.

### Types

See `packages/erk-shared/src/erk_shared/gateway/gt/types.py` for the type definitions:

- `SyncSuccess`: Frozen dataclass with `success: Literal[True]`
- `SyncError`: Frozen dataclass with `success: Literal[False]`, `error_type: SyncErrorType`, `message: str`
- `SyncErrorType`: Literal type with two variants: "other-branch-conflict" | "sync-failed"

### Error Type Semantics

- **"other-branch-conflict"**: Issue is in another worktree; current branch synced successfully. Caller should warn and continue.
- **"sync-failed"**: Actual sync failure requiring intervention. Caller should fail fast.

### Caller Branching Pattern

```python
result = graphite.sync_idempotent(repo_root, force=force, quiet=quiet)
if isinstance(result, SyncError):
    if result.error_type == "other-branch-conflict":
        # Warn and continue - issue is elsewhere
        user_output(click.style("...", fg="yellow") + " Warning message")
    else:
        # Fail fast - actual problem
        raise click.ClickException(result.message)
```
```

---

#### 4. Update pr-sync-workflow.md: Document sync_idempotent Usage

**Location:** `docs/learned/erk/pr-sync-workflow.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8217]

**Draft Content:**

```markdown
## Sync Step: Resilience to Other-Worktree Issues

The sync step now uses `sync_idempotent()` for structured error handling.

### Behavior Change

**Before**: `pr sync` failed completely when `gt sync` encountered issues in ANY worktree, even if the current branch synced successfully.

**After**: `pr sync` distinguishes between:
- **Warning path**: Other worktree has dirty state (other-branch-conflict) - workflow continues with warning
- **Error path**: Actual sync failure (sync-failed) - workflow fails fast

### User Experience

When another worktree has uncommitted changes, users now see:
```
Syncing with remote...
... Sync completed with warnings (other branches had issues)
```

The workflow continues to restack and push. Genuine sync errors still fail immediately with the error message.

### Why This Matters

Multi-worktree development commonly has dirty worktrees. The previous behavior made `pr sync` unusable in these scenarios despite the current branch being fine.

### Source Reference

See `src/erk/cli/commands/pr/sync_cmd.py` for the sync_idempotent usage and error handling logic.
```

---

### MEDIUM Priority

#### 5. Document Runtime Import Pattern for Circular Dependencies

**Location:** `docs/learned/conventions.md`
**Action:** UPDATE
**Source:** [PR #8217]

**Draft Content:**

```markdown
## Runtime Imports for Circular Dependency Avoidance

In rare cases, runtime imports are acceptable to avoid circular dependencies at module boundaries.

### When to Use

1. **Circular dependency at ABC boundary**: ABC needs to reference types defined in a child module
2. **Import only used for return types**: Not used for class inheritance or instantiation
3. **Justified in code comment**: Comment explains why runtime import is necessary

### Example Pattern

```python
def some_idempotent_method(self, ...) -> SomeSuccess | SomeError:
    """Method docstring explaining the operation."""
    # Import at runtime to avoid circular dependency
    from erk_shared.gateway.some.types import SomeError, SomeSuccess

    # Method implementation...
```

### Source Reference

See `packages/erk-shared/src/erk_shared/gateway/graphite/abc.py` for examples in `sync_idempotent`, `restack_idempotent`, and `squash_branch_idempotent` methods.

### Anti-Pattern

Do NOT use runtime imports for:
- Type hints at module level (use `TYPE_CHECKING` guard instead)
- Class inheritance or base types
- Any import that could be resolved by restructuring modules
```

---

#### 6. Document Error Classification Strategy

**Location:** `docs/learned/architecture/error-classification-strategy.md`
**Action:** CREATE
**Source:** [Impl], [PR #8217]

**Draft Content:**

```markdown
---
title: Error Classification Strategy
category: architecture
read-when: implementing error handling for external tool wrappers, distinguishing recoverable from fatal errors, parsing error messages to classify failures
---

# Error Classification Strategy

Pattern for categorizing external tool errors by message parsing when the tool lacks structured error codes.

## When to Use

When wrapping external CLI tools (like Graphite's `gt` commands) that:
1. Exit non-zero for multiple distinct failure modes
2. Don't provide structured error codes
3. Produce error messages with identifiable patterns

## Pattern

Parse the error message to classify into categories:

```python
error_msg = str(e).lower()

if "pattern_a" in error_msg and "pattern_b" in error_msg:
    return SpecificError(error_type="specific-category", ...)
return GenericError(error_type="operation-failed", ...)
```

## Examples in Codebase

- **sync_idempotent**: "cannot sync" + "unstaged changes" = "other-branch-conflict"
- **restack_idempotent**: "conflict" or "unmerged files" = restack conflict

See `packages/erk-shared/src/erk_shared/gateway/graphite/abc.py` for both implementations.

## Key Principles

1. **Conservative classification**: Unknown errors default to generic/fatal category
2. **Case-insensitive matching**: Use `.lower()` for reliable pattern matching
3. **Multiple indicators**: Combine patterns for accuracy (avoid false positives)
4. **Encapsulate in gateway layer**: Classification logic lives in gateway, not CLI

## False Negative Safety

If classification fails (treats recoverable as fatal), the worst case is the operation fails when it could have continued. This is safe - better to fail fast than silently ignore real errors.
```

---

### LOW Priority

#### 7. Cross-Reference from Multi-Worktree Docs

**Location:** `docs/learned/architecture/multi-worktree-state.md`
**Action:** UPDATE
**Source:** [PR #8217]

**Draft Content:**

```markdown
## Sync Resilience in Multi-Worktree Environments

When using multiple worktrees, `gt sync` failures in OTHER worktrees are handled gracefully by erk commands.

### How It Works

The `sync_idempotent()` method classifies sync errors:
- Dirty state in other worktrees: Warn and continue (current branch synced fine)
- Actual sync failures: Fail fast

### Related Documentation

- [git-graphite-quirks.md](git-graphite-quirks.md) - SyncError handling section
- [abc-convenience-methods.md](abc-convenience-methods.md) - sync_idempotent pattern
```

---

## Contradiction Resolutions

**No contradictions found.** All existing documentation aligns with the new patterns. The implementation follows established patterns:

- Error handling uses discriminated unions (aligned with existing docs)
- Idempotent wrapper follows `restack_idempotent()` pattern (aligned with existing docs)
- LBYL checks in CLI layer (aligned with existing docs)
- Multi-worktree handling uses graceful degradation (aligned with existing docs)

---

## Stale Documentation Cleanup

**No stale documentation found.** All referenced files verified to exist. No phantom references detected in existing documentation.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Generic RuntimeError Obscures Root Cause

**What happened:** Using primitive `sync()` method directly produces generic RuntimeError, losing the ability to distinguish recoverable from fatal errors.

**Root cause:** Primitive gateway methods raise exceptions without structured error information. Callers catch generic exceptions and can't branch on error type.

**Prevention:** Use convenience methods like `sync_idempotent()` that return discriminated unions with error_type fields. CLI layer should call idempotent versions, not primitives.

**Recommendation:** TRIPWIRE - Add tripwire for using `sync()` directly instead of `sync_idempotent()`.

### 2. erk pr sync Fails When OTHER Worktree Has Dirty State

**What happened:** The command failed completely even though the current branch synced successfully.

**Root cause:** `gt sync` is repo-wide and exits non-zero when ANY worktree has issues. Previous implementation treated all sync errors as fatal.

**Prevention:** Classify errors by parsing message. "other-branch-conflict" errors indicate the issue is elsewhere and the current branch is fine.

**Recommendation:** ADD_TO_DOC - Already covered in git-graphite-quirks.md update above.

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Using sync() Instead of sync_idempotent()

**Score:** 7/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2, External tool quirk +1)

**Trigger:** Before calling `graphite.sync()` directly in CLI commands

**Warning:** Use `sync_idempotent()` for structured error handling. The CLI layer should branch on error types (warn on other-branch-conflict, fail on sync-failed) rather than catching generic RuntimeError.

**Target doc:** `docs/learned/architecture/tripwires.md`

This tripwire is warranted because the failure mode is subtle: using `sync()` directly produces working code that handles errors, but loses the ability to distinguish recoverable from fatal errors. The anti-pattern isn't obviously wrong at code review time - it's only discovered when users report that `pr sync` fails in common multi-worktree scenarios.

The tripwire should be added to the architecture tripwires file with a grep pattern like `graphite\.sync\(` to catch direct usage of the primitive method in CLI code.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Not Catching Both RuntimeError and CalledProcessError

**Score:** 3/10 (criteria: Non-obvious +2, Cross-cutting +1)

**Notes:** The current implementation only catches RuntimeError, which works because FakeGraphite also raises RuntimeError. However, if future fake implementations raise CalledProcessError (as subprocess calls might), the convenience method would miss those. This is documented in abc-convenience-methods.md but may not reach tripwire threshold because the current approach works.

### 2. Testing Error Classification Without Integration Tests

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)

**Notes:** Unit tests verify classification logic, but integration tests are essential to verify CLI user experience (correct warning messages, appropriate exit codes). This PR includes both, but future similar work might skip integration tests. May warrant tripwire if pattern repeats without integration coverage.

---

## Key Insights

### Pattern Repeatability Established

This is the second occurrence of the idempotent convenience method pattern in the Graphite ABC:
1. `restack_idempotent()` - first occurrence
2. `sync_idempotent()` - second occurrence (this PR)

Documenting both as canonical examples reinforces that this is a repeatable architectural approach, not a one-off solution.

### Review Bot Validation

All automated review bots (dignified-python-review, test-coverage-review, tripwires-review) reported zero violations. This indicates:
- Clean implementation following established patterns
- Proper test coverage at both unit and integration levels
- Correct discriminated union usage with LBYL checks

The fact that review bots had to explain WHY certain patterns were correct (e.g., "template method pattern correctly implemented", "runtime import justified") suggests those patterns need better upfront documentation - which this learn plan addresses.

### Migration Template

The diff analysis includes a detailed migration template (see diff-analysis.md lines 441-513) for future similar patterns. This template should be referenced when documenting the pattern in abc-convenience-methods.md and could form the basis for a dedicated "Adding Idempotent Gateway Methods" guide.
