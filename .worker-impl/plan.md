# Plan: Consolidated Documentation from 6 Learn Plans

> **Consolidates:** #6988, #6986, #6985, #6975, #6971, #6966

## Context

Six erk-learn plans accumulated on 2026-02-14, each capturing documentation opportunities from completed implementation PRs. All implementations are merged to master -- only documentation work remains. This plan consolidates them into a single actionable set of documentation changes.

## Source Plans

| #    | Title                                                  | Items Merged | Source PR |
| ---- | ------------------------------------------------------ | ------------ | --------- |
| 6988 | Skip local session discovery when gist URL exists      | 3 items      | PR #6979  |
| 6986 | Fix: Include Remote Sessions in trigger-async-learn    | 4 items      | PR #6974  |
| 6985 | Add Creation Datetime Column to erk dash               | 2 items      | PR #6978  |
| 6975 | Enrich PlanBackend ABC                                 | 3 items      | PR #6871  |
| 6971 | Restore third-party reference content                  | 2 items      | PR #6882  |
| 6966 | Test check_command via ErkContext + Fakes               | 3 items      | PR #6852  |

## Investigation Findings

### Corrections to Original Plans

- **#6986**: async-learn-local-preprocessing.md has MISLEADING tripwire stating "Remote sessions are already preprocessed" -- now INCORRECT after PR #6974
- **#6986**: Plan said --skip-workflow flag was removed -- it still exists in trigger_async_learn.py:321-324
- **#6971**: Plan said WORKFLOW_COMMAND_MAP has dead "objective-reconcile" reference -- this is already CLEAN on master
- **#6971**: content_type field was REMOVED, not added

### Overlap Analysis

- **#6975 + #6966**: Both identify the gateway vs backend ABC distinction as undocumented -- MERGED into single doc
- **#6988 + #6986**: Both relate to learn pipeline improvements -- kept separate (different aspects)
- **#6985**: TUI column patterns -- standalone, no overlap
- **#6971**: Third-party content preservation -- standalone, no overlap

## Implementation Steps

### Step 1: Fix misleading tripwire in async-learn-local-preprocessing.md _(from #6986)_

**File:** `docs/learned/planning/async-learn-local-preprocessing.md`

- Remove or correct the tripwire at lines 10-11 that states "Remote sessions are already preprocessed"
- After PR #6974, remote sessions now go through the same preprocessing pipeline as local sessions
- Update the document to reflect unified preprocessing for both local and remote session sources
- **Verification:** Content matches trigger_async_learn.py lines 409-460

### Step 2: Update learn-pipeline-workflow.md with remote session preprocessing _(from #6986)_

**File:** `docs/learned/planning/learn-pipeline-workflow.md`

- Update Stage 1 (Session Discovery) to document three session source types: local, remote gist-based, legacy artifact
- Update Stage 2 (Session Preprocessing) to reflect that BOTH local and remote sessions go through `_preprocess_session_direct()`
- Add detail about `_download_remote_session_for_learn()` function and `{session_id}.jsonl` filename convention
- **Verification:** Content matches current implementation in trigger_async_learn.py

### Step 3: Create gateway-vs-backend.md _(from #6975, #6966)_

**File:** `docs/learned/architecture/gateway-vs-backend.md`

**Content outline:**
1. Problem: Agents confuse Gateway ABCs (external system wrappers) with Backend ABCs (business logic abstractions)
2. Gateway ABCs: 5-place pattern (abc, real, fake, dry_run, printing) -- wraps subprocess, CLI, HTTP
3. Backend ABCs: 3-place pattern (abc, real, fake) -- business logic abstraction layer
4. Example: `PlanBackend` is a Backend ABC at `packages/erk-shared/src/erk_shared/plan_store/backend.py`
5. Example: `Git` is a Gateway ABC at `packages/erk-shared/src/erk_shared/gateway/git/`
6. Decision guide: when to create each type

**Add frontmatter tripwire:**
- action: "creating a new ABC without deciding gateway vs backend pattern"
- warning: "Read gateway-vs-backend.md first..."

**Update:** `docs/learned/architecture/index.md` and `docs/learned/architecture/tripwires.md`
**Verification:** PlanBackend at plan_store/backend.py matches description; Git at gateway/git/ matches description

### Step 4: Document PlanBackend ABC new methods _(from #6975)_

**File:** `docs/learned/architecture/gateway-vs-backend.md` (add section) OR create `docs/learned/planning/plan-backend-methods.md`

