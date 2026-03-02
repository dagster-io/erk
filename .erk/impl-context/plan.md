# Plan: Consolidate documentation from Mar 2 learn sessions

> **Consolidates:** #8587, #8584, #8583, #8582, #8581, #8578, #8576, #8572, #8566, #8565, #8564, #8562

## Context

Twelve learn plans were created from implementation sessions on Mar 1-2, 2026. These plans capture documentation opportunities from recently merged PRs. This consolidated plan merges overlapping items and organizes them into actionable documentation steps.

## Source Plans

| # | Title | Items Merged | Cluster |
| --- | --- | --- | --- |
| 8587 | Skip learn plan creation when no session material | 3 items | Learn Lifecycle |
| 8576 | Fix `erk land` hanging when no sessions for learn plan | 2 items | Learn Lifecycle |
| 8566 | Update CHANGELOG.md with recent features and fixes | 1 item | Learn Lifecycle |
| 8582 | Eliminate master checkout from plan-save and dispatch | 3 items | Git Plumbing |
| 8578 | Convert `_submit_draft_pr_plan` to Git Plumbing | 2 items | Git Plumbing |
| 8584 | Refactor download_remote_session.py to use read_file_from_ref gateway | 1 item | Gateway |
| 8583 | Standardize exec script terminology (Phase 5, nodes 5.3-5.5) | 1 item | CLI/Exec |
| 8581 | Show workflow source and switch run list to PR-centric view | 2 items | CLI/Workflow |
| 8562 | Move `erk run` under `erk workflow run` command hierarchy | 1 item | CLI/Workflow |
| 8572 | Fix rebase shortcut key from 'f' to 'r' | 1 item | TUI |
| 8564 | Unify Launch Modal and Command Palette | 2 items | TUI |
| 8565 | Document mid-rebase recovery for `erk pr rebase` | 1 item | Architecture |

## Investigation Findings

### Corrections to Original Plans

- **#8587**: Guard condition reverted from `if not xml_files:` to `if not all_session_ids:`. Two tests removed. Possible regression.
- **#8578**: Actual target file was `dispatch_cmd.py`, not `submit.py` as named in the plan title.
- **#8572 + #8564**: Tests in `test_launch_screen.py` still assert key "f" instead of "r" — stale after PR #8560.

### Overlap Analysis

