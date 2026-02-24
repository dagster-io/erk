# Documentation Plan: Fix address dispatch polling and stacked PR indicator display

## Context

This plan captures documentation opportunities from PR #8042, which fixed two related issues in the TUI: (1) the `address_remote` dispatch mechanism was not polling for real `run_id` values because it used `--no-wait`, and (2) the display was not refreshing after the operation completed. The fix removed the `--no-wait` flag and added an `action_refresh()` call after success, following the established pattern from `_close_plan_async`.

The implementation session was notable for its efficiency -- zero errors, zero user corrections, and 100% CI pass rate. The agent correctly identified and followed existing patterns, loaded appropriate skills proactively, and produced clean, well-tested code. This exemplary session provides valuable documentation material about TUI async patterns, subprocess testing, and the interaction between CLI flags and worker thread behavior.

Future agents working on TUI development will benefit from understanding these patterns: when to call `action_refresh()` after async operations, how to test TUI subprocess calls, and when `--no-wait` is appropriate in worker thread contexts. The tripwire candidates identified here will help prevent similar bugs in future TUI async implementations.

## Raw Materials

No gist URL provided

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 11    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score2-3) | 3     |

## Stale Documentation Cleanup

Existing docs with phantom references requiring immediate action:

### 1. Fix phantom reference in stacked-pr-indicator.md

**Location:** `docs/learned/tui/stacked-pr-indicator.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `RealPlanDataProvider._build_plan_row()` (method no longer exists)

**Cleanup Instructions:**

The document references a method `_build_plan_row()` that no longer exists. Based on code evolution, this was likely renamed to `_build_row_data()`. Update the reference to point to the correct method name. The core content about stacked PR indicators remains valid -- only the method reference needs correction.

## Documentation Items

### HIGH Priority

#### 1. Update pr-address-workflows.md with dispatch polling fix

**Location:** `docs/learned/erk/pr-address-workflows.md`
**Action:** UPDATE
**Source:** [PR #8042]

**Draft Content:**

```markdown
## TUI Dispatch Polling Pattern

When the TUI dispatches PR address operations, it no longer uses `--no-wait`. This change ensures:

1. **Real metadata capture**: The CLI polls until the workflow run_id is available (~5-30s)
2. **Accurate status display**: The dashboard shows real run_id and run_status instead of placeholders
3. **Non-blocking behavior**: Despite waiting, the UI remains responsive because dispatch runs in a `@work(thread=True)` worker

### Implementation Pattern

The `_address_remote_async` method:
- Removes `--no-wait` to allow polling for real run_id
- Calls `self.call_from_thread(self.action_refresh)` after success to update display
- Follows same pattern as `_close_plan_async`

See `src/erk/tui/app.py` for implementation details.
```

---

#### 2. Update stacked-pr-indicator.md with recent fixes

**Location:** `docs/learned/tui/stacked-pr-indicator.md`
**Action:** UPDATE
**Source:** [PR #8040], [PR #8042]

**Draft Content:**

```markdown
## Recent Evolution (February 2026)

### Pancake Emoji Restoration

PR #8040 temporarily removed the pancake emoji from stacked PR indicators. Commit 8a9884e27 immediately restored it, maintaining visual consistency with the established indicator design.

### Rocket Emoji Blocking Logic Fix

PR #8042 fixed a bug where the rocket emoji (dispatching indicator) could block the stacked PR pancake indicator from displaying. The fix replaced emoji-scanning logic with direct condition checks:

- **Before**: Scanned rendered text for emoji characters to decide blocking
- **After**: Uses direct boolean checks on state flags

This ensures both indicators can coexist when a stacked PR is being dispatched.

See `src/erk/tui/app.py` for the status column rendering logic.
```

---

#### 3. Add TUI async action refresh tripwire

**Location:** `docs/learned/tui/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Async Action Refresh Pattern

**Trigger:** Before implementing a TUI async action with `@work(thread=True)` that mutates remote state

**Warning:** After success toast, add `self.call_from_thread(self.action_refresh)` to pick up state changes. Pattern: see `_close_plan_async` and `_address_remote_async`.

**Rationale:** Worker threads don't automatically trigger UI updates. The `action_refresh()` call ensures the dashboard re-fetches data and displays updated state (run_id, run_status, etc.). Without this call, the TUI will appear to succeed but won't show the new state until manual refresh.