**Content outline:**
1. Three new methods added in PR #6871: `get_metadata_field()`, `update_plan_content()`, `post_event()`
2. Implementation patterns: GitHubPlanStore uses two-tier lookup (plan_comment_id, fallback to first comment)
3. Metadata validation change: whitelist of 9 allowed fields replaced with blocklist of 3 immutable fields (schema_version, created_at, created_by)
4. Schema v2/v3 architecture: metadata in issue body, plan content in first comment
5. FakeLinearPlanBackend pattern: frozen dataclass replacement on updates

**Verification:** Methods at backend.py lines 93-222; GitHubPlanStore at github.py lines 198-516

### Step 5: Add learn command conditional pipeline doc _(from #6988)_

**File:** `docs/learned/cli/learn-command-conditional-pipeline.md`

**Content outline:**
1. Pattern: Check for preprocessed materials (gist URL) BEFORE session discovery
2. Implementation: `_get_learn_materials_gist_url()` checks plan header for gist_url
3. If gist exists: display message, skip all session discovery, launch with gist_url
4. If no gist: existing flow (discover sessions, preprocess, upload, launch)
5. Extracted helper: `_confirm_and_launch()` at learn_cmd.py:215-237

**Add frontmatter tripwire:**
- action: "adding session discovery code before checking for preprocessed materials"
- warning: "Check gist URL first to avoid misleading output..."

**Update:** `docs/learned/cli/index.md` and `docs/learned/cli/tripwires.md`
**Verification:** learn_cmd.py lines 136-151 match description

### Step 6: Add incomplete command removal tripwire _(from #6971)_

**File:** `docs/learned/cli/incomplete-command-removal.md`

**Content outline:**
1. Pattern: When removing a workflow/command, all traces must be removed (WORKFLOW_COMMAND_MAP, trigger functions, CLI entries, workflow YAML files)
2. Why static analysis fails: string-based dispatch maps aren't caught by type checkers
3. Real example: objective-reconcile removal in PR #6882
4. 4-step prevention pattern: search for all string references before removing
5. Related: docs/learned/architecture/gateway-abc-implementation.md (5-place pattern)

**Add frontmatter tripwire:**
- action: "removing a workflow command or CLI entry"
- warning: "Read incomplete-command-removal.md first. Search all string references..."

**Update:** `docs/learned/cli/tripwires.md`
**Verification:** constants.py verified clean (no dead references)

### Step 7: Document TUI column addition worked example _(from #6985)_

**File:** `docs/learned/tui/column-addition-pattern.md`

**Content outline:**
1. Pattern overview: Adding a column to PlanDataTable requires 5 coordinated changes
2. Worked example from PR #6978: created_at datetime column
3. Files: types.py (add field), real.py (populate), plan_table.py (add column + value), fake.py (update make_plan_row)
4. Serialization: dash_data.py handles datetime conversion for JSON
5. Column positioning: index-based, check filter gate conditions
6. Sentinel pattern in make_plan_row: `effective_created_at = created_at or datetime(2025, 1, 1, tzinfo=UTC)`

**Update:** `docs/learned/tui/index.md`
**Verification:** PlanRowData at types.py has created_at/created_display; plan_table.py has column

### Step 8: Create monkeypatch vs fakes decision guide _(from #6966)_

**File:** `docs/learned/testing/monkeypatch-vs-fakes-decision.md`

**Content outline:**
1. Default: Always prefer gateway fakes over monkeypatch
2. Exception: Path.home() in exec scripts (use monkeypatch for process-level globals)
3. Exception: Genuine dotted-path import conflicts
4. Decision tree: Is there a gateway? Use fake. No gateway? Create one first. Still need monkeypatch? Document why.
5. Reference: monkeypatch-elimination-checklist.md for migration patterns

**Add frontmatter tripwire:**
- action: "choosing between monkeypatch and fakes for a test"
- warning: "Read monkeypatch-vs-fakes-decision.md first..."

**Update:** `docs/learned/testing/tripwires.md`
**Verification:** Existing test patterns in tests/ confirm fake-first approach

### Step 9: Run `erk docs sync` to regenerate indexes

After all documentation changes:
- Run `erk docs sync` to regenerate `tripwires-index.md` with updated counts
- Run `erk docs sync` to regenerate category `index.md` files
- Verify all new docs appear in their category indexes

**Verification:** `erk docs check` passes with no errors

## Attribution

Items by source:
- **#6988**: Step 5
- **#6986**: Steps 1, 2
- **#6985**: Step 7
- **#6975**: Steps 3, 4
- **#6971**: Step 6
- **#6966**: Steps 3, 8