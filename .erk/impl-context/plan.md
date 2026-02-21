# Documentation Plan: Move plan backend configuration to GlobalConfig

## Context

This implementation introduced a three-tier configuration resolution pattern for plan backends, allowing users to persist their preferred backend (issue-based or draft-PR) in a configuration file while maintaining environment variable overrides for CI workflows. The change touched 27 files across the codebase, including core configuration modules, CLI commands, TUI components, and the test infrastructure.

The most significant challenge was not the implementation itself but the testing implications. The three-tier resolution pattern (environment variable > config > default) introduced subtle test isolation issues that caused 6+ test failures. The environment variable having highest priority meant that ambient `ERK_PLAN_BACKEND` values from the developer's shell would leak into tests via CliRunner, overriding carefully configured test values. This pattern will recur for any future config fields that support environment variable overrides.

A future agent working on GlobalConfig fields, three-tier resolution, or backend-dispatching commands would benefit enormously from understanding: (1) the 4-place update pattern for GlobalConfig fields, (2) the mandatory environment variable isolation in tests, and (3) the requirement to explicitly configure backends in test contexts to avoid silent wrong-path routing.

## Raw Materials

https://gist.github.com/schrockn/80698a9cf1f004775cfdf327bf1bea2c

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 25    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 6     |
| Potential tripwires (score2-3) | 5     |

## Documentation Items

### HIGH Priority

#### 1. Three-tier resolution pattern

