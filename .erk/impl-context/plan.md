# Plan: Consolidated Documentation from Feb 22 Learn Sessions

> **Consolidates:** #7859, #7858, #7844, #7839, #7835, #7829, #7825, #7822, #7821, #7820, #7819, #7804, #7801

## Source Plans

| # | Title | Items Merged |
|---|-------|-------------|
| 7859 | Restore abbreviated stage names in TUI dashboard | 5 items |
| 7858 | LLM-generated branch name slugs for meaningful naming | 4 items |
| 7844 | Discriminated union validation gate and enhanced schema guidance | 5 items |
| 7839 | Fix release process documentation | 3 items |
| 7835 | Objective view parallel in-flight status | 4 items |
| 7829 | /local:objective-reevaluate command documentation | 4 items |
| 7825 | Slug validation gate with agent backpressure | 2 items |
| 7822 | Checkout race condition in one_shot_dispatch.py | 3 items |
| 7821 | Session branch prefix rename to async-learn | 3 items |
| 7820 | Unify plan checkout with erk br co --for-plan | 5 items |
| 7819 | ci-update-pr-body plan-header metadata preservation | 2 items |
| 7804 | get-pr-view command to avoid GraphQL rate limits | 3 items |
| 7801 | Remove conditional column display from TUI plans view | 4 items |

## Investigation Findings

### What Changed Since Original Plans

All 13 plans were created on Feb 22, 2026. The underlying PRs are all merged. Key codebase state:
- All referenced features are fully implemented in code
- Documentation has NOT been updated for any of these items
- Several existing docs contain stale references (lifecycle.md, data-contract.md, dashboard-columns.md)

### Overlap Analysis

After analyzing all 13 plans, the documentation items cluster into these categories:

1. **Architecture patterns** (validation gates, backpressure, git plumbing, discriminated unions) - Plans #7844, #7825, #7822
2. **TUI documentation** (columns, lifecycle, dashboard) - Plans #7859, #7835, #7801
3. **Planning/workflow docs** (checkout, session branches, one-shot) - Plans #7820, #7821, #7822, #7819
4. **CLI/command docs** (get-pr-view, release process, exec inventory) - Plans #7804, #7839, #7858
5. **Objective docs** (view enhancements, reevaluate command) - Plans #7835, #7829
6. **Tripwire additions** (cross-cutting) - All plans contribute tripwires

### Corrections to Original Plans

- **#7819**: Implementation used `--draft-pr` CLI flag, NOT `find_metadata_block()` fallback
- **#7801**: Learn column was subsequently removed in PR #7855; some items are obsolete
- **#7822**: `docs/learned/documentation/learned-docs.md` doesn't exist (needs CREATE not UPDATE)
- **#7839**: activate.sh path inconsistency between docs (`.erk/bin/activate.sh` vs `.erk/activate.sh`)

## Remaining Gaps

After deduplication and filtering out obsolete items, the consolidated work breaks into these implementation steps.

## Implementation Steps

### Phase 1: Fix Stale Documentation (HIGH priority)

