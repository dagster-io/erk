# Plan: Consolidated Documentation for Feb 21 Implementation Sessions

> **Consolidates:** #7758, #7755, #7753, #7752, #7751, #7748, #7742, #7737, #7732, #7710, #7707, #7703, #7701

## Source Plans

| #    | Title                                                             | Items Merged |
| ---- | ----------------------------------------------------------------- | ------------ |
| 7758 | impl-signal submitted → lifecycle stage "implemented"             | 5 items      |
| 7755 | Upgrade objective-plan command with safety guardrails             | 4 items      |
| 7753 | Add `erk wt create-from` command                                  | 6 items      |
| 7752 | Ensure impl-context cleanup for all plan-implement paths          | 3 items      |
| 7751 | Replace gist transport with branch-based materials (BLOCKED)      | 2 items      |
| 7748 | Simplify plan backend configuration to env vars                   | 3 items      |
| 7742 | Move plan backend configuration to GlobalConfig                   | 7 items      |
| 7737 | Fix one-shot dispatch metadata writing for draft_pr backend       | 5 items      |
| 7732 | Replace "issue" with "plan" in implement command output           | 3 items      |
| 7710 | Auto-force push for plan implementation branches in erk pr submit | 5 items      |
| 7707 | Rename 'instruction' to 'prompt' throughout one-shot feature      | 3 items      |
| 7703 | Fix learn pipeline for draft-PR plans                             | 5 items      |
| 7701 | Add branch column to TUI dashboard and reorder objective column   | 4 items      |

## What Changed Since Original Plans

- PR #7733 (gist→branch transport) is still **OPEN** — plan 7751 items are blocked
- PR #7740 (backend config simplification) is **merged** — docs already mostly updated
- PR #7747 (impl-context cleanup) is **merged** — convergence pattern docs still missing
- PR #7750 (objective-plan model upgrade) is **merged** — token-optimization-patterns.md is now stale
- PR #7712 (erk wt create-from) is **merged** — command undocumented

## Investigation Findings

### Corrections to Original Plans

- **#7755 CRITICAL**: `docs/learned/planning/token-optimization-patterns.md` cites `/erk:objective-plan` as canonical haiku example but PR #7750 upgraded it to sonnet. Contradiction must be fixed.
- **#7758**: `docs/learned/planning/lifecycle.md` Write Points table shows `implemented` is only set by `handle-no-changes`, missing `impl-signal submitted` as the primary (normal) path.
- **#7737 CRITICAL**: `docs/learned/planning/plan-creation-pathways.md:20` states one-shot dispatch is issue-only (GitHubPlanStore), but it now supports both backends.
- **#7710**: `docs/learned/planning/plan-title-prefix-system.md` incorrectly claims ALL THREE title prefix implementations are idempotent — the slash command `.claude/commands/erk/git-pr-push.md` blindly prepends without checking.
- **#7751 BLOCKED**: Files that plan claims were deleted (`upload_learn_materials.py`, `download_learn_materials.py`) still exist. PR #7733 is not merged. All gist→branch documentation items from #7751 must wait for PR #7733 to land.
- **#7748 COMPLETE**: Most items already done — `draft-pr-plan-backend.md` already reflects 2-tier resolution.
- **#7752**: impl-context cleanup tripwire already exists in `impl-context.md` (score 8/10, lines 9-12). Convergence points doc is genuinely missing.
- **#7703**: Plan fills genuine gaps (no pre-existing contradictions). DraftPRPlanBackend comment routing is a non-obvious difference that bit multiple sessions.

### Additional Details Discovered

- `src/erk/cli/commands/wt/create_from_cmd.py` exists and is implemented (plan 7753)
- `src/erk/cli/commands/exec/scripts/impl_signal.py` exists and is implemented (plan 7758)
- For draft-PR backends, `plan_id` IS the PR number — callers can skip metadata extraction and call `github.get_pr()` directly (plan 7703)
- Auto-force push uses `state.issue_number is not None` for detection (plan 7710); `effective_force = user_force OR is_plan_impl` is the derived flag pattern
- 5-bot automated PR review system exists but has NO documentation anywhere (plans 7707, 7701)
- Audit violations for `_`-prefixed (private) function references are enforced but not documented as a rule
- TUI test index cascade appeared in EVERY session when adding/reordering columns — the highest-signal tripwire candidate

### Overlap Analysis

- Plans 7748 + 7742 + 7737 all address backend configuration patterns → merged into "Backend Configuration" section
- Plans 7703 + 7710 both reference draft-PR branch patterns → consolidated under draft-PR section
- Plans 7707 + 7701 both reference the undocumented 5-bot PR review system → single new doc
- Plans 7753 + 7755 both identify batch PR thread resolution as a missing pattern → single doc

