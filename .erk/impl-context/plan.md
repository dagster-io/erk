# Documentation Plan: Fire-and-forget workflow dispatch with workflow-writes-metadata

## Context

This implementation introduces a fire-and-forget workflow dispatch mechanism for TUI responsiveness, solving a fundamental tension between instant user feedback and accurate workflow metadata tracking. The core innovation is the **workflow-writes-metadata pattern**: instead of the CLI blocking to poll for run IDs before writing metadata, the CLI dispatches immediately with pending sentinel values (timestamp set, run_id/node_id as None), and the GitHub Actions workflow writes its own metadata (actual run_id, node_id) as its first step after starting.

This architectural decision ripples across four layers: the gateway ABC (new `dispatch_workflow()` method alongside existing `trigger_workflow()`), CLI commands (new `--no-wait` flag and routing logic), TUI screens (all dispatch sites now use fire-and-forget), and GitHub Actions workflows (new `plan_number` input and early metadata write step). The implementation also consolidates four scattered exec scripts into a single agent-readable document (`plan-implement.md`), demonstrating the project's preference for documentation over code when the "code" is really just glue.

A future agent approaching similar challenges needs to understand several non-obvious constraints: the dashboard's `if node_id is not None` guard means string sentinels like "pending" would break GraphQL batch lookups (use None instead), gateway ABC signature changes require atomic 5-place + callers updates, and `plan-update-issue` trusts session context without validating plan identity (leading to a critical incident where PR #8000 was overwritten with wrong plan content). These learnings justify both new documentation and tripwire additions.

## Raw Materials

N/A

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 18    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 5     |
| Potential tripwires (score 2-3)| 4     |

## Documentation Items

### HIGH Priority

#### 1. Gateway ABC dispatch_workflow() pattern

