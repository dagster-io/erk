# Documentation Plan: Fix ci-update-pr-body plan-header metadata preservation on draft PR plans

## Context

This plan addresses documentation gaps from PR #7815, which fixed a bug where draft-PR plan metadata was lost during CI execution. The bug's root cause was a fundamental mismatch between CI cleanup timing and script expectations: the `ci-update-pr-body` script ran after a `git reset --hard` cleanup step that wiped the `.impl/` directory, making disk-based detection of draft-PR plans impossible.

The fix represents an important architectural shift from **implicit detection** (reading filesystem state, parsing PR body) to **explicit parameter passing** (workflow passes `--draft-pr` flag based on its `plan_backend` input). This pattern is reusable across CI exec scripts and addresses a class of reliability issues where disk state doesn't survive between workflow steps.

Key insights worth documenting include: the CI cleanup timing that wipes untracked directories, the workflow-to-script communication pattern using CLI flags, metadata block format requirements (which caused test failures during development), and the process of investigating root causes when initial fixes treat symptoms.

## Raw Materials

PR: #7815

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 9 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score>=4) | 4 |
| Potential tripwires (score 2-3) | 2 |

## Documentation Items

### HIGH Priority

#### 1. Workflow State Passing to CI Exec Scripts

**Location:** `docs/learned/ci/workflow-state-passing.md`
**Action:** CREATE
**Source:** [Impl], [PR #7815]

**Draft Content:**

```markdown
---
read-when:
  - adding exec scripts called from GitHub Actions
  - debugging CI exec script state issues
  - implementing detection logic in CI contexts
tripwires: 1
---

# Workflow State Passing to CI Exec Scripts

## Problem

When GitHub Actions workflows call erk exec scripts, the workflow often already knows state information (e.g., `plan_backend: "draft_pr"`) but scripts may attempt to detect this state from disk files or API responses. This creates fragility when:

1. Disk files are cleaned up between workflow steps (`git reset --hard`)
2. API responses may not contain the expected metadata
3. Detection logic duplicates knowledge the workflow already has

## Solution Pattern

**Pass workflow-known state explicitly via CLI flags.**

When a workflow receives state as inputs (`plan_backend`, `session_id`, etc.) and a script needs to branch behavior based on that state, add a CLI flag and pass it from the workflow.

### Example: ci-update-pr-body --draft-pr flag (PR #7815)

**Before:** Script detected draft-PR plans by reading `.impl/plan-ref.json`
**Problem:** File wiped by cleanup step, causing metadata loss
**After:** Workflow passes `--draft-pr` flag based on `inputs.plan_backend`

See `src/erk/cli/commands/exec/scripts/ci_update_pr_body.py` for implementation.
See `.github/workflows/plan-implement.yml` for workflow integration (grep for `--draft-pr`).

## When to Use

- Workflow receives state as inputs that script needs
- Script would otherwise detect state from disk artifacts
- Disk-based detection would be fragile (files cleaned up between steps)

## When NOT to Use

- State is not available to workflow (must be detected from git/API)
- Detection is equally reliable (no cleanup between detection and use)

## Related

- [PR Body Assembly](../architecture/pr-body-assembly.md) - Metadata preservation pattern
- [Draft PR Lifecycle](../planning/draft-pr-lifecycle.md) - Metadata lifecycle touchpoints
```

---

#### 2. CI Tripwires: Git Reset Cleanup and State Passing

**Location:** `docs/learned/ci/tripwires.md`
**Action:** UPDATE
**Source:** [Impl], [PR #7815]

**Draft Content:**

Add these four tripwires to the existing CI tripwires file:

```markdown
## `.impl/` Directory Unavailable After CI Cleanup

Before reading `.impl/` directory in CI exec scripts, verify the directory survives cleanup steps.

**Why:** The `plan-implement.yml` workflow runs `git reset --hard` in its cleanup step, which wipes all untracked files including `.impl/`. Scripts running after cleanup cannot access `.impl/` contents.

**Instead:** Pass state explicitly via CLI flags from workflow inputs.

**Source:** PR #7815 - `ci-update-pr-body` script failed to detect draft-PR plans because `.impl/plan-ref.json` was wiped before the script ran.

## Workflow Input Propagation Pattern

Before implementing file-based state detection in CI exec scripts, check if the workflow already has the information as an input.

**Why:** Workflows often receive state via inputs (e.g., `plan_backend`) that scripts then try to detect indirectly from disk or API. This creates fragile detection logic for information the workflow already has.

**Instead:** Add CLI flags and pass workflow inputs explicitly to scripts.

**Example:** `plan-implement.yml` has `inputs.plan_backend` - pass `--draft-pr` flag to `ci-update-pr-body` rather than having it read `.impl/plan-ref.json`.

## CI Cleanup Step Ordering

Before adding steps to `plan-implement.yml` after the cleanup step, understand what state is available.

**Cleanup sequence:**
1. Implementation commits and pushes changes
2. Cleanup runs `git reset --hard` (wipes `.impl/` untracked directory)
3. Cleanup removes `.worker-impl/` explicitly (tracked directory)
4. Steps after cleanup execute (e.g., `ci-update-pr-body`)

**Consequence:** Post-cleanup scripts cannot access `.impl/` or `.worker-impl/` disk state. Pass required state from workflow inputs.

## `.impl/` vs `.worker-impl/` Cleanup Behavior

Before relying on plan staging directories in CI, understand their cleanup behavior:

- **`.impl/`**: Untracked directory, wiped by `git reset --hard`
- **`.worker-impl/`**: Tracked directory, explicitly removed via `git rm -rf`

Both are unavailable after cleanup. Use workflow inputs to pass state to post-cleanup scripts.
```

---

#### 3. Metadata Block Format Reference

**Location:** `docs/learned/reference/metadata-blocks.md`
**Action:** CREATE
**Source:** [Impl], [PR #7815]

**Draft Content:**

```markdown
---
read-when:
  - writing tests for metadata block parsing
  - implementing code that reads plan-header or objective-header metadata
  - debugging "None returned" from find_metadata_block
tripwires: 1
---

# Metadata Block Format Reference

## Overview

Metadata blocks are HTML-comment-wrapped structures in GitHub issue/PR bodies that store machine-readable YAML data. Used in draft-PR plans and objectives.

## Format Requirements

### Required Structure

The parser requires this exact structure:

1. **Opening tag:** `<!-- erk:metadata-block:KEY -->`
2. **Details tag:** `<details>` or `<details open>`
3. **Summary tag:** `<summary>Human-readable title</summary>`
4. **YAML fence:** Triple-backtick yaml block with valid YAML
5. **Closing details:** `</details>`
6. **Closing tag:** `<!-- /erk:metadata-block -->`

### Valid Block Types (KEY values)

- `plan-header`: Plan stage, objective, status metadata
- `objective-header`: Objective status, progress metadata
- `turn-record`: Turn history for objectives

## Parser Behavior

`find_metadata_block(text: str, key: str) -> MetadataBlock | None`

Returns `None` (does NOT raise) when:
- HTML comments missing or malformed
- `<details>` tag missing
- `<summary>` tag missing
- YAML fence missing or malformed
- YAML content invalid

See `packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py` for implementation.

## Writing Tests

**Before inventing test data, grep existing tests for format examples:**

```bash
rg "erk:metadata-block" tests/
```

**Anti-pattern (causes silent parsing failure):**
```python
# WRONG - parser skips this, returns None
test_data = "<!-- erk:metadata-block:plan-header -->\nplain text\n<!-- /erk:metadata-block -->"
```

See existing tests in `tests/unit/cli/commands/exec/scripts/test_ci_update_pr_body.py` for correct format.
```

---

#### 4. Update pr-body-assembly.md with ci-update-pr-body Example

**Location:** `docs/learned/architecture/pr-body-assembly.md`
**Action:** UPDATE
**Source:** [PR #7815]

**Draft Content:**

Add after the existing metadata preservation tripwire section:

```markdown
## Example: ci-update-pr-body (PR #7815)

The `ci-update-pr-body` exec script demonstrates the metadata preservation pattern in CI context:

1. Script receives `--draft-pr` flag from workflow (based on `inputs.plan_backend`)
2. When flag is set, extracts `metadata_prefix` before building new body
3. Reassembles: `metadata_prefix + summary_body + original_plan_section`

**Key constraint:** Script runs after CI cleanup (`git reset --hard`) wipes `.impl/`. Cannot reconstruct metadata from disk - must extract from existing PR body and preserve through body regeneration.

See `src/erk/cli/commands/exec/scripts/ci_update_pr_body.py` for implementation.
```

---

### MEDIUM Priority

#### 5. Update draft-pr-lifecycle.md with CI Touchpoint

**Location:** `docs/learned/planning/draft-pr-lifecycle.md`
**Action:** UPDATE
**Source:** [PR #7815]

**Draft Content:**

Add to lifecycle stages section:

```markdown
## CI Lifecycle Touchpoint

**ci-update-pr-body** (runs after implementation in CI):
- Receives `--draft-pr` flag from workflow
- Cannot access `.impl/plan-ref.json` (wiped by cleanup)
- Extracts metadata from current PR body before regenerating
- Preserves metadata_prefix through body update

This is the final touchpoint where metadata must be preserved. The script has no access to `.impl/` state and relies entirely on workflow-provided flag and existing PR body content.
```

---

#### 6. Symptom vs Root Cause Investigation Pattern

**Location:** `docs/learned/architecture/symptom-vs-root-cause.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - implementing fallback detection mechanisms
  - user questions approach as potentially missing root cause
  - adding workarounds for missing data
---

# Symptom vs Root Cause Investigation

## When to Suspect Symptom Treatment

Red flags that suggest treating symptoms rather than root causes:
- Implementing "fallback detection" mechanisms
- User questions approach as potentially missing root cause
- Adding workarounds for missing data that should exist
- Parsing remote state to reconstruct local state

## Investigation Pattern

### Step 1: Acknowledge the concern

When user signals "we may not understand the full lifecycle," pause implementation.

### Step 2: Trace complete lifecycle

Don't just examine the immediate code path. Trace from origin:
1. Where does this knowledge originate? (workflow input, user input, git state)
2. How does it flow through the system? (files, env vars, API calls)
3. Where are we trying to detect it? (disk, API response, parsing)

### Step 3: Identify upstream knowledge

Often the information already exists upstream:
- Workflow receives it as input
- Calling code already computed it
- Earlier step in pipeline produced it

### Step 4: Propose explicit solution

Eliminate detection by passing knowledge explicitly:
- Add CLI flag receiving workflow input
- Add parameter to function call
- Add field to data structure

## Example: PR #7815 (ci-update-pr-body)

**Symptom fix attempted:** Parse PR body to detect draft-PR plan when `.impl/plan-ref.json` missing

**User challenge:** "we do not understand the full lifecycle here"

**Lifecycle trace:**
1. Workflow receives `inputs.plan_backend` ("draft_pr" or "github")
2. Implementation creates `.impl/plan-ref.json`
3. Cleanup runs `git reset --hard` (wipes `.impl/`)
4. `ci-update-pr-body` runs (no `.impl/` available)

**Discovery:** Workflow already has `plan_backend` input!

**Root cause fix:** Pass `--draft-pr` flag from workflow to script

## When Fallbacks Are Valid

Fallbacks are appropriate when:
- Information genuinely unavailable upstream
- Detection is equally reliable as explicit passing
- Backward compatibility requires it

Fallbacks are symptoms when:
- Upstream has the information but doesn't pass it
- Primary source fails due to our own cleanup/pipeline design
```

---

#### 7. Test Data Format Validation

**Location:** `docs/learned/testing/test-data-format-validation.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - writing tests for parsers or format validators
  - debugging "None returned" or "empty result" test failures
  - working with metadata blocks, YAML, or structured formats
tripwires: 1
---

# Test Data Format Validation

## Problem

When writing tests for parsers (metadata blocks, JSON schemas, YAML configs), agents may invent test data without understanding format requirements. Parsers with lenient error handling (skip invalid, return None) fail silently, causing confusing test failures.

## Prevention Pattern

**Before inventing test data, grep existing tests for format examples.**

### Example: Metadata Block Format (PR #7815 implementation)

**What happened:**
1. Agent wrote test for `find_metadata_block` parser
2. Invented test data: plain text inside HTML comments
3. Parser silently skipped invalid format, returned None
4. Test failed with "expected metadata but got None"

**What agent should have done:**
```bash
rg "find_metadata_block" tests/
rg "erk:metadata-block" tests/
```

## When to Apply

- Writing tests for any parser or format validator
- Test fails with "None returned" or "empty result"
- Working with structured formats (HTML, YAML, JSON)

## Why This Matters

Lenient parsers (common in erk codebase) skip invalid input without raising errors. Inventing format without reference causes silent parsing failure and wasted debugging time.

**Severity:** MEDIUM - doesn't cause production bugs (test fails before merge), but wastes 10-30 minutes debugging.
```

---

### LOW Priority

No LOW priority items - all actionable items are HIGH or MEDIUM.

## Contradiction Resolutions

No contradictions found. Existing documentation is consistent across:
- `docs/learned/architecture/pr-body-assembly.md` (metadata_prefix requirement)
- `docs/learned/planning/draft-pr-lifecycle.md` (metadata preservation lifecycle)
- `docs/learned/ci/exec-script-environment-requirements.md` (ci-update-pr-body environment)

All referenced files verified to exist in codebase. No phantom references detected.

## Stale Documentation Cleanup

No stale documentation detected. All referenced source files verified to exist:
- `src/erk/cli/commands/pr/shared.py`
- `src/erk/cli/commands/exec/scripts/ci_update_pr_body.py`
- `packages/erk-shared/src/erk_shared/plan_store/draft_pr_lifecycle.py`

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Metadata Block Format Mismatch

**What happened:** Agent wrote test with plain text metadata block body instead of required `<details>/<summary>/YAML` structure. Parser silently returned None, causing confusing test failure.

**Root cause:** Agent invented test data format without consulting existing tests or format specification.

**Prevention:** Before writing tests for parsers, grep existing tests for format examples: `rg "erk:metadata-block" tests/`

**Recommendation:** ADD_TO_DOC (documented in test-data-format-validation.md)

### 2. Disk-Based Detection After CI Cleanup

**What happened:** Initial fix attempted to read `.impl/plan-ref.json` to detect draft-PR plans, but file was wiped by `git reset --hard` cleanup before script ran.

**Root cause:** Lack of understanding of CI cleanup lifecycle and workflow step ordering.

**Prevention:** Before relying on `.impl/` or other untracked directories in CI exec scripts, trace the full CI workflow to ensure directories survive cleanup steps.

**Recommendation:** TRIPWIRE (documented in ci/tripwires.md)

### 3. Fallback Detection Treating Symptoms

**What happened:** After disk detection failed, agent proposed parsing PR body metadata as fallback. User correctly identified this as treating a symptom.

**Root cause:** Not tracing complete lifecycle to discover workflow already had the information as input.

**Prevention:** When adding fallback detection, investigate whether upstream has the information to pass explicitly.

**Recommendation:** ADD_TO_DOC (documented in symptom-vs-root-cause.md)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Git Reset Cleanup Wipes `.impl/` Directory

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before reading `.impl/` directory in CI exec scripts
**Warning:** `git reset --hard` in plan-implement.yml cleanup wipes all untracked files including `.impl/`. Scripts running after cleanup cannot access `.impl/` contents. Pass state explicitly via CLI flags from workflow inputs instead.
**Target doc:** `docs/learned/ci/tripwires.md`

This is tripwire-worthy because the failure is silent (script just doesn't find the file) and affects any CI script relying on `.impl/` state. Multiple future scripts could hit this issue.

### 2. Workflow Input Propagation Pattern

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, External tool quirk +1)
**Trigger:** Before implementing file-based state detection in CI exec scripts
**Warning:** Check if the workflow already has the information as an input (e.g., `plan_backend`). Pass it explicitly via CLI flag instead of detecting from disk artifacts that may be cleaned up between steps.
**Target doc:** `docs/learned/ci/tripwires.md`

This pattern applies to any exec script called from workflows that receive state as inputs. Prevents fragile detection logic.

### 3. CI Cleanup Step Ordering

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before adding steps to plan-implement.yml after cleanup
**Warning:** The cleanup step runs `git reset --hard` which wipes `.impl/` (untracked). Steps after cleanup must not rely on `.impl/` disk state. Pass required state explicitly from workflow inputs.
**Target doc:** `docs/learned/ci/tripwires.md`

Understanding the workflow step sequence is critical for any CI work on plan-implement.yml.

### 4. `.impl/` vs `.worker-impl/` Cleanup Behavior

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before relying on plan staging directories in CI
**Warning:** `.impl/` is untracked and wiped by `git reset --hard`. `.worker-impl/` is tracked and explicitly removed. Both are unavailable after cleanup. Use workflow inputs to pass state to post-cleanup scripts.
**Target doc:** `docs/learned/ci/tripwires.md`

The distinction between tracked and untracked cleanup behavior is subtle but important.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Metadata Block Format Requirements

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)
**Notes:** Parser silently skips invalid format, causing confusing test failures. Currently documented as a reference doc with a tripwire in testing docs. May elevate to stronger tripwire if pattern recurs in multiple sessions.

### 2. Test Fixture Format Exploration

**Score:** 2/10 (criteria: Non-obvious +2)
**Notes:** Time-waste rather than critical error. Documented in test-data-format-validation.md. Not severe enough for standalone tripwire - better as testing best practice.

## Implementation Order

1. **HIGH Priority Tripwires** (immediate prevention value)
   - Update `docs/learned/ci/tripwires.md` with 4 new CI tripwires
   - Create `docs/learned/reference/metadata-blocks.md`

2. **HIGH Priority New Docs** (captures core pattern from PR)
   - Create `docs/learned/ci/workflow-state-passing.md`
   - Update `docs/learned/architecture/pr-body-assembly.md`

3. **MEDIUM Priority Updates** (extends existing docs)
   - Update `docs/learned/planning/draft-pr-lifecycle.md`

4. **MEDIUM Priority New Docs** (process improvements)
   - Create `docs/learned/architecture/symptom-vs-root-cause.md`
   - Create `docs/learned/testing/test-data-format-validation.md`

## Attribution

All documentation should reference:
- **Sessions:** 2b2655c6, c4ab72f2-part1, c4ab72f2-part2
- **PR:** #7815
- **Plan:** "Fix ci-update-pr-body plan-header metadata preservation on draft PR plans"