**Step 1.1: Update `docs/learned/sessions/lifecycle.md`** _(from #7821)_
- Replace `session/{plan_id}` with `async-learn/{plan_id}` at lines 36-38 and 47-53
- Verification: `grep "session/{plan" docs/learned/sessions/lifecycle.md` returns nothing

**Step 1.2: Update `docs/learned/tui/dashboard-columns.md`** _(from #7801, #7835, #7859)_
- Remove conditional visibility flags from column table (all columns now always visible)
- Add "fly" column entry (from #7835 - in-flight status)
- Add stage abbreviation note (from #7859 - "impling"/"impld")
- Verification: No references to `show_prs`, `show_runs` as conditional flags

**Step 1.3: Update `docs/learned/planning/next-steps-output.md`** _(from #7820)_
- Add missing `checkout_and_implement` property to `DraftPRNextSteps` table
- Source: `packages/erk-shared/src/erk_shared/output/next_steps.py:59`
- Verification: Property count matches code

**Step 1.4: Update `docs/learned/objectives/objective-view-json.md`** _(from #7835)_
- Add `in_flight` field to summary section
- Add `pending_unblocked` field to graph section
- Source: `src/erk/cli/commands/objective/view_cmd.py:139,157`

### Phase 2: New Architecture Documentation (HIGH priority)

**Step 2.1: Create `docs/learned/architecture/validation-gates.md`** _(from #7844, #7825)_
- Document two-phase validation pattern (pre-normalization salvageability + post-normalization validation)
- Reference implementation: `normalize_tripwire_candidates.py:121-139` (check_salvageable) and lines 173-178 (post-validation)
- Include agent error message design pattern from `tripwire_candidates.py:54-72`
- Cross-reference: `discriminated-union-error-handling.md`, `agent-backpressure-gates.md`
- Verification: File exists with frontmatter

**Step 2.2: Create `docs/learned/architecture/branch-slug-generator.md`** _(from #7858)_
- Document `BranchSlugGenerator` architecture, system prompt design, post-processing pipeline
- Reference: `src/erk/core/branch_slug_generator.py`
- 5 integration points: plan_save, plan_migrate_to_draft_pr, setup_impl_from_issue, one_shot_dispatch, submit
- Include testing pattern with FakePromptExecutor
- Verification: File exists with frontmatter

**Step 2.3: Update `docs/learned/architecture/plan-save-branch-restoration.md`** _(from #7822)_
- Add `one_shot_dispatch.py` as second usage site for `commit_files_to_branch`
- Source: `one_shot_dispatch.py:239-244`
- Verification: Both usage sites documented

### Phase 3: New Planning/Session Documentation (MEDIUM priority)

**Step 3.1: Create `docs/learned/sessions/session-upload-branches.md`** _(from #7821)_
- Document `async-learn/{plan_id}` branch format, creation from `origin/master`, force-push idempotency
- Reference: `upload_session.py:101-125`
- Verification: File exists, references correct branch prefix

**Step 3.2: Create `docs/learned/planning/backend-checkout-patterns.md`** _(from #7820)_
- Document draft-PR vs issue backend checkout differences
- Reference: `branch/checkout_cmd.py:440-460`
- Three-tier branch availability: `worktree_branch > pr_head_branch > inferred`
- Verification: File exists with frontmatter

**Step 3.3: Create `docs/learned/planning/impl-folder-setup.md`** _(from #7820)_
- Document `.impl/` folder creation during plan checkout
- Reference: `branch/checkout_cmd.py:279-328` (`_setup_impl_for_plan()`)
- Verification: File exists with frontmatter

**Step 3.4: Update `docs/learned/planning/one-shot-workflow.md`** _(from #7822)_
- Add section on git plumbing approach (commit_files_to_branch) replacing checkout pattern
- Source: `one_shot_dispatch.py:239-244`

### Phase 4: New CLI/Integration Documentation (MEDIUM priority)

**Step 4.1: Create `docs/learned/erk-dev/release-process.md`** _(from #7839)_
- Resolve phantom reference in `docs/learned/erk-dev/index.md`
- Document release learnings from PR #7832: Step 9 git commands, activate.sh limitations, Graphite branch naming
- Source: `RELEASING.md` (current, 155 lines)
- Verification: File exists, phantom reference resolved

**Step 4.2: Update `docs/learned/cli/erk-exec-commands.md`** _(from #7804)_
- Add `get-pr-view` to PR Operations section
- Source: `src/erk/cli/commands/exec/scripts/get_pr_view.py`
- Verification: Command listed in PR Operations table

**Step 4.3: Update `docs/learned/architecture/github-api-rate-limits.md`** _(from #7804)_
- Add tripwire for general `gh pr view` usage directing to `erk exec get-pr-view`
- Existing: Only specific `gh pr view --json merged` tripwire exists (lines 23-25)
- Verification: General `gh pr view` tripwire exists

**Step 4.4: Update `docs/learned/erk/branch-naming.md`** _(from #7858, #7821)_
- Add LLM-based slug generation section with before/after examples
- Add `async-learn/{plan_id}` as third branch type
- Verification: Three branch type categories documented

### Phase 5: Tripwire Updates (HIGH priority, done after content steps)

**Step 5.1: Update `docs/learned/tui/tripwires.md`** _(from #7859)_
- Add: Stage detection by substring matching in `format_lifecycle_with_status()`
- Add: TUI column width calculation for emojis (2 visual columns)
- Source: `lifecycle.py:69-100`, `plan_table.py`

**Step 5.2: Update `docs/learned/testing/tripwires.md`** _(from #7859, #7835, #7822)_
- Add: Shared temp directory scanning anti-pattern for xdist
- Add: PlanRowData field addition requires 5-place coordination
- Add: Test assertion migration when commit mechanism changes (branch_commits vs commits)
- Add: Incomplete test discovery when refactoring shared functions

**Step 5.3: Update `docs/learned/objectives/tripwires.md`** _(from #7844, #7829)_
- Add: update-objective-node requires --plan flag with three-state pattern
- Add: Run `erk objective check` after manual YAML edits

**Step 5.4: Update `docs/learned/erk/tripwires.md`** _(from #7858, #7829)_
- Add: Branch slug generation tripwire (MUST call generate_slug_or_fallback before branch naming)
- Add: Graphite divergence after rebase (run gt track --no-interactive)
- Source: 5 integration points documented in branch-slug-generator.md

**Step 5.5: Update `docs/learned/planning/tripwires.md`** _(from #7820, #7825)_
- Add: Breaking change - `erk br create --for-plan` removed, use `erk br co --for-plan`
- Add: Validation gate placement (validate before issue creation, not after)

**Step 5.6: Update `docs/learned/architecture/tripwires.md`** _(from #7825, #7835)_
- Add: Validation gates vs sanitization (score 6/10)
- Add: PlanRowData frozen dataclass field addition requires 5-place coordination

**Step 5.7: Update `docs/learned/commands/tripwires.md`** _(from #7829)_
- Add: pr-feedback-classifier must use Task tool, not Skill tool

**Step 5.8: Update `docs/learned/cli/tripwires.md`** _(from #7801)_
- Add: Removed `--runs`, `--show-prs`, `--show-runs` flags from TUI plan view

### Phase 6: Update testing.md and discriminated-union docs (MEDIUM priority)

**Step 6.1: Update `docs/learned/testing/testing.md`** _(from #7822, #7844, #7858)_
- Add: branch_commits assertion pattern (FakeGit.branch_commits vs git.commits)
- Add: Discriminated union testing pattern (test return types, not exceptions)
- Add: Stable branch name testing with FakePromptExecutor

**Step 6.2: Update `docs/learned/architecture/discriminated-union-error-handling.md`** _(from #7844)_
- Add: Validation gate section for discriminated union validation results
- Add: Migration section (exception-based to discriminated union)
- Source: `tripwire_candidates.py:40-72`

**Step 6.3: Update `docs/learned/erk/slot-pool-architecture.md`** _(from #7820)_
- Add: `--new-slot` flag decision pattern vs stack-in-place
- Source: `branch/checkout_cmd.py:522-567`

### Phase 7: Run `erk docs sync` to regenerate indexes

**Step 7.1: Run `erk docs sync`**
- Regenerates `docs/learned/index.md` and all `tripwires-index.md` files
- Ensures frontmatter-based tripwire counts are accurate
- Verification: `erk docs sync` completes without errors

## Attribution

Items by source:
- **#7859**: Steps 1.2, 5.1
- **#7858**: Steps 2.2, 4.4, 5.4, 6.1
- **#7844**: Steps 2.1, 5.3, 5.6, 6.1, 6.2
- **#7839**: Step 4.1
- **#7835**: Steps 1.2, 1.4, 5.2, 5.6
- **#7829**: Steps 5.3, 5.4, 5.7
- **#7825**: Steps 2.1, 5.5, 5.6
- **#7822**: Steps 2.3, 3.4, 5.2, 6.1
- **#7821**: Steps 1.1, 3.1, 4.4
- **#7820**: Steps 1.3, 3.2, 3.3, 5.5, 6.3
- **#7819**: (documentation about flag-based approach; existing docs adequate, items merged into planning tripwires)
- **#7804**: Steps 4.2, 4.3
- **#7801**: Steps 1.2, 5.8
