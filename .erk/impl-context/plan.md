# Plan: Consolidate documentation from Mar 1 learn sessions

> **Consolidates:** #8527, #8526, #8524, #8521, #8520, #8519, #8518, #8510, #8509

## Context

Nine erk-learn plans were created from implementation sessions on March 1, 2026. Deep investigation of all 9 plans against the current codebase reveals that all source PRs have been merged successfully, but several documentation gaps remain. This plan consolidates the documentation work into a single actionable plan.

## Source Plans

| # | Title | Items Merged |
| --- | --- | --- |
| 8527 | Auto-resolution of pre-existing bot threads in code-move PRs | 1 new doc |
| 8526 | Split health_checks.py into focused subpackage structure | 1 new doc + 1 fix |
| 8524 | Sync changelog with 16 merged commits and update erk-exec reference | 0 (already documented) |
| 8521 | Add cmux workspace integration to dashboard and CLI | 0 (skill doc comprehensive) |
| 8520 | Rename "fix-conflicts" to "rebase" across the codebase | 0 (code gap, not docs) |
| 8519 | Make "p" open objective issue page in Objectives view | 3 doc fixes |
| 8518 | Require branch_name in create_plan_draft_pr, use LLM slugs | 0 (already documented) |
| 8510 | Run fix-formatting before other CI jobs | 1 new doc |
| 8509 | Add pyproject.toml force-include sync test for bundled skills | 1 new doc |

## Investigation Findings

### Already Well-Documented (No Action Needed)

- **#8524**: Changelog standards, inference hoisting, categorization rules all documented
- **#8521**: cmux skill doc at `.claude/skills/cmux/SKILL.md` is comprehensive (216 lines)
- **#8518**: `docs/learned/architecture/inference-hoisting.md` already updated with full pattern
- **#8520**: Core rename complete; erkweb gap is a **code change** (not documentation). The rename pattern is documented in `docs/learned/refactoring/systematic-terminology-renames.md`

### Corrections to Original Plans

- **#8526**: Stale path reference in `docs/learned/testing/erk-package-info-pattern.md` (lines 46, 53, 55) — references old `src/erk/core/health_checks.py` instead of `src/erk/core/health_checks/managed_artifacts.py`
- **#8519**: Three TUI docs have outdated shortcut `i` that should be `p`:
  - `docs/learned/tui/view-aware-commands.md` (line 56)
  - `docs/learned/tui/action-inventory.md` (line 71)
  - `docs/learned/tui/keyboard-shortcuts.md` (line 39)

## Implementation Steps

### Step 1: Fix stale health_checks.py path _(from #8526)_

**File:** `docs/learned/testing/erk-package-info-pattern.md`

Update 3 references from `src/erk/core/health_checks.py` to `src/erk/core/health_checks/managed_artifacts.py`:
- Line 46: function location reference
- Line 53: source comment
- Line 55: see-also reference

**Verification:** Grep for `health_checks.py` in docs/learned/ returns no stale monolithic references

### Step 2: Fix outdated shortcut references in TUI docs _(from #8519)_

Update `open_objective` shortcut from `i` to `p` in 3 files:

- **`docs/learned/tui/view-aware-commands.md`** (line 56): Change shortcut in table
- **`docs/learned/tui/action-inventory.md`** (line 71): Change shortcut in table
- **`docs/learned/tui/keyboard-shortcuts.md`** (line 39): Add context about view-aware dispatching for `p` shortcut

**Verification:** Grep for shortcut `"i"` associated with `open_objective` returns no results

### Step 3: Create pre-existing-detection.md _(from #8527)_

**File:** `docs/learned/pr-operations/pre-existing-detection.md`

**Frontmatter:**
- category: pr-operations
- read-when: handling bot review comments on code-move PRs, understanding auto-resolution of pre-existing issues

**Content outline:**
1. Problem: Code-move PRs trigger bot comments on patterns that existed before restructuring
2. Detection logic: ALL of (bot author + file restructuring in diff + pattern flaggable in original location)
3. Implementation: `pr-feedback-classifier` SKILL.md adds `pre_existing: bool` field and Batch 0
4. Resolution: `pr-address.md` Phase 3 auto-resolves with standard comment, no code changes
5. Preview: `pr-preview-address.md` shows "Pre-Existing Items (Auto-Resolve)" section

