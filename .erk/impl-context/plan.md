# Plan: Update remaining .impl/issue.json references and tripwires in docs/learned/

> **Replans:** #8338

## Context

The erk codebase migrated from `.impl/issue.json` to `.impl/plan-ref.json` as the primary plan reference file. The source code and some docs have been updated, but ~39 occurrences of `.impl/issue.json` remain across ~19 files in `docs/learned/`. These references mislead agents into using the legacy format as primary. This plan (Phase 4 of Objective #8197) updates the remaining documentation.

## What Changed Since Original Plan

- Investigation confirmed that **no codebase changes** have occurred in `docs/learned/` since the plan was created — all target files remain as identified
- Two files (`architecture/issue-reference-flow.md` and `architecture/plan-ref-architecture.md`) are already correct and need no changes
- Some files are in mixed state (body updated but tripwire outdated, or vice versa)

## Investigation Findings

### Corrections to Original Plan
- **2 files already correct** — `issue-reference-flow.md` (priority table correct, plan-ref.json is #1) and `plan-ref-architecture.md` (already documents both formats)
- **`issue-pr-linkage-storage.md` has dual state** — body line 41 already correctly documents plan-ref.json with legacy fallback, but frontmatter/sections still reference issue.json as primary
- **`pr-validation-rules.md` partially updated** — table at line 26 uses plan-ref.json, but tripwire at line 8 still says issue.json

### Key Architectural Context
- `.impl/plan-ref.json` = primary reference file (new format)
- `.impl/issue.json` = legacy fallback (still supported via `read_plan_ref()`)
- `read_plan_ref()` in `erk_shared/impl_folder.py` tries plan-ref.json first, falls back to issue.json transparently
- References should say "`.impl/plan-ref.json` (or legacy `.impl/issue.json`)" — not remove issue.json entirely

## Implementation Steps

### Phase 1: Update document content (11 files)

Each file needs `.impl/issue.json` references updated to use `plan-ref.json` as primary, with legacy note where appropriate.

**1. `docs/learned/pr-operations/checkout-footer-syntax.md`** (3 refs)
   - Line 36: Change "issue number from `.impl/issue.json`" → "plan issue number from `.impl/plan-ref.json`"
   - Line 41: Change `| \`.impl/issue.json\`` → `| \`.impl/plan-ref.json\`` in table
   - Line 55: Update table row for issue number source (if still referencing issue.json)
   - Verification: No remaining `.impl/issue.json` as primary reference

**2. `docs/learned/pr-operations/pr-submit-phases.md`** (1 ref)
   - Line 62: Change "Looks for `.impl/issue.json`" → "Looks for `.impl/plan-ref.json` (or legacy `.impl/issue.json`)"
   - Verification: Phase 3 description matches actual PlanContextProvider behavior

**3. `docs/learned/erk/pr-commands.md`** (3 refs)
   - Line 10 (tripwire): Change "from .impl/issue.json" → "from .impl/plan-ref.json"
   - Line 55: Update table row — `.impl/issue.json` → `.impl/plan-ref.json`
   - Line 60: Update explanation text
   - Verification: PR number vs issue number table uses plan-ref.json

**4. `docs/learned/erk/issue-pr-linkage-storage.md`** (5 refs)
   - Line 6 (read_when): Change "working with .impl/issue.json" → "working with .impl/plan-ref.json or .impl/issue.json"
   - Line 49 (section header): "Local Worktree: `.impl/issue.json`" → "Local Worktree: `.impl/plan-ref.json` (primary) / `.impl/issue.json` (legacy)"
   - Lines 51-57: Add note that this JSON example shows the legacy format; add plan-ref.json example
   - Line 112: "Check `.impl/issue.json` contains correct number" → "Check `.impl/plan-ref.json` (or legacy `.impl/issue.json`) contains correct plan ID"
   - Line 121: "`.impl/issue.json` was missing" → "`.impl/plan-ref.json` was missing"
   - Verification: Document accurately describes both formats with plan-ref.json as primary

**5. `docs/learned/erk/index.md`** (1 ref)
   - Line 14: Change "working with .impl/issue.json" → "working with .impl/plan-ref.json or .impl/issue.json"
   - Note: This is auto-generated — update the source frontmatter in `issue-pr-linkage-storage.md` (step 4) and run `erk docs sync`

**6. `docs/learned/cli/pr-submission.md`** (4 refs)
   - Line 62: Change "When `.impl/issue.json` exists" → "When `.impl/plan-ref.json` (or legacy `.impl/issue.json`) exists"
   - Line 64: Change "Branch/issue agreement — Branch name pattern `P123-...` must match `.impl/issue.json` issue number" → "...must match `.impl/plan-ref.json` plan ID"
   - Line 81: Change "`.impl/issue.json` contains a `plans_repo` field" → "`.impl/plan-ref.json` contains a `plans_repo` field"
   - Line 113-114: Update ".impl/issue.json" references in auto-repair section
   - Verification: All validation rule descriptions use plan-ref.json as primary

**7. `docs/learned/cli/pr-submit-pipeline.md`** (3 refs)
   - Line 33: Change "validates `.impl/issue.json` linkage" → "validates `.impl/plan-ref.json` linkage (with legacy `.impl/issue.json` fallback)"
   - Line 70-74: Update auto-repair section — "Auto-Repair Pattern: .impl/issue.json Creation" → "Auto-Repair Pattern: .impl/ Reference File Creation"; update body text
   - Verification: Pipeline architecture doc matches actual prepare_state() behavior

**8. `docs/learned/cli/pr-rewrite.md`** (1 ref)
   - Line 41: Change "`.impl/issue.json` primary" → "`.impl/plan-ref.json` primary (with legacy `.impl/issue.json` fallback)" in discover_issue_for_footer description
   - Verification: Issue discovery description matches actual shared utility behavior

**9. `docs/learned/cli/optional-arguments.md`** (1 ref)
   - Line 23: Already has correct priority order (plan-ref.json is #2, issue.json is #3). No content change needed — investigation confirmed this is correct.
   - **SKIP this file** — already correct

**10. `docs/learned/planning/pr-submission-patterns.md`** (3 refs)
   - Line 58: Change "`.impl/issue.json`" → "`.impl/plan-ref.json`" in table
   - Line 61: Update explanation about why agents get confused (reference plan-ref.json)
   - Verification: PR Number vs Issue Number table uses plan-ref.json

**11. `docs/learned/architecture/pr-finalization-paths.md`** (5 refs)
   - Line 13: Change "auto-read from `.impl/issue.json`" → "auto-read from `.impl/plan-ref.json` (or legacy `.impl/issue.json`)"
   - Line 19: Same pattern for Local Path description
   - Line 26: Same pattern for Remote Path description
   - Line 31: Key Principle section — update to reference plan-ref.json
   - Line 35: Anti-Pattern section — update reference
   - Verification: Both paths describe plan-ref.json as primary

**12. `docs/learned/architecture/state-threading-pattern.md`** (1 ref)
   - Line 102: Change "validates `.impl/issue.json` linkage" → "validates `.impl/plan-ref.json` linkage (with legacy fallback)"
   - Verification: Discovery consolidation example matches actual behavior

### Phase 2: Update tripwire frontmatter (4 files)

These are tripwire `action` strings in YAML frontmatter that mention `.impl/issue.json`:

**1. `docs/learned/pr-operations/checkout-footer-syntax.md`** line 8
   - Change: `"writing checkout footer with issue number from .impl/issue.json"` → `"writing checkout footer with issue number from .impl/plan-ref.json"`

**2. `docs/learned/pr-operations/pr-validation-rules.md`** line 8
   - Change: `"using issue number from .impl/issue.json in a checkout footer"` → `"using issue number from .impl/plan-ref.json in a checkout footer"`

**3. `docs/learned/erk/pr-commands.md`** line 10
   - Change: `"from .impl/issue.json"` → `"from .impl/plan-ref.json"` (within the existing action text)

**4. `docs/learned/planning/pr-submission-patterns.md`** line 11
   - Change: `"using issue number from .impl/issue.json in a checkout footer"` → `"using issue number from .impl/plan-ref.json in a checkout footer"`

### Phase 3: Regenerate auto-generated index files

After all frontmatter changes:
- Run `erk docs sync` to regenerate all tripwire index files and category index files
- This will update: `pr-operations/tripwires.md`, `erk/tripwires.md`, `planning/tripwires.md`, `erk/index.md`, and any other affected auto-generated files

### Phase 4: Audit remaining references

After Phase 1-3, grep `docs/learned/` for any remaining `.impl/issue.json` references:
- References in `issue-reference-flow.md` and `plan-ref-architecture.md` are **intentional** (they document the legacy format)
- Any other remaining references should be evaluated — they may be in context where mentioning the legacy format is appropriate

## Verification

1. `grep -r "impl/issue.json" docs/learned/ | grep -v "legacy\|fallback\|issue-reference-flow\|plan-ref-architecture"` — should return no results (all remaining mentions should be in legacy context or in the two exempt files)
2. Run `erk docs sync` — should complete without errors
3. Spot-check 3 auto-generated tripwire files to confirm `.impl/plan-ref.json` appears in tripwire text
4. Run `make fast-ci` to confirm no formatting issues