**Implementation Pattern:**
1. Use `@work(thread=True)` decorator for background execution
2. Perform operation in try/except with explicit error handling
3. Call `self.call_from_thread(self.notify, ...)` for user feedback
4. Call `self.call_from_thread(self.action_refresh)` AFTER success only
5. Do NOT refresh on error path (avoids unnecessary network calls)

See `src/erk/tui/app.py` for reference implementations in `_close_plan_async` and `_address_remote_async`.
```

---

### MEDIUM Priority

#### 4. Create TUI subprocess testing pattern doc

**Location:** `docs/learned/testing/tui-subprocess-testing.md`
**Action:** CREATE
**Source:** [PR #8042]

**Draft Content:**

```markdown
---
read-when:
  - writing tests for TUI code that calls subprocess
  - testing fire-and-forget async operations
  - verifying subprocess arguments in TUI tests
---

# TUI Subprocess Testing (Layer 4)

TUI code often calls `subprocess.run` directly for fire-and-forget operations. This document covers testing patterns for these scenarios.

## Context

Unlike gateway methods which are tested via fakes, TUI subprocess calls need explicit monkeypatching to verify behavior without spawning real processes.

## Pattern: Monkeypatch subprocess.run

When testing async methods that call subprocess directly:

1. **Capture arguments**: Monkeypatch `subprocess.run` with a fake that captures args
2. **Control return code**: Return controlled `CompletedProcess` result
3. **Verify args**: Assert expected arguments are passed (and unexpected args are NOT passed)
4. **Test refresh behavior**: Use `provider.fetch_count` to verify data refresh was triggered
5. **Test error path**: Verify no refresh occurs on subprocess failure

## Refresh Verification

To verify `action_refresh()` was called after an async operation:

```
count_before = provider.fetch_count
# ... perform async operation ...
await pilot.pause(0.3)  # Allow operation to complete
assert provider.fetch_count > count_before
```

This tests the actual behavior (data refresh) rather than mocking `action_refresh()` directly.

## Reference

See `tests/tui/test_app.py` for the `TestAddressRemoteAsync` class demonstrating this pattern.

## Tripwires

- When testing TUI subprocess calls, use monkeypatch (not gateway fakes)
- Verify refresh via `fetch_count`, not by mocking `action_refresh`
- Test both success (with refresh) and error (no refresh) paths
```

---

#### 5. Document bot review lifecycle

**Location:** `docs/learned/ci/github-actions-review-bots.md`
**Action:** CREATE
**Source:** [PR #8042]

**Draft Content:**

```markdown
---
read-when:
  - understanding automated code review comments
  - addressing bot-generated PR feedback
  - configuring review bot behavior
---

# GitHub Actions Review Bots

Four automated review bots comment on PRs to enforce code quality standards.

## Bot Names

1. **Dignified Code Simplifier**: Simplification suggestions
2. **Dignified Python Review**: Python style violations (import aliases, etc.)
3. **Test Coverage Review**: Missing test coverage for modified methods
4. **Tripwires Review**: Pattern violations against documented tripwires

## Bot Comment Lifecycle

1. **Initial review**: Bot posts review comment threads identifying violations
2. **Agent addresses**: Human or AI addresses the violations
3. **Follow-up comment**: Bot posts discussion comment confirming resolution
4. **Thread closed**: Thread is resolved via `erk exec resolve-review-threads`

## Important Distinctions

- **Initial review comments**: Actionable, require code changes
- **Follow-up discussion comments**: Informational, confirm resolution
- The pr-feedback-classifier correctly distinguishes these

## Interaction Model

Bots cite specific documentation when validating exceptions:
- Example: "subprocess-wrappers.md lines 108-129 (Graceful Degradation Pattern)"
- This helps contributors understand why certain patterns are allowed

## Activity Log Format

Bot comments include timestamps in Pacific Time for tracking review iteration timing.
```

---

#### 6. Document test coverage expectations

**Location:** `docs/learned/testing/test-coverage-expectations.md`
**Action:** CREATE
**Source:** [PR #8042]

**Draft Content:**

```markdown
---
read-when:
  - addressing test coverage review comments
  - understanding test granularity requirements
  - writing tests for modified methods
---

# Test Coverage Expectations

The Test Coverage Review bot enforces test coverage for modified source methods.

## Requirements

When modifying a method in `src/`:

1. **Behavioral coverage**: Tests must cover the modification's behavior
2. **Success path**: Test the happy path completes correctly
3. **Error path**: Test error handling behavior
4. **Layer-appropriate**: Use correct test layer (Layer 4 for TUI, Layer 5 for CLI)