**Source:** Investigation of `.claude/skills/pr-feedback-classifier/SKILL.md` lines 40-96, `.claude/commands/erk/pr-address.md` lines 103-122

### Step 4: Create monolith-to-subpackage-pattern.md _(from #8526)_

**File:** `docs/learned/architecture/monolith-to-subpackage-pattern.md`

**Frontmatter:**
- category: architecture
- read-when: splitting a large module into a subpackage, refactoring monolithic files

**Content outline:**
1. Pattern: Split monolithic module into one-file-per-function subpackage
2. Exemplar: `health_checks.py` (1640 lines) → `health_checks/` (27 focused modules)
3. Structure: `__init__.py` as orchestrator, `models.py` for shared types, one module per function
4. Import rules: Canonical submodule paths, no re-exports from `__init__.py`
5. Lazy imports in orchestrator to prevent circular dependencies
6. Comparison with gateway decomposition (same principles)
7. Test migration: Update mock paths to new submodule locations

**Source:** Investigation of `src/erk/core/health_checks/` structure

### Step 5: Create job-ordering-strategy.md _(from #8510)_

**File:** `docs/learned/ci/job-ordering-strategy.md`

**Frontmatter:**
- category: ci
- read-when: modifying CI job dependencies, adding new CI jobs, understanding fix-formatting gating

**Content outline:**
1. Three-tier architecture: check-submission (gate) → fix-formatting (auto-fix) → 7 parallel validation jobs
2. Why: Prevents wasted compute when formatting issues would cause failures
3. Cancellation mechanism: `cancel-in-progress: true` restarts workflow when fix-formatting pushes
4. Job dependencies: All 7 jobs include `fix-formatting` in `needs` list
5. Autofix job: Depends on formatting and validation jobs (not test jobs, per autofix-job-needs.md)
6. Timing: ~2 min if no changes needed, workflow restart if changes pushed

**Source:** Investigation of `.github/workflows/ci.yml` lines 20-482, commit `ba459022561f9ae9`

### Step 6: Create artifact-distribution-sync.md _(from #8509)_

**File:** `docs/learned/testing/artifact-distribution-sync.md`

**Frontmatter:**
- category: testing
- read-when: adding portable skills, modifying pyproject.toml force-include, understanding bundled skill testing

**Content outline:**
1. Three-layer validation pyramid: on-disk inventory → registry consistency → distribution consistency
2. `_get_force_included_skill_names()`: TOML parsing via `tomllib`, extracts skill names from force-include entries
3. `test_codex_portable_skills_match_force_include()`: Asserts exact set match between registry and pyproject.toml
4. Error messages: Actionable guidance for missing/extra entries
5. Guard: `"/" not in skill_name` prevents nested path matches
6. Troubleshooting: Added skill to `codex_portable_skills()` but tests fail → add force-include entry

**Source:** Investigation of `tests/unit/artifacts/test_codex_compatibility.py` lines 39-260, `pyproject.toml` lines 60-77

### Step 7: Run docs sync and verify

After all documentation changes:
1. Run `erk docs sync` to regenerate index files
2. Verify no broken links or stale references
3. Run fast-ci to confirm no regressions

## Attribution

Items by source:
- **#8527**: Step 3
- **#8526**: Steps 1, 4
- **#8524**: No action (already documented)
- **#8521**: No action (skill doc comprehensive)
- **#8520**: No action (code gap, not docs)
- **#8519**: Step 2
- **#8518**: No action (already documented)
- **#8510**: Step 5
- **#8509**: Step 6

## Overlap Analysis

- Steps 4 and 5 share the theme of "architectural patterns documentation" but target different categories
- #8524 and #8518 were both about changelog/branch-slug patterns, but both are already well-documented
- #8520 and #8519 both involve renames/shortcut changes, but #8520 is a code gap while #8519 is a docs gap
