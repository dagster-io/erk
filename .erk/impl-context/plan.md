# Documentation Plan: Enhance objective view to display parallel in-flight status and multiple unblocked nodes

## Context

This implementation enhanced the objective view across CLI, TUI, and JSON output to provide visibility into parallel dispatch workflows. The core problem was that when multiple objective nodes are dispatched in parallel (using `--all-unblocked`), users had no visibility into which nodes were actively being worked on versus which were merely pending. The "planning" status (dispatched but not yet started) was invisible, and the UI only showed a single "next node" even when multiple nodes were unblocked.

This work is critical to document because it establishes patterns that will recur whenever objective display logic is extended. The implementation touched 5 core files and required coordinated updates across frozen dataclasses, real/fake data providers, TUI columns, CLI output, and JSON schema. Future agents working on similar display enhancements will benefit from understanding the 5-place update pattern for PlanRowData fields and the TUI column addition workflow.

Key insights from the implementation include: (1) the frozen dataclass field addition pattern requiring updates in 5 places, (2) pre-existing test failure verification using git stash, (3) expected git divergence after `erk pr submit`, and (4) bot review false positive handling. These patterns were learned through errors during implementation and deserve tripwire status to prevent future agents from repeating them.

## Raw Materials

PR #7827

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 12    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 4     |
| Potential tripwires (score2-3) | 3     |

## Documentation Items

### HIGH Priority

#### 1. Adding fields to frozen dataclass PlanRowData

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] session part1, part2

**Draft Content:**

```markdown
## PlanRowData Field Addition Pattern

When adding a new field to `PlanRowData` (frozen dataclass), you must update in 5 places:

1. **Dataclass definition**: Add field to `src/erk/tui/data/types.py` PlanRowData class
2. **Real provider**: Compute and populate field in `RealPlanDataProvider._build_row_data()` (see `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`)
3. **Fake helper signature**: Add parameter to `make_plan_row()` in fake provider (see `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py`)
4. **Fake helper constructor**: Add field to PlanRowData constructor call inside `make_plan_row()`
5. **Display logic**: Update `_row_to_values()` in `src/erk/tui/widgets/plan_table.py` if field appears in TUI

Additionally, grep for all `PlanRowData(` constructor calls in tests/ and update test data.

Missing any location causes hard-to-debug test failures (TypeError for missing required argument or assertion failures for field count mismatches).
```

---

#### 2. Git push rejection after erk pr submit

**Location:** `docs/learned/pr-operations/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] session part5

**Draft Content:**

```markdown
## Expected Divergence After erk pr submit

After running `erk pr submit`, your local branch will diverge from remote because the command squashes commits.

**What happens:**
- `erk pr submit` squashes your commits into a single commit on the remote
- Your local branch still has the original unsquashed commits
- Next `git push` fails with non-fast-forward error

**This is expected behavior, not a bug.**

**Resolution:**
```bash
git pull --rebase origin <branch-name>
git push
```

The rebase reconciles your local history with the squashed remote commit.
```

---

#### 3. TUI column additions require test count updates

**Location:** `docs/learned/tui/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] session part2

**Draft Content:**

```markdown
## TUI Column Addition Checklist

When adding columns to `PlanDataTable` objectives view:

1. **Add PlanRowData field**: New field in `src/erk/tui/data/types.py`
2. **Update `_row_to_values()`**: Insert value at correct index in `src/erk/tui/widgets/plan_table.py`
3. **Add column definition**: Add to `_setup_columns()` with width and alignment
4. **Update test assertions**: All `len(values) == N` assertions must be incremented
5. **Shift value indices**: Test assertions checking `values[N]` after insertion point need index adjustment

The "fly" column addition in PR #7827 demonstrates this pattern. Search for `len(values) ==` in test files when modifying `_row_to_values`.
```

---

#### 4. Missing PlanRowData field in dash_data tests

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] session part2

**Draft Content:**

