# Documentation Plan: Add branch-scoped implementation directories under .erk/impl-context/<branch>/

## Context

This implementation fundamentally changed how erk manages plan-based implementation context. Previously, implementation directories lived at a flat `.impl/` path in each worktree, which meant that only one branch could have an active implementation at a time. The migration to branch-scoped directories under `.erk/impl-context/<branch>/` enables multiple branches to maintain independent implementation state in the same worktree.

This architectural change touched 26 test files and 15+ call sites across CLI commands, exec scripts, and status collectors. The agent discovered several non-obvious patterns during implementation: FakeGit requires explicit `current_branches` configuration for branch-aware tests, branch names undergo 31-character truncation that affects path assertions, and the branch name resolution chain differs significantly between commands (`erk implement` uses current branch, `erk wt create` uses sanitized worktree name, `erk branch checkout` uses plan branch).

Documentation matters because future agents working with impl folders, writing tests for plan-based workflows, or implementing branch-aware commands will need to understand: (1) the new directory structure and API, (2) the subtle FakeGit configuration requirements, and (3) the branch name sanitization rules that affect directory naming.

## Raw Materials

See PR #8215

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 14 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score>=4) | 3 |
| Potential tripwires (score 2-3) | 2 |

## Stale Documentation Cleanup

Existing docs with phantom references requiring action:

### 1. Impl-context file path references

**Location:** `docs/learned/planning/impl-context.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `src/erk/cli/commands/submit.py` (MISSING)
**Cleanup Instructions:** Update file path references to reflect current code structure. The submit command code has moved to `packages/erk-shared/src/erk_shared/gateway/pr/submit.py`. Scan the document for any other outdated path references and update them to current locations.

## Documentation Items

### HIGH Priority

#### 1. Branch-Scoped Impl-Context Architecture

**Location:** `docs/learned/planning/branch-scoped-impl-context.md`
**Action:** CREATE
**Source:** [Impl], [PR #8215]

**Draft Content:**

```markdown
---
description: Documents the branch-scoped implementation directory structure under .erk/impl-context/<branch>/
read-when:
  - working with implementation directories
  - creating or modifying impl folders
  - understanding plan file locations
  - implementing branch-aware commands
tripwires: 3
---

# Branch-Scoped Impl-Context Directories

Implementation context is stored in branch-scoped directories under `.erk/impl-context/<branch>/`.

## Directory Structure

The implementation context for each branch lives at:
```
worktree/
  .erk/
    impl-context/
      <sanitized-branch-name>/
        plan.md          # The implementation plan
        ref.json         # GitHub issue reference metadata
```

## Branch Name Sanitization

Branch names containing `/` are sanitized for directory names:
- `main` -> `main`
- `feature/user-auth` -> `feature--user-auth`
- `hotfix/urgent/fix` -> `hotfix--urgent--fix`

See `packages/erk-shared/src/erk_shared/impl_folder.py` for the `_sanitize_branch_for_dirname()` function.

## Core API

Two key functions handle impl directory paths:
- `get_impl_dir(worktree_path, branch_name)`: Returns the branch-scoped directory path (pure path computation)
- `get_impl_path(worktree_path, *, branch_name, git_ops)`: Returns the full path to `plan.md`

See `packages/erk-shared/src/erk_shared/impl_folder.py:39-110` for implementation.

## Benefits

1. **Multi-branch workflows**: Work on multiple plans simultaneously by switching branches
2. **Isolation**: Each branch's impl context is independent
3. **No conflicts**: No risk of cross-branch contamination during branch switches

## Backward Compatibility

The `impl-init` exec script searches both:
1. `.erk/impl-context/<branch>/` (new location)
2. `.impl/` (legacy fallback)

See `src/erk/cli/commands/exec/scripts/impl_init.py:56-74` for the search logic.

## Related Documentation

- [impl-folder-api.md](impl-folder-api.md) - API reference for impl folder functions
- [branch-name-resolution.md](branch-name-resolution.md) - How different commands resolve branch names
```

---

#### 2. Impl Folder API Breaking Changes

**Location:** `docs/learned/planning/impl-folder-api.md`
**Action:** CREATE
**Source:** [Impl], [PR #8215]

**Draft Content:**

```markdown
---
description: API reference for impl_folder.py module with breaking change documentation
read-when:
  - calling create_impl_folder() or get_impl_path()
  - migrating code that uses impl folders
  - implementing plan-based workflows
tripwires: 1
---

# Impl Folder API Reference

The `impl_folder.py` module provides the core API for working with implementation directories.

## Breaking Changes

All impl folder functions now require an explicit `branch_name` parameter:

- `create_impl_folder(worktree_path, plan_content, *, branch_name, overwrite)` - branch_name is now required
- `get_impl_path(worktree_path, *, branch_name, git_ops=None)` - branch_name is now required

### Migration Guide

Before (old API):
```python
# No longer works
create_impl_folder(worktree_path, plan_content)
get_impl_path(worktree_path)
```

After (new API):
```python
# Pass branch_name explicitly
branch = ctx.git.branch.get_current_branch(ctx.cwd)
create_impl_folder(worktree_path, plan_content, branch_name=branch or "default")
get_impl_path(worktree_path, branch_name=branch)
```

## Function Reference

See `packages/erk-shared/src/erk_shared/impl_folder.py` for the complete implementation.

### get_impl_dir(worktree_path, branch_name)

Pure path computation. Returns the branch-scoped directory path without checking existence.

### get_impl_path(worktree_path, *, branch_name, git_ops=None)

Returns the full path to `plan.md`. When `git_ops` is provided, uses it to resolve the current branch if `branch_name` is None.

### create_impl_folder(worktree_path, plan_content, *, branch_name, overwrite)

Creates the impl folder structure and writes the plan file. Returns the path to the created `plan.md`.

## File Naming

- New implementations write `ref.json` (not `plan-ref.json`)
- Read operations check `ref.json`, then `plan-ref.json`, then legacy `issue.json` for backward compatibility
```

---

#### 3. Add FakeGit current_branches tripwire to testing tripwires

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add this tripwire to the existing testing tripwires document:

```markdown
## FakeGit current_branches Configuration

**Trigger:** Before testing impl folders or branch-aware code

**Warning:** Always configure `current_branches` in FakeGit. Missing this causes `get_current_branch()` to return `None`, triggering fallback to `"current"` string literal.

**Example:**
```python
# WRONG: Missing current_branches - get_current_branch() returns None
git = FakeGit(
    git_common_dirs={env.cwd: env.git_dir},
    default_branches={env.cwd: "main"},
    local_branches={env.cwd: ["main", "feature-branch"]},
)

# RIGHT: Include current_branches mapping
git = FakeGit(
    git_common_dirs={env.cwd: env.git_dir},
    default_branches={env.cwd: "main"},
    local_branches={env.cwd: ["main", "feature-branch"]},
    current_branches={worktree_path: "feature-branch"},  # Required!
)
```

See `tests/fakes/` for FakeGit implementation.
```

---

#### 4. Add branch sanitization tripwire to planning tripwires

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8215]

**Draft Content:**

Add this tripwire to the existing planning tripwires document:

```markdown
## Branch Name Sanitization for Impl Directories

**Trigger:** Before constructing impl directory paths manually

**Warning:** Always use `get_impl_dir()` or `_sanitize_branch_for_dirname()`. Never duplicate the `/` -> `--` transformation logic manually.

**Why:** Branch names containing `/` must be sanitized for filesystem compatibility. The transformation `feature/foo` -> `feature--foo` is centralized in `_sanitize_branch_for_dirname()`. Duplicating this logic leads to path mismatches.

See `packages/erk-shared/src/erk_shared/impl_folder.py:34-36` for the sanitization function.
```

---

### MEDIUM Priority

#### 5. Branch Name Resolution Chain

**Location:** `docs/learned/planning/branch-name-resolution.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
description: Documents how different commands resolve branch names for impl directories
read-when:
  - debugging impl folder path issues
  - understanding why tests see unexpected branch names
  - implementing new branch-aware commands
tripwires: 0
---

# Branch Name Resolution Chain

Different commands resolve branch names for impl directories differently. Understanding this chain is critical for debugging path issues and writing correct tests.

## Resolution by Command

### erk implement

Uses the current branch from git:
```python
branch = ctx.git.branch.get_current_branch(ctx.cwd)
branch_name = branch or "current"  # Fallback if detached HEAD
```

See `src/erk/cli/commands/implement.py:140-148`.

### erk wt create --from-plan-file

Uses a sanitized version of the worktree name:
```python
wt_branch = branch or default_branch_for_worktree(name)
# default_branch_for_worktree() -> sanitize_branch_component(name)
```

See `src/erk/cli/commands/wt/create_cmd.py:883-888`.

### erk branch checkout --for-plan

Uses the branch name from the plan being checked out:
```python
create_impl_folder(worktree_path, setup.plan_content, branch_name=branch_name, ...)
```

See `src/erk/cli/commands/branch/checkout_cmd.py:280-320`.

## Testing Implications