**Location:** `docs/learned/architecture/github-gateway-dispatch.md`
**Action:** CREATE
**Source:** [Impl], [PR #8000]

**Draft Content:**

```markdown
---
title: GitHub Gateway Fire-and-Forget Dispatch
read-when:
  - implementing workflow dispatch in CLI
  - choosing between dispatch_workflow and trigger_workflow
  - adding fire-and-forget functionality
tripwire-count: 1
---

# GitHub Gateway Fire-and-Forget Dispatch

## Overview

The gateway provides two workflow dispatch methods with different semantics:

- `trigger_workflow()`: Polls for run ID, returns run_id string. Use for scripts needing run URLs.
- `dispatch_workflow()`: Fire-and-forget, no polling, no return. Use for TUI/interactive flows.

## When to Use Each

**Use `dispatch_workflow()` when:**
- TUI responsiveness matters more than immediate run URL
- Workflow will write its own metadata (workflow-writes-metadata pattern)
- User doesn't need to wait for workflow confirmation

**Use `trigger_workflow()` when:**
- Script needs run URL for logging or linking
- Immediate confirmation of workflow start is required
- Metadata must be written by CLI (blocking acceptable)

## Implementation Architecture

Both methods share `_dispatch_workflow_impl()` which handles:
- Distinct ID generation via `_generate_distinct_id()`
- Workflow invocation via GitHub API
- Common input assembly

See `packages/erk-shared/src/erk_shared/gateway/github/real.py` for implementation.

## Zero-Cost Branch Resolution

Plan numbers are extracted from P-prefixed branches via regex, not GitHub API calls.
See `ctx.plan_backend.resolve_plan_id_for_branch()`.

## Output Formatting

The `_format_workflow_run_command()` helper in printing.py provides consistent output for both dispatch modes.

## Related

- [Pending dispatch metadata](../planning/pending-dispatch-metadata.md) - Null sentinel pattern
- [Workflow-writes-metadata](../ci/workflow-writes-metadata.md) - How workflows write their own metadata
```

---

#### 2. Pending dispatch metadata sentinel pattern

**Location:** `docs/learned/planning/pending-dispatch-metadata.md`
**Action:** CREATE
**Source:** [Impl], [PR #8000]

**Draft Content:**

```markdown
---
title: Pending Dispatch Metadata Sentinel Pattern
read-when:
  - writing plan dispatch metadata with pending state
  - working with last_dispatched_run_id or last_dispatched_node_id fields
  - implementing fire-and-forget workflow dispatch
tripwire-count: 1
---

# Pending Dispatch Metadata Sentinel Pattern

## The Problem

Fire-and-forget workflow dispatch returns immediately without a run_id. The dashboard needs to display workflow status, but we have no run_id to show.

## The Solution

Use `None` (not string "pending") for `run_id` and `node_id` fields. Pending state is inferred from:
- `last_dispatched_at` is set (timestamp exists)
- `run_id` is None (workflow hasn't written metadata yet)
- `node_id` is None

## Why Not String "pending"?

The schema validates fields as `str | None`. A string "pending" would:
1. Pass schema validation
2. Pass dashboard's `if node_id is not None` guard
3. Be sent to GitHub GraphQL API as a real node_id
4. Cause API failures

The dashboard's guard at `plan_list_service.py` (look for batch lookup logic) relies on `is not None` checks before GraphQL operations.

## CLI Implementation

`maybe_write_pending_dispatch_metadata()` in `src/erk/cli/commands/pr/metadata_helpers.py`:
- Called after fire-and-forget dispatch
- Writes timestamp with null run_id/node_id
- Silent early-return on non-plan branches

## Workflow Overwrite

GitHub Actions workflow first step writes real values (see workflow-writes-metadata pattern).

## Related

- [Workflow-writes-metadata](../ci/workflow-writes-metadata.md)
- [GitHub gateway dispatch](../architecture/github-gateway-dispatch.md)
```

---

#### 3. Workflow-writes-metadata pattern

**Location:** `docs/learned/ci/workflow-writes-metadata.md`
**Action:** CREATE
**Source:** [Impl], [PR #8000]

**Draft Content:**

```markdown
---
title: Workflow-Writes-Metadata Pattern
read-when:
  - adding GitHub Actions workflow dispatch with plan metadata
  - implementing fire-and-forget workflow features
  - working with plan_number workflow input
tripwire-count: 1
---

# Workflow-Writes-Metadata Pattern

## Overview

Instead of CLI polling for run_id and writing metadata (blocking), the workflow writes its own metadata when it starts.

## The Pattern

1. **CLI dispatches** with `plan_number` as workflow input
2. **CLI writes pending sentinel** (timestamp set, run_id/node_id as None)
3. **Workflow starts** and has `${{ github.run_id }}` in context
4. **Workflow first step** writes real run_id + node_id to plan metadata
5. **Dashboard infers state** from null vs non-null fields

## Workflow Input Design

Use optional input with empty string default:

```yaml
inputs:
  plan_number:
    description: 'Plan number for metadata updates'
    required: false
    default: ''
```

Then gate metadata steps:

```yaml
- name: Write dispatch metadata
  if: inputs.plan_number != ''
  continue-on-error: true  # Non-critical
  run: |
    NODE_ID=$(gh api /repos/.../actions/runs/${{ github.run_id }} --jq '.node_id')
    erk exec update-plan-header ${{ inputs.plan_number }} \
      last_dispatched_run_id="${{ github.run_id }}" \
      last_dispatched_node_id="$NODE_ID" \
      last_dispatched_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

## Why Optional Input?

Required inputs break workflows triggered on non-plan branches. Use `required: false` with `default: ""`, then conditionally execute.

## Why continue-on-error: true?

Plans may lack metadata blocks (`PlanHeaderNotFoundError`). Metadata writes are non-critical - workflow should complete even if metadata update fails.

## Step Placement

Place metadata step:
1. **After** `erk-remote-setup` (erk CLI available)
2. **Before** main work begins (minimize pending window)

See `.github/workflows/pr-address.yml` for reference implementation.

## Related

- [Pending dispatch metadata](../planning/pending-dispatch-metadata.md)
- [GitHub gateway dispatch](../architecture/github-gateway-dispatch.md)
```

---

#### 4. Gateway ABC implementation checklist update

**Location:** `docs/learned/architecture/gateway-abc-implementation.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8000]

**Draft Content:**

```markdown
## Updates to Add

### dispatch_workflow() in 5-Place Pattern

The gateway ABC now includes both `trigger_workflow()` and `dispatch_workflow()`. When implementing or modifying workflow dispatch:

1. **abc.py** - Abstract method definition
2. **real.py** - Implementation with `_dispatch_workflow_impl()` shared logic
3. **fake.py** - Mutation tracking for test assertions
4. **dry_run.py** - No-op implementation
5. **printing.py** - Output formatting delegation

### Atomic Signature Changes

Changing method signatures requires coordinated updates:
1. Grep for all implementations (5 files)
2. Grep for all callers (CLI commands, tests)
3. Update in sequence: ABC -> implementations -> callers
4. Verify with ty/ruff/pytest before committing

Never remove default parameters partially - update all callers atomically.

### DRY Helper Extraction

When dispatch and trigger share logic (like distinct_id generation), extract to `_dispatch_workflow_impl()` helper. See real.py for pattern.
```

---

#### 5. Plan-update-issue identity validation (TRIPWIRE)

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl] - Session incident

This is a tripwire entry documenting the plan-update-issue identity validation requirement.

**Trigger:** Before running `erk exec plan-update-issue`

**Warning:** NEVER run plan-update-issue without verifying session context contains correct plan identity. The command doesn't validate plan identity - only that ANY plan exists in context. Running it can overwrite unrelated PRs with wrong plan content. Always check recent conversation or run `erk plan list` to confirm plan number matches target PR.

**Rationale:** During implementation of PR #8000, the command grabbed plan content from wrong session context (picked up "LLM Inference Hoisting" instead of "Fire-and-Forget Workflow Dispatch"), completely overwriting the PR body. Recovery required reconstructing the plan from git history.

**Score:** 8/10 (Non-obvious +2, Destructive potential +2, Silent failure +2, Repeated pattern +1, Cross-cutting +1)

---

#### 6. ABC method signature atomic update (TRIPWIRE)

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl]

