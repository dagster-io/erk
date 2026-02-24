# Documentation Plan: Add diagnostics for dispatch metadata failures and improve TUI feedback

## Context

This implementation addressed a significant user experience problem: when TUI dispatch operations partially succeeded (workflow dispatched but metadata not written), users saw generic success messages with no indication that something went wrong. The root cause was twofold: (1) helper functions like `maybe_update_plan_dispatch_metadata` had silent early-return guard clauses that returned without diagnostic output, and (2) TUI handlers only checked subprocess exit codes, which were 0 even when optional operations were skipped.

The solution introduced observable diagnostics at two layers. First, the helper functions now emit `user_output()` warnings before each early return, explaining why the operation was skipped (no plan found, missing node_id, missing plan-header block). Second, the TUI dispatch handlers now inspect subprocess stderr for the "Updated dispatch metadata" marker and conditionally append "(metadata not updated)" to toast messages when the marker is absent.

Future agents working on subprocess-callable helpers or TUI dispatch handlers need to understand these patterns. Silent failures in fail-open code paths create debugging nightmares when operations appear successful but data isn't written. The patterns established here provide a template for observable fail-open behavior throughout the codebase.

## Raw Materials

PR #8078: https://github.com/dagster-io/erk/pull/8078

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 6     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. Silent early-return guard clauses require diagnostics

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8078]

**Draft Content:**

```markdown
## Silent Guard Clauses in Subprocess-Callable Functions

When functions with multiple guard clauses are called from subprocess contexts (TUI dispatch, CLI commands), silent early returns create invisible failures. The parent process sees exit code 0 but has no way to know which operations were skipped.

**Pattern**: Every guard clause in a subprocess-callable function MUST emit diagnostic output before returning.

**Example locations**: See `src/erk/cli/commands/pr/metadata_helpers.py` for the `maybe_update_plan_dispatch_metadata` and `maybe_write_pending_dispatch_metadata` functions, which demonstrate this pattern with `user_output()` calls before each early return.

**Why it matters**: TUI toast messages show "Success" when exit code is 0, even if critical metadata operations were silently skipped. Diagnostic output makes failures observable.
```

---

#### 2. TUI subprocess stderr inspection for operational feedback

**Location:** `docs/learned/tui/tripwires.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8078]

**Draft Content:**

```markdown
## TUI Subprocess Feedback via Stderr Markers

When TUI handlers dispatch subprocesses that perform optional operations, exit code 0 doesn't distinguish between "complete success" and "partial success with some operations skipped."

**Pattern**: TUI dispatch handlers MUST inspect subprocess stderr for operation-specific success markers. Conditionally modify toast messages based on marker presence.

**Example locations**: See `src/erk/tui/app.py` for `_address_remote_async` and `_fix_conflicts_remote_async` methods, which check for "Updated dispatch metadata" in stderr and append "(metadata not updated)" suffix when absent.

**Marker convention**: Use descriptive, grep-able markers like "Updated dispatch metadata" that subprocess-callable helpers emit alongside their diagnostic output.
```

---

### MEDIUM Priority

#### 3. Comprehensive test coverage for guard clause early returns

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8078]

**Draft Content:**

```markdown
## Testing Functions with Multiple Guard Clauses

Functions with multiple early-return guards require comprehensive test coverage. Each guard clause needs a dedicated test proving it emits correct diagnostic output.

**Test organization pattern**:
- 1 test per guard clause (verifying diagnostic warning is emitted)
- 1 happy path test (verifying successful operation when all guards pass)

**Example**: See `tests/unit/cli/commands/pr/test_metadata_helpers.py` for the `maybe_update_plan_dispatch_metadata` tests, which cover 3 guard clauses (non-plan branch, missing node_id, missing plan-header) plus 1 happy path.

**Helper fakes for None returns**: When testing Optional return paths, default fake gateways generate values. Create custom subclasses that override specific methods to return None. Example: `_FakeGitHubNoNodeId` in the test file overrides `get_workflow_run_node_id()` to return None.
```

---

#### 4. YAML serialization testing pattern

**Location:** `docs/learned/testing/yaml-testing.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: YAML Serialization Testing
read-when: writing tests for YAML-serialized output, debugging test assertions on metadata blocks
tripwires: 3
---

# YAML Serialization Testing

## Verify Before Asserting

When writing tests for YAML-serialized data, verify actual `yaml.safe_dump()` behavior before writing assertions. YAML quoting rules are not intuitive.

**Key insight**: YAML doesn't quote valid identifiers. For example, `run-42` renders as `run-42`, not `'run-42'`.

**Verification pattern**: Before writing test assertions, run a quick verification:

```bash
uv run python -c "import yaml; print(yaml.safe_dump({'key': 'run-42'}))"
```

## Common Pitfalls