Tests must configure FakeGit's `current_branches` mapping to match the command's resolution strategy. Without this, `get_current_branch()` returns `None`, causing unexpected fallback behavior.
```

---

#### 6. Branch Name Truncation in Tests

**Location:** `docs/learned/testing/impl-folder-testing.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
description: Testing patterns for branch-scoped impl directories including truncation handling
read-when:
  - writing tests for impl folder operations
  - debugging path assertion failures in tests
  - comparing worktree names to impl directory paths
tripwires: 1
---

# Testing Impl Folder Operations

## Branch Name Truncation Trap

The `sanitize_branch_component()` function truncates branch names to 31 characters. This creates a subtle trap when test assertions compare worktree names to impl directory paths.

**Example:**
- Worktree name: `"devclikit-extraction-26-02-26-0409"` (34 chars)
- Branch name: `"devclikit-extraction-26-02-26-04"` (31 chars, truncated)
- Impl directory uses the truncated branch name

**Solution:** Always use the source code sanitization function in tests:

```python
from erk_shared.naming import default_branch_for_worktree

expected_branch = default_branch_for_worktree(worktree_name)
expected_impl_path = env.cwd / ".erk" / "impl-context" / expected_branch / "plan.md"
```

See `erk_shared/naming.py` for the sanitization functions.

## Test Setup Pattern

When testing impl folder operations:

1. Configure `current_branches` in FakeGit
2. Use `get_impl_path()` for path assertions (not hardcoded paths)
3. Account for branch name truncation when deriving paths from worktree names
4. Verify both the impl directory and `ref.json` (not `plan-ref.json`)

## Related Documentation

- [FakeGit current_branches tripwire](tripwires.md#fakegit-current_branches-configuration)
```

---

#### 7. Backward Compatibility for impl-init

**Location:** `docs/learned/planning/backward-compatibility.md`
**Action:** CREATE
**Source:** [Impl], [PR #8215]

**Draft Content:**

```markdown
---
description: Documents backward compatibility handling for impl directories during migration
read-when:
  - debugging impl folder not found errors
  - understanding why old .impl/ folders still work
  - implementing migration-aware code
tripwires: 0
---

# Impl Directory Backward Compatibility

The `impl-init` exec script searches both old and new impl directory locations for backward compatibility.

## Search Order

1. `.erk/impl-context/<current-branch>/` (new location)
2. `.impl/` (legacy fallback)

## impl_type Field

The `impl-init` output includes an `impl_type` field:
- `"impl-context"`: Found at new branch-scoped location
- `"impl"`: Found at legacy `.impl/` location

See `src/erk/cli/commands/exec/scripts/impl_init.py:56-74` for the search logic.

## Migration Path

No manual migration required:
- New impl folders use branch-scoped locations automatically
- Old `.impl/` folders continue to work
- Gradual migration as users create new impl folders

## Reference File Compatibility

The `read_plan_ref()` function reads from multiple file names:
1. `ref.json` (preferred)
2. `plan-ref.json` (legacy)
3. `issue.json` (very old legacy)

New code writes only `ref.json`. See `packages/erk-shared/src/erk_shared/impl_folder.py:241-276`.
```

---

#### 8. plan-ref.json to ref.json migration note

**Location:** `docs/learned/planning/impl-context.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8215]

**Draft Content:**

Add a section to the existing impl-context.md:

```markdown
## Reference File Naming

The GitHub issue reference file has been renamed:
- **New name:** `ref.json`
- **Legacy names:** `plan-ref.json`, `issue.json` (still readable for backward compatibility)

New impl folders write `ref.json`. The `read_plan_ref()` function checks all three names in order.
```

---

#### 9. Test Migration Pattern for Path Changes

**Location:** `docs/learned/testing/impl-folder-testing.md`
**Action:** UPDATE (merge with item 6)
**Source:** [Impl]

**Draft Content:**

Add to the impl-folder-testing.md document:

```markdown
## Test Migration Pattern

When updating tests after impl directory path structure changes:

1. **Update message assertions**: Success messages changed from `"Created .impl/ folder"` to `"✓ Created impl folder"`
2. **Update path assertions**: Change `.impl/` to `.erk/impl-context/<branch>/`
3. **Update reference file assertions**: Change `plan-ref.json` to `ref.json`
4. **Use helper functions**: Import `get_impl_path()` instead of hardcoding paths

### Grep Patterns for Migration

Find affected tests:
```bash
grep -r '\.impl/' tests/
grep -r 'plan-ref\.json' tests/
grep -r 'Created .impl' tests/
```
```

---

### LOW Priority

#### 10. CLI Command Internal Path Updates

