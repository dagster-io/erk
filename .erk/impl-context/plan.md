# Plan: Consolidated Documentation Updates from 35 Learn Sessions

> **Consolidates:** #9281, #9279, #9278, #9275, #9270, #9266, #9264, #9256, #9252, #9246, #9245, #9244, #9243, #9236, #9235, #9230, #9225, #9222, #9211, #9207, #9205, #9203, #9197, #9195, #9194, #9192, #9191, #9190, #9188, #9187, #9180, #9173, #9170, #9168, #9167

## Source Plans

| # | Title | Items Merged |
| --- | --- | --- |
| #9167 | Update documentation for plan→PR rename and new features | 16 items (mega-plan) |
| #9278, #9275, #9197, #9195, #9190, #9187, #9170, #9168, #9236, #9173, #9252 | Plan→PR rename wave (11 plans) | Overlap with #9167 |
| #9281 | Replace `erk pr rebase` with `erk pr resolve-conflicts` | 1 item |
| #9180 | Add PR status emoji column to Runs tab | 1 item |
| #9205 | Add implementation failure summary to remote CI | 1 item |
| #9203 | Pass claude CLI prompts via stdin to avoid ARG_MAX | 1 item |
| #9266, #9264 | NPX skills management + npx-skills skill creation | 2 items |
| #9235, #9230 | erk-planning skill deletion + tombstone | 1 item (overlap) |
| #9225 | Teleport slot awareness | 1 item |
| #9222 | UV workspace explicit members | 1 item |
| #9246, #9279, #9270, #9256, #9188, #9194, #9245, #9244, #9243, #9211, #9207, #9192, #9191 | 13 plans with complete/no docs needed | 0 items |

## What Changed Since Original Plans

- All 35 source PRs are **merged to master** — documentation captures completed work
- Plan→PR rename is fully complete across codebase
- `erk pr rebase` replaced by `erk pr resolve-conflicts`
- NPX skills ecosystem adopted (skill-creator migrated, npx-skills skill created)
- erk-planning skill deleted with tombstone pattern

## Investigation Findings

### Corrections to Original Plans

- **#9167** (mega-plan): Config section renamed `[plans]` → `[github]` — 6 docs still reference old name
- **#9236**: PlanBackend → ManagedPrBackend rename needs propagation to 2 architecture docs
- **#9235/#9230**: These two plans overlap — both document erk-planning deletion from different angles
- **#9281**: `rebase-confirmation-workflow.md` is now completely stale (documents deleted command)

### Items Already Documented (No Action Needed)

20 of 35 plans produced changes that are already fully documented:
- #9279, #9270, #9256, #9252, #9246, #9245, #9244, #9243, #9211, #9207, #9192, #9191, #9188, #9194, #9173 — existing docs cover these changes
- #9278, #9275, #9197, #9195, #9190, #9187 — subsumed by mega-plan #9167

### Overlap Analysis

- **Plan→PR rename**: 12 plans all feed into mega-plan #9167's scope
- **erk-planning deletion**: #9235 and #9230 are two phases of the same work
- **NPX skills**: #9266 (migration) and #9264 (new skill) are complementary

## Remaining Gaps

Organized by priority and grouped by documentation area.

## Implementation Steps

### Step 1: Fix stale `[plans]` → `[github]` config references _(from #9167)_

**Files to update:**
- `docs/learned/configuration/config-layers.md` — lines 51, 75: change `[plans]` → `[github]`
- `docs/learned/configuration/issues-repo.md` — lines 19, 28, 34: change `[plans]` → `[github]`
- `docs/learned/planning/cross-repo-plans.md` — lines 24, 34: change `[plans]` → `[github]`
- `docs/learned/glossary.md` — lines 345, 349, 387: change `[plans]` → `[github]`

**Verification:** `grep -r '\[plans\]' docs/learned/` returns no matches

### Step 2: Update PlanBackend → ManagedPrBackend references _(from #9236)_

**Files to update:**
- `docs/learned/architecture/plan-backend-migration.md` — update ABC class name references (preserve `PlannedPRBackend` implementation class name)
- `docs/learned/architecture/gateway-vs-backend.md` — lines 6, 9-10, 60: update ABC class name

**Verification:** `grep -r 'PlanBackend' docs/learned/` returns no matches (except where referring to migration history)

### Step 3: Rewrite rebase-confirmation-workflow.md for resolve-conflicts _(from #9281)_

**File:** `docs/learned/cli/rebase-confirmation-workflow.md`