## Remaining Gaps (Implementation Items)

### CRITICAL: Contradictions to Fix

1. **Fix token-optimization-patterns.md** — remove `/erk:objective-plan` as haiku canonical example; use `replan.md` as new example; add criteria for when to use sonnet (validation, status mapping, recommendations)
2. **Fix lifecycle.md Write Points table** — add `impl-signal submitted` as the PRIMARY write point for `implemented` stage (handle-no-changes is the edge case, not the primary path)
3. **Fix plan-creation-pathways.md:20** — update one-shot dispatch row to show dual-backend support (github + draft_pr backends)
4. **Fix plan-title-prefix-system.md** — correct idempotency claim: Python implementations are idempotent, slash command is NOT; convert line number refs to name-based pointers (PLANNED_PR_TITLE_PREFIX)

### HIGH: New Documentation (Core Patterns)

5. **Create `docs/learned/architecture/convergence-points.md`** — document convergence point architecture pattern: when multiple setup paths must reach a single cleanup point; show plan-implement Step 2d as the canonical example
6. **Create `docs/learned/planning/plan-id-semantics.md`** — for draft-PR backends, plan_id = PR number; callers can use `github.get_pr(plan_id)` directly without metadata extraction
7. **Create `docs/learned/configuration/three-tier-resolution.md`** — document the 3-tier config pattern (env var → GlobalConfig → default) used for plan_backend and similar settings
8. **Create `docs/learned/architecture/globalconfig-field-addition.md`** — checklist for adding new fields to GlobalConfig frozen dataclass: field definition, load/save logic, migration, tests
9. **Create `docs/learned/cli/wt-create-from.md`** — document the new `erk wt create-from` command: purpose (allocate worktree slots to existing branches), syntax, when to use vs `create` vs `create --from-current-branch`
10. **Create `docs/learned/cli/wt-command-comparison.md`** — semantic comparison table: `create` vs `create-from` vs `create --from-current-branch` vs `checkout`; clarify the subtle differences
11. **Create `docs/learned/architecture/derived-flags.md`** — document the "effective flag" pattern: combining user-intent flags with auto-detection for transparent automation (e.g., `effective_force = user_force OR is_plan_impl`)
12. **Create `docs/learned/testing/fake-git-divergence.md`** — testing pattern for branch divergence scenarios using `BranchDivergence` config in FakeGit

### HIGH: Updates to Existing Docs

13. **Update `docs/learned/planning/one-shot-workflow.md`** — add dual-backend support: explain that one-shot dispatch creates a skeleton issue for github backend but a draft PR for draft_pr backend
14. **Update `docs/learned/planning/draft-pr-plan-backend.md`** — add learn pipeline integration section, plan_id semantics, PlanHeaderNotFoundError behavior (reads soft-fail, writes hard-fail)
15. **Extend `docs/learned/planning/draft-pr-branch-sync.md`** — add section: "Auto-force Push for Plan Implementation Branches" covering divergence detection, `effective_force` derivation, and user transparency echo
16. **Extend `docs/learned/cli/pr-submit-pipeline.md`** — add: state-based detection pattern (`state.issue_number is not None`) and informational echo for auto-behavior
17. **Update `docs/learned/planning/token-optimization-patterns.md`** — add sonnet vs haiku selection criteria table; remove stale objective-plan example
18. **Extend `docs/learned/cli/output-styling.md`** — add user-facing terminology table: "plan" not "issue" in all user-facing strings; list affected commands

### HIGH: Tripwire Additions (score 6+/10)

19. **planning/tripwires.md**: Add self-referential close prevention (score 9/10) — closing a plan's own PR during a plan-implement merge triggers recursive close; always verify merge target is not current PR before close
20. **planning/tripwires.md**: Add one-shot metadata block preservation (score 8/10) — do not overwrite plan body when writing dispatch metadata; use targeted metadata block updates
21. **testing/tripwires.md**: Add context-based backend detection (score 7/10) — use `plan_backend.get_provider_name()` for backend-conditional logic, not isinstance checks
22. **ci/tripwires.md**: Add format-then-commit workflow (score 6/10) — formatters (ruff, prettier) must be run and committed BEFORE CI; format check failures do not auto-fix
23. **tui/tripwires.md**: Add test index cascade for TUI columns (score 6/10) — adding or reordering PlanDataTable columns breaks ALL tests using column indices; update systematically before submitting
24. **planning/tripwires.md**: Add PlanHeaderNotFoundError from update_metadata() (score 6/10) — draft-PR plan write operations raise PlanHeaderNotFoundError if header block is absent; reads return None gracefully
25. **testing/tripwires.md**: Add DraftPRPlanBackend comment routing (score 6/10) — test assertions for DraftPRPlanBackend.add_comment() must check `FakeGitHub.pr_comments`, NOT `FakeGitHubIssues.added_comments`