**Location:** `docs/learned/cli/` (various)
**Action:** UPDATE_EXISTING
**Source:** [PR #8215]

**Draft Content:**

Update existing CLI documentation to note that impl folders now use branch-scoped paths. This is a low-priority update since user-visible behavior is unchanged. Key commands affected:
- `erk branch checkout --for-plan`
- `erk branch create`
- `erk implement`
- `erk wt create --from-plan`
- `erk wt list`

---

#### 11. CI Run Timeline Verification Pattern

**Location:** `docs/learned/ci/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add to the CI tripwires:

```markdown
## CI Run Timeline Verification

**Trigger:** Before debugging CI test failures

**Pattern:** Always check the CI run timestamp against your commit history before investigating failures. A CI run may be from before your fixes were pushed.

**Commands:**
```bash
gh run list --branch <branch> --json databaseId,createdAt,status --jq '.[] | select(.status != "completed")'
```

This avoids wasting time debugging failures that are already fixed in a newer commit.
```

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Hardcoded .impl/ Paths in Tests

**What happened:** 21 tests failed after the path structure migration because they used hardcoded `.impl/` paths instead of helper functions.

**Root cause:** Tests directly constructed paths like `worktree / ".impl" / "plan.md"` instead of using `get_impl_path()`.

**Prevention:** Always use the `get_impl_path()` helper function in test assertions. Never hardcode impl directory paths.

**Recommendation:** TRIPWIRE (covered by branch sanitization tripwire)

### 2. FakeGit Missing current_branches Configuration

**What happened:** Branch-aware code used fallback string `"current"` instead of the expected branch name, causing path mismatches.

**Root cause:** `FakeGit` was configured with `local_branches` and `default_branches` but not `current_branches`. When `get_current_branch()` looked up the current branch, it returned `None`.

**Prevention:** Always configure `current_branches` in FakeGit when testing impl folders or any code that calls `get_current_branch()`.

**Recommendation:** TRIPWIRE (documented in item 3 above)

### 3. Branch Name Truncation Not Accounted For

**What happened:** Test compared a 34-character worktree name to the impl directory path, but the directory used the 31-character truncated branch name.

**Root cause:** `sanitize_branch_component()` truncates to 31 characters, but the test used the full worktree name.

**Prevention:** Use `default_branch_for_worktree()` to compute the expected branch name in tests. Never assume worktree name == branch name.

**Recommendation:** ADD_TO_DOC (covered in impl-folder-testing.md)

### 4. Debugging Stale CI Failures

**What happened:** Agent investigated test failures from a CI run that was triggered before fixes were pushed.

**Root cause:** Did not check the CI run timestamp against the commit history.

**Prevention:** Always verify CI run timestamp matches your latest push before debugging failures.

**Recommendation:** ADD_TO_DOC (covered in CI tripwires)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Branch Name Sanitization for Directory Paths

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1, Silent failure +1)
**Trigger:** Before constructing impl directory paths manually
**Warning:** Always use `get_impl_dir()` or `_sanitize_branch_for_dirname()`. Never duplicate the `/` -> `--` transformation logic.
**Target doc:** `docs/learned/planning/tripwires.md`

Branch names containing `/` must be sanitized for filesystem compatibility. The transformation is centralized but easy to accidentally reimplement incorrectly. This causes silent path mismatches that are difficult to debug.

### 2. FakeGit current_branches Configuration

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1, Silent failure +1)
**Trigger:** Before testing impl folders or branch-aware code
**Warning:** Always configure `current_branches` in FakeGit. Missing this causes `get_current_branch()` to return `None`, triggering fallback to `"current"` string literal.
**Target doc:** `docs/learned/testing/tripwires.md`

Tests frequently break because FakeGit seems fully configured (with `local_branches`, `default_branches`, etc.) but is missing `current_branches`. The symptom is mysterious path mismatches where the impl directory is created at `impl-context/current/` instead of the expected branch name.

### 3. Branch Name Parameter Required

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** Before calling `create_impl_folder()` or `get_impl_path()`
**Warning:** Always pass `branch_name` parameter. This is a breaking change from the previous API.
**Target doc:** `docs/learned/planning/tripwires.md`

The API signature changed to require `branch_name`. Code that worked before will now fail with a TypeError. The fix is straightforward (pass the branch name) but the error message may not immediately suggest this is a recent breaking change.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. CI Run Timeline Verification

**Score:** 3/10 (Non-obvious +1, Repeated pattern +1, External tool quirk +1)
**Notes:** Useful pattern but not destructive. More of a debugging efficiency tip than a critical tripwire. Could be promoted if this pattern causes repeated time waste.

### 2. Branch Name Truncation in Tests

**Score:** 3/10 (Non-obvious +1, Silent failure +2)
**Notes:** Important when comparing worktree names to impl paths, but limited scope. Only affects tests where worktree names exceed 31 characters. Could be promoted to tripwire if this causes repeated test failures.