## Coverage Mapping

The bot tracks test-to-source modification mapping at line-level granularity. Each modified line should have corresponding test coverage.

## Remediation

When flagged for missing coverage:

1. Identify what behavior changed in the source modification
2. Write tests covering that specific behavior
3. Include both positive and negative test cases
4. Run tests to verify they exercise the modified code

## Reference

See `tests/tui/test_app.py:TestAddressRemoteAsync` for an example of comprehensive coverage for a method modification.
```

---

#### 7. Document inline test import exception

**Location:** `docs/learned/conventions.md`
**Action:** UPDATE
**Source:** [PR #8042]

**Draft Content:**

```markdown
## Test Import Exceptions

**General rule:** No inline imports (move to top of file)

**Exception:** Monkeypatching in tests

When a test needs to monkeypatch a module, inline import is acceptable:

- Importing the module inside the test function ensures the monkeypatch applies correctly
- This is particularly relevant for `subprocess` module patching in TUI tests

This exception was validated by bot review during PR #8042.
```

---

#### 8. Document bot pattern exception enforcement

**Location:** `docs/learned/ci/tripwires-review.md`
**Action:** CREATE
**Source:** [PR #8042]

**Draft Content:**

```markdown
---
read-when:
  - understanding why tripwires review passed or failed
  - adding new pattern exceptions
  - citing documentation in code
---

# Tripwires Review Bot

The Tripwires Review bot validates code against documented patterns and their exceptions.

## How It Works

1. Bot scans modified code for pattern matches
2. Checks if pattern has documented exception
3. Cites specific documentation lines when validating exceptions

## Example

When reviewing TUI subprocess calls, the bot may cite:
- "subprocess-wrappers.md lines 108-129 (Graceful Degradation Pattern)"
- This indicates the code matches an allowed exception

## Adding New Exceptions

To add a pattern exception:

1. Document the exception in the appropriate tripwires file
2. Include clear criteria for when the exception applies
3. The bot will automatically recognize the exception on future reviews

## Graceful Degradation Pattern

TUI subprocess calls use "graceful degradation" -- errors show toast notifications rather than crashing the app. This is an exception to the normal subprocess wrapper requirements.

See `docs/learned/architecture/subprocess-wrappers.md` for the complete pattern definition.
```

---

### LOW Priority

#### 9. Document --no-wait removal in worker threads as tripwire

**Location:** `docs/learned/tui/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Worker Thread CLI Flags

**Trigger:** Before adding `--no-wait` to a CLI command in a TUI `@work(thread=True)` method

**Warning:** Question whether `--no-wait` is needed. In `@work(thread=True)` contexts, the wait doesn't block the UI, so omitting `--no-wait` enables accurate `run_id`/status capture.

**Rationale:** Worker threads run in background, so blocking for real results (5-30s) doesn't freeze the UI. The trade-off:

- **With `--no-wait`**: Immediate return, but metadata (run_id, node_id) may be placeholders
- **Without `--no-wait`**: Brief wait (~5-30s), but accurate metadata captured

**When to keep `--no-wait`**: Only when the caller explicitly needs immediate return and doesn't need real metadata.

**Important**: After removing `--no-wait`, MUST add `action_refresh()` call to display updated state.
```

---

#### 10. Add column width evolution note

**Location:** `docs/learned/tui/dashboard-columns.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - modifying TUI dashboard column widths
  - adding new visual indicators to status column
  - balancing information density with visual clarity
---

# Dashboard Column Width Evolution

The status column has evolved through several widths as visual indicators were added and removed.

## History

- **4 characters**: Minimal indicators
- **7 characters**: Expanded for multiple emoji indicators
- **4 characters**: Reduced after consolidation

## Trade-offs

- **Wider columns**: More information, but less space for other columns
- **Narrower columns**: Cleaner appearance, but may require indicator consolidation

## Pancake Indicator

