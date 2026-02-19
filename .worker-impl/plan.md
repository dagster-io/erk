# Plan: Consolidated Documentation for Recent Implementation Sessions

> **Consolidates:** #7611, #7607, #7590, #7586, #7582

## Context

Five erk-learn plans were generated from recent implementation sessions covering draft PR plan branches, TUI modal streaming, batch dispatch, backend-agnostic plan resolution, and CI workflow migration. All underlying implementations are complete and merged. The documentation gaps remain: patterns, testing approaches, and tripwires discovered during these sessions need to be captured in `docs/learned/` so future agents don't rediscover them.

## Source Plans

| # | Title | Items Merged |
| --- | --- | --- |
| 7611 | Track Draft PR Plan Branches with Graphite | 3 items |
| 7607 | Restore Land and Submit to Modals in TUI | 5 items |
| 7590 | Atomic Batch Status Update for All-Unblocked Dispatch | 3 items |
| 7586 | Migrate Objective Linkage to Backend-Agnostic Plan Resolution | 4 items |
| 7582 | Migrate CI Workflows for Draft PR Plan Support | 3 items |

## Overlap Analysis

- **#7586 + #7582**: Both document the issue-number-to-plan-id migration pattern. Merged into a single "backend-agnostic plan identity" doc.
- **#7590 + #7611**: Both involve fake gateway testing patterns. Merged into fake gateway testing guidance within respective docs.
- **#7607 + #7582**: Both touch TUI features. Kept separate (different subsystems).

## Implementation Steps

### Step 1: Fix contradiction in `github-actions-api.md` _(from #7582)_

**File:** `docs/learned/reference/github-actions-api.md`

- **Line 43**: Change `${{ inputs.issue_number }}` to `${{ inputs.plan_id }}`
- **Line 18**: Update `last_audited` to current date
- **Verification:** Grep for `inputs.issue_number` in the file; should return 0 matches after fix

### Step 2: Update `dependency-graph.md` with `min_dep_status()` _(from #7582)_

**File:** `docs/learned/objectives/dependency-graph.md`

- Add section documenting `DependencyGraph.min_dep_status()` method (source: `dependency_graph.py:70-84`)
- Document return semantics: returns minimum status among blocking dependencies, or None if no dependencies
- Document use case: powers the "deps" column in TUI Objectives view via `PlanRowData.objective_deps_display`
- Update `last_audited` date
- **Verification:** Section exists with correct method signature and return type

### Step 3: Create `branch-manager-testing.md` _(from #7611)_

**File:** `docs/learned/testing/branch-manager-testing.md`

**Content outline:**
1. Problem: BranchManager is a lazy property on ErkContext (context.py:173-199), not a separately injectable gateway
2. Pattern: Inject `FakeGraphite` via `context_for_test(graphite=fake_graphite)`, NOT FakeBranchManager directly
3. Key method: `FakeGraphite.create_linked_branch_ops()` creates ops with shared mutation tracking
4. Assertions: Use `fake_graphite.track_branch_calls` for Graphite tracking verification
5. Checkout count expectations: branch_manager.create_branch() performs 2 internal checkouts (new branch + restore), plan_save adds 2 more = 4 total
6. Reference: `tests/unit/cli/commands/exec/scripts/test_plan_save.py:278-303`

**Frontmatter tripwire:**
- action: "injecting FakeBranchManager directly in tests"
- warning: "BranchManager is a lazy property. Inject FakeGraphite via context_for_test() instead."

**Verification:** File exists with correct frontmatter and content referencing actual test file

### Step 4: Update `branch-manager-decision-tree.md` with plan branch example _(from #7611)_

**File:** `docs/learned/architecture/branch-manager-decision-tree.md`

- Add concrete example for plan branches in the "Use ctx.branch_manager" section (after line ~37)
- Content: Plan branches created by `erk plan save --draft-pr` are user-facing branches that become PRs. They MUST use `ctx.branch_manager.create_branch()` for Graphite tracking. Without tracking, Graphite rejects operations on untracked branches during `erk prepare`.
- Reference: `_save_as_draft_pr()` in `plan_save.py:143-150`
- **Verification:** Example appears in decision tree under user-facing branch examples

### Step 5: Update `branch-manager-abstraction.md` with test expectations _(from #7611)_

**File:** `docs/learned/architecture/branch-manager-abstraction.md`

- Add "Test Expectations" subsection under behavioral differences
- Content: When converting from `git.branch.create_branch()` to `branch_manager.create_branch()`, expect +2 checkouts from branch_manager's internal gt track sequence. Your code's checkout/restore adds more. Update test checkout count assertions accordingly.
- Reference: `test_plan_save.py:220-236` for full example
- **Verification:** Section exists with checkout count guidance

### Step 6: Create `modal-streaming-pattern.md` _(from #7607)_

**File:** `docs/learned/tui/modal-streaming-pattern.md`

**Content outline:**
1. Problem: Long-running CLI operations (land PR, submit to queue) need real-time output visibility
2. Pattern: `PlanDetailScreen.run_streaming_command()` mounts `CommandOutputPanel`, streams subprocess output line-by-line via `_stream_subprocess()` worker
3. Callback mechanism: `on_success: Callable[[], None] | None` called via `app.call_from_thread()` on returncode==0
4. Timeouts: Land PR=600s, Submit to Queue=120s
5. Thread safety: All widget mutations from background threads MUST go through `app.call_from_thread()`
6. Testing: Use `_CapturingPlanDetailScreen` pattern (~80 lines vs 475+ with old worker mocking)
7. Reference: `src/erk/tui/screens/plan_detail_screen.py:395-426` (run_streaming_command), `tests/tui/commands/test_execute_command.py:13` (_CapturingPlanDetailScreen)

