# Plan: Consolidate documentation from 9 erk-learn plans

> **Consolidates:** #8862, #8861, #8860, #8859, #8858, #8854, #8851, #8846, #8844

## Context

Nine erk-learn plans have accumulated from recent implementation sessions. All source PRs are merged. This plan consolidates their documentation gaps into a single actionable plan. All code changes are already landed — this plan is purely documentation.

## Source Plans

| # | Title | Items Merged |
| --- | --- | --- |
| #8862 | Split test_preprocess_session.py into subpackage | 2 items |
| #8861 | Improve incremental dispatch commit message | 2 items |
| #8860 | Replace monkeypatch with HealthCheckRunner gateway | 2 items |
| #8859 | Fix Graphite divergence + introduce erk pr prepare | 2 items |
| #8858 | Add erk reconcile command + rename diverge-fix | 2 items |
| #8854 | Create module-to-subpackage skill | 1 item |
| #8851 | Fix doctor warning display + artifact allowlist | 2 items |
| #8846 | Restore progress feedback with background thread polling | 2 items |
| #8844 | Fix Dignified Python false positives | 2 items |

## What Changed Since Original Plans

- All 9 source PRs are merged to master — code is fully implemented
- Policy change (e14b58a9b): unbundled skills excluded from codex_portable.py registries
- HealthCheckRunner infrastructure appears in both #8860 and #8851 (overlap)
- module-to-subpackage skill appears in both #8854 and #8862 (overlap)

## Investigation Findings

### Corrections to Original Plans

- **#8862**: Plan claimed 93 tests but actual count is 102 (+9 tests added during/after implementation)
- **#8854**: Plan said to register in codex_portable.py but policy changed — unbundled skills excluded
- **#8846**: Plan proposed single 5s interval but implementation uses two-layer architecture (2s generator poll + 5s queue timeout)
- **#8844**: Plan said assert rule is "type narrowing only" but implementation enhanced to "no side effects" (broader)

### Overlap Analysis

- **#8860 + #8851**: Both document HealthCheckRunner gateway. Merged into single doc covering the gateway pattern + doctor warning display + artifact allowlist
- **#8854 + #8862**: Both reference module-to-subpackage skill. Merged into single doc covering skill creation + usage precedent

## Remaining Documentation Gaps

All code is implemented. The following documentation needs to be created or updated:

1. Update `test-file-organization.md` with test_preprocess_session precedent
2. Create doc for incremental dispatch system (commit-level vs PR-level plan embedding)
3. Create doc for HealthCheckRunner gateway pattern + doctor improvements
4. Create doc for `erk pr prepare` command
5. Create doc for `erk reconcile` command
6. Update `alias-verification-pattern.md` for library alias exception
7. Update `testing/tripwires.md` for library alias exception
8. Create doc for progress feedback two-layer threading pattern

## Implementation Steps

### Step 1: Update test-file-organization.md _(from #8862)_

**File:** `docs/learned/testing/test-file-organization.md`
**Action:** Add test_preprocess_session to "Existing Precedents" section (after line ~73)

**Content to add:**
```markdown
### `tests/unit/cli/commands/exec/scripts/test_preprocess_session/` (from `test_preprocess_session.py`)

8 files organized by feature area (102 tests, split from 2,182-line monolith):

| File | Focus | Tests |
|------|-------|-------|
| `test_xml_escaping.py` | XML escaping | 4 |
| `test_deduplication.py` | Assistant message deduplication | 5 |
| `test_xml_generation.py` | XML generation | 21 |
| `test_log_processing.py` | Log file processing | 6 |
| `test_agent_discovery.py` | Agent discovery | 11 |
| `test_session_helpers.py` | Session analysis and helpers | 17 |
| `test_preprocess_workflow.py` | CLI and workflow integration | 16 |
| `test_splitting.py` | Token estimation and splitting | 22 |
```

**Verification:** Confirm precedent count matches actual test files in directory

### Step 2: Create incremental dispatch documentation _(from #8861)_

**File:** `docs/learned/planning/incremental-dispatch.md`

**Content outline:**
1. Purpose: dispatch local plan against existing PR for remote implementation
2. Implementation: `src/erk/cli/commands/exec/scripts/incremental_dispatch.py`
3. Commit message format: subject line + blank line + plan content body (line 131)
4. Two-part plan embedding strategy: commit-level (local history) vs PR-level (reviewer context)
5. Worktree interaction: index sync when branch is checked out (lines 134-144)
6. Workflow trigger: dispatches with `dispatch_type: "incremental"` and `plan_backend: "planned_pr"`

**Source:** `src/erk/cli/commands/exec/scripts/incremental_dispatch.py`
**Verification:** File paths and line numbers match current code

### Step 3: Create HealthCheckRunner + doctor improvements documentation _(from #8860, #8851)_

**File:** `docs/learned/architecture/health-check-runner-gateway.md`

**Content outline:**
1. Problem: monkeypatch in doctor tests for health check results
2. Pattern: simplified 3-file gateway (ABC + Real + Fake, no dry-run/printing wrappers)
3. ABC: `src/erk/core/health_checks/runner.py` (lines 18-22) — single `run_all()` method
4. Real: same file (lines 25-31) — delegates to `run_all_checks()`
5. Fake: `tests/fakes/health_check_runner.py` (lines 14-21) — constructor-injected results
6. Context integration: optional field in ErkContext with TYPE_CHECKING import
7. Doctor fallback: None check before calling injected runner (lines 170-173)
8. Doctor warning display: three-way conditional for condensed subgroups (lines 86-113)
9. Artifact allowlist: `_load_artifact_allowlist()` reads config.toml + config.local.toml, merges into frozenset

