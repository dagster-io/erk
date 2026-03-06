# Plan: Consolidate documentation from 14 erk-learn plans

> **Consolidates:** #8840, #8839, #8837, #8833, #8822, #8818, #8817, #8816, #8815, #8813, #8806, #8803, #8802, #8798

## Context

14 erk-learn plans have accumulated from recent implementation sessions. Each captures documentation opportunities discovered during development. This plan consolidates them into actionable documentation updates, eliminating overlap and prioritizing by value.

## Source Plans

| # | Title | Items Merged |
| --- | --- | --- |
| 8840 | Upgrade code-stats date parsing to LLM-intelligent | 1 item (LLM parameter pattern) |
| 8839 | Fix is_rebase_in_progress in git worktrees | 2 items (git_dir distinction, worktree state) |
| 8837 | Upgrade astral-sh/setup-uv v5 to v7 | 0 items (pure implementation, no docs) |
| 8833 | Split test_capabilities.py into subpackage | 1 item (fix stale references) |
| 8822 | Replace Claude CLI subprocess with Anthropic API | 2 items (LlmCaller migration, commit gen update) |
| 8818 | Mechanical rebase with Claude TUI fallback | 1 item (two-phase rebase pattern) |
| 8817 | ObjectiveNodesScreen modal (b key) | 1 item (modal reference update) |
| 8816 | Branch name in workflow run-name | 1 item (run-name format update) |
| 8815 | Extract CI check formatting to shared module | 1 item (TUI formatting module) |
| 8813 | Attribute pushes to github-actions[bot] | 0 items (reverted, docs already current) |
| 8806 | Move code-reviews into ci.yml | 0 items (already well-documented) |
| 8803 | Parallelize extract_diff and fetch_plan_context | 2 items (pipeline update, phase refs) |
| 8802 | Remove PR cache polling from submit | 1 item (removal rationale) |
| 8798 | Fix incremental-dispatch robustness | 2 items (plumbing patterns, index sync) |

## Investigation Findings

### Plans with No Documentation Work

- **#8837** (setup-uv upgrade): Pure CI implementation task. No documentation deliverables.
- **#8813** (github-actions[bot] attribution): Implementation was reverted by PR #8812. `github-token-scopes.md` already reflects current state.
- **#8806** (code-reviews in ci.yml): Already comprehensively documented in `job-ordering-strategy.md`, `automated-review-system.md`, and `convention-based-reviews.md`.

### Overlap Analysis

- **#8803 + #8802**: Both touch PR submit pipeline docs. Merged into steps 4-5.
- **#8839 + #8798**: Both relate to git worktree/plumbing patterns. Merged into steps 1-2.
- **#8822 + #8840**: Both involve LLM/API call patterns. Kept separate as they target different docs.

## Implementation Steps

### Step 1: Update git-plumbing-patterns.md _(from #8798)_

**File:** `docs/learned/architecture/git-plumbing-patterns.md`

**Changes:**
- Add section on checked-out branch handling: conditional logic using `update_local_ref` when branch is checked out vs `create_branch` when not
- Add index sync pattern: `git checkout HEAD --` after plumbing commit to reset stale staged changes
- Add PR #8789 to evolution history section
- Fix line ~75 which incorrectly states `update_local_ref` is only safe for non-checked-out branches

**Source:** Investigation of `src/erk/cli/commands/exec/scripts/incremental_dispatch.py`
**Verification:** Document accurately describes the branch sync logic in incremental_dispatch.py

### Step 2: Update git-graphite-quirks.md _(from #8839)_

**File:** `docs/learned/architecture/git-graphite-quirks.md`

**Changes:**
- Add explicit section on `get_git_dir()` vs `get_git_common_dir()` distinction
- Document that rebase state files (`.git/rebase-merge`, `.git/rebase-apply`) live in per-worktree git directory, not common directory
- Reference the `GitRepoOps.get_git_dir()` method added in PR #8838

**Source:** `src/erk/gateway/git/repo_ops.py` (abc + real implementations)
**Verification:** Document explains why `is_rebase_in_progress` must use `get_git_dir()` not `get_git_common_dir()`

### Step 3: Update commit-message-generation.md _(from #8822)_

**File:** `docs/learned/pr-operations/commit-message-generation.md`

**Changes:**
- Update constructor signature: `CommitMessageGenerator` now takes `llm_caller` instead of `(executor, time, model)`
- Document migration from `PromptExecutor.execute_prompt()` (15+ sec) to `LlmCaller.call()` (2-3 sec)
- Remove references to threading and legacy prompt building
- Cross-reference `docs/learned/architecture/inference-hoisting.md` which already covers LlmCaller pattern

**Source:** `src/erk/core/commit_message_generator.py` (lines 66-157)
**Verification:** Document matches current constructor signature and call pattern

### Step 4: Update pr-submit-pipeline.md _(from #8803, #8802)_

**File:** `docs/learned/cli/pr-submit-pipeline.md`