**Frontmatter tripwire:**
- action: "mutating TUI widgets from a background thread without call_from_thread()"
- warning: "Cross-thread widget mutations cause silent UI corruption. Always use app.call_from_thread()."

**Verification:** File exists with streaming pattern and thread safety guidance

### Step 7: Create `dual-abc-callback-injection.md` _(from #7607)_

**File:** `docs/learned/architecture/dual-abc-callback-injection.md`

**Content outline:**
1. Problem: TUI needs both UI callback exposure (CommandExecutor) and subprocess execution (PlanDataProvider), but circular imports prevent direct coupling
2. Pattern: Two ABCs with overlapping method (`update_objective_after_land`). Lambda injection bridges them: `update_objective_fn=lambda oi, pn, br: self._update_objective_async(...)`
3. Lambda abbreviation convention: Parameters abbreviated to 2-3 chars (oi, pn, br) with immediate expansion to keyword arguments
4. Testing: FakeCommandExecutor tracks `updated_objectives` as `list[tuple[int, int, str]]`
5. Reference: `src/erk/tui/app.py:519-580` (_push_streaming_detail), `packages/erk-shared/src/erk_shared/gateway/command_executor/abc.py`

**Verification:** File exists with dual-ABC pattern and lambda injection example

### Step 8: Create `batch-objective-update.md` _(from #7590)_

**File:** `docs/learned/objectives/batch-objective-update.md`

**Content outline:**
1. Problem: N separate GitHub API write cycles for N nodes during `--all-unblocked` dispatch
2. Pattern: Fetch-once-accumulate-write-once via `_batch_update_objective_nodes()` (plan_cmd.py:342-404)
3. Two-phase dispatch: O(N) API calls for PR creation, then O(1) for objective body update
4. Partial failure handling: Successful nodes marked "planning", failed remain "pending" (no rollback)
5. Surgical replacement: Uses `_replace_node_refs_in_body()`, not full-body rewrite
6. v2 format handling: Also updates separate comment body if present
7. Testing: FakeGitHubIssues.updated_bodies is GLOBAL across all issues. Tests MUST filter by issue number: `[(num, body) for num, body in issues.updated_bodies if num == target_issue]`
8. Reference: `src/erk/cli/commands/exec/scripts/objective/plan_cmd.py:342-404`, test at `test_plan_cmd.py:325-331`

**Frontmatter tripwire:**
- action: "asserting on FakeGitHubIssues.updated_bodies without filtering by issue number"
- warning: "updated_bodies is global across all issues. Filter to your target issue number to avoid false positives from plan issue creation side effects."

**Verification:** File exists with batch pattern and filtering tripwire

### Step 9: Create `backend-agnostic-plan-identity.md` _(from #7586, #7582)_

**File:** `docs/learned/planning/backend-agnostic-plan-identity.md`

**Content outline:**
1. Problem: Plan resolution was hardcoded to GitHub issues. Draft PR plans need the same resolution without issue numbers.
2. Pattern: `PlanBackend.get_plan_for_branch()` returns `Plan | PlanNotFound` discriminated union. Two implementations: `GitHubPlanBackend` (regex-based, zero-cost) and `DraftPRPlanBackend` (API-based via `github.get_pr_for_branch()`)
3. Pre-parsed metadata: `Plan.header_fields: dict[str, object]` + `Plan.objective_id: int | None` extracted during conversion. Typed accessors: `header_str()`, `header_int()`, `header_datetime()`
4. Plan identifier typing: `PlanInfoDict.number: str | int` accommodates both backends
5. Exec script migration: `--issue-number` renamed to `--plan-id` across CI workflows and exec scripts. Scripts migrated: ci_update_pr_body.py, handle_no_changes.py, post_workflow_started_comment.py, upload_session.py, update_plan_remote_session.py
6. Not yet migrated: `register_one_shot_plan.py` (still uses `--issue-number`), `get_pr_body_footer.py` (still uses `--issue-number`)
7. Reference: `packages/erk-shared/src/erk_shared/plan_store/backend.py` (ABC), `objective_fetch_context.py:146-159` (usage)

**Frontmatter tripwires:**
- action: "manually extracting metadata from plan issue body instead of using Plan.objective_id"
- warning: "Use pre-parsed Plan fields. Plan.objective_id is extracted during conversion. Manual regex/YAML parsing is error-prone."
- action: "typing plan identifiers as just int"
- warning: "Plan identifiers must be str | int to accommodate both issue-based and draft-PR-based plans."

**Verification:** File exists with both backend patterns and pre-parsed metadata guidance

### Step 10: Run `erk docs sync` to regenerate index files

**Command:** `erk docs sync`

**Verification:** `docs/learned/index.md` and category tripwire files include all new documents

## Attribution

Items by source:
- **#7611**: Steps 3, 4, 5
- **#7607**: Steps 6, 7
- **#7590**: Step 8
- **#7586**: Step 9 (merged with #7582)
- **#7582**: Steps 1, 2, 9 (merged with #7586), 10

## Verification

After all steps:
1. `erk docs sync` completes without errors
2. `docs/learned/index.md` lists all new files
3. Each new file has valid frontmatter with `title`, `read_when`, and `tripwires` (where applicable)
4. No broken file path references in new docs (grep for referenced source files)