**Source:** `src/erk/core/health_checks/runner.py`, `src/erk/cli/commands/doctor.py`, `src/erk/core/health_checks/managed_artifacts.py`
**Verification:** grep for HealthCheckRunner in tests confirms zero remaining monkeypatch

### Step 4: Create erk pr prepare documentation _(from #8859)_

**File:** `docs/learned/cli/commands/pr-prepare.md`

**Content outline:**
1. Purpose: set up impl-context for current worktree's PR
2. Implementation: `src/erk/cli/commands/pr/prepare_cmd.py` (84 lines)
3. Auto-detection: uses `ctx.github.get_pr_for_branch()` when plan_number omitted
4. Idempotency: reads existing impl_dir, compares plan_id, skips if match
5. Extracted function: `create_impl_context_from_pr()` in `setup_impl_from_pr.py:116-218`
6. Graphite divergence fix context: retracking moved to AFTER rebase in checkout_cmd.py:289-309
7. Related: `erk pr checkout` error message now suggests `erk pr prepare` as alternative

**Source:** `src/erk/cli/commands/pr/prepare_cmd.py`, `src/erk/cli/commands/pr/checkout_cmd.py`
**Verification:** `erk pr prepare --help` shows expected options

### Step 5: Create erk reconcile documentation _(from #8858)_

**File:** `docs/learned/cli/commands/reconcile.md`

**Content outline:**
1. Purpose: detect and clean up branches whose PRs have been merged
2. Implementation: `src/erk/cli/commands/reconcile_cmd.py` (173 lines) + `reconcile_pipeline.py` (248 lines)
3. Detection pipeline: fetch_prune → filter gone branches → exclude trunk → check PR state → resolve metadata
4. Processing: fail-open pipeline (learn PR → objective update → cleanup)
5. Cleanup: unassign slot → delete branch → remove worktree
6. Options: `--force`, `--dry-run`, `--skip-learn`
7. Git layer extensions: `gone` field on `BranchSyncInfo`, `fetch_prune` across 5 gateway implementations
8. Rename context: `reconcile-with-remote` → `diverge-fix` (16 files updated)
9. Related: `/erk:diverge-fix` slash command for manual divergence resolution

**Source:** `src/erk/cli/commands/reconcile_cmd.py`, `src/erk/cli/commands/reconcile_pipeline.py`
**Verification:** `erk reconcile --help` shows expected options; grep for "reconcile-with-remote" finds zero stray references

### Step 6: Update alias-verification-pattern.md _(from #8844)_

**File:** `docs/learned/testing/alias-verification-pattern.md`
**Action:** Update "The One Exception" section (around line 39-41) to add second exception for well-known library aliases

**Content to add:**
```markdown
### Exception 2: Well-Known Library Aliases

Standard library aliases are acceptable:
- `import pandas as pd`
- `import numpy as np`
- `import dagster as dg`
- `import matplotlib.pyplot as plt`

Internal/project aliasing remains prohibited.
```

**Also update:** Tripwire warning (line 11) to reflect the new exception
**Verification:** Content aligns with `.claude/skills/dignified-python/dignified-python-core.md`

### Step 7: Update testing/tripwires.md _(from #8844)_

**File:** `docs/learned/testing/tripwires.md`
**Action:** Find and update the contradictory warning about pandas aliases to reflect the new exception

**Verification:** No contradictions between tripwires and dignified-python-core.md rules

### Step 8: Create progress feedback threading documentation _(from #8846)_

**File:** `docs/learned/architecture/progress-feedback-threading.md`

**Content outline:**
1. Problem: blocking LLM calls during PR description generation with no user feedback
2. Solution: two-layer architecture for progress feedback
3. Layer 1 — CommitMessageGenerator (`src/erk/core/commit_message_generator.py`):
   - Background thread runs LLM call (lines 144-146)
   - Polls with `thread.join(timeout=2.0)` (line 149)
   - Yields ProgressEvent/CompletionEvent
4. Layer 2 — `run_commit_message_generation()` (`src/erk/cli/commands/pr/shared.py:345-423`):
   - Wraps generator in second producer thread
   - Queue-based event collection with 5s timeout
   - Emits "Still waiting" on queue.Empty
   - Resets timer on each progress event (line 411)
5. Why two layers: separation of concerns (core pure, UI handles presentation)
6. Production call sites: submit_pipeline.py, rewrite_cmd.py, update_pr_description.py
7. Time abstraction: `time: Time` parameter with FakeTime for tests

**Source:** `src/erk/core/commit_message_generator.py`, `src/erk/cli/commands/pr/shared.py`
**Verification:** All 3 production sites pass `time=ctx.time`

## Attribution

Items by source:
- **#8862**: Step 1
- **#8861**: Step 2
- **#8860**: Step 3
- **#8859**: Step 4
- **#8858**: Step 5
- **#8854**: Step 1 (skill precedent reference)
- **#8851**: Step 3
- **#8846**: Step 8
- **#8844**: Steps 6, 7

## Verification

After implementation:
1. Run `erk docs sync` to regenerate index files
2. Grep for contradictions between new docs and existing tripwires
3. Verify all file paths referenced in new docs exist in current codebase
4. Run `make fast-ci` to confirm no formatting/lint issues
