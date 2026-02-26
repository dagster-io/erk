# Documentation Plan: Complete dead code elimination after erk pr sync deletion

## Context

This plan captures documentation learnings from PR #8254, which completed the dead code elimination following the deletion of `erk pr sync` command. The PR removed 5 abstract methods from the Graphite ABC (`sync`, `restack`, `continue_restack`, `sync_idempotent`, `restack_idempotent`) along with their 30 implementations across 6 variant files, 6 discriminated union types, 22+ test functions, and 11 documentation updates totaling ~2,728 lines deleted.

The implementation sessions demonstrated excellent refactoring discipline, with systematic execution across multiple files and comprehensive verification. However, one critical gap emerged: an integration test calling the deleted `sync()` method wasn't caught until CI, revealing that integration tests require explicit grepping during gateway method deletions. This plan captures that insight along with other documentation gaps discovered during analysis.

Existing documentation coverage is strong at ~90%. The primary gaps are: (1) the 6th variant pattern unique to Graphite gateways (disabled.py), (2) explicit type cleanup scope during discriminated union removal, (3) integration test cleanup as distinct from unit test cleanup, and (4) documentation example code maintenance.

## Raw Materials

PR #8254: https://github.com/dagster-io/erk/pull/8254

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 8     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 4     |
| Potential tripwires (score 2-3)| 3     |

## Documentation Items

### HIGH Priority

#### 1. 6-Variant Pattern for Graphite Gateways

