# Documentation Plan: Add force parameter to stage_files gateway for gitignored paths

## Context

This plan documents learnings from PR #8312, which added a `force` parameter to the `stage_files` gateway method to enable staging of gitignored paths. The implementation addressed a critical bug where `erk pr dispatch` failed when trying to stage `.erk/impl-context/` (a gitignored directory) for remote plan dispatch.

The work exemplifies the 5-place gateway implementation pattern: updating the ABC, real, fake, dry_run, and printing implementations in lockstep. It also reveals an important gap between plan scope and implementation reality - the plan specified tests and fake tracking that were not delivered. This documentation captures both the successful patterns and the gaps for future agent guidance.

Future agents working on gateway modifications, gitignore-aware operations, or dispatch workflows will benefit from understanding when force-staging is appropriate, how to modify gateway signatures consistently, and the importance of verifying test coverage matches plan commitments.

## Raw Materials

PR #8312

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 10 |
| Contradictions to resolve | 1 |
| Tripwire candidates (score>=4) | 2 |
| Potential tripwires (score 2-3) | 2 |

## Documentation Items

### HIGH Priority

#### 1. Fake Implementation Parameter Tracking Pattern

**Location:** `docs/learned/testing/gateway-fake-testing-exemplar.md`
**Action:** UPDATE
**Source:** [PR #8312]

**Draft Content:**

```markdown
## Parameter Tracking in Fakes

### When to Track Parameters

Not every parameter passed to a fake needs a corresponding tracking property. Add tracking properties only when tests need to assert on that specific behavior.

**Pattern: Accept but don't track**

When a parameter affects real implementation behavior but tests don't need to verify it:
- Accept the parameter in the signature (for type consistency)
- Do not create a tracking property
- Document this explicitly in the method docstring

**Example: stage_files(force) in FakeGitCommitOps**

The `force` parameter is accepted but not tracked because:
- Current tests don't need to assert whether files were force-staged
- The fake records staged paths regardless of force flag
- If future tests need force-staging assertions, add `force_staged_files` property

See `packages/erk-shared/src/erk_shared/gateway/git/commit_ops/fake.py` for implementation.

### When tracking IS required

Add tracking properties when:
- Tests verify the parameter was passed correctly
- The parameter changes observable fake behavior
- Integration tests depend on distinguishing parameter values
```

---

#### 2. Git Force-Staging Pattern for Gitignored Files

**Location:** `docs/learned/architecture/git-force-staging-pattern.md`
**Action:** CREATE
**Source:** [Impl], [PR #8312]

**Draft Content:**

```markdown
---
read-when:
  - staging gitignored files via gateway
  - implementing git operations on .gitignored paths
  - adding force parameter to git gateway methods
  - working with .erk/impl-context directory
---

# Git Force-Staging Pattern

## When to Use

Force-staging (`git add -f`) is needed when ALL of these conditions apply:
- Path is in `.gitignore`
- File needs to be committed (even temporarily)
- Standard `git add` would reject the path

## Canonical Example: .erk/impl-context/

The `.erk/impl-context/` directory is gitignored but needs temporary staging for:
1. **Remote dispatch** (`dispatch_cmd.py`): Commits impl-context before pushing plan branch
2. **Cleanup** (`cleanup_impl_context.py`): Commits deletion of impl-context before implementation

Without force-staging, these operations fail with "paths are ignored by .gitignore".

## Gateway Pattern

Add `*, force: bool` as keyword-only parameter (no default per erk conventions):

See `packages/erk-shared/src/erk_shared/gateway/git/commit_ops/abc.py` for the ABC signature.
See `packages/erk-shared/src/erk_shared/gateway/git/commit_ops/real.py` for implementation that conditionally adds `-f` flag.

## When NOT to Use

Force-staging should be rare. Do NOT use when:
- Files should be in version control (remove from .gitignore instead)
- Staging tracked file deletions (git tracks deletions without -f)
- Working with normal project files

## Callers

- `src/erk/cli/commands/pr/dispatch_cmd.py` - staging before push
- `src/erk/cli/commands/exec/scripts/cleanup_impl_context.py` - staging deletion
```

---

#### 3. Test Coverage Requirements for Gateway Modifications

**Location:** `docs/learned/testing/gateway-testing-requirements.md`
**Action:** CREATE
**Source:** [PR #8312]

**Draft Content:**

```markdown
---
read-when:
  - modifying gateway ABC method signatures
  - adding parameters to existing gateway methods
  - creating new gateway methods
  - reviewing gateway-related PRs
---

# Gateway Testing Requirements

## Decision Tree

When modifying a gateway, determine required test coverage:

### New Gateway Method
- Layer 1 (fake tests): Test fake behavior and tracking
- Layer 4 (unit tests): Test business logic using fake
- Integration: Test actual external tool behavior

### Parameter Addition to Existing Method
- Layer 1: Only if fake needs new tracking property
- Integration: If the parameter changes external tool behavior

### Signature-Only Change (no behavior change)
- Verify existing tests pass
- No new tests required

## Test Layer Definitions

**Layer 1 (Fake Tests):** Tests for the fake implementation itself
- Location: `tests/unit/fakes/`
- Purpose: Verify fake tracking and state management

**Layer 4 (Unit Tests):** Business logic tests using fakes
- Location: `tests/unit/` (non-fakes)
- Purpose: Test code that calls gateway methods

**Integration Tests:** Tests against real external tools
- Location: `tests/integration/`
- Purpose: Verify actual git/gh/etc behavior

## Example: stage_files(force) Parameter Addition

PR #8312 added `force` parameter but did NOT add tests because:
- Fake accepts but doesn't track `force` (no Layer 1 test needed)
- Callers pass explicit `force=True` (self-documenting usage)
- Integration test would verify `git add -f` on gitignored path

Note: The plan specified tests that weren't delivered. This is an acceptable scope reduction when the parameter is straightforward, but should be documented in PR.
```

---

#### 4. Resolve Fake Implementation Code Comment

**Location:** `packages/erk-shared/src/erk_shared/gateway/git/commit_ops/fake.py`
**Action:** CODE_CHANGE
**Source:** [PR #8312]

**Draft Content:**

Add docstring clarification to the `stage_files` method explaining why `force` is accepted but not tracked:

```python
def stage_files(self, cwd: Path, paths: list[str], *, force: bool) -> None:
    """Record staged files for commit.

    Note: The force parameter is accepted for signature compatibility but not
    tracked. Current tests don't require distinguishing force-staged files.
    If future tests need this, add a force_staged_files property.
    """
    self._staged_files.extend(paths)
```

This clarifies intent and prevents future confusion about whether the fake is "incomplete".

---

### MEDIUM Priority

#### 5. Gateway ABC Parameter Addition Pattern

**Location:** `docs/learned/architecture/gateway-abc-implementation.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Adding Parameters to Existing Methods

When adding a parameter to an existing gateway method:

1. **Update all 5 implementations** - ABC, real, fake, dry_run, printing
2. **Use keyword-only syntax** - `*, param: Type` (no defaults per erk conventions)
3. **Find all callers** - `Grep(pattern='method_name', glob='*.py')`
4. **Update all callers** - Each must explicitly pass the new parameter
5. **Run type checker** - `ty check` verifies all implementations match

### Example: stage_files(force)

Added `force: bool` parameter to enable force-staging gitignored files.

See `packages/erk-shared/src/erk_shared/gateway/git/commit_ops/` for all 5 implementations.

### Verification

After signature changes:
1. `ty check` - Type errors reveal missing implementations
2. `Grep` for method name - Find all call sites
3. Run affected tests - Verify behavior unchanged for existing callers
```

---

#### 6. Dispatch Troubleshooting Guide

**Location:** `docs/learned/pr-operations/dispatch-troubleshooting.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - erk pr dispatch fails with staging error
  - "paths are ignored by .gitignore" error
  - recovering from interrupted dispatch
---

# Dispatch Troubleshooting

## Error: Failed to stage files (gitignore)

**Symptom:** `RuntimeError: Failed to stage files: .erk/impl-context`
**Cause:** Attempting to stage gitignored path without force flag

**Resolution:**
1. Check if gateway supports `force` parameter
2. If not supported, update gateway (see PR #8312 as example)
3. For manual recovery: `git add -f .erk/impl-context && git commit`

**Important:** Manual recovery fixes state but not code. Create plan to fix root cause.

## Common Failure Modes

| Error | Cause | Fix |
|-------|-------|-----|
| "paths are ignored" | Staging gitignored file | Add force parameter to gateway |
| "index.lock exists" | Concurrent git operation | Wait or remove stale lock |
| "remote branch exists" | Branch already pushed | Use `--force` or new branch name |
```

---

#### 7. PR Review Response Workflow

**Location:** `docs/learned/pr-operations/responding-to-reviews.md`
**Action:** CREATE
**Source:** [PR #8312]

**Draft Content:**

```markdown
---
read-when:
  - responding to PR review comments
  - addressing automated review feedback
  - using /erk:pr-address command
---

# Responding to PR Reviews

## Commands

**`/erk:pr-address`** - Address review comments on current branch
- Reads pending review threads
- Generates inline resolution documentation
- Updates PR with response timestamps

## Automated Review Types

PRs receive automated reviews for:
- **dignified-python**: Python style and convention checks
- **test-coverage**: Missing test coverage detection
- **tripwires**: Known error pattern detection

## Response Patterns

**Code change needed:** Make the fix, push, reply with "Fixed in [commit]"

**Clarification:** Reply explaining design decision, optionally update docs

**Won't fix:** Reply explaining why, may need discussion
```

---

#### 8. Test Requirements by Change Type

**Location:** `docs/learned/testing/test-requirements-by-change-type.md`
**Action:** CREATE
**Source:** [PR #8312]

**Draft Content:**

```markdown
---
read-when:
  - determining test requirements for a change
  - reviewing PR test coverage
  - writing tests for new features
---

# Test Requirements by Change Type

## Decision Matrix

| Change Type | Layer 1 (Fake) | Layer 4 (Unit) | Integration |
|-------------|----------------|----------------|-------------|
| New source file | If has fake | Yes | If external calls |
| Modified gateway method | If fake behavior changes | If business logic changes | If external behavior changes |
| Modified CLI command | No | Verify existing | No |
| Modified ABC definition | No | No | No |
| Pure refactoring | No | Verify existing | No |

## Interpretation

**"Verify existing"** means run existing tests, don't add new ones.

**"If [condition]"** means test only if that condition applies.

## Example: stage_files(force) Parameter Addition

- Layer 1: No (fake accepts but doesn't track)
- Layer 4: No (callers use explicit value)
- Integration: Recommended (verifies git add -f works)

The plan specified tests that weren't delivered. This is acceptable when:
- Parameter is straightforward
- Existing tests cover surrounding behavior
- Risk is low

Document scope reduction in PR.
```

---

### LOW Priority

#### 9. Gateway Signature Migration Verification

**Location:** `docs/learned/architecture/gateway-signature-migration.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Verification Steps

After completing all signature updates:

1. **Type check** - Run `ty check` to verify all implementations match ABC
2. **Grep verification** - Search for method name to find any missed callers
3. **Test run** - Execute affected test suites

The type checker is critical - it catches implementation drift that grep might miss.
```

---

#### 10. Missing Test Coverage Tripwire

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8312]

**Draft Content:**

```markdown
## Gateway Modification Test Coverage

**Trigger:** When modifying gateway ABC method signatures

**Warning:** Breaking gateway interface changes should include tests for behavior changes. Verify test coverage matches plan commitments before merging.

**Context:** PR #8312 planned tests for `force` parameter but delivered without them. While acceptable for low-risk parameter additions, this pattern should be explicitly documented in PR rather than silently omitted.
```

---

## Contradiction Resolutions

### 1. Fake Implementation Tracking Discrepancy

**Existing doc:** PR #8312 body states "Track force_staged_files"
**Conflict:** Actual implementation in `fake.py` accepts `force` but ignores it, does NOT expose `force_staged_files` property
**Resolution:**
- Update `docs/learned/testing/gateway-fake-testing-exemplar.md` to document that fakes may accept parameters without tracking
- Add code comment in `fake.py` explaining why `force` is ignored (item #4 above)
- This is acceptable pattern, not incomplete implementation

## Stale Documentation Cleanup

None detected. All referenced paths in existing documentation were verified and exist.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Git Gateway Missing Force Flag

**What happened:** `erk pr dispatch` failed with "paths are ignored by .gitignore" when staging `.erk/impl-context/`
**Root cause:** Gateway abstraction for `stage_files` didn't expose the `-f` flag needed for gitignored paths
**Prevention:** When designing git operations that interact with intentionally-gitignored paths, include `force` parameter from the start
**Recommendation:** ADD_TO_DOC (covered by item #2)

### 2. Unresolved Merge Conflict Markers

**What happened:** `SyntaxError: invalid decimal literal` at plan_body_screen.py:194 prevented erk from loading
**Root cause:** Git merge conflict markers (`>>>>>>> 80726c8e8`) left in source file after merge
**Prevention:** Check for unresolved conflict markers before running erk commands; add pre-commit hooks to detect
**Recommendation:** TRIPWIRE (high score - prevents silent failures)

### 3. Manual Recovery Without Root Cause Fix

**What happened:** User ran `git add -f .erk/impl-context && git commit` to recover, but dispatch still failed on retry
**Root cause:** Manual workaround fixed immediate state but didn't fix the underlying code issue
**Prevention:** When manually recovering from a failed command, still create a plan to fix root cause in code
**Recommendation:** TRIPWIRE (common pattern worth warning about)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Git Merge Conflict Markers Preventing CLI Load

**Score:** 6/10 (criteria: Non-obvious +2, Destructive potential +2, Silent failure +2)
**Trigger:** Before running erk commands after git merge/rebase
**Warning:** Check for unresolved conflict markers (<<<<<<, >>>>>>) in source files - these cause SyntaxError and prevent erk from loading
**Target doc:** `docs/learned/universal-tripwires.md`

This is tripwire-worthy because the error message ("invalid decimal literal") doesn't indicate merge conflicts, making diagnosis non-obvious. The failure is silent until you try to run erk commands, potentially after significant work.

### 2. Manual Recovery Without Root Cause Fix

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** After manually recovering from a failed command
**Warning:** Manual workarounds (like `git add -f`) fix immediate state but don't fix root cause - still create plan to update code
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because the pattern repeats across different failure modes. Manual recovery feels like success but masks underlying code issues that will recur.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Missing Test Coverage for Gateway Changes

**Score:** 3/10 (criteria: Non-obvious +2, Destructive potential +1)
**Notes:** Test coverage bot flagged this in PR review, but it's not "silent failure" since CI catches it. May warrant promotion if untested gateway changes cause production issues.

### 2. Git Operations with Gitignored Paths

**Score:** 3/10 (criteria: Non-obvious +2, External tool quirk +1)
**Notes:** Specific to git add behavior, not broadly cross-cutting. If more gitignore-related failures appear, consider promotion.