The stacked PR pancake indicator was briefly removed (PR #8040) then restored (commit 8a9884e27). Changes to column width should consider impact on established visual indicators.
```

---

#### 11. Provider fetch_count belongs in code

**Location:** N/A (code comment)
**Action:** CODE_CHANGE
**Source:** [PR #8042]

**Code Change:**

Add a docstring or comment in `tests/fakes/plan_data_provider.py` explaining that `fetch_count` is used for testing data refresh behavior. This is a testing implementation detail that belongs in code documentation, not in learned docs.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. TUI State Not Refreshing After Background Operations

**What happened:** The TUI showed "Success!" toast but the dashboard didn't update with new run_id/status
**Root cause:** Missing `action_refresh()` call after async operations complete
**Prevention:** Always call `self.call_from_thread(self.action_refresh)` after successful background operations in `@work(thread=True)` methods
**Recommendation:** TRIPWIRE (captured in HIGH priority item #3)

### 2. Missing Metadata from CLI Dispatches

**What happened:** run_id and node_id columns showed placeholder values instead of real IDs
**Root cause:** Using `--no-wait` flag causes CLI to return before metadata is available
**Prevention:** In TUI worker thread contexts, avoid `--no-wait` unless immediate return is explicitly required
**Recommendation:** TRIPWIRE (captured in LOW priority item #9)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. TUI Async Action Refresh Pattern

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** Before implementing a TUI async action with `@work(thread=True)` that mutates remote state
**Warning:** After success toast, add `self.call_from_thread(self.action_refresh)` to pick up state changes. Pattern: see `_close_plan_async` and `_address_remote_async`.
**Target doc:** `docs/learned/tui/tripwires.md`

This pattern is non-obvious because the success toast provides immediate feedback, making it seem like the operation is complete. However, without the refresh call, the dashboard data won't update until the next manual refresh. The pattern applies to all TUI async actions that modify remote state, making it cross-cutting. It's already implemented in multiple places (`_close_plan_async`, `_address_remote_async`), demonstrating it's a repeated pattern.

### 2. Missing Test Coverage for Modified Methods

**Score:** 4/10 (criteria: Non-obvious +2, Cross-cutting +2)
**Trigger:** After modifying a method in src/ without corresponding test changes
**Warning:** Test Coverage Review bot will flag this. Add Layer-appropriate tests covering behavioral changes, success paths, and error paths.
**Target doc:** `docs/learned/testing/tripwires.md`

While the bot enforces this automatically, documenting it as a tripwire helps agents proactively add tests rather than waiting for bot feedback. This saves review iterations.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. --no-wait in Worker Threads

**Score:** 3/10 (criteria: Non-obvious +2, External tool quirk +1)
**Notes:** Specific to TUI context; broader `--no-wait` usage is documented elsewhere. May warrant promotion if more cases arise where incorrect `--no-wait` usage causes metadata loss.

### 2. Inline Test Import Exception

**Score:** 2/10 (criteria: Non-obvious +2)
**Notes:** Bot approved the exception during PR #8042 review, but it's not explicitly documented. Could prevent confusion when agents see "no inline imports" rule but need to use inline imports for monkeypatching.

### 3. Bot Pattern Exception Citing

**Score:** 2/10 (criteria: External tool quirk +1, Non-obvious +1)
**Notes:** Understanding how bots cite documentation is helpful but not a "mistake" to prevent. More informational than tripwire-worthy.

## Cross-File Dependencies

When implementing these documentation updates:

1. **TUI async action refresh tripwire**: Reference `_close_plan_async` and `_address_remote_async` in `src/erk/tui/app.py`

2. **TUI subprocess testing doc**: Reference `TestAddressRemoteAsync` in `tests/tui/test_app.py`

3. **Bot review lifecycle doc**: Link to `docs/learned/python/dignified-python-core.md` (import alias rule) and `docs/learned/architecture/subprocess-wrappers.md` (graceful degradation)

4. **Stacked PR indicator update**: Fix phantom reference before adding new sections

## Implementation Recommendations

### Sequencing

**Phase 1 (Immediate):**
- Fix stale reference in stacked-pr-indicator.md
- Quick fix, prevents propagation of incorrect method name

**Phase 2 (High Impact):**
- Update pr-address-workflows.md with dispatch polling fix
- Update stacked-pr-indicator.md with recent evolution
- Add TUI async action refresh tripwire

**Phase 3 (New Content):**
- Create tui-subprocess-testing.md
- Create github-actions-review-bots.md
- Create test-coverage-expectations.md

**Phase 4 (Polish):**
- Add column width documentation
- Update conventions.md with inline test import exception
- Create tripwires-review.md

### Quality Checkpoints

Before marking documentation complete:

1. **Verify code references**: All file paths and function names resolve correctly
2. **Cross-link**: Ensure new docs link to related existing docs
3. **Add tripwires**: Each doc includes "When to read" and tripwire sections
4. **Test coverage**: Reference test files that verify documented behavior
5. **Run `erk docs sync`**: Update auto-generated indices
