# Documentation Plan: Update tests to exercise branch-scoped .erk/impl-context/ primary code paths

## Context

This plan captures the learnings from PR #8325, which completed Phase 2 of objective #8197: migrating erk's test suite from legacy flat `.impl/` directories to the primary branch-scoped `.erk/impl-context/<branch>/` code paths. The implementation updated approximately 290 test references across 18 files, demonstrating significant patterns around test migration, FakeGit configuration, and the critical relationship between test fixtures and production code paths.

The implementation revealed several non-obvious challenges: tests using `resolve_impl_dir()` require git branch context via FakeGit configuration; test fixtures must exactly mirror production path resolution logic; and some production code remains unmigrated from Phase 1, creating a constraint where certain tests must continue using legacy paths. These findings have cross-cutting implications for any future agent working with impl directories, worktree-scoped paths, or test fixture design.

Most significantly, the session uncovered a fundamental architectural insight: the `.erk/impl-context/` directory serves two distinct purposes (staging area for committed files vs parent for branch-scoped impl folders), which creates confusion and contributed to the cleanup-after-setup bug discovered in the session. Documentation of this dual-purpose architecture and the associated tripwires will prevent future agents from encountering the same subtle failures.

## Raw Materials

PR #8325

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 10    |
| Contradictions to resolve      | 2     |
| Tripwire candidates (score>=4) | 4     |
| Potential tripwires (score 2-3)| 3     |

## Documentation Items

### HIGH Priority

#### 1. Branch-scoped impl directory architecture

