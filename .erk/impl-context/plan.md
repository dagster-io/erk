# Document resolve_impl_dir and branch-scoped impl directory patterns

## Context

This implementation introduced a unified approach for resolving implementation directories across exec scripts. The core change is a new `resolve_impl_dir()` function that consolidates three discovery strategies (branch-scoped `.erk/impl-context/<branch>/`, legacy `.impl/`, and discovery-based scan) into a single reusable utility. Eight exec scripts that previously hardcoded `.impl/` paths were systematically migrated to use this function with proper Click context injection for testability.

The documentation from this work matters because it establishes critical patterns that future exec script authors must follow. The migration revealed several non-obvious requirements: all exec scripts must use `@click.pass_context` and `require_cwd(ctx)` instead of `Path.cwd()`, tests must use `ErkContext.for_test()` with configured `FakeGit` instances, and the `ty` type checker has limitations with NoReturn type narrowing that require specific workarounds. Without documenting these patterns, future developers will encounter the same errors (8 test failures from context injection, type narrowing failures, CI failures from outdated reference docs) that this implementation session discovered and resolved.

The implementation is part of Objective #8197 (branch-scoped impl directories), with this PR completing Node 1.4 (discovery/read side). Future work (Node 1.8) will continue the migration, making this documentation essential for continuity.

## Raw Materials

PR #8279

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 13    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 5     |
| Potential tripwires (score2-3) | 7     |

## Documentation Items

### HIGH Priority

#### 1. Core Architecture: `resolve_impl_dir()` Function