### MEDIUM: New Documentation

26. **Create `docs/learned/tui/derived-display-columns.md`** — document the exception to the 5-step column addition pattern: when a new column uses an already-present `PlanRowData` field, skip the gateway→query→data steps; show branch column as example
27. **Update `docs/learned/tui/column-addition-pattern.md`** — add section on column reordering (update ALL index-based test assertions); add view-specific column insertion guidance (columns before early-return only appear in one view path)
28. **Create `docs/learned/commands/multi-path-command-refactoring.md`** — document the convergence refactoring pattern for commands with multiple setup paths: how to extract common teardown/cleanup to a single convergence function
29. **Update `docs/learned/ci/automated-reviews.md` (or create)** — document the 5-bot automated PR review system: which bot checks what, how to interpret their feedback, when false positives occur, how to trigger re-analysis
30. **Create `docs/learned/planning/backend-naming-conventions.md`** — document the backend naming inconsistency: env var uses `draft_pr` (underscore) while code class is `DraftPRPlanBackend` (no underscore); glossary of official terms

### BLOCKED: Plan 7751 Items (wait for PR #7733)

These items from plan #7751 cannot be implemented until PR #7733 (gist→branch transport) is merged:

- Update learn-pipeline-workflow.md Stages 4-5
- Update async-learn-local-preprocessing.md
- Update learn-command-conditional-pipeline.md
- Create learn-branch-transport.md
- Remove stale gist-format tripwire from planning/tripwires.md
- Update learn-workflow.md (phantom gist_url)
- Update learn-without-pr-context.md

## Implementation Steps

### Phase 1: Fix Contradictions (do first, standalone edits)

**Step 1: Fix token-optimization-patterns.md**

- **File:** `docs/learned/planning/token-optimization-patterns.md`
- Remove `/erk:objective-plan` from the haiku examples section
- Add `/erk:replan` as the new canonical haiku example (pure data gathering)
- Add a new subsection: "When to upgrade from haiku to sonnet" with criteria: status validation, status→label mapping, multi-step recommendations
- Verification: No mention of objective-plan in the haiku section

**Step 2: Fix lifecycle.md Write Points table**

- **File:** `docs/learned/planning/lifecycle.md`
- Find the Write Points table and the `implemented` row
- Add `impl-signal submitted` as the PRIMARY write point (the normal PR submission path)
- Note `handle-no-changes` as the SECONDARY/edge case write point
- Update Phase 5 narrative to mention the `impl-signal submitted` event
- Verification: Table shows both write points; normal path is primary

**Step 3: Fix plan-creation-pathways.md**

- **File:** `docs/learned/planning/plan-creation-pathways.md`
- Update line ~20: one-shot dispatch row — change from "Issue-based (GitHubPlanStore) | Skeleton issue" to "Backend-aware (github or draft_pr) | Skeleton issue (github) or Draft PR (draft_pr)"
- Verification: Table accurately reflects dual-backend behavior

**Step 4: Fix plan-title-prefix-system.md**

- **File:** `docs/learned/planning/plan-title-prefix-system.md`
- Update idempotency section: clarify only Python implementations (`plan/save.py` and `pr/prepare_state.py`) check `startswith()` before prepending
- Clarify slash command `git-pr-push.md` blindly prepends and will double-prefix if called twice
- Convert line number references to name-based pointers (use `PLANNED_PR_TITLE_PREFIX` constant name instead of specific line numbers)
- Verification: Idempotency claim is accurate and scoped

### Phase 2: High-Priority New Documentation

**Step 5: Create convergence-points.md**

- **File:** `docs/learned/architecture/convergence-points.md`
- Content: Definition (when multiple code paths must share a single cleanup/teardown point), motivation (prevents resource leaks when paths diverge), canonical example (plan-implement Step 2d: cleanup runs regardless of which setup path was taken), implementation pattern (extract convergence point to standalone function called by all paths)
- Reference: `.claude/commands/erk/plan-implement.md` Step 2d, `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py`

**Step 6: Create plan-id-semantics.md**

- **File:** `docs/learned/planning/plan-id-semantics.md`
- Content: For issue-based backend, plan_id = GitHub issue number; for draft-PR backend, plan_id = PR number. Callers working with draft-PR plans should call `github.get_pr(plan_id)` directly without metadata extraction. Include code example of correct detection.