**Content outline:**
1. Rename or rewrite to document `erk pr resolve-conflicts` command
2. Remove mechanical rebase initiation paths (gt restack, git rebase)
3. Document new scope: requires active rebase in progress
4. Keep confirmation workflow pattern (still applies)
5. Add error message for "no rebase in progress"

**Also update:** `docs/learned/cli/workflow-commands.md` line 17 — change `pr rebase` → `pr resolve-conflicts`

**Source:** `/workspaces/erk/src/erk/cli/commands/pr/resolve_conflicts_cmd.py`

**Verification:** No references to `erk pr rebase` remain in docs/learned/

### Step 4: Verify and fix stale function references _(from #9167)_

**Files to check:**
- `docs/learned/testing/import-conflict-resolution.md` — references `parse_plan_number` (verify if renamed to `parse_pr_number`)
- `docs/learned/cli/workflow-run-list.md` — references `extract_plan_number()` (verify)

**Action:** Search codebase for actual function names, update docs to match

**Verification:** All function names in docs match actual source code

### Step 5: Verify TUI field names _(from #9168, #9167)_

**File:** `docs/learned/tui/plan-row-data.md`

**Action:** Check `src/erk/tui/data/types.py` for actual field names (plan_id vs pr_id, plan_url vs pr_url, etc.) and update documentation to match

**Verification:** Field names in doc match `PlanRowData` dataclass definition

### Step 6: Update runs-tab-architecture.md with new column _(from #9180)_

**File:** `docs/learned/tui/runs-tab-architecture.md`

**Content to add:**
- Add `pr_status_display: str` to RunRowData field table (around lines 19-40)
- Add "pr-st" column to column config section (around lines 42-56)
- Note: column appears between "pr" and "branch" columns

**Source:** `src/erk/tui/data/types.py` (RunRowData), `src/erk/tui/widgets/run_table.py` (column config)

**Verification:** RunRowData fields and column list in doc match source code

### Step 7: Create impl-failure-summarization.md _(from #9205)_

**File:** `docs/learned/ci/impl-failure-summarization.md`

**Content outline:**
1. Flow: implementation failure → session JSONL capture → tail extraction → Haiku analysis → PR comment + job summary
2. Exec script: `summarize-impl-failure` using `generate_compressed_xml()`
3. Prompt template: `.github/prompts/impl-failure-summarize.md`
4. Haiku model selection rationale (cost/accuracy trade-off)
5. Integration point: `plan-implement.yml` step at line 325
6. Tripwire: modifying failure summarization without updating prompt template

**Source:** `src/erk/cli/commands/exec/scripts/summarize_impl_failure.py`, `.github/workflows/plan-implement.yml`

**Verification:** Doc accurately describes the flow shown in source files

### Step 8: Update prompt-executor docs for stdin/ARG_MAX _(from #9203)_

**File:** `docs/learned/architecture/subprocess-wrappers.md` (add section)

**Content to add:**
- Python-level stdin pattern: `input=prompt` parameter in `subprocess.run()`
- When ARG_MAX overflow occurs (large diffs, session logs >1MB)
- Distinction from shell `--body-file` temp file patterns
- Applied in `execute_prompt()` and `execute_prompt_passthrough()` methods

**Source:** `src/erk/core/prompt_executor.py` lines 569, 636

**Verification:** Doc describes the actual pattern used in prompt_executor.py

### Step 9: Create npx-skill-management.md _(from #9266, #9264)_

**File:** `docs/learned/capabilities/npx-skill-management.md`