**Location:** `docs/learned/architecture/gateway-removal-pattern.md`
**Action:** UPDATE
**Source:** [PR #8254]

**Draft Content:**

```markdown
## Graphite-Specific: The 6th Variant

While most gateway ABCs follow the standard 5-place pattern (abc.py, real.py, fake.py, dry_run.py, printing.py), the Graphite ABC has a **6th variant**: `disabled.py`.

**GraphiteDisabled** is a sentinel implementation that raises errors for all operations when Graphite is disabled at the project level. When removing methods from the Graphite ABC, you must update 6 places, not 5:

1. `abc.py` - Remove abstract method and any concrete idempotent wrapper
2. `real.py` - Remove real implementation
3. `fake.py` - Remove method, constructor params (`*_raises`), call tracking (`_*_calls`)
4. `dry_run.py` - Remove no-op wrapper
5. `printing.py` - Remove printing wrapper
6. `disabled.py` - Remove error-raising sentinel stub

See `packages/erk-shared/src/erk_shared/gateway/graphite/disabled.py` for the disabled variant pattern.
```

---

#### 2. Dead Type Cleanup Scope for Discriminated Unions

**Location:** `docs/learned/architecture/gateway-removal-pattern.md`
**Action:** UPDATE
**Source:** [PR #8254]

**Draft Content:**

```markdown
## Delete Associated Types

When removing gateway methods that return discriminated union results, delete ALL associated types from `types.py`:

- **Success types**: e.g., `SyncSuccess`, `RestackSuccess`
- **Error types**: e.g., `SyncError`, `RestackError`
- **Error type enums**: e.g., `SyncErrorType`, `RestackErrorType`
- **Operation-specific error types**: e.g., `ContinueRestackError`

The multiplicative pattern: 5 methods with discriminated unions can mean 6+ types to delete (Success, Error, and ErrorType for each, plus any helper types).

**Verification command:**
```bash
grep -r "DeletedTypeName" packages/erk-shared/src/
```

Should return 0 results after cleanup is complete.
```

---

#### 3. Integration Test Co-Evolution Tripwire

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl - Session f4141645]

This item addresses a HIGH severity error that occurred during CI: an integration test called `ctx.graphite.sync()` after the method was deleted, causing `AttributeError` in CI.

**Draft Content:**

```markdown
## Integration Tests and Gateway Method Deletions

**Trigger:** Before deleting gateway methods

**Warning:** Grep `tests/integration/` for method name references. Integration tests call gateway methods via context (`ctx.graphite.sync()`) and won't appear in unit test greps. These must be updated or removed alongside production code deletion.

**Background:** Integration tests access gateways through the context object pattern (`ctx.<gateway>.<method>()`). When unit tests are deleted alongside production code, integration tests can be missed because they live in a separate directory and access methods indirectly.
```

---

### MEDIUM Priority

#### 4. Documentation Example Rot Pattern

**Location:** `docs/learned/documentation/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8254]

**Draft Content:**

```markdown
## Architecture Documentation Contains Example Code

**Trigger:** When removing gateway methods or commands

**Warning:** Scan `docs/learned/architecture/` for code examples that reference removed methods. Documentation can contain inline code examples demonstrating patterns - these become stale silently, unlike broken cross-reference links which are more obvious.

**What to check:**
- Code blocks showing method calls
- Pattern examples using the removed functionality
- Architecture diagrams referencing deleted components

This goes beyond standard link repair - it's example code maintenance.
```

---

#### 5. Large Edit Pattern for Bulk Deletions

**Location:** `docs/learned/refactoring/tripwires.md`
**Action:** UPDATE
**Source:** [Impl - Session ef0fcd06-part2]

**Draft Content:**

```markdown
## Efficient Multi-Function Deletion

**Trigger:** When removing multiple contiguous functions from a single file

**Pattern:** Use one large Edit call with a multi-function `old_string` (1500+ chars) rather than multiple small Edit calls. This reduces tool call overhead and maintains atomic file state.

**Example scenario:** Deleting 5 test functions from a test file. Instead of 5 separate Edit calls, use one Edit with the full block of contiguous functions as `old_string`.

**Benefits:**
- Fewer tool calls = faster execution
- Atomic file modification = no intermediate broken states
- Easier to verify the deletion scope
```

---

#### 6. LBYL Import Verification Before Deletion

**Location:** `docs/learned/refactoring/tripwires.md`
**Action:** UPDATE
**Source:** [Impl - Session ef0fcd06-part2]

**Draft Content:**

```markdown
## Verify Import Usage Before Removal

**Trigger:** Before removing imports after function/method deletion

**Pattern:** Grep for remaining usage of the import symbol in the same file before removing the import statement.

**Example:** After deleting tests that used `pytest.raises`, verify the `pytest` import is still needed elsewhere in the file before removing the import.

```bash
grep -n "pytest" tests/unit/path/to/file.py
```

This prevents import errors from prematurely removed imports that have other consumers in the same file.
```

---

### LOW Priority

#### 7. CI Autofix Race Condition Pattern

**Location:** `docs/learned/ci/tripwires.md`
**Action:** UPDATE
**Source:** [Impl - Session f4141645]

**Draft Content:**

```markdown
## Handling CI Autofix Race Conditions

**Trigger:** When CI format failures occur with autofix enabled

**Pattern:** Check if remote has an autofix commit before applying local format fixes.

**Recovery workflow:**
1. Detect remote autofix: `git fetch && git log origin/<branch> --oneline -1`
2. If autofix commit exists: `git stash && git pull --rebase origin <branch> && git stash pop`
3. Resolve any conflicts from stash pop
4. Continue with local changes

**Background:** CI workflows with autofix can push format fixes to the remote branch while you're working on local fixes. This creates divergence that requires reconciliation.
```

---

#### 8. Deleted Graphite Method Anti-Hallucination Tripwire

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8254]

**Draft Content:**

```markdown
## Deleted Graphite ABC Methods (PR #8254)

**NEVER suggest calling these deleted Graphite ABC methods:**
- `sync()`
- `restack()`
- `continue_restack()`
- `sync_idempotent()`
- `restack_idempotent()`

These methods were removed in PR #8254 after `erk pr sync` was deleted. They have no production callers.

**Instead use:** `erk pr sync-divergence` or `/erk:sync-divergence` for syncing PRs with divergent remote state.

**Methods that REMAIN (have production callers):**
- `squash_branch_idempotent()`
- `submit_stack()`
```

---

## Contradiction Resolutions

No contradictions detected. All existing documentation is consistent with the dead code elimination work.

---

## Stale Documentation Cleanup

No stale documentation requiring deletion was identified.

The existing-docs-checker flagged `docs/learned/cli/commands/pr-sync-divergence.md` for investigation, but this documents `erk pr sync-divergence` which is a **different, active command** - not the deleted `erk pr sync`. This doc should remain unchanged.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Integration Test Calling Deleted Gateway Method

**What happened:** After deleting `sync()` from the Graphite ABC and all unit tests, CI failed with `AttributeError: 'DryRunGraphite' object has no attribute 'sync'`. An integration test still called `ctx.graphite.sync()`.

**Root cause:** The initial deletion only grepped unit test directories. Integration tests were in a separate directory (`tests/integration/`) and accessed gateway methods through the context object, making them easy to miss.

**Prevention:** Before deleting any gateway method, explicitly grep `tests/integration/` for the method name, not just unit tests.

**Recommendation:** TRIPWIRE (High priority - item #3 above)

### 2. Git Pull Failure with Local Changes

**What happened:** Attempted `git pull --rebase` while having uncommitted local test fixes, causing the pull to fail.

**Root cause:** CI had pushed an autofix commit while local fixes were in progress, creating divergence.

**Prevention:** Check `git status` before pulling. If local changes exist, use `git stash && git pull --rebase && git stash pop`.

**Recommendation:** ADD_TO_DOC (Low priority - item #7 above)

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Integration Test Co-Evolution for Gateway Deletions

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before deleting gateway methods
**Warning:** Grep `tests/integration/` for method name references. Integration tests call gateway methods via context (ctx.graphite.sync()) and won't show up in unit test greps.
**Target doc:** `docs/learned/testing/tripwires.md`

This is the highest priority tripwire. The error that occurred (AttributeError in CI) was a direct result of missing this step. Integration tests are structurally different from unit tests - they access gateways through context objects and live in a separate directory. Without explicit guidance, agents will miss them.

### 2. Grep Test Helpers Before Deletion

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** Before deleting test helper methods from fake builders
**Warning:** Grep entire `tests/` directory for method name - test helpers often have surprising consumers in unrelated test files.
**Target doc:** `docs/learned/testing/tripwires.md`

Test helper methods like `with_continue_restack_failure()` in fake_ops.py can be consumed by tests in completely unrelated test files. Deleting them without grepping causes test compilation errors.

### 3. 6-Variant Graphite Pattern

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** When removing methods from Graphite ABC
**Warning:** Update 6 places (not 5): abc.py, real.py, fake.py, dry_run.py, printing.py, disabled.py. Graphite has a special disabled variant that other gateways don't have.
**Target doc:** `docs/learned/architecture/gateway-removal-pattern.md`

The existing gateway-removal-pattern.md documents the 5-place pattern, but agents applying it to Graphite will miss disabled.py. This is a Graphite-specific deviation from the standard pattern.

### 4. Documentation Example Code Rot

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** When removing gateway methods or commands
**Warning:** Scan `docs/learned/architecture/` for code examples using removed methods. Documentation example code rots silently - unlike broken links.
**Target doc:** `docs/learned/documentation/tripwires.md`

PR #8254 had to update architecture docs that contained code examples using removed methods. This is distinct from link repair and often missed.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Large Edit Pattern for Bulk Deletions

**Score:** 2/10 (Repeated pattern +1, External tool quirk +1)
**Notes:** This is an efficiency optimization, not error prevention. Agents can successfully delete code with multiple small edits - it's just slower. May warrant promotion if edit atomicity issues emerge.

### 2. LBYL Import Verification

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** Prevents import errors but these are caught quickly by ty/ruff checks. Low blast radius - promotes to tripwire if import errors become frequent.

### 3. CI Autofix Race Condition

**Score:** 2/10 (External tool quirk +1, Repeated pattern +1)
**Notes:** Fully recoverable with git stash workflow. Low severity because it doesn't cause data loss or incorrect behavior - just requires manual reconciliation. Keeps as documentation only.

---

## Attribution

| Item | Identified By |
|------|---------------|
| 6-variant pattern | Session analyzer (part 1), code diff analyzer |
| Dead type cleanup scope | Code diff analyzer, existing docs checker |
| Integration test co-evolution | Session analyzer (f4141645) |
| Documentation example rot | Session analyzer (part 2), code diff analyzer |
| Large edit pattern | Session analyzer (part 2) |
| LBYL import verification | Session analyzer (part 2) |
| CI autofix race condition | Session analyzer (f4141645) |
| Deleted method anti-hallucination | Code diff analyzer |