**Step 7: Create three-tier-resolution.md**

- **File:** `docs/learned/configuration/three-tier-resolution.md`
- Content: The three-tier pattern (env var → GlobalConfig field → hardcoded default), when to use it (user-configurable settings that CI also needs to override), implementation pattern in `packages/erk-shared/src/erk_shared/plan_store/__init__.py`

**Step 8: Create globalconfig-field-addition.md**

- **File:** `docs/learned/architecture/globalconfig-field-addition.md`
- Content: Checklist for adding a new field to `GlobalConfig` frozen dataclass in `packages/erk-shared/src/erk_shared/context/types.py` — field definition (no defaults in frozen dataclass), load/save in `real.py`, migration for existing config files, test context updates

**Step 9: Create wt-create-from.md**

- **File:** `docs/learned/cli/wt-create-from.md`
- Content: Document `erk wt create-from` command: purpose (allocate an existing slot to an existing branch), syntax (`erk wt create-from <slot> <branch>`), key difference from `erk wt create` (does not create a new branch), reference implementation at `src/erk/cli/commands/wt/create_from_cmd.py`

**Step 10: Create wt-command-comparison.md**

- **File:** `docs/learned/cli/wt-command-comparison.md`
- Content: Comparison table of `erk wt create`, `erk wt create-from`, `erk wt create --from-current-branch`, and `erk wt checkout` — when to use each, what branch state they require, what slot state they require

**Step 11: Create derived-flags.md**

- **File:** `docs/learned/architecture/derived-flags.md`
- Content: Pattern for combining user-intent boolean flags with auto-detection: `effective_flag = user_flag OR auto_detected_condition`. Canonical example: `effective_force = user_force OR (state.issue_number is not None)` in the PR submit pipeline. Includes user transparency: print dim-styled informational message explaining why auto-behavior activated.
- Reference: `src/erk/cli/commands/pr/` submit pipeline

**Step 12: Create fake-git-divergence.md**

- **File:** `docs/learned/testing/fake-git-divergence.md`
- Content: Testing pattern for branch divergence scenarios. How to configure `BranchDivergence` in `FakeGit`. Which divergence states map to which real-world scenarios (ahead-only, behind-only, both). Examples from plan implementation test suite.

### Phase 3: Update Existing High-Priority Docs

**Step 13: Update one-shot-workflow.md**

- **File:** `docs/learned/planning/one-shot-workflow.md`
- Add section: "Backend-Specific Behavior" — for github backend: creates skeleton issue; for draft_pr backend: creates draft PR directly
- Update any diagrams or flow descriptions that only show the issue path

**Step 14: Update draft-pr-plan-backend.md**

- **File:** `docs/learned/planning/draft-pr-plan-backend.md`
- Add subsection: "Learn Pipeline Integration" — how the learn pipeline detects draft-PR plans, `plan_id` = PR number semantics
- Add subsection: "Metadata API Asymmetry" — read operations return None gracefully; write operations raise `PlanHeaderNotFoundError` if header block absent

**Step 15: Extend draft-pr-branch-sync.md**

- **File:** `docs/learned/planning/draft-pr-branch-sync.md`
- Add section: "Auto-force Push for Plan Implementation Branches" — why plan branches always diverge (draft PR scaffolding commits vs worker implementation), detection via `state.issue_number`, `effective_force` derivation, user-facing echo message

**Step 16: Extend pr-submit-pipeline.md**

- **File:** `docs/learned/cli/pr-submit-pipeline.md`
- Add: state-based plan detection pattern (`state.issue_number is not None`)
- Add: informational echo pattern for transparent auto-behavior

**Step 17: Update token-optimization-patterns.md**

- **File:** `docs/learned/planning/token-optimization-patterns.md`
- Add criteria table: haiku for pure data gathering/formatting; sonnet when task requires validation, status mapping, or multi-step recommendations
- (Contradiction fix already done in Phase 1 Step 1)

**Step 18: Extend output-styling.md**

- **File:** `docs/learned/cli/output-styling.md`
- Add section: "User-Facing Terminology" — "plan" not "issue" in user-facing output strings; list affected commands: `implement`, `implement_shared`, `create_cmd`; contrast with internal variable names which may still use `issue_number`

### Phase 4: Add Tripwires

**Step 19: Add high-score tripwires to planning/tripwires.md**