**Location:** `docs/learned/architecture/impl-directory-resolution.md`
**Action:** CREATE
**Source:** [Impl] [PR #8279]

**Draft Content:**

```markdown
---
read-when: resolving implementation directories, working with .impl/ or .erk/impl-context/, writing exec scripts that need plan context
keywords: resolve_impl_dir, impl directory, branch-scoped, implementation folder discovery
---

# Implementation Directory Resolution

This document describes the `resolve_impl_dir()` function for discovering implementation directories.

## Overview

Implementation directories can exist in multiple locations (branch-scoped, legacy, or discovered). The `resolve_impl_dir()` function provides a unified discovery mechanism.

## Resolution Strategy

The function performs 4-step fallback discovery:

1. **Branch-scoped lookup** (if branch_name provided): `.erk/impl-context/<branch>/` with plan.md
2. **Legacy fallback**: `.impl/` directory in cwd
3. **Discovery scan**: Any subdirectory in `.erk/impl-context/` containing plan.md
4. **Not found**: Returns None

## When to Use

- **Use `resolve_impl_dir()`**: When you need to find an existing implementation directory (discovery with I/O)
- **Use `get_impl_dir()`**: When you need to compute a path for a new implementation directory (pure path computation, no I/O)

## Source

See `packages/erk-shared/src/erk_shared/impl_folder.py` for the implementation.

## Tripwires

- Always check `if impl_dir is None:` after calling `resolve_impl_dir()` before using the result
- Use "implementation folder" in user-facing messages, not ".impl/" (location is now dynamic)
```

---

#### 2. Click Context Injection Pattern for Exec Scripts

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] [PR #8279]

**Draft Content:**

```markdown
## Exec Script Context Injection

**Trigger:** When writing or modifying exec scripts

**Requirements:**

- MUST use `@click.pass_context` decorator on command functions
- MUST use `require_cwd(ctx)` to get working directory, FORBIDDEN to use `Path.cwd()` directly
- MUST use `require_git(ctx)` to get git gateway, FORBIDDEN to use subprocess git calls
- Helper functions SHOULD accept `ctx: click.Context` and extract values internally, not `cwd: Path`

**Why:** Enables testability via dependency injection. Tests use `ErkContext.for_test(cwd=..., git=FakeGit(...))`.

**Anti-patterns fixed in PR #8279:**

- `Path.cwd()` replaced with `require_cwd(ctx)` across 8 scripts
- Raw subprocess git calls replaced with `require_git(ctx).branch.get_current_branch()`
- `_run_impl_init(cwd: Path)` signature changed to `_run_impl_init(ctx: click.Context)`

**Source:** See `src/erk/cli/commands/exec/scripts/AGENTS.md` for canonical documentation.
```

---

#### 3. Impl Directory Resolution Pattern

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] [PR #8279]

**Draft Content:**

```markdown
## Impl Directory Resolution

**Trigger:** When resolving implementation directories in exec scripts

**Requirements:**

- MUST use `resolve_impl_dir(cwd, branch_name=branch)` for discovery
- FORBIDDEN to hardcode `cwd / ".impl"` or `cwd / ".erk" / "impl-context"`
- FORBIDDEN to implement manual dual-fallback patterns (replaced by `resolve_impl_dir()`)
- Always check `if impl_dir is None:` before using the result

**Pattern:**

```python
impl_dir = resolve_impl_dir(require_cwd(ctx), branch_name=branch_name)
if impl_dir is None:
    # Handle missing implementation folder
    raise SystemExit(1)
# impl_dir is now Path, not Path | None
```

**Source:** See `packages/erk-shared/src/erk_shared/impl_folder.py` for resolve_impl_dir().
```

---

#### 4. Type Narrowing with NoReturn Limitation

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] [PR #8279]

**Draft Content:**

```markdown
## ty Type Checker NoReturn Limitation

**Trigger:** When using NoReturn functions for type narrowing in guard clauses

**Problem:** The `ty` type checker does not properly infer that code after a NoReturn function call is unreachable. This causes type errors like "possibly-missing-attribute" or "unsupported-operator" when working with `T | None` types.

**Anti-pattern:**

```python
def _error_json(msg: str) -> NoReturn:
    print(json.dumps({"error": msg}))
    raise SystemExit(1)

impl_dir = resolve_impl_dir(cwd, branch_name=branch)
if impl_dir is None:
    _error_json("No implementation folder")  # ty doesn't narrow here!
# ty still thinks impl_dir is Path | None
```

**Solution:** Inline `raise SystemExit(1)` directly in guard clauses:

```python
impl_dir = resolve_impl_dir(cwd, branch_name=branch)
if impl_dir is None:
    print(json.dumps({"error": "No implementation folder"}))
    raise SystemExit(1)  # ty understands this narrows the type
# impl_dir is now Path
```

**Note:** This is a ty-specific limitation. The syntax `# type: ignore[return-value]` is mypy syntax and does not work with ty.
```

---

#### 5. Context Not Initialized Error in Exec Script Tests

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] [PR #8279]

**Draft Content:**

```markdown
## Context Not Initialized in Exec Script Tests

**Trigger:** When adding `@click.pass_context` to exec scripts

**Problem:** Tests using `monkeypatch.chdir()` fail with "Error: Context not initialized" because `monkeypatch.chdir()` only changes the working directory but doesn't inject the Click context object that `require_cwd(ctx)` and `require_git(ctx)` expect.

**Symptom:** 8 test failures in a single refactoring (experienced in PR #8279)

**Solution:** Migrate tests to use `ErkContext.for_test()`:

1. Remove `monkeypatch` parameter from test function signature
2. Remove `monkeypatch.chdir(path)` call
3. Add `obj=ErkContext.for_test(cwd=path, git=FakeGit(...))` to `runner.invoke()` call
4. Import `ErkContext` from `erk_shared.context.context`
5. Import `FakeGit` from `erk_shared.fake_gateways.fake_git`

**When branch-scoped resolution is used**, tests must also configure FakeGit with branch information:

```python
git=FakeGit(current_branches={tmp_path: "feature/branch-name"})
```

**Source:** See `docs/learned/testing/exec-script-testing.md` for complete patterns.
```

---

### MEDIUM Priority

#### 6. Branch-Scoped Directory Migration (Objective #8197)

**Location:** `docs/learned/planning/branch-scoped-migration.md`
**Action:** CREATE
**Source:** [Plan] [PR #8279]

**Draft Content:**

```markdown
---
read-when: working on branch-scoped implementation directories, continuing Objective #8197
keywords: branch-scoped, impl-context, objective 8197, migration
---

# Branch-Scoped Implementation Directory Migration

Tracks the migration from legacy `.impl/` directories to branch-scoped `.erk/impl-context/<branch>/` directories.

## Objective #8197 Status

| Node | Description | Status | PR |
|------|-------------|--------|-----|
| 1.3 | Creation side (create_impl_folder, get_impl_path, setup_impl.py) | Complete | #8215 |
| 1.4 | Discovery side (resolve_impl_dir, all exec scripts) | Complete | #8279 |
| 1.8 | Remove impl_type return value from impl_init.py | Future | - |

## Directory Types

Three implementation directory types are now supported:

1. **Branch-scoped** (primary): `.erk/impl-context/<branch>/` - Branch name is sanitized for filesystem
2. **Legacy** (fallback): `.impl/` - Backward compatible, still works
3. **Discovered** (emergency): Any subdirectory in `.erk/impl-context/` containing `plan.md`

## Resolution Priority

`resolve_impl_dir()` checks in order: branch-scoped first, legacy fallback, discovery last, None if not found.

## Backward Compatibility

Legacy `.impl/` directories continue to work. No user action required for migration.
```

---

#### 7. FakeGit current_branches Configuration

**Location:** `docs/learned/testing/fake-git-patterns.md`
**Action:** UPDATE
**Source:** [Impl] [PR #8279]

**Draft Content:**

```markdown
## FakeGit Branch Configuration for resolve_impl_dir Tests

**Trigger:** When testing code that uses `resolve_impl_dir()` or calls `git.branch.get_current_branch()`

**Pattern:**

```python
BRANCH = "feature/test-branch"

def _fake_git(tmp_path: Path) -> FakeGit:
    """Create FakeGit configured for branch-scoped tests."""
    return FakeGit(current_branches={tmp_path: BRANCH})

def test_branch_scoped_resolution(tmp_path: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        my_command,
        obj=ErkContext.for_test(cwd=tmp_path, git=_fake_git(tmp_path))
    )
```

**Why needed:** `resolve_impl_dir()` calls `git.branch.get_current_branch(cwd)` to determine the current branch for branch-scoped lookup. Without configuring `current_branches`, FakeGit returns None, triggering only legacy/discovery fallbacks.

**Test helper factory pattern:** Creating `_fake_git(tmp_path)` helper functions improves test maintainability by centralizing FakeGit configuration.
```

---

#### 8. Test Context Injection Pattern

**Location:** `docs/learned/testing/exec-script-testing.md`
**Action:** UPDATE
**Source:** [Impl] [PR #8279]

**Draft Content:**

```markdown
## Branch-Scoped Test Configuration

When testing exec scripts that use `resolve_impl_dir()`, tests must configure both the working directory and the git branch:

```python
from erk_shared.context.context import ErkContext
from erk_shared.fake_gateways.fake_git import FakeGit

BRANCH = "feature/test-branch"

def test_with_branch_scoped_impl(tmp_path: Path, runner: CliRunner) -> None:
    # Create branch-scoped impl directory
    impl_dir = tmp_path / ".erk" / "impl-context" / "feature--test-branch"
    impl_dir.mkdir(parents=True)
    (impl_dir / "plan.md").write_text("# Plan")

    result = runner.invoke(
        my_command,
        obj=ErkContext.for_test(
            cwd=tmp_path,
            git=FakeGit(current_branches={tmp_path: BRANCH})
        )
    )
```

Note: Branch names are sanitized for filesystem paths (e.g., "feature/test-branch" becomes "feature--test-branch").
```

---

#### 9. impl_dir None Check Before read_plan_ref

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] [PR #8279]

**Draft Content:**

```markdown
## Check impl_dir Before read_plan_ref

**Trigger:** Before calling `read_plan_ref(impl_dir)`

**Problem:** `read_plan_ref()` expects a `Path`, not `None`. Since `resolve_impl_dir()` returns `Path | None`, calling `read_plan_ref()` directly can cause type errors or runtime failures.

**Pattern:**

```python
impl_dir = resolve_impl_dir(cwd, branch_name=branch)
if impl_dir is None:
    # Handle missing implementation folder
    raise SystemExit(1)

plan_ref = read_plan_ref(impl_dir)  # Safe: impl_dir is narrowed to Path
```

**Or with conditional:**

```python
plan_ref = read_plan_ref(impl_dir) if impl_dir is not None else None
```

**Source:** 3+ scripts were updated with this check in PR #8279.
```

---

#### 10. Auto-Generated Docs Regeneration

**Location:** `docs/learned/ci/auto-generated-docs.md`
**Action:** CREATE
**Source:** [Impl] [PR #8279]

**Draft Content:**

```markdown
---
read-when: modifying exec scripts, CI fails on exec-reference-check, seeing "reference.md out of date" errors
keywords: exec reference, auto-generated, gen-exec-reference-docs
---

# Auto-Generated Exec Reference Docs

The file `.claude/skills/erk-exec/reference.md` is auto-generated from exec script code. CI validates this file is current.

## When to Regenerate

Run `erk-dev gen-exec-reference-docs` after:

- Adding new exec scripts
- Changing exec script command signatures
- Modifying exec script descriptions or option help text

## CI Validation

The `exec-reference-check` CI step compares the committed reference.md against freshly generated output. If they differ, CI fails.

## Symptoms of Stale Docs

- CI error: "exec-reference-check failed"
- Local `make fast-ci` fails after exec script changes

## Resolution

```bash
erk-dev gen-exec-reference-docs
git add .claude/skills/erk-exec/reference.md
```
```

---

#### 11. Exec Script Context Injection Examples

**Location:** `docs/learned/cli/exec-script-patterns.md`
**Action:** UPDATE
**Source:** [Impl] [PR #8279]

**Draft Content:**

```markdown
## Helper Function Context Injection

When refactoring exec scripts, helper functions should accept `ctx: click.Context` rather than extracted values like `cwd: Path`. This enables full access to context objects.

**Before (anti-pattern):**

```python
def _run_impl_init(cwd: Path) -> None:
    # Limited to just cwd
    ...

@click.command()
@click.pass_context
def setup_impl(ctx: click.Context) -> None:
    _run_impl_init(require_cwd(ctx))  # Extracts then passes
```

**After (recommended):**

```python
def _run_impl_init(ctx: click.Context) -> None:
    cwd = require_cwd(ctx)
    git = require_git(ctx)
    # Full access to context objects
    ...

@click.command()
@click.pass_context
def setup_impl(ctx: click.Context) -> None:
    _run_impl_init(ctx)  # Passes context directly
```

**Source:** See PR #8279 changes to `src/erk/cli/commands/exec/scripts/setup_impl.py`.
```

---

### LOW Priority

#### 12. Error Message Terminology Consistency

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] [PR #8279]

**Draft Content:**

```markdown
## Implementation Folder Terminology

**Trigger:** In user-facing CLI messages

**Requirement:** Use "implementation folder" not ".impl/" or ".erk/impl-context/"

**Why:** Implementation directory location is now dynamic (branch-scoped or legacy). Hardcoding path names in messages is misleading.

**Examples:**

- Good: "No implementation folder found"
- Bad: "No .impl/ folder found"
- Bad: "No .erk/impl-context/ folder found"
```

---

#### 13. Import Removal Checking Type Annotations

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] [PR #8279]

**Draft Content:**

```markdown
## Import Removal Must Check Type Annotations

**Trigger:** When removing Python imports

**Problem:** Removing an import that appears unused in function bodies but is still used in type annotations causes NameError at runtime.

**Symptom:** NameError on `Path` after removing `from pathlib import Path` (experienced in PR #8279 part 2)

**Prevention:** When removing imports, grep the entire file for all usages including:

- Return type annotations
- Parameter type annotations
- Class attribute annotations
- Type aliases
- `TYPE_CHECKING` blocks

**Pattern:**

```bash
# Before removing an import, check all usages
grep -n "Path" path/to/file.py
```
```

---

## Stale Documentation Cleanup

No stale documentation detected. All existing documentation files have clean references.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Context Not Initialized Error

**What happened:** 8 test failures when adding `@click.pass_context` to check_impl.py. Tests used `monkeypatch.chdir()` but the refactored script required Click context via `require_cwd(ctx)`.

**Root cause:** `monkeypatch.chdir()` only changes working directory but doesn't inject Click context object. The `require_cwd(ctx)` function checks for `ctx.obj` which is None without proper context injection.

**Prevention:** When adding `@click.pass_context` to exec scripts, update ALL tests to use `obj=ErkContext.for_test(cwd=...)` instead of `monkeypatch.chdir()`.

**Recommendation:** TRIPWIRE (score 6)

### 2. ty Type Checker NoReturn Narrowing

**What happened:** Multiple type errors (unsupported-operator, possibly-missing-attribute) when using `resolve_impl_dir()` which returns `Path | None`.

**Root cause:** The `ty` type checker doesn't properly infer that code after a NoReturn function call is unreachable. Calling `_error_json()` (NoReturn) in guard clauses didn't narrow the type.

**Prevention:** Inline `raise SystemExit(1)` directly in guard clauses instead of calling helper functions when type narrowing is needed.

**Recommendation:** TRIPWIRE (score 5)

### 3. NameError on Removed Import

**What happened:** Runtime NameError on `Path` after "successful" refactoring in session part 2.

**Root cause:** Removed `from pathlib import Path` import but function return type still used `tuple[Path, str]`.

**Prevention:** When removing imports, grep file for all usages including return types and parameter annotations, not just function bodies.

**Recommendation:** ADD_TO_DOC (medium severity, common Python mistake)

### 4. Test Assertion Mismatch After Refactoring

**What happened:** Test assertion failures because error messages changed from "No .impl/ folder found" to "No implementation folder found".

**Root cause:** Refactoring changed error messages but test assertions still checked for old text.

**Prevention:** After changing error messages, grep test files for old message text and update assertions to match.

**Recommendation:** ADD_TO_DOC (medium severity)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Click Context Injection in Exec Scripts

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** When writing exec scripts
**Warning:** MUST use `@click.pass_context` and `require_cwd(ctx)`; FORBIDDEN to use `Path.cwd()` directly
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because 8 scripts were migrated in a single PR, and the pattern is not intuitive for developers familiar with standard Click usage. The error manifests as cryptic "Context not initialized" failures in tests, not obvious from the source code.

### 2. Impl Directory Resolution Pattern

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** When resolving impl directories
**Warning:** Use `resolve_impl_dir(cwd, branch_name=branch)`; FORBIDDEN to hardcode `cwd / '.impl'` paths
**Target doc:** `docs/learned/architecture/tripwires.md`

This prevents regression to hardcoded paths. 8 scripts were refactored to use the new pattern. Without the tripwire, new exec scripts would likely copy old patterns from training data.

### 3. ty Type Narrowing with NoReturn

**Score:** 5/10 (Non-obvious +2, Silent failure +2, External tool quirk +1)
**Trigger:** When using NoReturn functions for type narrowing
**Warning:** Inline `raise SystemExit(1)` directly; ty doesn't narrow from NoReturn function calls
**Target doc:** `docs/learned/testing/tripwires.md`

This is a tool-specific quirk that doesn't match developer expectations from mypy or other type checkers. The workaround is non-obvious.

### 4. impl_dir None Check Before read_plan_ref

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** Before calling `read_plan_ref(impl_dir)`
**Warning:** Check `if impl_dir is None:` first; `read_plan_ref` expects Path, not None
**Target doc:** `docs/learned/planning/tripwires.md`

Common error pattern that occurred in 3+ scripts during implementation.

### 5. Context Not Initialized in Exec Tests

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** When adding `@click.pass_context` to exec scripts
**Warning:** Update ALL tests to use `obj=ErkContext.for_test(cwd=...)` not `monkeypatch.chdir()`
**Target doc:** `docs/learned/testing/tripwires.md`

Caused 8 test failures in implementation. The error message doesn't indicate the solution.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Test Assertion Alignment After Error Message Changes

**Score:** 3/10 (Non-obvious +1, Repeated pattern +2)
**Notes:** May upgrade to tripwire if pattern continues across more refactorings.

### 2. Import Removal Checking Type Annotations

**Score:** 3/10 (Non-obvious +1, Repeated pattern +2)
**Notes:** Common Python mistake, not erk-specific. Already well-known.

### 3. Terminology Consistency (implementation folder)

**Score:** 2/10 (Cross-cutting +2)
**Notes:** User-facing consistency, low severity. Error messages guide toward correct terminology.

### 4. FakeGit Branch Configuration for resolve_impl_dir Tests

**Score:** 3/10 (Non-obvious +1, Repeated pattern +2)
**Notes:** Testing-specific, may upgrade with more occurrences.

### 5. Test Helper Factory Pattern

**Score:** 2/10 (Repeated pattern +2)
**Notes:** Good practice but not critical. Tests still work without helper factories.

### 6. Auto-Generated Docs Regeneration

**Score:** 3/10 (Non-obvious +1, External tool +2)
**Notes:** CI catches this, and the error message explains how to fix it.

### 7. Session ID Substitution Limitations

**Score:** 2/10 (External tool quirk +2)
**Notes:** Low impact, has workaround (`|| true` pattern).

## Cornerstone Redirects (SHOULD_BE_CODE)

### 1. resolve_impl_dir() API Signature

**Action:** CODE_CHANGE
**What to add:** Verify the function has a comprehensive docstring with Args/Returns/Examples sections
**Where:** `packages/erk-shared/src/erk_shared/impl_folder.py`
**Why:** Single function with well-defined API should have complete docstring; learned doc references the module

### 2. require_cwd/require_git/require_repo_root Helpers

**Action:** CODE_CHANGE
**What to add:** Ensure `helpers.py` has module docstring and individual function docstrings explaining usage patterns
**Where:** `erk_shared/context/helpers.py`
**Why:** API reference for helpers module belongs in code; learned doc references the module