**Changes:**
- Update from 11-step to 10-step pipeline model
- Document parallelized `extract_diff_and_fetch_plan_context()` using `ThreadPoolExecutor(max_workers=2)`
- Add note that PR cache polling was removed from critical path (PR #8794) — statusline handles PR info display independently
- Reference `docs/learned/architecture/erk-statusline.md` for caching strategy

**Source:** `src/erk/cli/commands/pr/submit_pipeline.py`
**Verification:** Step count and parallelization description matches current implementation

### Step 5: Update pr-submit-phases.md and plan-embedding-in-pr.md _(from #8803)_

**File 1:** `docs/learned/pr-operations/pr-submit-phases.md`
- Update Phase 2 ("Getting diff") and Phase 3 ("Fetching plan context") to note they now run concurrently
- Correct mapping: "6 user-facing phases map to 10 internal pipeline steps" (was 11)

**File 2:** `docs/learned/pr-operations/plan-embedding-in-pr.md`
- Update phase references at lines ~26-27 and ~51 to reflect combined Phase 2/3

**Verification:** Phase descriptions match runtime behavior

### Step 6: Update workflow-run-list.md _(from #8816)_

**File:** `docs/learned/cli/workflow-run-list.md`

**Changes:**
- Add new plan-implement run-name format: `"plnd/fix-auth-bug-01-15-1430 (#460):abc456"`
- Update "Supported formats" section to include branch-name format alongside legacy formats
- Note backward compatibility: `extract_pr_number()` regex `#(\d+)` works with both old and new formats

**Source:** `.github/workflows/plan-implement.yml` (run-name template), `src/erk/cli/commands/run/shared.py`
**Verification:** Example formats in doc match actual workflow run-name template

### Step 7: Fix stale test file references _(from #8833)_

**File 1:** `docs/learned/capabilities/bundled-skills.md` (lines ~63, ~73)
- Change `tests/unit/core/test_capabilities.py` → `tests/unit/core/capabilities/test_skills.py`

**File 2:** `.claude/skills/erk-skill-onboarding/SKILL.md` (lines ~122-123)
- Change `tests/unit/core/test_capabilities.py` → `tests/unit/core/capabilities/test_skills.py`

**Verification:** Referenced test file paths exist on disk

### Step 8: Update modal-screen-pattern.md _(from #8817)_

**File:** `docs/learned/tui/modal-screen-pattern.md`

**Changes:**
- Add `ObjectiveNodesScreen` to the reference implementations list (alongside UnresolvedCommentsScreen, PlanBodyScreen, PlanDetailScreen)
- Note: Features async data loading, phase separators, PR data enrichment, next-node highlighting

**Source:** `src/erk/tui/screens/objective_nodes_screen.py` (529 lines)
**Verification:** ObjectiveNodesScreen appears in reference list

### Step 9: Document two-phase rebase pattern _(from #8818)_

**File:** `docs/learned/cli/pr-operations.md` (or new section in `docs/learned/architecture/rebase-conflict-patterns.md`)

**Changes:**
- Add section documenting the two-phase rebase: Phase 1 attempts mechanical rebase via `gt restack` (Graphite) or `git rebase <target>` (non-Graphite); Phase 2 falls back to Claude TUI with `/erk:rebase` on conflicts
- Document `_is_graphite_enabled()` helper and `--target` option
- Reference `execute_interactive()` for TUI fallback

**Source:** `src/erk/cli/commands/pr/rebase_cmd.py`
**Verification:** Document describes both phases and the fallback trigger condition

### Step 10: Add TUI formatting module tripwire _(from #8815)_

**File:** `docs/learned/tui/tripwires.md`

**Changes:**
- Add tripwire: When adding CI check formatting to TUI screens, use `src/erk/tui/formatting/ci_checks.py` shared module instead of duplicating formatting logic

**Source:** `src/erk/tui/formatting/ci_checks.py` (format_check_line, format_summary_blockquote, format_check_runs)
**Verification:** Tripwire references existing module path

### Step 11: Add LLM-intelligent parameter pattern note _(from #8840)_

**File:** `docs/learned/commands/` (add to existing command patterns doc or as note in `architecture/task-context-isolation.md`)

**Changes:**
- Document pattern: replacing rigid format-matching with LLM interpretation for user-facing parameters
- Example: code-stats date parsing upgraded from fixed format list to flexible natural language (model upgraded haiku→sonnet for accuracy)
- Note: rolling defaults (e.g., "last 30 days") preferred over fixed dates

**Source:** `.claude/commands/local/code-stats.md`
**Verification:** Pattern description matches actual command implementation

## Attribution

| Source Plans | Steps |
| --- | --- |
| #8798 | Step 1 |
| #8839 | Step 2 |
| #8822 | Step 3 |
| #8803, #8802 | Steps 4, 5 |
| #8816 | Step 6 |
| #8833 | Step 7 |
| #8817 | Step 8 |
| #8818 | Step 9 |
| #8815 | Step 10 |
| #8840 | Step 11 |
| #8837, #8813, #8806 | No steps (no documentation needed) |

## Verification

After implementation:
1. Run `erk docs sync` to regenerate auto-generated index files
2. Verify all referenced file paths exist: `grep -r "test_capabilities.py" docs/ .claude/skills/` should return no stale references
3. Spot-check 3 updated docs against source code to confirm accuracy