**Location:** `docs/learned/configuration/three-tier-resolution.md`
**Action:** CREATE
**Source:** [Impl] [PR #7722]

**Draft Content:**

```markdown
---
read-when:
  - implementing configuration with environment variable override
  - adding config fields that CI needs to override
  - debugging unexpected config resolution in tests
tripwires: 2
---

# Three-Tier Configuration Resolution

Pattern for resolving configuration values with multiple sources.

## Resolution Order

1. **Environment variable** (highest priority) - CI and override scenarios
2. **Config file** - User's persisted preference
3. **Default value** - Fallback when neither is set

## When Each Tier Applies

- **Env var**: CI workflows, temporary overrides, debugging
- **Config file**: User's persistent preference across sessions
- **Default**: New users, minimal configuration

## Implementation Pattern

See `packages/erk-shared/src/erk_shared/plan_store/__init__.py` for `get_plan_backend()` reference implementation.

Key implementation details:
- Check env var with `os.environ.get()` first
- Validate env var value against allowed values
- Fall back to config field when env var is absent or invalid
- Fall back to default when config field matches default

## Testing Considerations

CRITICAL: Environment variables have highest priority, so ambient values from developer's shell will override test config values. See testing tripwires for isolation patterns.

## Cross-References

- `docs/learned/testing/environment-variable-isolation.md`
- `docs/learned/configuration/config-layers.md`
```

---

#### 2. GlobalConfig field addition checklist

**Location:** `docs/learned/architecture/globalconfig-field-addition.md`
**Action:** CREATE
**Source:** [Impl] [PR #7722]

**Draft Content:**

```markdown
---
read-when:
  - adding a new field to GlobalConfig
  - modifying config schema
  - updating config persistence
tripwires: 1
---

# GlobalConfig Field Addition Checklist

When adding a new field to GlobalConfig, you MUST update 4 places in synchrony.

## Required Updates

1. **Dataclass definition** (`context/types.py`)
   - Add field with type annotation
   - Use explicit default value or mark as required

2. **Test factory method** (`GlobalConfig.test()`)
   - Add matching parameter with same default
   - Thread parameter to constructor call

3. **Config loading** (`real.py` - `load_config()`)
   - Parse field from TOML with validation
   - Handle invalid values (fallback to default)
   - Use LBYL pattern with explicit validation

4. **Config saving** (`real.py` - `save_config()`)
   - Conditionally write only non-default values
   - Keep config files minimal

## Finding All Constructor Calls

CRITICAL: Use Grep to find ALL `GlobalConfig(` constructor calls in tests:

```bash
rg "GlobalConfig\(" tests/
```

PR #7722 required updating 7+ test files with explicit field values.

## Source Reference

See `packages/erk-shared/src/erk_shared/context/types.py` for GlobalConfig definition.
See `packages/erk-shared/src/erk_shared/gateway/erk_installation/real.py` for load/save implementation.
```

---

#### 3. Backend dispatcher test context requirement

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl] Session add78f25

**Draft Content:**

```markdown
## Backend Dispatcher Test Context

**Trigger:** Testing commands that dispatch to multiple backends (plan_save, implement_shared, etc.)

**Warning:** ALWAYS set plan_backend explicitly in test context. Without explicit backend, test routes to default code path and may pass with invalid assumptions about backend behavior.

**Pattern:**
- Use `plan_backend="draft_pr"` parameter in `context_for_test()`
- Or use the `_draft_pr_context()` helper if available
- Verify test data matches the backend type (draft PR needs branch_name, issue-based needs erk-plan label)

**Why:** Silent wrong-path routing causes tests to pass for wrong reasons. The KeyError on `branch_name` in session add78f25 was caused by test defaulting to issue-based backend while expecting draft PR output.
```

---

#### 4. Environment variable isolation in CliRunner

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl] Session part6

**Draft Content:**

```markdown
## CliRunner Environment Variable Isolation

**Trigger:** Writing tests that rely on GlobalConfig values in three-tier resolution

**Warning:** CliRunner does NOT automatically isolate environment variables. When testing three-tier resolution (env > config > default), use `env_overrides` in `erk_isolated_fs_env()` or `monkeypatch.delenv()` to prevent ambient env vars from overriding test config. ERK_PLAN_BACKEND leaking from user's shell will override all test GlobalConfig values.

**Pattern:**
```python
# Option 1: Override in erk_isolated_fs_env
with erk_isolated_fs_env(env_overrides={"ERK_PLAN_BACKEND": "github"}):
    ...

# Option 2: Clear with monkeypatch
def test_something(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("ERK_PLAN_BACKEND", raising=False)
    ...
```

**Why:** Session part6 had 6 test failures because developer's `ERK_PLAN_BACKEND=draft_pr` leaked through CliRunner and overrode all test configurations.
```

---

#### 5. PlanBackendType canonical import location

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl] Diff analysis

**Draft Content:**

```markdown
## PlanBackendType Canonical Import

**Trigger:** Importing PlanBackendType from any module

**Warning:** PlanBackendType is defined ONLY in `erk_shared.context.types`. All imports must use this canonical location. Never re-export or duplicate the type definition in plan_store/ or other modules.

**Correct:**
```python
from erk_shared.context.types import PlanBackendType
```

**Why:** Type consolidation prevents import confusion and ensures single source of truth for type definition.
```

---

#### 6. Update draft-pr-plan-backend.md

**Location:** `docs/learned/planning/draft-pr-plan-backend.md`
**Action:** UPDATE
**Source:** [Impl] Existing docs checker

**Draft Content:**

Add section explaining three-tier resolution:

```markdown
## Configuration Resolution

Plan backend is resolved in priority order:

1. `ERK_PLAN_BACKEND` environment variable (for CI override)
2. `plan_backend` field in GlobalConfig (user preference)
3. Default: `"github"` (issue-based backend)

### Setting via Config

```bash
# Set persistent preference
erk config set plan_backend draft_pr

# Or edit ~/.erk/config.toml directly
[global]
plan_backend = "draft_pr"
```

### CLI Usage

The `get_plan_backend()` function now requires `global_config` parameter:
```python
plan_backend = get_plan_backend(ctx.global_config)
```

### Backward Compatibility

The environment variable `ERK_PLAN_BACKEND` continues to work and takes highest priority, ensuring CI workflows function unchanged.
```

---

### MEDIUM Priority

#### 7. Test context plan_backend parameter

**Location:** `docs/learned/testing/test-context-plan-backend.md`
**Action:** CREATE
**Source:** [Impl] Session part4

**Draft Content:**

```markdown
---
read-when:
  - writing tests for plan commands
  - migrating tests from env var fixtures to explicit parameters
  - understanding test context setup
tripwires: 0
---

# Test Context Plan Backend Parameter

The `context_for_test()` factory now accepts an explicit `plan_backend` parameter.

## Migration Pattern

Before (env var fixture):
```python
@pytest.fixture(autouse=True)
def _use_draft_pr_backend():
    os.environ["ERK_PLAN_BACKEND"] = "draft_pr"
    yield
    del os.environ["ERK_PLAN_BACKEND"]
```

After (explicit parameter):
```python
ctx = context_for_test(plan_backend="draft_pr")
```

## Benefits

- Test intent is visible in test code
- No environment variable contamination
- Works correctly with three-tier resolution

## Source Reference

See `packages/erk-shared/src/erk_shared/context/testing.py` for `context_for_test()` implementation.
```

---

#### 8. JSON stdin with heredoc pattern

**Location:** `docs/learned/cli/erk-exec-json-stdin.md`
**Action:** CREATE
**Source:** [Impl] Session part7

**Draft Content:**

```markdown
---
read-when:
  - passing complex JSON to erk exec commands
  - seeing JSON parse errors with control characters
  - using erk exec with stdin
tripwires: 0
---

# JSON stdin with Heredoc Pattern

When passing complex JSON (especially with newlines) to `erk exec` commands, use the heredoc file pattern instead of inline echo.

## The Problem

```bash
# FAILS: Control characters in JSON
echo '[{"thread_id": "123", "comment": "Fixed...\nReplaced..."}]' | erk exec resolve-review-threads
# Error: Invalid control character at: line 1 column 121
```

## The Solution

```bash
# Create temp file with heredoc
cat > /tmp/threads.json << 'EOF'
[{"thread_id": "123", "comment": "Fixed the issue.\nReplaced with new approach."}]
EOF

# Pipe file contents
cat /tmp/threads.json | erk exec resolve-review-threads
```

## Why This Works

- Heredoc preserves newlines as literal characters
- File-based approach avoids shell escaping issues
- Single-quoted EOF prevents variable expansion
```

---

#### 9. Dataclass required field migration

**Location:** `docs/learned/refactoring/dataclass-required-field.md`
**Action:** CREATE
**Source:** [Impl] Session part5

**Draft Content:**

```markdown
---
read-when:
  - making dataclass fields required (removing default)
  - adding required fields to existing dataclasses
  - systematic multi-file refactoring
tripwires: 0
---

# Dataclass Required Field Migration

Systematic pattern for updating all constructor calls when a dataclass field becomes required.

## Process

1. **Grep for constructor calls**
   ```bash
   rg "ClassName\(" --type py
   ```

2. **Analyze indentation patterns**
   - Module-level: typically 8 spaces
   - Class method bodies: typically 12 spaces
   - Group similar patterns for batch edits

3. **Apply batch edits**
   - Use `replace_all=True` for uniform patterns
   - Verify exact whitespace before attempting

4. **Verify completeness**
   ```bash
   rg "ClassName\(" --type py  # Should show updated calls only
   ```

## Example from GlobalConfig

PR #7722 added `plan_backend` as required field:
- Grepped for `GlobalConfig(`
- Found 15+ call sites across 7 test files
- Grouped by indentation pattern
- Applied targeted replacements

## Common Pitfall

Read file to verify exact indentation before replace_all. Class method bodies use different indentation than module-level code.
```

---

#### 10. LBYL ternary conversion with cast

**Location:** `docs/learned/architecture/lbyl-patterns.md`
**Action:** UPDATE (or CREATE if doesn't exist)
**Source:** [Impl] Session part7

**Draft Content:**

```markdown
## Ternary to If-Else Guard with Cast

When converting validation ternaries to LBYL guards, use `cast()` for type narrowing.

### Before (ternary):
```python
plan_backend = raw_value if raw_value in ("draft_pr", "github") else "github"
```

### After (LBYL guard):
```python
if raw_value in ("draft_pr", "github"):
    plan_backend: PlanBackendType = cast(PlanBackendType, raw_value)
else:
    plan_backend: PlanBackendType = "github"
```

### Why Cast is Needed

After the `if` check validates `raw_value`, the type checker doesn't automatically narrow `raw_value` to `PlanBackendType`. The `cast()` informs the type checker that we've validated the value.

### Source Reference

See `packages/erk-shared/src/erk_shared/gateway/erk_installation/real.py` for example in `load_config()`.
```

---

#### 11. False positive bot review handling

**Location:** `docs/learned/pr-operations/bot-review-false-positives.md`
**Action:** CREATE
**Source:** [Impl] Session part7, PR comments analysis

**Draft Content:**

```markdown
---
read-when:
  - responding to bot review comments
  - seeing duplicate or outdated feedback
  - resolving PR review threads
tripwires: 0
---

# False Positive Bot Review Handling

Pattern for identifying and responding to bot review false positives.

## Identifying False Positives

1. **Already resolved**: Code already follows the suggested pattern
2. **Stale commit**: Bot reviewed an older commit, changes already made
3. **Duplicate**: Same issue flagged multiple times (bot review lag)

## Response Templates

### Already Resolved
```
Already resolved - the latest bot review shows 0 violations for this pattern. This comment was based on an earlier commit.
```

### False Positive (with explanation)
```
This is a false positive. Line N already extracts the expression to an intermediate variable:
`erk_global_config = erk_ctx.global_config if erk_ctx is not None else None`
```

### Duplicate Thread
```
Same fix applied in thread above. All instances updated in commit abc123.
```

## Checking Review Timing

Compare comment timestamp against commit history to identify stale feedback. Bot reviews can lag behind push-to-review timing.
```

---

#### 12. Backend-aware test data validity

**Location:** `docs/learned/testing/backend-test-data.md`
**Action:** CREATE
**Source:** [Impl] Session add78f25

**Draft Content:**

```markdown
---
read-when:
  - writing tests for backend-dispatching commands
  - seeing KeyError in tests for expected fields
  - creating test fixtures for plan operations
tripwires: 0
---

# Backend-Aware Test Data Validity

Test data must match the configured backend type to avoid silent failures.

## Backend Data Requirements

| Backend | Required Fields | Label |
|---------|----------------|-------|
| draft_pr | branch_name, PR metadata | N/A |
| github (issue) | N/A | erk-plan label |

## Error Pattern

```
KeyError: 'branch_name'
```

This occurs when test expects draft PR output but backend defaults to issue-based.

## Prevention

1. Verify test context sets correct `plan_backend`
2. Ensure test fixtures have data matching that backend
3. Use helper functions that couple context and data correctly

## Example

```python
# WRONG: Generic context, draft PR expectations
ctx = context_for_test()  # defaults to github
# Test expects branch_name -> KeyError

# RIGHT: Explicit backend with matching data
ctx = context_for_test(plan_backend="draft_pr")
# Test data includes branch_name -> passes
```
```

---

#### 13. Three-tier resolution test coverage

**Location:** `docs/learned/testing/three-tier-resolution-tests.md`
**Action:** CREATE
**Source:** [Impl] Session part4

**Draft Content:**

```markdown
---
read-when:
  - testing three-tier configuration resolution
  - writing config integration tests
  - verifying config precedence
tripwires: 0
---

# Three-Tier Resolution Test Coverage

Required test scenarios for three-tier resolution (env var > config > default).

## Unit Tests (3 scenarios)

1. **Env var overrides config**
   - Set env var to value A, config to value B
   - Assert resolution returns A

2. **Config used when env var absent**
   - No env var, config set to value B
   - Assert resolution returns B

3. **Default used when both absent**
   - No env var, no config (or default config)
   - Assert resolution returns default

## Integration Tests (5 scenarios)

1. **Load non-default value** - Verify config file with draft_pr loads correctly
2. **Load default** - Verify missing field defaults to github
3. **Invalid value fallback** - Verify invalid config value falls back to default
4. **Roundtrip persistence** - Save then load preserves non-default value
5. **Default suppression** - Verify default values not written to config file

## Source Reference

See `tests/unit/plan_store/test_get_plan_backend.py` and `tests/integration/test_real_global_config.py` for implementation.
```

---

#### 14. Update config-layers.md

**Location:** `docs/learned/configuration/config-layers.md`
**Action:** UPDATE
**Source:** [Impl] Existing docs checker

**Draft Content:**

Add `plan_backend` to GlobalConfig section:

```markdown
## GlobalConfig Fields

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| erk_root | Path | required | Root path of erk installation |
| plan_backend | PlanBackendType | "github" | Plan storage backend (three-tier resolution) |

### plan_backend

Controls which plan storage backend to use. Supports three-tier resolution:
1. `ERK_PLAN_BACKEND` env var (highest priority)
2. Config file `plan_backend` field
3. Default: `"github"`

Valid values: `"github"`, `"draft_pr"`

See `docs/learned/configuration/three-tier-resolution.md` for details.
```

---

#### 15. Bot review timing and staleness

**Location:** `docs/learned/ci/bot-review-timing.md`
**Action:** CREATE
**Source:** [Impl] PR comments analysis

**Draft Content:**

```markdown
---
read-when:
  - debugging duplicate PR review comments
  - addressing outdated bot feedback
  - understanding CI timing
tripwires: 0
---

# Bot Review Timing and Staleness

Bot reviews can lag behind code state, creating duplicate or obsolete feedback.

## Identifying Stale Feedback

1. Check comment timestamp against commit history
2. Compare with latest bot review run
3. Look for "0 violations" in newer runs for same pattern

## Common Patterns

- **Duplicate threads**: Same issue flagged 2-4 times across multiple bot runs
- **Already-fixed feedback**: Comment on code that was fixed in subsequent commit
- **Outdated violation**: Bot ran on base commit before your changes merged

## Response Strategy

1. Check latest bot run for violation count
2. If 0 violations, mark as "already resolved"
3. If still present, address and note which commit fixes it
4. Reference commit hash in resolution comment

PR #7722 had 4 duplicate threads due to bot review timing lag - all valid feedback but already addressed.
```

---

#### 16. Click context extraction patterns

**Location:** `docs/learned/cli/click-patterns.md`
**Action:** UPDATE (or CREATE if doesn't exist)
**Source:** [Impl] Session part3

**Draft Content:**

```markdown
## Context Extraction Patterns

Different patterns for extracting ErkContext depending on function type.

### From click.Context (CLI commands)

```python
@click.command()
@click.pass_context
def my_command(ctx: click.Context):
    erk_ctx: ErkContext = ctx.obj
    global_config = erk_ctx.global_config
    # or directly: ctx.obj.global_config
```

### From ErkContext directly (internal helpers)

```python
def helper_function(ctx: ErkContext):
    global_config = ctx.global_config
```

### In hooks

```python
# Hooks typically extract early
global_config = ctx.obj.global_config
# Then thread through helper calls
result = _gather_inputs(global_config, ...)
```

### When to Use Each

- CLI command entry point: `click.Context` with `ctx.obj`
- Internal helper: Direct `ErkContext` parameter
- Hooks: Extract once, thread through helpers
```

---

### LOW Priority

#### 17. Update testing.md for integration test coverage

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [Impl] PR bot review

**Draft Content:**

Add section:

```markdown
## Integration Test Coverage for Config Fields

When adding config fields, ensure 5 integration test scenarios:

1. **Load non-default value** - Config file contains non-default, loads correctly
2. **Load default** - Field missing from config, defaults correctly
3. **Invalid value fallback** - Invalid value in config falls back to default
4. **Roundtrip persistence** - Save then load preserves value
5. **Default suppression** - Default values NOT written to config file

See `tests/integration/test_real_global_config.py` for `plan_backend` examples.
```

---

#### 18. Refactoring vs logic change test coverage

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [Impl] PR comments analysis

**Draft Content:**

Add section:

```markdown
## When Refactoring Requires New Tests

### Requires new tests:
- Logic changes (new branches, different behavior)
- New functionality (new outputs, new error cases)
- Bug fixes (test should fail before fix, pass after)

### Does NOT require new tests:
- Parameter renames (existing tests cover behavior)
- Call signature updates (threading params through)
- Import reorganization
- Type annotation additions

PR bot reviews may flag "significant modifications" - distinguish between logic changes and signature updates when deciding test coverage.
```

---

#### 19. Update schema-driven-config.md

**Location:** `docs/learned/configuration/schema-driven-config.md`
**Action:** UPDATE
**Source:** [Impl] Session part2

**Draft Content:**

Reinforce config minimalism pattern:

```markdown
## Config Minimalism

Default values are NOT written to config file. Only non-default values are persisted.

### Implementation Pattern

```python
def save_config(config: GlobalConfig):
    doc = {}
    # Only write non-defaults
    if config.plan_backend != "github":
        doc["plan_backend"] = config.plan_backend
    # ... write doc to file
```

### Benefits

- Clean config files (only user customizations)
- Easier upgrades (defaults can change)
- Clear intent (explicit values are intentional)
```

---

#### 20. Frozen dataclass field addition

**Location:** `docs/learned/architecture/erk-architecture.md`
**Action:** UPDATE
**Source:** [Impl] Session part2

**Draft Content:**

Add to frozen dataclass section:

```markdown
## Adding Fields to Frozen Dataclasses

When adding a field with a default value to a frozen dataclass:

1. Add field to dataclass definition with type and default
2. Update `.test()` factory method with matching parameter

```python
@dataclass(frozen=True)
class GlobalConfig:
    erk_root: Path
    plan_backend: PlanBackendType = "github"  # New field

    @classmethod
    def test(cls, *, erk_root: Path = ..., plan_backend: PlanBackendType = "github"):
        return cls(erk_root=erk_root, plan_backend=plan_backend)
```

The test factory must mirror the dataclass defaults for consistent behavior.
```

---

#### 21. Config mocking in integration tests

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [Impl] Session part4

**Draft Content:**

Add section:

```markdown
## Config Mocking in Integration Tests

When testing components that load real config files, mock the loading mechanism rather than manipulating environment variables.

### Pattern

```python
def test_with_custom_config(monkeypatch):
    custom_config = GlobalConfig.test(plan_backend="draft_pr")

    mock_installation = Mock()
    mock_installation.load_config.return_value = custom_config

    monkeypatch.setattr(RealErkInstallation, "__call__", lambda: mock_installation)
    # Component now sees custom_config
```

### Why Not Env Vars

- Env vars can leak to/from other tests
- Three-tier resolution makes env vars override config
- Mocking the source is more reliable
```

---

#### 22. Test isolation via explicit parameters

**Location:** `docs/learned/testing/environment-variable-isolation.md`
**Action:** UPDATE (or CREATE if doesn't exist)
**Source:** [Impl] Session part4

**Draft Content:**

```markdown
## Migration: Env Var Fixtures to Explicit Parameters

### Before (env var fixture)

```python
@pytest.fixture(autouse=True)
def _use_draft_pr_backend():
    os.environ["ERK_PLAN_BACKEND"] = "draft_pr"
    yield
    del os.environ["ERK_PLAN_BACKEND"]

def test_something(_use_draft_pr_backend):
    ctx = context_for_test()  # Relies on env var
```

### After (explicit parameter)

```python
def test_something():
    ctx = context_for_test(plan_backend="draft_pr")  # Intent visible
```

### Benefits

- Test intent is visible in test code (no hidden fixture magic)
- No env var contamination between tests
- Works correctly with three-tier resolution
- Easier to understand test requirements at a glance
```

---

#### 23. PR feedback complete workflow

**Location:** `docs/learned/pr-operations/pr-feedback-workflow.md`
**Action:** UPDATE (or CREATE in pr-operations/)
**Source:** [Impl] Session part7, add78f25

**Draft Content:**

```markdown
## Complete PR Feedback Cycle

1. **Preview** - `/erk:pr-preview-address` to see pending comments
2. **Classify** - Comments auto-classified into batches
3. **Execute batches** - Apply fixes per batch
4. **Resolve threads** - `erk exec resolve-review-threads` with JSON
5. **CI verification** - Run `make fast-ci` or `make all-ci`
6. **Submit** - `erk pr submit` to push and update PR

### Commands Reference

- Preview: `/erk:pr-preview-address`
- Full address: `/erk:pr-address`
- Thread resolution: `cat threads.json | erk exec resolve-review-threads`
- Submit: `erk pr submit`
```

---

#### 24. DRY for deterministic function calls

**Location:** `docs/learned/architecture/dignified-python-core.md`
**Action:** UPDATE
**Source:** [Impl] Session part7

**Draft Content:**

```markdown
## DRY for Deterministic Function Calls

When the same deterministic function call appears multiple times in the same scope with identical arguments, extract to a variable.

### Before

```python
def list_plans():
    if get_plan_backend(ctx.global_config) == "draft_pr":
        # ... draft PR logic
    plans = fetch_plans(get_plan_backend(ctx.global_config))  # Duplicate
```

### After

```python
def list_plans():
    plan_backend = get_plan_backend(ctx.global_config)  # Extract once
    if plan_backend == "draft_pr":
        # ... draft PR logic
    plans = fetch_plans(plan_backend)
```

### Why

- Clearer code (intent stated once)
- Easier to change (single location)
- Bot reviewers flag this pattern
```

---

#### 25. get_plan_backend() must receive global_config parameter

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl] Diff analysis

**Draft Content:**

```markdown
## get_plan_backend() Parameter Requirement

**Trigger:** Calling get_plan_backend() from CLI commands or hooks

**Warning:** ALWAYS pass global_config parameter when available: `get_plan_backend(ctx.global_config)`. This enables config-based resolution. Without the parameter, only env var and default are considered.

**Correct:**
```python
plan_backend = get_plan_backend(ctx.global_config)
```

**Wrong:**
```python
plan_backend = get_plan_backend()  # Misses config tier
```
```

---

## Contradiction Resolutions

No contradictions detected. All existing documentation is consistent. The environment variable `ERK_PLAN_BACKEND` is documented as the current mechanism, and the migration to GlobalConfig is an evolution (with env var as fallback), not a contradiction.

## Stale Documentation Cleanup

No stale documentation detected. All code references in existing documentation were verified and are current. No phantom references found.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. CliRunner Environment Variable Leakage

**What happened:** 6 tests failed with exit code 1 after removing env var overrides, expecting config-based resolution to work
**Root cause:** CliRunner does not isolate environment variables. Developer's `ERK_PLAN_BACKEND=draft_pr` leaked through and overrode all test config values due to three-tier resolution priority
**Prevention:** ALWAYS use `env_overrides` in `erk_isolated_fs_env()` or `monkeypatch.delenv()` when tests rely on specific config values
**Recommendation:** TRIPWIRE - This caused the most implementation friction and will affect all future three-tier features

### 2. Backend Dispatcher Test Routing

**What happened:** `KeyError: 'branch_name'` in test expecting draft PR output
**Root cause:** Test context missing `plan_backend="draft_pr"`, causing silent routing to issue-based backend which doesn't produce `branch_name` field
**Prevention:** All tests for backend-dispatching commands must explicitly set the backend in test context
**Recommendation:** TRIPWIRE - Silent wrong-path routing is HIGH severity

### 3. GlobalConfig Constructor Call Sites

**What happened:** After adding required field, many tests failed with constructor errors
**Root cause:** 7+ test files had `GlobalConfig()` calls that needed the new `plan_backend` parameter
**Prevention:** Use Grep to find ALL `GlobalConfig(` constructor calls before running tests
**Recommendation:** TRIPWIRE - The 4-place update pattern needs systematic documentation

### 4. JSON stdin Control Character Errors

**What happened:** `erk exec resolve-review-threads` failed with "Invalid control character" JSON parse error
**Root cause:** Newlines in comment field when using `echo` to pipe JSON
**Prevention:** Use heredoc file pattern for multi-line JSON: `cat > /tmp/file.json << 'EOF'`
**Recommendation:** ADD_TO_DOC - Medium severity, workaround is straightforward

### 5. Edit Without Read

**What happened:** Edit tool error "File has not been read yet"
**Root cause:** Attempted to edit files without reading them first in session
**Prevention:** When grep reveals files to edit, read all of them in parallel BEFORE any edits
**Recommendation:** CONTEXT_ONLY - Low severity, tool enforces the pattern

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Backend Dispatcher Test Context Requirement

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before testing commands that dispatch to multiple backends (plan_save, implement_shared, etc.)
**Warning:** ALWAYS set plan_backend explicitly in test context (via context_for_test(plan_backend="...")) to avoid silent routing to wrong code path
**Target doc:** `docs/learned/testing/tripwires.md`

This is tripwire-worthy because the failure mode is silent - tests pass but exercise the wrong code path. The KeyError discovered in session add78f25 was only caught because the output structure differed between backends. A less obvious difference could have gone undetected.

### 2. Environment Variable Isolation in CliRunner

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before writing tests that use CliRunner with GlobalConfig values in three-tier resolution
**Warning:** ALWAYS use env_overrides in erk_isolated_fs_env() or monkeypatch.delenv() to prevent ambient environment variables from overriding test config values
**Target doc:** `docs/learned/testing/tripwires.md`

This is tripwire-worthy because it caused 6 test failures and the root cause was non-obvious (tests worked locally for developers without ERK_PLAN_BACKEND set). The three-tier resolution priority means env vars always win, even over carefully configured test values.

### 3. GlobalConfig Field Addition 4-Place Update

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before adding new field to GlobalConfig dataclass
**Warning:** MUST update 4 places: (1) dataclass definition, (2) .test() factory, (3) load_config(), (4) save_config(). Use Grep to find ALL GlobalConfig() constructor calls in tests.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because missing any of the 4 places causes subtle bugs. PR #7722 required updating 7+ test files, and forgetting the test factory would cause all tests to fail.

### 4. PlanBackendType Canonical Import Location

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** Before importing PlanBackendType from any module
**Warning:** ALWAYS import from erk_shared.context.types (canonical location). Never re-export or duplicate type definition.
**Target doc:** `docs/learned/architecture/tripwires.md`

This tripwire prevents the type from being accidentally re-introduced in the wrong location, which happened during the original implementation before consolidation.

### 5. get_plan_backend() Global Config Parameter

**Score:** 4/10 (Cross-cutting +2, External tool quirk +2)
**Trigger:** Before calling get_plan_backend() from CLI commands or hooks
**Warning:** ALWAYS pass global_config parameter when available: get_plan_backend(ctx.global_config). This enables config-based resolution.
**Target doc:** `docs/learned/planning/tripwires.md`

Without the parameter, the function only considers env var and default, skipping the config tier entirely. This is a behavioral change that needs consistent application.

### 6. Test Data Must Match Configured Backend

**Score:** 4/10 (Non-obvious +2, Silent failure +2)
**Trigger:** Before writing test data for backend-aware tests
**Warning:** MUST ensure test data matches backend type (draft PR needs branch_name + metadata, issue-based needs erk-plan label)
**Target doc:** `docs/learned/testing/tripwires.md`

This prevents the KeyError scenario where test data was structured for one backend but the test context routed to another.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. JSON stdin Control Character Errors

**Score:** 3/10 (Non-obvious +1, External tool quirk +2)
**Notes:** The heredoc file pattern is straightforward once known. May warrant promotion if this error recurs across multiple implementations.

### 2. Frozen Dataclass Field Addition Requires Factory Update

**Score:** 3/10 (Cross-cutting +1, Repeated pattern +2)
**Notes:** Part of the 4-place pattern, but could be split out for dataclass-specific guidance.

### 3. Bot Review False Positives

**Score:** 2/10 (Repeated pattern +2)
**Notes:** More of an awareness item than a tripwire. PR #7722 had 4 duplicate threads but all were identifiable from timestamps.

### 4. Config Minimalism (Don't Write Defaults)

**Score:** 2/10 (Non-obvious +2)
**Notes:** Already documented in schema-driven-config.md, but could be promoted if agents frequently write defaults to config.

### 5. Three-Tier Resolution Priority

**Score:** 3/10 (Non-obvious +1, Cross-cutting +2)
**Notes:** Covered by the CliRunner isolation tripwire, but the concept of "env var always wins" deserves explicit callout.

## Code Changes (SHOULD_BE_CODE Items)

### 1. Nested Ternary Extraction

**Location:** dignified-python skill
**Action:** CODE_CHANGE
**Description:** Add specific before/after example showing nested ternary in function argument extracted to intermediate variable before call. The principle "clarity over brevity" is documented, but a concrete example would reinforce the pattern for bot reviewers.

### 2. DRY for Repeated Function Calls

**Location:** dignified-python skill OR `docs/learned/architecture/dignified-python-core.md`
**Action:** CODE_CHANGE (borderline)
**Description:** Document pattern: when same deterministic function call appears multiple times in same scope with same arguments, extract to variable once. Example: repeated `get_plan_backend(ctx.global_config)` calls extracted to `plan_backend` variable.

### 3. Line Length Refactoring (Extract Variable)

**Location:** dignified-python skill
**Action:** SKIP (already documented)
**Description:** The pattern of extracting complex expressions to local variables before function calls is already covered by "clarity over brevity" and line length guidance.
