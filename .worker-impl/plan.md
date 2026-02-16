# Documentation Plan: Add bundled path params to artifact health functions

## Context

This PR (#7135) implements Step 1.1 of Objective #7129, demonstrating the canonical pattern for eliminating monkeypatching via parameter injection. Three functions in `artifact_health.py` were refactored to accept bundled directory paths as explicit keyword-only parameters instead of calling `get_bundled_*_dir()` functions internally. This architectural shift moves dependency resolution from core business logic to application boundaries (CLI commands, health checks), creating a clear testability boundary.

The documentation matters because this pattern is designed to be repeated in Steps 1.2-1.5 of the objective. Creating comprehensive documentation now will accelerate future implementation and prevent agents from re-discovering the same insights. Multiple analysis agents converged on identical conclusions from different angles (planning, implementation, diff analysis), providing strong signal that these patterns are genuinely valuable.

The implementation revealed several non-obvious pitfalls: when imports move between modules, monkeypatch targets break with `AttributeError`; tests must be categorized into direct calls (use parameter injection) vs CLI tests (update patch targets); and pre-existing test failures can be falsely attributed to current changes. These lessons deserve permanent documentation as tripwires.

## Raw Materials

https://gist.github.com/schrockn/037afc2ec912d479c930e48a7d7788b2

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 9     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 4     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. Parameter Injection Pattern for Monkeypatch Elimination

**Location:** `docs/learned/testing/parameter-injection-pattern.md`
**Action:** CREATE
**Source:** [Plan], [Impl], [PR #7135]

**Draft Content:**

```markdown
---
title: Parameter Injection Pattern
read_when:
  - eliminating monkeypatch from tests
  - adding testability to existing functions
  - refactoring functions that call global getters
tripwires:
  - action: "adding parameters for dependency injection"
    warning: "Use keyword-only syntax (`*,`) to prevent breaking existing positional parameter usage"
  - action: "tests with 3+ monkeypatch statements"
    warning: "Consider refactoring to parameter injection - see parameter-injection-pattern.md"
---

# Parameter Injection Pattern

Replace internal function calls to global getters with explicit keyword-only parameters. This eliminates monkeypatch fragility and makes dependencies explicit.

## Problem

Functions that call `get_bundled_*_dir()` internally require `monkeypatch.setattr` in tests. This creates fragile tests that break when imports move between modules.

## Solution

Three-phase refactoring:

1. **Add keyword-only parameters** to functions that call getters internally
2. **Update callers** (CLI commands, health checks) to pass values from getters
3. **Remove internal getter calls** from the function bodies

## Pattern Structure

<!-- Source: src/erk/artifacts/artifact_health.py, find_orphaned_artifacts -->

See `find_orphaned_artifacts()` in `src/erk/artifacts/artifact_health.py` for the signature pattern with keyword-only bundled path parameters.

<!-- Source: src/erk/cli/commands/artifact/check.py -->

See the call sites in `src/erk/cli/commands/artifact/check.py` for the boundary function pattern - getters are called once and values passed to multiple core functions.

## Test Transformation

Tests calling functions directly pass parameters instead of monkeypatching:

<!-- Source: tests/artifacts/test_orphans.py -->

See test functions in `tests/artifacts/test_orphans.py` for the parameter injection test pattern.

## When to Use

- Functions with 3+ monkeypatch statements in tests
- Functions calling module-level getters for paths or configuration
- Core business logic functions (not CLI/boundary code)

## Related

- [dependency-injection-boundaries.md](../architecture/dependency-injection-boundaries.md) - Architectural context
- Objective #7129 - Parent objective for monkeypatch consolidation
```

---

#### 2. Monkeypatch Retargeting When Imports Move (Tripwire)

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

This tripwire addresses the most severe error encountered during implementation: 10 test failures from `AttributeError` when imports moved between modules. The session analysis shows this is non-obvious (tests were patching `artifact_health.get_bundled_*` but the import had moved to `check.py`) and cross-cutting (affected two test files).

**Tripwire Content:**

The trigger is moving imports between modules that are monkeypatched in tests. When this happens, tests monkeypatch `module_a.function` but code now imports the function in `module_b`, causing `AttributeError: module 'module_a' has no attribute 'function'`. The impact is severe - 10 test failures across 2 test files in this PR.

Prevention requires grepping for all monkeypatch references before moving imports: `Grep(pattern="monkeypatch.*module_name.*function_name", path="tests/")`. Then either retarget patches to the new import location, or better yet, eliminate monkeypatch via parameter injection.

This tripwire scores 6/10: Non-obvious (+2) because the error message doesn't explain that imports moved, Cross-cutting (+2) because it affects any module with monkeypatched imports, Repeated pattern (+1) from the session history, Silent failure in wrong context (+1) because tests fail mysteriously.

---

#### 3. Keyword-Only Parameters for Dependency Injection (Tripwire)

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Plan], [Impl]

The planning session explicitly reasoned through this: erk's "no default parameter values" standard means dependency injection parameters must be keyword-only, not optional with `None` defaults.

**Tripwire Content:**

The trigger is adding parameters for dependency injection to existing functions. The warning is to use keyword-only syntax (`*,`) to prevent breaking existing positional parameter usage. All three functions in PR #7135 demonstrate this pattern.

This prevents API breaks when adding testability parameters. Positional parameters would force all existing callers to be updated even if they don't need the new parameters. Keyword-only parameters are additive.

This tripwire scores 5/10: Non-obvious (+2) because the natural instinct is optional parameters with defaults, Cross-cutting (+2) because it applies to any function gaining DI parameters, Destructive potential (+1) because getting this wrong breaks all callers.

---

#### 4. Dead Patch Removal After Refactoring (Tripwire)

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

Session impl part 3 shows the agent removing `get_bundled_github_dir` patches that were "both broken AND unnecessary" - the refactoring removed the function calls, making the patches dead.

**Tripwire Content:**

The trigger is refactoring that removes function calls from production code. The warning is to search for and remove associated test monkeypatch statements that are now dead. The pattern from the implementation: after removing `get_bundled_github_dir()` calls, grep showed lingering patches that needed removal.

This creates test maintenance burden - dead patches clutter test files and confuse future readers about what's actually being tested. The fix is simple once you know to look for it.

This tripwire scores 4/10: Cross-cutting (+2) because it applies to any refactoring removing function calls, Repeated pattern (+1) from standard refactoring workflows, Silent maintenance burden (+1).

---

### MEDIUM Priority

#### 5. Dependency Injection Boundary Pattern

**Location:** `docs/learned/architecture/dependency-injection-boundaries.md`
**Action:** CREATE
**Source:** [Impl], [PR #7135]

**Draft Content:**

```markdown
---
title: Dependency Injection Boundaries
read_when:
  - deciding where to call configuration getters
  - structuring functions for testability
  - understanding the call site pattern
tripwires:
  - action: "calling global getters inside business logic functions"
    warning: "Consider parameter injection instead - call getters at boundaries, pass values to core functions"
---

# Dependency Injection Boundaries

Core business logic functions accept dependencies as explicit parameters. Boundary functions (CLI commands, health checks, entry points) resolve production dependencies by calling getters and passing values.

## Architecture

**Core Functions (Business Logic):**
- Accept dependencies as keyword-only parameters
- No imports of global getters
- Fully testable with any values
- Location: domain-specific modules (e.g., `artifact_health.py`)

**Boundary Functions (Integration):**
- Import and call production dependency getters
- Wire up real dependencies at the application boundary
- Location: CLI commands, health checks, entry points

## Benefits

1. **Testability**: Core functions testable with any Path values - no monkeypatch needed
2. **Explicit dependencies**: Reading function signature tells you all dependencies
3. **Clear architectural layers**: Boundaries handle wiring, core handles logic

## Example

<!-- Source: src/erk/artifacts/artifact_health.py, find_missing_artifacts -->

See `find_missing_artifacts()` in `src/erk/artifacts/artifact_health.py` for a core function accepting bundled paths as parameters.

<!-- Source: src/erk/cli/commands/artifact/check.py -->

See `check.py` for the boundary that imports `get_bundled_claude_dir()` and passes the result to core functions.

## Testing Strategy

- **Direct function tests**: Pass test paths as parameters (no monkeypatch)
- **CLI integration tests**: Monkeypatch at the boundary module (e.g., `check.py`)

## Related

- [parameter-injection-pattern.md](../testing/parameter-injection-pattern.md) - Testing pattern details
```

---

#### 6. Pre-Existing Test Failure Verification Workflow

**Location:** `docs/learned/testing/pre-existing-test-failures.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Pre-Existing Test Failure Verification
read_when:
  - test failures appear during refactoring
  - uncertain if current changes broke tests
  - before major refactoring work
tripwires:
  - action: "starting major refactoring on code with existing tests"
    warning: "Verify test status first with `git stash && pytest <path> && git stash pop`"
---

# Pre-Existing Test Failure Verification

Before attributing test failures to current changes, verify the test status on the clean codebase.

## Pattern

```bash
git stash && pytest <test-path> && git stash pop
```

This stashes current changes, runs tests against clean code, then restores changes.

## When to Use

- Test failures appear during refactoring
- Unsure if failure is from your changes or pre-existing
- Before starting major refactoring (baseline verification)

## Example from PR #7135

The implementation session encountered `test_check_version_mismatch_does_not_show_artifacts` failure. Agent used the stash pattern to verify it failed on clean master - the test was pre-existing broken (doesn't patch `get_bundled_*` functions). The agent correctly excluded it from the test run rather than attempting to fix an out-of-scope issue.

## Benefits

- Prevents false blame attribution
- Avoids rabbit-hole fixes for unrelated issues
- Documents baseline test health
```

---

#### 7. Incremental Signature Refactoring Workflow

**Location:** `docs/learned/refactoring/signature-refactoring-workflow.md`
**Action:** CREATE
**Source:** [Plan], [Impl]

**Draft Content:**

```markdown
---
title: Signature Refactoring Workflow
read_when:
  - changing function signatures with multiple call sites
  - adding parameters to public functions
  - systematic refactoring across multiple files
tripwires:
  - action: "changing function signature without grepping for call sites first"
    warning: "Always grep for all call sites before signature changes - use Grep to find `function_name(`"
---

# Signature Refactoring Workflow

Systematic approach to changing function signatures with multiple call sites.

## Six-Phase Process

**Phase 1: Discovery**
Grep for all call sites before making changes:
```bash
Grep(pattern="function_name\\(", path="src/")
Grep(pattern="function_name\\(", path="tests/")
```

**Phase 2: Modify Function Signatures**
Add parameters, update function body, remove internal calls.

**Phase 3: Update Production Callers**
Update all production call sites (CLI commands, other modules).

**Phase 4: Update Direct Test Calls**
Tests calling functions directly use parameter injection.

**Phase 5: Update CLI Test Patches**
CLI integration tests update monkeypatch targets to boundary modules.

**Phase 6: Cleanup**
- Remove unused imports
- Run ty, ruff, pytest to verify

## Key Insight

Tests require two-tier updates:
1. **Direct calls**: Use parameter injection (cleaner)
2. **CLI tests**: Update patch targets (patches at boundary)

## Example

PR #7135 followed this workflow for three functions across 4 call sites in 2 production files and tests in 4 test files.
```

---

### LOW Priority

#### 8. Update bundled-artifacts.md Function Signatures

**Location:** `docs/learned/architecture/bundled-artifacts.md`
**Action:** UPDATE
**Source:** [PR #7135]

**Draft Content:**

The existing documentation covers `get_artifact_health()`, `find_orphaned_artifacts()`, and `find_missing_artifacts()`. These function signatures changed to accept bundled path parameters. Update the documentation to note:

- These functions now accept bundled paths as keyword-only parameters
- They no longer call `get_bundled_*_dir()` internally
- Call sites (CLI commands, health checks) are responsible for passing bundled paths
- Link to `docs/learned/testing/parameter-injection-pattern.md` for the pattern details

---

#### 9. Update testing.md with Parameter Injection Preference

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [PR #7135]

**Draft Content:**

Add a section or reference emphasizing parameter injection over monkeypatch:

- Prefer parameter injection for dependency customization
- Monkeypatch is the fallback when parameter injection isn't feasible
- Link to `docs/learned/testing/parameter-injection-pattern.md` for complete guide
- Benefits: explicit dependencies, no fragile patch targets, cleaner test code

---

## Contradiction Resolutions

**None found.** All existing documentation is consistent with the implementation patterns. The gap analysis verified all code references in existing docs have valid targets.

## Stale Documentation Cleanup

**None required.** The gap analysis found no phantom file paths or stale references in existing documentation.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. AttributeError on Monkeypatch Targets After Import Relocation

**What happened:** After refactoring removed imports from `artifact_health.py`, 10 tests failed with `AttributeError: module 'erk.artifacts.artifact_health' has no attribute 'get_bundled_claude_dir'`

**Root cause:** Tests monkeypatched `erk.artifacts.artifact_health.get_bundled_claude_dir`, but the refactoring moved this import to `check.py` and `health_checks.py`. The patch target no longer existed.

**Prevention:** Before removing imports, grep for all monkeypatch references: `Grep(pattern="monkeypatch.*artifact_health.*get_bundled", path="tests/")`. Then either retarget patches or eliminate via parameter injection.

**Recommendation:** TRIPWIRE - This is the highest-severity error encountered (10 test failures) and is non-obvious because the error message doesn't explain that imports moved.

### 2. False Attribution of Test Failures During Refactoring

**What happened:** `test_check_version_mismatch_does_not_show_artifacts` failed during implementation, creating confusion about whether current changes broke it.

**Root cause:** The test doesn't patch `get_bundled_*` functions, causing real bundled directories (86+ files) to be compared against minimal test setup. This was a pre-existing failure.

**Prevention:** Verify test status before refactoring with `git stash && pytest <path> && git stash pop`. This establishes baseline test health.

**Recommendation:** ADD_TO_DOC - Create pre-existing-test-failures.md (item #6 above).

### 3. Incomplete Test Updates After Signature Changes

**What happened:** The agent initially updated patch targets from `artifact_health.*` to `check.*` in all test files, but user corrected this approach.

**Root cause:** Tests calling functions directly should use parameter injection, not updated patches. Only CLI tests should retain patches (at the boundary level).

**Prevention:** Categorize tests into direct calls vs CLI tests before updating. Use grep to find all test usages and plan updates accordingly.

**Recommendation:** ADD_TO_DOC - Covered in parameter-injection-pattern.md "Test Transformation" section.

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Monkeypatch Retargeting When Imports Move

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Repeated pattern +1, Silent failure in wrong context +1)

**Trigger:** Before moving imports between modules that are monkeypatched in tests

**Warning:** "Grep for all monkeypatch references to the moved function and retarget them to the new import location"

**Target doc:** `docs/learned/testing/tripwires.md`

This tripwire addresses the most severe error in PR #7135: 10 test failures from `AttributeError` when patches targeted stale import locations. The error message is misleading - it says the attribute doesn't exist, not that the import moved. Without this tripwire, agents will repeat the same debugging cycle of: (1) see AttributeError, (2) check if function exists (it does), (3) eventually realize the *import location* changed.

### 2. Keyword-Only Parameters for Dependency Injection

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, Destructive potential +1)

**Trigger:** When adding parameters for dependency injection to existing functions

**Warning:** "Use keyword-only syntax (`*,`) to prevent breaking existing positional parameter usage"

**Target doc:** `docs/learned/testing/tripwires.md`

The planning session explicitly reasoned through this: erk forbids default parameters, so the natural instinct of `bundled_dir: Path = None` is wrong. But making parameters positional would break existing callers. The keyword-only pattern solves both constraints.

### 3. Dead Patch Removal After Refactoring

**Score:** 4/10 (criteria: Cross-cutting +2, Repeated pattern +1, Silent maintenance burden +1)

**Trigger:** When refactoring removes function calls from production code

**Warning:** "Search for and remove associated test monkeypatch statements that are now dead"

**Target doc:** `docs/learned/testing/tripwires.md`

Session impl part 3 shows the pattern: after removing `get_bundled_github_dir()` calls, the agent found and removed now-dead patches. These patches were both broken (wrong target) and unnecessary (no longer needed). Without this tripwire, dead patches accumulate and confuse future readers.

### 4. Pre-Existing Test Failure Verification

**Score:** 4/10 (criteria: Non-obvious +2, Destructive potential +1, Repeated pattern +1)

**Trigger:** Before starting major refactoring work on code with existing tests

**Warning:** "Run `git stash && pytest && git stash pop` to verify pre-existing test status"

**Target doc:** `docs/learned/testing/tripwires.md`

This prevents the rabbit-hole of trying to fix test failures that weren't caused by current changes. The implementation session correctly used this pattern to identify and exclude a pre-existing broken test.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Import Location Changes Break Tests

**Score:** 3/10 (criteria: Cross-cutting +2, Repeated pattern +1)

**Notes:** This is a specific case of the "monkeypatch retargeting" tripwire above. The general tripwire about retargeting likely covers this case. Would become its own tripwire if we see import-related failures that don't involve monkeypatch (e.g., circular imports, import ordering issues).

### 2. Systematic Call Site Discovery Before Signature Changes

**Score:** 3/10 (criteria: Non-obvious +1, Cross-cutting +2)

**Notes:** Good practice that's covered in the refactoring workflow documentation. Didn't reach tripwire threshold because the consequences of skipping it (missing a call site) are immediately visible (type errors, test failures) rather than silent. The workflow doc is sufficient guidance.