- **File:** `docs/learned/planning/tripwires.md`
- Add (score 9/10): Self-referential close prevention — when merging a plan's PR, check that close target ≠ current PR before running close logic
- Add (score 8/10): One-shot metadata block preservation — use targeted metadata block updates; never overwrite the full plan body when writing dispatch metadata
- Add (score 6/10): PlanHeaderNotFoundError from update_metadata() — call `plan_backend.update_metadata()` only when confident the header block exists; check for None first on reads

**Step 20: Add tripwires to testing/tripwires.md**

- **File:** `docs/learned/testing/tripwires.md`
- Add (score 7/10): Context-based backend detection — use `plan_backend.get_provider_name()` for backend-conditional logic; not isinstance; not string comparison
- Add (score 6/10): DraftPRPlanBackend comment routing — `FakeGitHub.pr_comments` not `FakeGitHubIssues.added_comments`

**Step 21: Add tripwire to ci/tripwires.md**

- **File:** `docs/learned/ci/tripwires.md`
- Add (score 6/10): Format-then-commit — run ruff/prettier locally and commit the formatted output BEFORE pushing; CI format checks do not auto-fix

**Step 22: Add tripwire to tui/tripwires.md**

- **File:** `docs/learned/tui/tripwires.md`
- Add (score 6/10): TUI column index cascade — adding or reordering PlanDataTable columns invalidates ALL test assertions using column indices; run a systematic grep for column-index assertions before/after the change

### Phase 5: Medium-Priority Documentation

**Step 23: Create derived-display-columns.md**

- **File:** `docs/learned/tui/derived-display-columns.md`
- Content: Exception to the standard 5-step column addition pattern. When a new display column reuses an existing `PlanRowData` field (no new data needed), skip gateway query, data class, and data-layer steps. Only add: column definition, render method, test assertion updates. Example: branch column (uses `pr_head_branch` and `worktree_branch` already in PlanRowData).

**Step 24: Update column-addition-pattern.md**

- **File:** `docs/learned/tui/column-addition-pattern.md`
- Add section: "Column Reordering" — update ALL index-based test assertions when changing column order
- Add section: "View-Specific Columns" — columns inserted before an early return only appear in one view path; verify `_row_to_values()` produces correct count for both paths

**Step 25: Create multi-path-command-refactoring.md**

- **File:** `docs/learned/commands/multi-path-command-refactoring.md`
- Content: Pattern for refactoring commands with multiple setup paths that share teardown logic. Step 1: identify all paths. Step 2: extract shared teardown to standalone convergence function. Step 3: call convergence from all paths. Step 4: verify via tests that cleanup runs regardless of path taken.

**Step 26: Document automated PR review system**

- **File:** `docs/learned/ci/automated-reviews.md` (create or update)
- Content: Document the 5-bot automated review system — which bot validates what, how to interpret their comments, when false positives occur, how to trigger re-analysis after addressing feedback

**Step 27: Create backend-naming-conventions.md**

- **File:** `docs/learned/planning/backend-naming-conventions.md`
- Content: Backend name inconsistency glossary. Env var: `DRAFT_PR` (or `draft_pr`). Class: `DraftPRPlanBackend`. Provider name string: `draft-pr` (check actual value). Issue-based: `github`. Official terms for user-facing docs.

### Phase 6: Tripwires Sync

**Step 28: Run `erk docs sync` to regenerate tripwires-index.md**

- After adding new tripwires to category tripwire files, run the sync to update the counts in `docs/learned/tripwires-index.md`
- Verification: All new tripwire entries appear in the index

### Deferred (BLOCKED on PR #7733)

After PR #7733 lands, implement these items from plan #7751:

- Update learn-pipeline-workflow.md Stages 4-5 (gist refs → branch refs)
- Update async-learn-local-preprocessing.md (remove gist-based packing)
- Update learn-command-conditional-pipeline.md (`_get_learn_materials_branch` not `_get_learn_materials_gist_url`)
- Update gist-materials-interchange.md (mark as historical/deprecated)
- Create learn-branch-transport.md
- Update learn-workflow.md (remove phantom gist_url from inputs table)
- Update learn-without-pr-context.md
- Remove stale gist-format tripwire from planning/tripwires.md

## Attribution

Items by source plan:

- **#7758**: Steps 2
- **#7755**: Steps 1, 17
- **#7753**: Steps 9, 10, 21
- **#7752**: Steps 5, 25
- **#7751**: Deferred section
- **#7748**: Steps 21, 25
- **#7742**: Steps 7, 8, 20
- **#7737**: Steps 3, 13, 19
- **#7732**: Steps 18
- **#7710**: Steps 4, 11, 12, 15, 16
- **#7707**: Steps 26
- **#7703**: Steps 6, 14, 19, 20
- **#7701**: Steps 22, 23, 24