- Assuming all string values are quoted (they're not)
- Assuming numeric-looking strings like `123` are quoted (they become integers)
- Assuming strings with hyphens are quoted (they're valid YAML identifiers)

## Flexible Assertions

When format details are immaterial, use flexible assertions:

```python
assert "run-42" in output  # Not: assert "'run-42'" in output
```
```

---

### LOW Priority

#### 5. TUI subprocess feedback pattern documentation

**Location:** `docs/learned/tui/subprocess-feedback.md`
**Action:** CREATE
**Source:** [PR #8078]

**Draft Content:**

```markdown
---
title: TUI Subprocess Feedback Coordination
read-when: implementing TUI handlers that dispatch subprocesses, coordinating CLI and TUI feedback
tripwires: 5
---

# TUI Subprocess Feedback Coordination

## The Problem

TUI dispatch handlers receive subprocess exit codes and stdio, but exit code 0 can mean both "complete success" and "partial success with some operations skipped." Users deserve accurate feedback.

## The Solution

Coordinate between CLI helpers and TUI handlers using stderr markers.

### CLI Helper Side

Emit descriptive markers to stderr alongside diagnostic output:

See `src/erk/cli/commands/pr/metadata_helpers.py` for implementation of `user_output()` calls that emit markers before early returns.

### TUI Handler Side

Inspect stderr for markers and conditionally modify feedback:

See `src/erk/tui/app.py` for `_address_remote_async` and `_fix_conflicts_remote_async` implementations that check for "Updated dispatch metadata" marker.

## Marker Design

- Use descriptive, grep-able text: "Updated dispatch metadata"
- Emit markers alongside user-visible diagnostics (not instead of)
- Keep markers stable; TUI code depends on exact text match
```

---

#### 6. FakeGateway customization for None returns

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## FakeGateway Customization for Optional Returns

Default fake gateway implementations (e.g., `FakeGitHub`) generate values for all methods. This prevents testing code paths where gateway methods return None.

**Pattern**: Create custom subclasses that override specific methods to return None:

See `tests/unit/cli/commands/pr/test_metadata_helpers.py` for `_FakeGitHubNoNodeId`, which overrides `get_workflow_run_node_id()` to return None, enabling tests for the "missing node_id" guard clause.

**When to use**: When testing Optional return type error paths, and the default fake prevents reaching the code path you need to test.
```

---

## Contradiction Resolutions

No contradictions detected. The existing documentation checker found no conflicts between existing docs and the patterns in this implementation.

## Stale Documentation Cleanup

No stale documentation detected. All referenced files in existing docs were verified as existing.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Silent Operational Failures Appearing as Success

**What happened:** TUI showed "Dispatched" success message when subprocess exited 0, even though metadata update was silently skipped due to guard clause early returns.

**Root cause:** Guard clauses in `maybe_update_plan_dispatch_metadata` and `maybe_write_pending_dispatch_metadata` returned early without diagnostic output. TUI only checked exit codes.

**Prevention:** Always emit `user_output()` diagnostics before early returns in subprocess-callable functions. TUI handlers should inspect stderr for operation-specific markers.

**Recommendation:** TRIPWIRE - This pattern affects all subprocess-callable helpers across the codebase.

### 2. YAML Quoting Assumptions in Tests

**What happened:** Test asserted `'run-42'` (quoted) but YAML output was `run-42` (unquoted).

**Root cause:** Assumed YAML quotes all string values. YAML spec allows unquoted identifiers (strings that look like valid YAML scalars).

**Prevention:** Before writing assertions about serialized format output, verify actual serialization behavior with a quick CLI test: `uv run python -c "import yaml; print(yaml.safe_dump(...))"`.

**Recommendation:** NEW_DOC - Document the verification pattern in testing docs.

### 3. Fake Gateway Masking Error Paths

**What happened:** Couldn't reach the "node_id is None" code path because `FakeGitHub.get_workflow_run_node_id()` always returns a generated value.

**Root cause:** Default fake implementations generate values for all methods to make happy-path testing easy, but this prevents testing Optional return error paths.

**Prevention:** Create custom fake subclasses that override specific methods to return None when testing error paths.

**Recommendation:** UPDATE_EXISTING - Add note to testing tripwires about FakeGateway customization.

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Silent early-return guard clauses in subprocess-callable functions

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before adding early-return guard clauses to functions called from subprocess/TUI contexts
**Warning:** MUST emit user_output() diagnostic messages before each early return. Silent failures confuse users when parent process only checks exit codes. See src/erk/cli/commands/pr/metadata_helpers.py for reference implementation.
**Target doc:** `docs/learned/architecture/tripwires.md`

This tripwire is critical because the anti-pattern is tempting (guard clauses that just return are clean and simple) but the consequence is severe (users see success when operations fail). The pattern affects all subprocess-callable helpers, not just the metadata functions fixed in this PR.

### 2. TUI subprocess stderr inspection

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +1)
**Trigger:** Before implementing TUI handlers that dispatch subprocesses with optional operations
**Warning:** MUST inspect subprocess stderr for operation-specific success markers. Don't rely solely on exit codes for user feedback. Conditionally modify toast messages based on stderr content. See src/erk/tui/app.py for reference implementation.
**Target doc:** `docs/learned/tui/tripwires.md`

This tripwire addresses the TUI side of the subprocess feedback coordination problem. Without it, TUI handlers will show misleading success messages when optional operations are skipped.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. YAML serialization quoting assumptions

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)
**Notes:** Specific to testing scenarios where assertions check serialization format. The error is self-correcting (test fails, you investigate, you learn). May not need tripwire if test failures are caught early. However, if this pattern causes repeated debugging sessions, it should be promoted to tripwire status.

### 2. FakeGateway always returns values

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)
**Notes:** Already has some coverage in the fake-driven-testing skill documentation. The pattern is learnable after one encounter. May need tripwire promotion if agents repeatedly struggle to test Optional return error paths. Consider promoting if future sessions show repeated discovery of this issue.