**Content outline:**
1. What is npx skills (Vercel Labs, skills@1.4.5)
2. `.agents/skills/` canonical directory + symlinks to `.claude/skills/`
3. `skills-lock.json` for reproducible installation
4. Migration workflow: bundled → npx-managed (example: skill-creator #9265)
5. Adding skills to `_UNBUNDLED_SKILLS` registry in `bundled.py`
6. Comparison: npx-managed vs unbundled vs required-bundled
7. Tripwire: installing skills without updating unbundled registry

**Source:** `src/erk/capabilities/skills/bundled.py` (lines 17-38), `skills-lock.json`, `.agents/skills/`

**Verification:** Doc describes current npx-managed skills list matching `.agents/skills/` directory

### Step 10: Create skill-deletion-patterns.md _(from #9235, #9230)_

**File:** `docs/learned/capabilities/skill-deletion-patterns.md`

**Content outline:**
1. Tombstone pattern: keep minimal SKILL.md with "[REMOVED]" description
2. Why tombstones: overwrites stale cached installations in external repos on sync
3. Complete deletion checklist (5-6 locations):
   - `.claude/skills/<name>/SKILL.md` → replace with tombstone
   - `bundled_skills()` dict → add tombstone entry
   - `codex_portable_skills()` → keep for tombstone distribution
   - `pyproject.toml` force-include → remove
   - `AGENTS.md` → remove references
   - Related commands → remove references
4. When to use tombstone vs complete removal
5. Example: erk-planning deletion (2-phase: #9223 deletion + #9228 tombstone)

**Source:** `.claude/skills/erk-planning/SKILL.md` (12-line tombstone), `bundled.py` line 65

**Verification:** Checklist matches the actual locations modified in source PRs

### Step 11: Create teleport-slot-awareness.md _(from #9225)_

**File:** `docs/learned/cli/teleport-slot-awareness.md`

**Content outline:**
1. How teleport now updates slot assignments when operating in-place (mirrors `erk br co`)
2. The `_navigate_to_existing_worktree()` shared helper extraction
3. When slot assignments are updated vs. left unchanged
4. Links to: slot-pool-architecture.md, checkout-teleport-split.md

**Source:** `src/erk/cli/commands/pr/teleport_cmd.py`

**Verification:** Doc describes behavior matching teleport_cmd.py implementation

### Step 12: Create uv-workspace-configuration.md _(from #9222)_

**File:** `docs/learned/config/uv-workspace-configuration.md`

**Content outline:**
1. Why explicit member lists preferred over globs
2. Impact of stray directories on `uv sync` (error: missing pyproject.toml)
3. Current explicit members: erk-dev, erk-mcp, erk-shared, erk-statusline
4. Trade-off: manual updates when adding packages vs. resilience to stray dirs
5. Tripwire: adding new workspace package without updating pyproject.toml members list

**Source:** Root `pyproject.toml` workspace configuration

**Verification:** Member list in doc matches `pyproject.toml` `[tool.uv.workspace]` section

### Step 13: Create new docs from mega-plan #9167 _(from #9167)_

**Files to create:**

1. **`docs/learned/testing/fakes-directory-structure.md`**
   - Rule: test fakes live in `tests/fakes/`, not production code
   - Tripwire: "creating a fake in src/" should point here

2. **`docs/learned/cli/workflow-run-management.md`**
   - Document `erk workflow run cancel` and `erk workflow run retry` commands
   - Source: Plan #9158

3. **`docs/learned/architecture/json-dataclass-utilities.md`**
   - Document consolidated JSON/dataclass utilities in erk_shared
   - Source: Plan #9155

4. **`docs/learned/cli/exec-review-activity-log.md`**
   - Document `erk exec get-review-activity-log` push-down command
   - Source: Plan #9141

5. **`docs/learned/erk/stack-sync.md`**
   - Document `erk stack sync` hidden command
   - Source: Plan #9137

**Verification:** Each new file has proper frontmatter, read-when conditions, and accurate code references

### Step 14: Update index files and tripwires

**Files to update:**
- `docs/learned/ci/index.md` — add impl-failure-summarization.md entry
- `docs/learned/capabilities/index.md` — add npx-skill-management.md and skill-deletion-patterns.md entries
- `docs/learned/cli/index.md` — add teleport-slot-awareness.md, workflow-run-management.md, exec-review-activity-log.md entries
- `docs/learned/config/index.md` — add uv-workspace-configuration.md entry
- `docs/learned/testing/index.md` — add fakes-directory-structure.md entry
- `docs/learned/erk/index.md` — add stack-sync.md entry
- `docs/learned/architecture/index.md` — add json-dataclass-utilities.md entry

**Verification:** All new docs appear in their category index

## Attribution

Items by source plan group:
- **#9167 (mega-plan)**: Steps 1, 4, 5, 13
- **#9236**: Step 2
- **#9281**: Step 3
- **#9168**: Step 5
- **#9180**: Step 6
- **#9205**: Step 7
- **#9203**: Step 8
- **#9266, #9264**: Step 9
- **#9235, #9230**: Step 10
- **#9225**: Step 11
- **#9222**: Step 12
- **All plans**: Step 14
- **No action needed**: #9279, #9270, #9256, #9252, #9246, #9245, #9244, #9243, #9211, #9207, #9192, #9191, #9188, #9194, #9173, #9278, #9275, #9197, #9195, #9190, #9187, #9170

## Verification

After implementation:
1. `grep -r '\[plans\]' docs/learned/` — no stale config references
2. `grep -r 'PlanBackend' docs/learned/` — no stale ABC references (except migration history)
3. `grep -r 'erk pr rebase' docs/learned/` — no stale command references
4. All new files have proper YAML frontmatter with `read_when` and `last_audited` fields
5. All index files updated with new entries
6. All code references verified against current source