```markdown
## PlanRowData Test Data Updates

When adding fields to `PlanRowData`, update test files in `tests/unit/cli/commands/exec/scripts/`:

1. **Constructor calls**: Grep for `PlanRowData(` and add the new field to each instance
2. **Expected fields set**: Update `EXPECTED_PLAN_ROW_FIELDS` in `test_serialize_plan_row_all_fields_present`

Missing updates cause TypeError (missing required argument) or assertion failures (field count mismatch).
```

---

#### 5. Parallel Dispatch Status Model

**Location:** `docs/learned/objectives/parallel-dispatch-status-model.md`
**Action:** CREATE
**Source:** [PR #7827]

**Draft Content:**

```markdown
---
read-when:
  - working with objective status display
  - implementing parallel dispatch features
  - extending objective view output
---

# Parallel Dispatch Status Model

## Status Lifecycle

Objective nodes have these statuses:

- **pending**: Not yet started, dependencies may be unresolved
- **blocked**: Waiting on predecessor nodes to complete
- **planning**: Dispatched for implementation but not yet started (agent preparing)
- **in_progress**: Actively being implemented
- **done**: Completed successfully
- **skipped**: Intentionally not implemented

## In-Flight Metric

**In-flight = planning + in_progress**

This metric shows total active work across parallel branches. Used in:
- CLI summary: "In flight: N"
- TUI "fly" column
- JSON output: `in_flight` field

## Unblocked Nodes

Multiple nodes can be unblocked simultaneously when their predecessors complete. The `pending_unblocked_nodes()` function returns all nodes ready for immediate dispatch.

When multiple nodes are unblocked, display shows count prefix: "(2) 2.1 Branch A"

## Use Cases

- `--all-unblocked` dispatch: Start work on all unblocked nodes in parallel
- Fan-out patterns: Parallel implementation branches from single predecessor
- Progress visibility: Understand active work vs waiting work

See `src/erk/cli/commands/objective/view_cmd.py` for CLI implementation.
```

---

#### 6. CLI Objective View Enhancement

**Location:** `docs/learned/cli/objective-view-enhancements.md`
**Action:** CREATE
**Source:** [PR #7827]

**Draft Content:**

```markdown
---
read-when:
  - modifying erk objective view output
  - adding new summary fields to objective display
  - working with objective CLI commands
---

# CLI Objective View Enhancements (PR #7827)

## Summary Section Format

The summary section now displays:

1. **Nodes line**: Includes planning count: "Nodes: 2/7 done, 2 planning, 1 in progress, 2 pending"
2. **In flight line**: Shows active work total: "In flight: 3" (planning + in_progress)
3. **Unblocked nodes listing**: Lists all pending unblocked nodes, not just single "Next node"

## Planning Status Display

The planning status (`status == "planning"`) renders as magenta rocket emoji with optional plan reference:
- Format: "rocket-emoji planning" or "rocket-emoji planning plan #N"
- Color: magenta (Rich markup)

See `_format_node_status()` in `src/erk/cli/commands/objective/view_cmd.py` for status rendering.

## Multiple Unblocked Nodes

When multiple nodes are unblocked, each is listed:
```
Pending unblocked:
  - 2.1 Branch A
  - 2.2 Branch B
```

When displayed in TUI next_node column, prefix shows count: "(2) 2.1 Branch A"
```

---

### MEDIUM Priority

#### 7. Planning status emoji display

**Location:** `docs/learned/objectives/planning-status-display.md`
**Action:** CREATE
**Source:** [Impl] session part2

**Draft Content:**

```markdown
---
read-when:
  - adding new objective status types
  - modifying status emoji rendering
---

# Planning Status Display

## Status Emoji Reference

| Status | Emoji | Color | Format |
|--------|-------|-------|--------|
| done | checkmark | green | "done" |
| in_progress | construction | yellow | "in progress PR #N" |
| planning | rocket | magenta | "planning plan #N" |
| pending | circle | dim | "pending" |
| blocked | stop | red | "blocked by X" |
| skipped | skip | dim | "skipped" |

## Planning Status

The planning status appears when a node has been dispatched (via `erk plan-implement` or similar) but implementation has not yet started. The agent is preparing but no code changes have been made.

See `_format_node_status()` in `src/erk/cli/commands/objective/view_cmd.py` for the complete status rendering logic.
```

---

#### 8. Unblocked count prefix pattern

**Location:** `docs/learned/objectives/unblocked-count-prefix.md`
**Action:** CREATE
**Source:** [Impl] session part2

**Draft Content:**

```markdown
---
read-when:
  - displaying multiple unblocked nodes
  - working with fan-out objective patterns
---

# Unblocked Count Prefix Pattern

When multiple objective nodes are unblocked simultaneously, the display shows a count prefix to indicate parallel opportunity.

## Format

`(N) <first-node-title>`

Example: "(2) 2.1 Branch A" means 2 nodes are unblocked, showing first alphabetically.

## Application

- **CLI next node column**: Shows count prefix when multiple unblocked
- **TUI next node display**: Same format in objectives view
- **JSON output**: `pending_unblocked` array contains all node IDs

## Fan-Out Pattern

This appears in fan-out objectives where one completed node unblocks multiple parallel branches. The count gives visibility into parallel dispatch opportunity without cluttering the display.

See `_build_row_data()` in `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` for computation logic.
```

---

#### 9. JSON Output Schema Extension

**Location:** `docs/learned/objectives/objective-view-json.md`
**Action:** UPDATE
**Source:** [PR #7827]

**Draft Content:**

```markdown
## New JSON Fields (PR #7827)

### summary.in_flight

Integer count of nodes with status "planning" or "in_progress". Represents total active work.

### graph.pending_unblocked

Array of node IDs that are pending and have no unresolved dependencies. These nodes are ready for immediate dispatch.

Example:
```json
{
  "summary": {
    "done": 2,
    "in_progress": 1,
    "planning": 2,
    "pending": 2,
    "blocked": 0,
    "in_flight": 3
  },
  "graph": {
    "nodes": [...],
    "pending_unblocked": ["2.1", "2.2"]
  }
}
```

See `_display_json()` in `src/erk/cli/commands/objective/view_cmd.py` for JSON structure.
```

---

#### 10. TUI "fly" column

**Location:** `docs/learned/tui/dashboard-columns.md`
**Action:** UPDATE
**Source:** [PR #7827]

**Draft Content:**

```markdown
## Objectives View Columns

### fly Column (PR #7827)

- **Width**: 3 characters
- **Position**: After "prog" column
- **Content**: In-flight count (planning + in_progress) or "-" if zero
- **Purpose**: Quick visual indicator of parallel activity

The column uses `objective_in_flight_display` field from `PlanRowData`, computed by `RealPlanDataProvider._build_row_data()`.

See `src/erk/tui/widgets/plan_table.py` for column definition in `_setup_columns()`.
```

---

#### 11. Pre-existing test failure verification

**Location:** `docs/learned/testing/pre-existing-failure-detection.md`
**Action:** CREATE
**Source:** [Impl] session part2

**Draft Content:**

```markdown
---
read-when:
  - encountering unexpected test failures during implementation
  - debugging test failures that don't match your changes
---

# Pre-existing Test Failure Verification

## The Problem

During implementation, you may encounter test failures that appear unrelated to your changes. Before debugging, verify whether the failure is pre-existing.

## Verification Pattern

```bash
# Stash your changes
git stash

# Run the failing test
pytest path/to/test.py::test_name -v

# If test still fails: pre-existing issue
# If test passes: your changes caused it

# Restore your changes
git stash pop
```

## Why This Matters

Debugging pre-existing failures wastes time. In PR #7827, `test_row_to_values_basic` showed `15 != 9` assertion failure. Using git stash verified this was pre-existing (unrelated to the column addition), saving significant debugging effort.

## Recommendation

When test failures seem unrelated to your changes, always verify with git stash before investigating.
```

---

#### 12. Bot false positive handling

**Location:** `docs/learned/pr-operations/bot-false-positives.md`
**Action:** CREATE
**Source:** [Impl] session part5

**Draft Content:**

```markdown
---
read-when:
  - addressing automated PR review comments
  - bot review flagged something unexpected
---

# Bot False Positive Handling

## Verification First

Before applying bot review suggestions, read the file to verify the violation exists. Bots can miscalculate.

Example from PR #7827: Bot flagged line 138 as "90 chars" when it was actually 85 chars.

## Pragmatic Resolution

Even when the bot is wrong:
1. **Read the file** to verify the claim
2. **Consider making the change anyway** if it's a minor improvement
3. **Avoid debating with the bot** - resolve the thread and move on

This approach prioritizes shipping over correctness debates with automated tools.

## When to Push Back

Push back if:
- The suggested change would harm readability
- The change introduces bugs
- The rule itself is wrong (file an issue to fix the bot)
```

---

### LOW Priority

#### 13. TUI in-flight column implementation

**Location:** `docs/learned/tui/in-flight-column.md`
**Action:** CREATE
**Source:** [PR #7827]

**Draft Content:**

```markdown
---
read-when:
  - adding similar aggregate columns to TUI
  - understanding in-flight display implementation
---

# TUI In-Flight Column Implementation

## Data Flow

1. **Computation**: `RealPlanDataProvider._build_row_data()` iterates graph nodes, counts planning + in_progress status
2. **Storage**: Result stored in `PlanRowData.objective_in_flight_display` as string ("-" if zero, count otherwise)
3. **Display**: `_row_to_values()` includes field, `_setup_columns()` defines "fly" column

## Implementation Pattern

This follows the standard display field pattern:
- Compute in real provider
- Store in dataclass
- Render in table widget

See packages/erk-shared/.../plan_data_provider/real.py for computation.
```

---

#### 14. In-flight calculation pattern

**Location:** `docs/learned/objectives/in-flight-metric.md`
**Action:** CREATE
**Source:** [Impl] session part2

**Draft Content:**

```markdown
---
read-when:
  - computing aggregate metrics from objective graphs
  - understanding in-flight vs other status aggregates
---

# In-Flight Metric

## Definition

**in_flight = count(planning) + count(in_progress)**

This metric represents total active work, distinct from:
- **done**: Completed work
- **pending**: Work not yet started
- **blocked**: Work that cannot start

## Usage

- CLI summary line: "In flight: N"
- TUI column: "fly" shows count
- JSON output: `summary.in_flight`

See `src/erk/cli/commands/objective/view_cmd.py` for calculation.
```

---

#### 15. String replacement indentation errors

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] session part1

**Draft Content:**

```markdown
## Edit Tool Whitespace Matching

When Edit fails with "string not found", the cause is often whitespace mismatch in heavily-indented code.

**Prevention Pattern:**
1. Use Grep to find the target line number
2. Use Read with offset to see exact context (5-10 lines around target)
3. Copy the exact whitespace from the file - never guess indentation
4. Apply Edit with verified whitespace

This is especially important in deeply nested code (callbacks, comprehensions, multi-level conditionals) where indentation levels are non-obvious.
```

---

## Contradiction Resolutions

None - no contradictions detected between existing documentation and new insights.

## Stale Documentation Cleanup

None - all referenced artifacts in existing docs were verified as existing.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. String Replacement Whitespace Mismatch

**What happened:** Edit tool failed to find target string in fake.py due to incorrect indentation guess
**Root cause:** Agent estimated whitespace level instead of verifying from source
**Prevention:** Always Grep + Read to see exact context before Edit in nested code
**Recommendation:** TRIPWIRE

### 2. Missing PlanRowData Fields in Test Data

**What happened:** 4 test failures in dash_data tests after adding `objective_in_flight_display` field
**Root cause:** Forgot to update test PlanRowData constructor calls when adding new field
**Prevention:** Grep for `PlanRowData(` in tests/ when adding any new field
**Recommendation:** TRIPWIRE

### 3. TUI Column Count Assertion Failures

**What happened:** Test assertion `len(values) == 15` failed after adding column (needed to be 16)
**Root cause:** Column addition changed value count but test wasn't updated
**Prevention:** Search for `len(values) ==` in tests when modifying `_row_to_values()`
**Recommendation:** TRIPWIRE

### 4. Git Push Rejection After PR Submit

**What happened:** `git push` failed with non-fast-forward error after `erk pr submit`
**Root cause:** `erk pr submit` squashes commits, causing local/remote divergence
**Prevention:** Expect this behavior; use `git pull --rebase` before next push
**Recommendation:** TRIPWIRE

### 5. Bot Line Length Miscalculation

**What happened:** Bot flagged line 138 as "90 chars" when actual length was 85 chars
**Root cause:** Bot miscalculation (possibly counting different than actual)
**Prevention:** Verify bot claims by reading file; make minor improvements anyway to avoid debate
**Recommendation:** ADD_TO_DOC

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Adding fields to frozen dataclass PlanRowData

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before adding field to PlanRowData or other frozen dataclass
**Warning:** Must update in 5 places: (1) dataclass def, (2) real provider constructor calls, (3) fake make_plan_row signature, (4) fake make_plan_row constructor call, (5) display logic. Grep for all PlanRowData( in tests.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because the frozen dataclass pattern means changes cannot be made incrementally - all 5 locations must be updated together or tests fail with TypeError. The error messages don't clearly indicate which location was missed, requiring manual grep to find all sites.

### 2. Git push rejection after erk pr submit

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** After running `erk pr submit`, before next git push
**Warning:** Expect git push rejection (non-fast-forward). This is normal - erk pr submit squashes commits. Run `git pull --rebase origin <branch>` before pushing new commits.
**Target doc:** `docs/learned/pr-operations/tripwires.md`

This is tripwire-worthy because the behavior appears to be an error but is actually expected. Without documentation, agents waste time debugging or asking users for help when the resolution is straightforward.

### 3. TUI column additions require test updates

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before adding column to PlanDataTable objectives view
**Warning:** Must update: (1) PlanRowData field, (2) _row_to_values() at correct index, (3) all test assertions checking `len(values) == N` (increment N), (4) value indices after insertion point
**Target doc:** `docs/learned/tui/tripwires.md`

Column additions consistently cause test failures if count assertions aren't updated. The pattern is easy to forget because the column renders correctly - only tests fail.

### 4. Missing PlanRowData field in dash_data tests

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before adding field to PlanRowData
**Warning:** Must grep for PlanRowData( constructor calls in tests/unit/cli/commands/exec/scripts/ and update test data + expected fields set
**Target doc:** `docs/learned/testing/tripwires.md`

The dash_data tests have their own PlanRowData instances that don't use make_plan_row helper. When adding fields, these are easy to miss because they're in a separate test directory from the main test suite.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. String replacement indentation errors

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)
**Notes:** Not cross-cutting (only affects Edit tool usage in heavily-indented code), but common enough to consider. Would benefit from more evidence of repeated occurrence across sessions.

### 2. Pre-existing test failure verification

**Score:** 2/10 (criteria: Non-obvious +2)
**Notes:** Specific to test debugging workflow, not cross-cutting enough for tripwire. However, the time savings are significant when applied. Consider promoting if pattern appears in more sessions.

### 3. Bot false positive handling

**Score:** 2/10 (criteria: Non-obvious +2)
**Notes:** Specific to PR review workflow with automated bots. Not cross-cutting enough for tripwire, but documents pragmatic approach that saves time. Better suited as pattern documentation than tripwire.