1. **Learn Lifecycle cluster** (#8587, #8576, #8566): All three address learn plan creation edge cases. #8576 fixed the hang, #8587 refined the skip guard, #8566 is an empty learn plan demonstrating the scenario. Merged into single doc item.
2. **Git Plumbing cluster** (#8582, #8578): Both document replacing checkout-based operations with git plumbing. `plan-save-branch-restoration.md` already exists but is incomplete. Merged into single doc update.
3. **TUI cluster** (#8572, #8564): Both affect the command registry / launch screen. `tui-command-registration.md` and `keyboard-shortcuts.md` exist but need updates. Merged into single doc update.
4. **CLI/Workflow cluster** (#8581, #8562): Run list refactoring and command hierarchy reorganization. Both affect the `erk workflow run` subcommand. Merged into single doc item.

## Implementation Steps

### Step 1: Update git plumbing architecture doc _(from #8582, #8578)_

**File:** `docs/learned/architecture/plan-save-branch-restoration.md`

**Changes:**
- Rename to `git-plumbing-patterns.md` to reflect broader scope
- Add section documenting the `update_local_ref` pattern from #8582 (fetch + update-ref replaces checkout + pull)
  - Source: `src/erk/cli/commands/pr/dispatch_helpers.py` `ensure_trunk_synced()` function
  - Gateway: `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/abc.py` `update_local_ref()` method
- Add section documenting the `commit_files_to_branch` pattern from #8578
  - Source: `src/erk/cli/commands/pr/dispatch_cmd.py` `_dispatch_planned_pr_plan()` function
  - Pattern: Build files in-memory via `build_impl_context_files()`, commit via `commit_files_to_branch()` — no checkout needed
- Add "When to use which" comparison table: update_local_ref (advance branch pointer) vs commit_files_to_branch (create commit without checkout) vs create_branch(force=True) (sync local to remote)
- Update frontmatter read_when to include: "eliminating git checkouts", "plumbing operations", "dispatch without checkout"
- Add tripwire: "When adding new git operations, prefer plumbing (update-ref, commit-tree) over checkout-based workflows"

**Verification:** Document accurately describes patterns in dispatch_helpers.py and dispatch_cmd.py

### Step 2: Update learn plan lifecycle documentation _(from #8587, #8576, #8566)_

**File:** `docs/learned/cli/land-learn-integration.md`

**Changes:**
- Add "Skip Guards" section documenting the two skip scenarios:
  1. No sessions tracked at all (e.g., manual CHANGELOG PRs)
  2. Sessions exist but XML extraction produces no content (warmup/empty sessions)
- Document the guard condition: `if not all_session_ids:` early return at `land_learn.py:373-375`
- Add "Session Discovery Pipeline" subsection:
  - `SessionsForPlan` → `get_readable_sessions()` → `_compute_session_stats()` → XML chunks
  - Type prefixing: `planning-`, `impl-`, `learn-` for XML filenames
  - Multi-chunk naming: `{prefix}-{sid}-part{N}.xml`
- Document fire-and-forget error handling: `_create_learn_pr_with_sessions()` catches all exceptions, reports as warnings
- Add note about cycle prevention: plans with `erk-learn` label skip learn plan creation
- Reference the hang fix from PR #8576: early return prevents nested Claude subprocess call
- Update frontmatter read_when to include: "learn plan creation", "session discovery", "empty learn plan"

**Verification:** Document matches current implementation in `land_learn.py` lines 345-434

### Step 3: Update TUI command registration doc _(from #8564, #8572)_

**File:** `docs/learned/tui/tui-command-registration.md`

**Changes:**
- Update "Single Source of Truth" section to document the `launch_key` field on `CommandDefinition` (added in PR #8559)
  - Source: `src/erk/tui/commands/types.py:60` — `launch_key: str | None`
  - Registry: `src/erk/tui/commands/registry.py` — 10 commands have launch_key assignments
- Document current launch key assignments:
  - Plan view: c (close), d (dispatch), l (land), r (rebase), a (address), w (rewrite), m (cmux)
  - Objective view: c (close), s (one-shot), k (check)
- Note the key change: rebase_remote changed from "f" to "r" (PR #8560) for mnemonic consistency
- Document view-mode isolation: plan and objective keys are independent namespaces
- Add note about `_key_to_command_id` dict construction in `LaunchScreen.__init__()`

**File:** `docs/learned/tui/keyboard-shortcuts.md`

**Changes:**
- Update launch key table with current assignments (especially r for rebase, w for rewrite, m for cmux)
- Add note that launch keys are now defined in `registry.py` CommandDefinition objects, not a separate LAUNCH_KEYS dict

**Verification:** Key assignments match `registry.py` lines 230-260

### Step 4: Create workflow run list documentation _(from #8581, #8562)_

**File:** `docs/learned/cli/workflow-run-list.md` (NEW)

**Content outline:**
1. **Command hierarchy**: `erk workflow run list` and `erk workflow run logs` (moved from top-level `erk run` in PR #8549)
2. **PR-centric display**: Runs shown with PR number extracted from run-name format
3. **Run-name format parsing**: `extract_pr_number()` in `shared.py` uses regex `r"#(\d+)"`
   - New format: `"<plan_id>:#<pr_number>:<distinct_id>"`
   - Fallback: plan→PR linkage via `get_prs_linked_to_issues()`
4. **Workflow source column**: Iterates `WORKFLOW_COMMAND_MAP` (6 workflows) and tags each run
5. **Constants**: `_MAX_DISPLAY_RUNS=50`, `_PER_WORKFLOW_LIMIT=20`, `_MAX_TITLE_LENGTH=50`
6. **Deduplication**: Dict-based `seen[run_id]` pattern (O(n) not O(n^2))
7. **learn.yml exception**: No PR number in run-name (runs post-merge, no `pr_number` input)

**Source files:**
- `src/erk/cli/commands/run/list_cmd.py` (192 lines)
- `src/erk/cli/commands/run/shared.py` (42 lines)
- `src/erk/cli/commands/doctor_workflow.py:253` (registration point)

**Frontmatter read_when:** "workflow run list", "erk run", "workflow runs", "run-name format"

**Verification:** Document describes patterns in list_cmd.py and shared.py

### Step 5: Update exec script terminology reference _(from #8583)_

**File:** `docs/learned/cli/erk-exec-commands.md`

**Changes:**
- Add note about Phase 5 terminology standardization (PR #8580):
  - CLI flags: `--plan-issue` → `--learn-plan`
  - Error codes: `missing-plan-issue` → `missing-learn-plan`, `unexpected-plan-issue` → `unexpected-learn-plan`, `no-issue-reference` → `no-plan-reference`, `issue-not-found` → `plan-not-found`
  - YAML schema fields (e.g., `learn_plan_issue`) were NOT renamed (stability)
- Add tripwire: "When adding new exec script parameters, use 'plan' terminology (not 'issue')"

**Source files:**
- `src/erk/cli/commands/exec/scripts/track_learn_result.py` (flag at line 76)
- `src/erk/cli/commands/exec/scripts/impl_signal.py` (error codes at lines 191, 304, 383, 408)

**Verification:** Error codes match current implementation in both scripts

### Step 6: Update gateway refactoring documentation _(from #8584)_

**File:** `docs/learned/architecture/gateway-abc-implementation.md`

**Changes:**
- Add `download_remote_session.py` as a completed migration example in the "Completed Migrations" section
- Note the pattern: `subprocess.run(["git", "show", ...])` → `git.commit.read_file_from_ref(ref, path)`
- Document that all callers of `read_file_from_ref` are now gateway-based (fetch_sessions, push_session, get_learn_sessions, download_remote_session)

**Verification:** `download_remote_session.py` lines 77-86 use gateway call

### Step 7: Update rebase conflict patterns doc _(from #8565)_

**File:** `docs/learned/architecture/rebase-conflict-patterns.md`

**Changes:**
- Verify the "Mid-Rebase Recovery" section added by PR #8544 is present and accurate
- If already complete (likely, since PR #8544 merged), no changes needed — mark as verified
- Ensure read_when includes "resuming a rebase with conflicts"

**Verification:** Section exists and matches `rebase_cmd.py` help text

### Step 8: Update category tripwires _(from all plans)_

**File:** `docs/learned/architecture/tripwires.md`

**New tripwires to add:**
- "When adding git operations, prefer plumbing (update-ref, commit-tree) over checkout-based workflows. See git-plumbing-patterns.md" _(from #8582, #8578)_
- "When adding exec script parameters, use 'plan' terminology not 'issue'. See erk-exec-commands.md" _(from #8583)_

**File:** `docs/learned/cli/tripwires.md`

**New tripwires to add:**
- "When adding launch keys to TUI commands, assign in CommandDefinition.launch_key in registry.py. See tui-command-registration.md" _(from #8564)_
- "Learn plan creation may skip silently when no sessions exist. Check land-learn-integration.md before modifying skip guards" _(from #8587, #8576)_

**Verification:** Run `erk docs sync` after adding tripwires to regenerate index

## Attribution

Items by source:
- **#8582, #8578**: Step 1 (git plumbing patterns)
- **#8587, #8576, #8566**: Step 2 (learn plan lifecycle)
- **#8564, #8572**: Step 3 (TUI command registration)
- **#8581, #8562**: Step 4 (workflow run list)
- **#8583**: Step 5 (exec terminology)
- **#8584**: Step 6 (gateway refactoring)
- **#8565**: Step 7 (rebase conflict patterns)
- **All**: Step 8 (tripwires)