**Trigger:** Before changing gateway ABC method signature

**Warning:** Changing method signatures in gateway ABCs requires atomic multi-file updates across 5 places (abc.py, real.py, fake.py, dry_run.py, printing.py) PLUS all callers. Before starting: (1) Grep for all implementations (2) Grep for all callers (3) Update in sequence: ABC -> implementations -> callers (4) Verify with ty/ruff/pytest before committing. Partial updates will break type checking and tests.

**Score:** 6/10 (Cross-cutting +2, Non-obvious +2, Destructive potential +2)

---

### MEDIUM Priority

#### 7. Fire-and-forget CLI command pattern

**Location:** `docs/learned/cli/launch-command.md`
**Action:** CREATE
**Source:** [Impl], [PR #8000]

**Draft Content:**

```markdown
---
title: Launch Command Fire-and-Forget Pattern
read-when:
  - adding workflow dispatch to CLI commands
  - implementing --no-wait flag behavior
  - routing between dispatch and trigger modes
---

# Launch Command Fire-and-Forget Pattern

## --no-wait Flag Semantics

The `--no-wait` flag switches from blocking (`trigger_workflow()`) to fire-and-forget (`dispatch_workflow()`).

## Routing Function

`_dispatch_or_trigger_workflow()` in `src/erk/cli/commands/launch_cmd.py`:
- When `no_wait=True`: Call `dispatch_workflow()`, then `maybe_write_pending_dispatch_metadata()`
- When `no_wait=False`: Call `trigger_workflow()`, then `maybe_update_plan_dispatch_metadata()` with run_id

## Plan Number Threading

Both `_trigger_pr_fix_conflicts()` and `_trigger_pr_address()` resolve plan ID from branch name and pass as workflow input. Empty string if non-plan branch.

## Output Differences

- `--no-wait`: Immediate return, no run URL shown
- Without flag: Blocks until run starts, displays run URL

## Related

- [GitHub gateway dispatch](../architecture/github-gateway-dispatch.md)
- [Pending dispatch metadata](../planning/pending-dispatch-metadata.md)
```

---

#### 8. TUI fire-and-forget integration

**Location:** `docs/learned/tui/fire-and-forget-dispatch.md`
**Action:** CREATE
**Source:** [Impl], [PR #8000]

**Draft Content:**

```markdown
---
title: TUI Fire-and-Forget Workflow Dispatch
read-when:
  - adding workflow dispatch buttons to TUI
  - improving TUI responsiveness
---

# TUI Fire-and-Forget Workflow Dispatch

## Problem

TUI screens blocked for 15+ seconds when triggering remote workflows (polling for run_id).

## Solution

All TUI dispatch sites pass `--no-wait` to `erk launch`, enabling fire-and-forget dispatch.

## Call Sites

- `src/erk/tui/app.py` - 2 dispatch sites
- `src/erk/tui/screens/plan_detail_screen.py` - 4 dispatch sites

Search for `--no-wait` in these files to see integration points.

## User Experience

- Immediate return to TUI after button press
- Dashboard shows "pending" state (timestamp set, run_id None)
- Workflow writes real metadata once it starts

## Related

- [Launch command pattern](../cli/launch-command.md)
- [Pending dispatch metadata](../planning/pending-dispatch-metadata.md)
```

---

#### 9. Fake GitHub dispatch testing

**Location:** `docs/learned/testing/fake-github-dispatch.md`
**Action:** CREATE
**Source:** [Impl], [PR #8000]

**Draft Content:**

```markdown
---
title: Testing Fire-and-Forget Dispatch with FakeGitHub
read-when:
  - testing workflow dispatch in FakeGitHub
  - writing assertions for dispatch vs trigger
---

# Testing Fire-and-Forget Dispatch with FakeGitHub

## FakeGitHub Mutation Tracking

`FakeGitHub.dispatch_workflow()` records dispatches for test assertions. Both dispatch and trigger record to the same `triggered_workflows` list but with different metadata.

See `packages/erk-shared/src/erk_shared/gateway/github/fake.py` for implementation.

## Testing Patterns

### Verifying Dispatch vs Trigger

Check `triggered_workflows` list contents:
- `dispatch_workflow()` records without run_id
- `trigger_workflow()` records with run_id (returned from method)

### Verifying Pending Metadata

Use `FakeGitHubIssues.updated_bodies` property (returns `list[tuple[int, str]]`) to verify metadata was written to plan issue body.

## Test Examples

See `tests/commands/launch/test_launch_cmd.py` for comprehensive examples:
- Test plan_number appears in workflow inputs for P-prefixed branches
- Test plan_number is empty string for non-P-prefixed branches
- Test both pr-fix-conflicts and pr-address workflows get plan numbers

## Related

- [Fake mutation tracking patterns](./testing.md)
```

---

#### 10. Exec script consolidation rationale

**Location:** `docs/learned/planning/exec-script-consolidation.md`
**Action:** CREATE
**Source:** [Impl], [PR #8000]

**Draft Content:**

```markdown
---
title: Exec Script Consolidation to Agent Documentation
read-when:
  - creating new exec script in src/erk/cli/commands/exec/scripts/
  - deciding between exec script and documented workflow
tripwire-count: 1
---

# Exec Script Consolidation to Agent Documentation

## What Was Consolidated

Four exec scripts were deleted and their logic moved to `.claude/commands/erk/plan-implement.md`:

1. `cleanup_impl_context.py`
2. `detect_plan_from_branch.py`
3. `setup_impl.py`
4. `upload_impl_session.py`

## Why Agent Documentation Over Scripts

**Problems with scattered scripts:**
- Multiple sources of truth
- No inline decision trees
- Harder for agents to understand context
- Code maintenance burden

**Benefits of documentation:**
- Single source of truth
- Inline decision trees and expanded context
- Agent-readable workflow steps
- No code to maintain

## When to Use Each

**Use exec scripts for:**
- Truly shared utilities across multiple commands
- Complex logic requiring full programming language
- Operations with side effects needing transaction handling

**Use documented workflows for:**
- Agent-orchestrated multi-step processes
- Decision trees with conditional branches
- Workflows that benefit from inline explanation

## Related

- [plan-implement.md](../../.claude/commands/erk/plan-implement.md) - Consolidated workflow
```

---

#### 11. Launch command testing patterns

**Location:** `docs/learned/testing/cli-launch-testing.md`
**Action:** CREATE
**Source:** [Impl], [PR #8000]

**Draft Content:**

```markdown
---
title: Launch Command Testing Patterns
read-when:
  - testing erk launch command
  - testing --no-wait flag behavior
---

# Launch Command Testing Patterns

## Test Structure

Tests live in `tests/commands/launch/test_launch_cmd.py`, following mirror-structure convention for Layer 4 tests.

## Key Test Cases

1. **Plan number in workflow inputs** - Verify P-prefixed branches pass plan_number
2. **Empty plan number for non-plan branches** - Non-P-prefixed branches pass empty string
3. **Dispatch vs trigger routing** - --no-wait uses dispatch, without uses trigger

## Fixture Patterns

Use `make_plan_body()` helper with valid plan-header metadata block. FakeTime for deterministic timestamp assertions.

See test file for complete examples.
```

---

#### 12. Metadata helpers testing

**Location:** `docs/learned/testing/metadata-helpers-testing.md`
**Action:** CREATE
**Source:** [Impl], [PR #8000]

**Draft Content:**

```markdown
---
title: Metadata Helpers Testing Patterns
read-when:
  - testing maybe_write_pending_dispatch_metadata
  - testing plan metadata functions
---

# Metadata Helpers Testing Patterns

## Test Location

`tests/unit/cli/commands/pr/test_metadata_helpers.py` - Layer 4 business logic tests.

## Test Cases for maybe_write_pending_dispatch_metadata

1. **Early return on non-plan branch** - Branch doesn't match P{number} pattern
2. **Early return without schema_version** - Plan exists but no metadata block
3. **Successful write** - Creates pending dispatch marker with correct timestamp

## Fixture Setup

- `FakeTime` with UTC timestamp for deterministic assertions
- `make_plan_body()` helper to create plan with plan-header metadata block
- `FakeGitHubIssues.updated_bodies` for mutation assertions
```

---

#### 13. Bot review false positive patterns

**Location:** `docs/learned/ci/bot-review-patterns.md`
**Action:** CREATE
**Source:** [Impl], [PR #8000]

**Draft Content:**

```markdown
---
title: Bot Review False Positive Patterns
read-when:
  - responding to automated review comments
  - dismissing false positive reviews
tripwire-count: 1
---

# Bot Review False Positive Patterns

## Common False Positives

### LBYL Split Across Lines

Bot flags EAFP violation, but LBYL guard exists on earlier lines. Example: `metadata_helpers.py:141` flagged as EAFP, but lines 135-138 have LBYL guard.

## Correct Response

1. **Read the flagged code carefully**
2. **Check if required pattern exists nearby** (may be split across lines)
3. **If false positive:**
   - Reply explaining why code is correct
   - Reference specific line numbers
   - Resolve thread
4. **Do NOT make unnecessary code changes** to satisfy incorrect bot feedback

## Related

- [False positive detection](../pr-operations/false-positive-detection.md)
```

---

#### 14. Test coverage exclusion patterns

**Location:** `docs/learned/testing/test-coverage-exclusions.md`
**Action:** CREATE
**Source:** [PR #8000]

**Draft Content:**

```markdown
---
title: Legitimate Test Coverage Exclusions
read-when:
  - reviewing test coverage reports
  - deciding what needs test coverage
---

# Legitimate Test Coverage Exclusions

## Categories of Legitimate Exclusions

1. **ABC definitions** - Abstract methods have no implementation to test
2. **Thin no-op wrappers** - `dry_run.py` methods that just return/log
3. **Output wrapper delegation** - `printing.py` methods that delegate to wrapped gateway
4. **CLI flag wiring** - TUI files that just pass flags through

## When Coverage IS Required

- Business logic functions
- Error handling paths
- State transformations
- Gateway implementations (real, fake)
```

---

#### 15. Tripwire routing mechanism

**Location:** `docs/learned/architecture/tripwire-routing.md`
**Action:** CREATE
**Source:** [PR #8000]

**Draft Content:**

```markdown
---
title: Tripwire Routing Mechanism
read-when:
  - understanding how tripwires work
  - adding new tripwires
---

# Tripwire Routing Mechanism

## How Tripwires Work

1. **Detection**: Pattern matches against file path or action being performed
2. **Loading**: Corresponding tripwire document is loaded into agent context
3. **Warning**: Agent sees warning message before proceeding

## Adding Tripwires

Add entries to category-specific `tripwires.md` files:
- `docs/learned/architecture/tripwires.md` - Cross-cutting patterns
- `docs/learned/planning/tripwires.md` - Planning workflow tripwires
- `docs/learned/ci/tripwires.md` - CI/workflow tripwires

## Tripwire File Structure

Each tripwire entry includes:
- **Trigger**: What action or pattern triggers it
- **Warning**: Concise warning message
- **Target doc**: Where to find detailed guidance
```

---

#### 16. Investigation-before-fix scope discipline

**Location:** `docs/learned/architecture/scope-discipline.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Investigation-Before-Fix Scope Discipline
read-when:
  - addressing review comments
  - deciding scope of fix
---

# Investigation-Before-Fix Scope Discipline

## The Pattern

When addressing feedback:
1. **Investigate broadly** - Search for related occurrences, understand context
2. **Fix narrowly** - Only change what was requested

## Example

Review requests extracting magic number to constant. Agent:
1. Read the file containing magic number
2. Searched for other occurrences across codebase (found discrepancy: 15 vs 11)
3. Made minimal requested change (extract constant)
4. Did NOT fix the discovered discrepancy (out of scope)

## When to Expand Scope

Only expand if:
- The original request is impossible without broader change
- User explicitly approves expanded scope
- Safety issue requires immediate fix

## Related

- [PR operations](../pr-operations/)
```

---

#### 17. False positive handling in PR reviews

**Location:** `docs/learned/pr-operations/false-positive-detection.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8000]

**Draft Content:**

```markdown
## Updates to Add

### LBYL/EAFP Split-Line Pattern

Automated reviewers can flag code as EAFP violation when LBYL guard exists but is split across multiple lines.

**Example:** `metadata_helpers.py:141` flagged as EAFP, but lines 135-138 contain:
```python
if not has_metadata_block:
    return
```

**Response pattern:**
1. Identify the LBYL guard on earlier lines
2. Reply citing specific line numbers
3. Resolve thread without code changes
```

---

#### 18. Workflow metadata schemas

**Location:** `docs/learned/reference/workflow-metadata-schemas.md`
**Action:** UPDATE
**Source:** [PR #8000]

**Draft Content:**

```markdown
## Updates to Add

### workflow-started Block Structure

When workflows write their own metadata:

Fields:
- `last_dispatched_run_id`: GitHub workflow run ID string
- `last_dispatched_node_id`: GitHub GraphQL node ID for batch lookups
- `last_dispatched_at`: ISO 8601 timestamp (UTC)

Schema: All three fields are `str | None`. None indicates pending state (dispatch happened but workflow hasn't written metadata yet).
```

---

## Stale Documentation Cleanup

**None detected.** All referenced files in existing documentation were verified to exist.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. plan-update-issue overwrites wrong PR

**What happened:** Running `erk exec plan-update-issue --plan-number 8000` grabbed plan content from wrong session context, overwriting PR #8000 body with unrelated "LLM Inference Hoisting" plan content.

**Root cause:** The command extracts plan from session context without validating plan identity matches target PR. Session contained discussion of multiple plans.

**Prevention:** Before running plan-update-issue, verify session context contains correct plan by checking recent conversation or running `erk plan list` to confirm plan number matches target PR.

**Recommendation:** TRIPWIRE (Score: 8 - highest severity)

### 2. Schema-valid but semantically invalid sentinel

**What happened:** Initial design used string "pending" for run_id/node_id fields during pending state.

**Root cause:** Schema validates as `str | None`, so "pending" passes validation. But dashboard's `if node_id is not None` guard sends "pending" to GitHub GraphQL API as a real node_id.

**Prevention:** Always validate sentinel values against actual usage patterns, not just schema types. Check all consumers of the field.

**Recommendation:** TRIPWIRE (Score: 6)

### 3. Incomplete ABC interface changes

**What happened:** Removing default parameters from gateway ABC methods required updating all implementations AND all callers atomically.

**Root cause:** Gateway ABC has 4 implementations plus printing wrapper. Callers span multiple CLI commands and tests.

**Prevention:** Before changing gateway ABC signatures: (1) Grep for all implementations (2) Grep for all callers (3) Update in sequence: ABC -> implementations -> callers (4) Verify with ty/ruff/pytest before committing.

**Recommendation:** TRIPWIRE (Score: 6)

### 4. Making workflow inputs required breaks non-plan branches

**What happened:** Marking `plan_number` as `required: true` in workflow YAML would break workflows triggered on branches without plan numbers.

**Root cause:** Not all branches that trigger these workflows are plan branches.

**Prevention:** Use `required: false` with `default: ""`, then conditionally execute steps with `if: inputs.plan_number != ''`.

**Recommendation:** ADD_TO_DOC

### 5. Plan metadata update failures block workflow

**What happened:** `erk exec update-plan-header` raises `PlanHeaderNotFoundError` when plan lacks metadata block, which would fail the workflow step.

**Root cause:** Not all plans have metadata blocks (especially older plans).

**Prevention:** Always use `continue-on-error: true` for plan metadata update steps in workflows.

**Recommendation:** ADD_TO_DOC

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Plan-update-issue identity validation

**Score:** 8/10 (criteria: Non-obvious +2, Destructive potential +2, Silent failure +2, Repeated pattern +1, Cross-cutting +1)

**Trigger:** Before running `erk exec plan-update-issue`

**Warning:** NEVER run plan-update-issue without verifying session context contains correct plan identity. The command doesn't validate plan identity - only that ANY plan exists in context. Running it can overwrite unrelated PRs with wrong plan content. Always check recent conversation or run `erk plan list` to confirm plan number matches target PR.

**Target doc:** `docs/learned/planning/tripwires.md`

This tripwire is critical because the failure mode is silent (no error, just wrong content) and destructive (PR body overwritten). The incident during PR #8000 implementation required manual recovery from git history.

### 2. ABC method signature atomic update

**Score:** 6/10 (criteria: Cross-cutting +2, Non-obvious +2, Destructive potential +2)

**Trigger:** Before changing gateway ABC method signature

**Warning:** Changing method signatures in gateway ABCs requires atomic multi-file updates across 5 places (abc.py, real.py, fake.py, dry_run.py, printing.py) PLUS all callers. Before starting: (1) Grep for all implementations (2) Grep for all callers (3) Update in sequence: ABC -> implementations -> callers (4) Verify with ty/ruff/pytest before committing. Partial updates will break type checking and tests.

**Target doc:** `docs/learned/architecture/tripwires.md`

### 3. Pending dispatch metadata sentinel

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)

**Trigger:** Before writing plan dispatch metadata with pending state

**Warning:** NEVER use string sentinel values for run_id or node_id. Use None for pending state. Dashboard's `if node_id is not None` guard treats "pending" as real node_id for GraphQL batch lookup, causing API failures. Pending is inferrable: last_dispatched_at is set but run_id and node_id are still None.

**Target doc:** `docs/learned/planning/tripwires.md`

### 4. Gateway dispatch_workflow() pattern

**Score:** 5/10 (criteria: Cross-cutting +2, External tool quirk +1, Non-obvious +2)

**Trigger:** Before implementing workflow dispatch in CLI

**Warning:** Choose between dispatch_workflow() (fire-and-forget, no run_id) and trigger_workflow() (polls for run_id). Use dispatch for TUI/interactive flows (responsiveness), trigger for scripts that need run URLs. Fire-and-forget requires workflow-writes-metadata pattern (CLI writes pending sentinel, workflow overwrites with real values).

**Target doc:** `docs/learned/architecture/tripwires.md`

### 5. Workflow-writes-metadata pattern

**Score:** 4/10 (criteria: Cross-cutting +2, Non-obvious +2)

**Trigger:** Before adding GitHub Actions workflow dispatch with plan metadata

**Warning:** If workflow needs to write plan metadata: (1) Add plan_number as optional input with default: '' (2) Add conditional metadata step: if: inputs.plan_number != '' (3) Place metadata step early (after erk-remote-setup, before main work) (4) Use continue-on-error: true (plans may lack metadata block). See pr-address.yml pattern.

**Target doc:** `docs/learned/ci/tripwires.md`

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Workflow input without CLI fallback

**Score:** 3/10 (criteria: Non-obvious +2, External tool quirk +1)

**Notes:** Making workflow inputs `required: true` can break workflows triggered on non-plan branches. Use `required: false` with `default: ''` instead, then conditionally execute steps with `if: inputs.field != ''`. This allows workflows to work for both plan and non-plan triggers. May warrant promotion if pattern proves confusing to agents.

### 2. Workflow dispatch without write_dispatch_metadata

**Score:** 3/10 (criteria: Non-obvious +2, Cross-cutting +1)

**Notes:** Fire-and-forget dispatch must still write pending sentinel or dashboard shows stale state. The pattern is new enough that agents may forget the pending sentinel step. Monitor for repeated mistakes before promoting to full tripwire.

### 3. Plan metadata update failures block workflow

**Score:** 3/10 (criteria: Non-obvious +2, Silent failure +1)

**Notes:** Always use `continue-on-error: true` for plan metadata steps in workflows. Plans may lack metadata blocks (`PlanHeaderNotFoundError`). Treating metadata writes as non-critical allows workflows to complete even when metadata update fails.

### 4. TUI workflow status before run_id

**Score:** 2/10 (criteria: Non-obvious +2)

**Notes:** How to show pending state in TUI before workflow writes run_id. Threshold barely missed but good candidate if pattern proves confusing. The pending state (timestamp set, run_id None) is inferrable but requires understanding the workflow-writes-metadata pattern.