**Location:** `docs/learned/architecture/branch-scoped-impl-directory.md`
**Action:** CREATE
**Source:** [Impl], [PR #8325]

**Draft Content:**

```markdown
---
read-when:
  - working with impl directories or impl_folder.py
  - testing code that uses resolve_impl_dir or get_impl_dir
  - implementing impl directory resolution logic
---

# Branch-Scoped Impl Directory Architecture

## Overview

Erk uses a branch-scoped directory structure for implementation workspaces. The
impl directory has evolved from flat `.impl/` at repo root to hierarchical
`.erk/impl-context/<branch>/` paths.

## Key Functions

See `packages/erk-shared/src/erk_shared/impl_folder.py` for implementation.

### Path Computation

- `get_impl_dir(base_path, *, branch_name)` - Pure path computation, returns
  `.erk/impl-context/<sanitized_branch>/`
- Branch names with slashes are sanitized (e.g., `plnd/O8197-...` becomes
  `plnd--O8197-...`)

### Resolution Strategy

`resolve_impl_dir(cwd, branch_name=None)` implements a 4-step discovery:

1. **Branch-scoped lookup**: Check `.erk/impl-context/<sanitized_branch>/`
2. **Legacy fallback**: Check flat `.impl/` at cwd
3. **Discovery scan**: Scan `.erk/impl-context/*/` for subdirs containing
   marker files (`plan.md` or `ref.json`)
4. **Return None**: No impl directory found

## The Dual Purpose of .erk/impl-context/

This directory serves TWO distinct purposes:

1. **Staging directory** (flat files): `.erk/impl-context/plan.md` and
   `.erk/impl-context/ref.json` are committed to plan branches for immediate
   PR visibility, then cleaned up before implementation

2. **Impl directory parent** (branch-scoped subdirs):
   `.erk/impl-context/<branch>/plan.md` is gitignored and used during local
   implementation

This dual purpose creates confusion: cleanup logic may inadvertently delete
branch-scoped subdirectories when removing flat staging files.

## Testing Requirements

Tests using `resolve_impl_dir()` require git branch context. See
testing/branch-scoped-test-migration.md for the complete checklist.

## Incomplete Migration Status

See architecture/incomplete-migrations.md for production functions still using
hardcoded `.impl/` paths.
```

---

#### 2. FakeGit current_branches configuration requirement [TRIPWIRE]

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8325]

**Draft Content:**

```markdown
## FakeGit Branch Configuration for Impl Tests

When tests use `resolve_impl_dir()` (directly or via production code that calls
it), you MUST configure FakeGit with branch context:

```python
git=FakeGit(current_branches={tmp_path: BRANCH})
```

Without this configuration, `git.branch.get_current_branch(cwd)` returns
`None`, causing `resolve_impl_dir` to skip branch-scoped lookup (step 1) and
fall back to legacy `.impl/` or discovery scan. Tests will fail silently with
"impl dir not found" even when the directory exists at the branch-scoped path.

**Action pattern**: Before testing commands that call `resolve_impl_dir()` or
`git.branch.get_current_branch()`

**Warning**: Configure `FakeGit(current_branches={cwd: branch_name})` or test
will fail to find branch-scoped impl directories
```

---

#### 3. Production code migration gaps check [TRIPWIRE]

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8325]

**Draft Content:**

```markdown
## Check Production Code Before Migrating Tests

BEFORE migrating tests to use `get_impl_dir()` or branch-scoped paths:

1. Check if the production code being tested uses `resolve_impl_dir()` or
   hardcodes `.impl/`
2. Only migrate the test if production uses `resolve_impl_dir()`
3. If production hardcodes `.impl/`, the test MUST use `.impl/` regardless of
   migration plan intent

**Action pattern**: Before migrating tests from `.impl/` to branch-scoped paths

**Warning**: Check production code paths first. Tests must match production
expectations or they will fail when production cannot locate fixtures.

**Verification command**:
```bash
grep -r 'cwd / ".impl"' src/
grep -r 'state.cwd / ".impl"' src/
```
```

---

#### 4. Test fixture path alignment principle [TRIPWIRE]

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8325]

**Draft Content:**

```markdown
## Test Fixtures Must Mirror Production Path Resolution

When production code changes path resolution strategy, ALL test fixtures
creating those paths must be updated to match:

- If production uses `resolve_impl_dir()`: Test can use `get_impl_dir()`
- If production hardcodes `cwd / ".impl"`: Test must use `tmp_path / ".impl"`

This is a two-phase migration pattern: production code first, tests second.
Migrating tests before production code creates path mismatches where tests
create directories that production cannot find.

**Action pattern**: When production code changes path resolution strategy

**Warning**: All test fixtures creating those paths must be updated to match
production's expected resolution logic
```

---

#### 5. Resolve contradiction: impl-context-api.md outdated

**Location:** `docs/learned/architecture/impl-context-api.md`
**Action:** UPDATE
**Source:** [Existing docs check]

**Draft Content:**

```markdown
<!-- Add to existing document, likely in a "Scope" or "Related Documentation"
section -->

## Scope of This Document

This document describes the **staging directory API** (`create_impl_context`,
`remove_impl_context`) for flat files committed to plan branches.

For the **branch-scoped impl directory API** (`get_impl_dir`, `resolve_impl_dir`)
used during local implementation, see
[branch-scoped-impl-directory.md](branch-scoped-impl-directory.md).

These are distinct concepts:
- Staging: `.erk/impl-context/plan.md` (committed, flat)
- Impl: `.erk/impl-context/<branch>/plan.md` (gitignored, nested)
```

---

#### 6. Remove phantom references: impl-context.md

**Location:** `docs/learned/planning/impl-context.md`
**Action:** UPDATE_REFERENCES
**Source:** [Existing docs check]

**Phantom References:** `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py` (lines 42, 48, 68, 72)

**Cleanup Instructions:** Remove all references to the phantom file `setup_impl_from_issue.py`. This file does not exist in the current codebase. Update any implementation details to reference the actual current implementation if needed.

---

#### 7. Incomplete Phase 1 migration tracking

**Location:** `docs/learned/architecture/incomplete-migrations.md`
**Action:** CREATE
**Source:** [Impl], [PR #8325]

**Draft Content:**

```markdown
---
read-when:
  - migrating tests from legacy .impl/ paths
  - debugging path resolution failures in tests
  - planning impl directory migrations
---

# Incomplete Impl Directory Migrations

## Status

Phase 1 of objective #8197 migrated most production code from flat `.impl/`
to branch-scoped `.erk/impl-context/<branch>/`. However, several functions
remain unmigrated and still use hardcoded `.impl/` paths.

## Unmigrated Functions

The following production functions still hardcode `cwd / ".impl"`:

1. **setup_impl.py** - Path 3a auto-detection (see impl_folder.py)
2. **submit_pipeline.py** - `link_pr_to_objective_nodes` function

Tests for these functions MUST use legacy `.impl/` paths until production code
migrates.

## Verification

Before migrating a test to branch-scoped paths, verify production code uses
`resolve_impl_dir()`:

```bash
grep -n 'cwd / ".impl"' path/to/production/file.py
grep -n 'resolve_impl_dir' path/to/production/file.py
```

## Migration Pattern

When migrating unmigrated functions:
1. Update production code to use `resolve_impl_dir()`
2. Then update corresponding tests to use `get_impl_dir()`
3. Add FakeGit configuration to tests (see testing/tripwires.md)
```

---

### MEDIUM Priority

#### 8. Test migration from .impl/ to branch-scoped paths

**Location:** `docs/learned/testing/branch-scoped-test-migration.md`
**Action:** CREATE
**Source:** [Impl], [PR #8325]

**Draft Content:**

```markdown
---
read-when:
  - updating tests to use branch-scoped impl directories
  - migrating from flat .impl/ to .erk/impl-context/<branch>/
  - writing new tests that create impl directories
---

# Test Migration for Branch-Scoped Impl Directories

## Migration Checklist

When updating tests from legacy `.impl/` to branch-scoped paths:

### 1. Add Required Imports

```python
from erk_shared.impl_folder import get_impl_dir
from erk_shared.gateway.git.fake import FakeGit
```

### 2. Define Branch Constant

```python
BRANCH = "test/branch"
```

### 3. Update Path Construction

```python
# Before:
impl_dir = tmp_path / ".impl"

# After:
impl_dir = get_impl_dir(tmp_path, branch_name=BRANCH)
```

### 4. Handle Directory Depth

```python
# Before (flat):
impl_dir.mkdir()

# After (nested):
impl_dir.mkdir(parents=True)
```

### 5. Configure FakeGit

```python
ctx = ErkContext.for_test(
    cwd=tmp_path,
    git=FakeGit(current_branches={tmp_path: BRANCH})
)
```

### 6. Update Filename Conventions

```python
# Before:
(impl_dir / "plan-ref.json").write_text(...)

# After:
(impl_dir / "ref.json").write_text(...)
```

### 7. Identify Legacy Tests to Preserve

Before migrating, grep for tests that intentionally validate fallback behavior:
```bash
grep -r "legacy\|fallback\|compat" tests/ --include="*.py"
```

Tests like `test_resolve_impl_dir_legacy_fallback` should NOT be migrated.

## Critical Pre-Check

BEFORE migrating any test, verify production code uses `resolve_impl_dir()`.
See architecture/incomplete-migrations.md for unmigrated functions.
```

---

#### 9. State branch mismatch prevention

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8325]

**Draft Content:**

```markdown
<!-- Add to existing test fixture guidance section -->

## Branch Name Consistency in Test Fixtures

When tests create impl directories at branch-scoped paths and then call
production code that uses `resolve_impl_dir(state.cwd, branch_name=state.branch_name)`:

- The test's impl directory branch MUST match the state's branch_name
- Don't rely on default branch names in state factories

```python
# WRONG: Creates impl at BRANCH but state defaults to "feature"
impl_dir = get_impl_dir(tmp_path, branch_name=BRANCH)
impl_dir.mkdir(parents=True)
state = _make_state(cwd=tmp_path)  # Uses default branch_name="feature"

# CORRECT: Branch names match
impl_dir = get_impl_dir(tmp_path, branch_name=BRANCH)
impl_dir.mkdir(parents=True)
state = _make_state(cwd=tmp_path, branch_name=BRANCH)
```

## Legacy Test Preservation

When migrating to new code paths, intentionally preserve tests that validate
fallback behavior. Before refactoring, grep for:
- Test names containing "legacy", "fallback", or "compat"
- Tests with comments explaining backward compatibility validation

These tests ensure the fallback logic continues to work.
```

---

#### 10. Parallel Task agent pattern for large refactorings

**Location:** `docs/learned/workflows/parallel-refactoring-pattern.md`
**Action:** CREATE
**Source:** [Impl], [PR #8325]

**Draft Content:**

```markdown
---
read-when:
  - planning large mechanical refactorings across many files
  - coordinating parallel Task agents for code changes
  - breaking down repetitive transformations
---

# Parallel Task Agent Pattern for Large Refactorings

## Overview

When faced with mechanical refactoring across many files (30+), use parallel
Task agents to complete work efficiently. This pattern was demonstrated in
PR #8325, completing 18 file updates in under 5 minutes.

## Process

### 1. Pre-Analysis

Examine representative files to understand transformation patterns before
delegating. Identify:
- Common code patterns to change
- Exceptions to preserve (legacy tests, special cases)
- Import changes needed

### 2. Task Decomposition

Break work into logical nodes, typically by directory:
- `tests/core/` - N files
- `tests/unit/` - N files
- `tests/commands/` - N files

### 3. Define Clear Instructions

Each Task agent needs:
- Explicit file list (scope)
- Transformation rules with examples
- Preservation instructions (what NOT to change)
- Verification steps

### 4. Parallel Execution

Launch all Task agents simultaneously. The pattern reduces wall-clock time
from O(files * time_per_file) to O(max_file_time).

### 5. Verification

Run CI after all agents complete. Address failures systematically:
1. Run failing tests with full output to understand exact failure
2. Identify distinct root causes (don't assume single systemic issue)
3. Apply targeted fixes based on root cause
```

---

## Contradiction Resolutions

### 1. Single vs Branch-Scoped Impl-Context Architecture

**Existing doc:** `docs/learned/architecture/impl-context-api.md`
**Conflict:** The existing doc describes a single `.erk/impl-context/` folder at repo root with flat staging files. The current implementation uses branch-scoped `.erk/impl-context/<branch>/` directories managed by `get_impl_dir()` and `resolve_impl_dir()`.
**Resolution:** Update the existing doc to clarify it describes the staging directory API only. Add a scope section and link to the new `branch-scoped-impl-directory.md` doc. The two APIs serve different purposes and both remain valid.

### 2. Phantom File References in Impl-Context Lifecycle

**Existing doc:** `docs/learned/planning/impl-context.md`
**Conflict:** The document extensively references `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py` which does not exist in the current codebase.
**Resolution:** Remove all references to the phantom file. If implementation details are needed, update to reference actual current implementation paths.

## Stale Documentation Cleanup

### 1. Phantom references in impl-context.md

**Location:** `docs/learned/planning/impl-context.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py` (appears at lines 42, 48, 68, 72)
**Cleanup Instructions:** Remove all references to this non-existent file. The document should reference actual implementation files if needed for context.

## Prevention Insights

### 1. Cleanup Deletes Newly-Created Impl Folder

**What happened:** The `setup-impl` command reported success, but the impl folder was missing. Investigation revealed the cleanup step runs after creating the impl folder and deletes the entire `.erk/impl-context/` tree, including the newly-created branch-scoped subdirectory.
**Root cause:** The `cleanup_impl_context` function uses `shutil.rmtree(".erk/impl-context/")` to remove staging files, but this also wipes out branch-scoped impl folders that live in subdirectories of the same parent.
**Prevention:** This is a production code bug that should be fixed by either (a) running cleanup before folder creation, or (b) making cleanup selective to only delete flat staging files without touching subdirectories.
**Recommendation:** CODE_FIX (not documentation - the underlying bug should be fixed)

### 2. resolve_impl_dir() Returns None in Tests

**What happened:** Tests failed with "impl dir not found" even though the directory existed at the branch-scoped path.
**Root cause:** FakeGit was instantiated without `current_branches` mapping, so `git.branch.get_current_branch()` returned `None`, causing `resolve_impl_dir` to skip branch-scoped lookup (step 1) and fall back to legacy `.impl/` which didn't exist.
**Prevention:** Always configure `FakeGit(current_branches={cwd: expected_branch})` when testing code that calls `resolve_impl_dir()`.
**Recommendation:** TRIPWIRE (added to testing/tripwires.md)

### 3. Test Uses Branch-Scoped Path but Production Uses Legacy

**What happened:** Tests were migrated to use `get_impl_dir()` but production code (`link_pr_to_objective_nodes`, `setup_impl` path 3a) still hardcoded `state.cwd / ".impl"`, causing path mismatches.
**Root cause:** Incomplete Phase 1 migration - some production functions weren't updated to use `resolve_impl_dir()`.
**Prevention:** Before migrating tests, grep production code for hardcoded path usage. Document unmigrated functions and keep test changes aligned with production code state.
**Recommendation:** TRIPWIRE (added to planning/tripwires.md)

### 4. Parent Directory Side Effects Break Existence Checks

**What happened:** Tests that check for `.erk/impl-context/` directory absence failed because creating nested `.erk/impl-context/<branch>/` directories via `mkdir(parents=True)` creates the parent directory as a side effect.
**Root cause:** Filesystem operations have non-local effects - creating nested paths creates all intermediate directories.
**Prevention:** When testing "directory should not exist" scenarios, use legacy `.impl/` path to avoid nested path creation, or use `list(path.iterdir())` instead of `path.exists()` to distinguish empty parents from directories with content.
**Recommendation:** ADD_TO_DOC (included in branch-scoped-test-migration.md)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. FakeGit current_branches configuration

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before testing commands that use `resolve_impl_dir()` or `git.branch.get_current_branch()`
**Warning:** Configure `FakeGit(current_branches={cwd: branch_name})` or test will fail to find branch-scoped impl directories
**Target doc:** `docs/learned/testing/tripwires.md`

This tripwire is critical because the failure mode is silent - `resolve_impl_dir` gracefully falls back to legacy paths or returns `None` instead of raising an error. Tests appear to "just not work" without clear indication of the root cause. The session demonstrated this pattern across 4 test failures in `test_mark_impl_started_ended.py`.

### 2. Production code migration gaps check

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before migrating tests to use `get_impl_dir()` or branch-scoped paths
**Warning:** Check if production code uses `resolve_impl_dir()` or hardcodes `.impl/` - only migrate test if production uses `resolve_impl_dir()`
**Target doc:** `docs/learned/planning/tripwires.md`

This tripwire prevents the most common failure pattern from Phase 2: tests were updated to use new paths while production code still used old paths, causing path mismatches. The session demonstrated this in `test_link_pr_to_objective_nodes.py` and `test_check.py`.

### 3. Test fixture path alignment

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** When production code changes path resolution strategy
**Warning:** All test fixtures creating those paths must be updated to match production's expected resolution logic
**Target doc:** `docs/learned/testing/tripwires.md`

This is the general principle underlying the migration gaps check. It applies beyond impl directories to any path resolution change. The session reinforced this through multiple iterations of discovery and correction.

### 4. State branch mismatch in fixtures

**Score:** 4/10 (Non-obvious +2, Repeated pattern +2)
**Trigger:** When creating test fixtures with branch-scoped paths
**Warning:** Explicitly pass `branch_name=` to state factory matching test impl setup. Avoid relying on default branch names.
**Target doc:** `docs/learned/testing/tripwires.md`

This caused the `test_adds_learn_plan_label` failure where impl was created at `BRANCH="test/branch"` but state defaulted to `branch_name="feature"`.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Parent directory creation side effects

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** Caused issues in 3 test files across multiple sessions. May warrant promotion if the pattern continues to cause problems. Currently addressed in migration documentation rather than as a standalone tripwire.

### 2. Discovery mechanism requires marker files

**Score:** 2/10 (Non-obvious +2)
**Notes:** The `resolve_impl_dir` step 3 (discovery scan) only finds subdirs containing `plan.md` or `ref.json`. Empty branch-scoped directories won't be discovered. This is important but can be part of the main architecture doc rather than a tripwire.

### 3. git add -f failure on missing directory

**Score:** 2/10 (Non-obvious +2)
**Notes:** Only happens when cleanup runs twice (edge case). The underlying cleanup sequencing bug should be fixed in production code rather than documented as a tripwire.
