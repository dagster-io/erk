# Plan: Consolidated Documentation from Learn Plans #6512, #6509, #6506, #6505, #6495, #6493

> **Consolidates:** #6512, #6509, #6506, #6505, #6495, #6493

## Source Plans

| #     | Title                                                         | Items Merged |
| ----- | ------------------------------------------------------------- | ------------ |
| #6512 | Address PR #6500 Review Feedback                              | 5 items      |
| #6509 | Add CI Job for erkdesk Tests                                  | 4 items      |
| #6506 | Set up Vitest + React Testing Library for erkdesk             | Cherry-pick  |
| #6505 | Fix trigger-async-learn field name mismatches                 | 5 items      |
| #6495 | Replace Verbatim Source Code with Source Pointers              | 3 items      |
| #6493 | Learned Docs Review for Verbatim Code Detection               | Cherry-pick  |

## What Changed Since Original Plans

- All code implementations are complete and merged to master
- PRs #6498, #6500, #6501, #6504 all shipped successfully
- Two branches have complete documentation ready to merge: P6506 (10 files, 1042 lines) and P6493 (7 files, 415 lines)
- The latest consolidation (commit 2a9f147db) covered different plans (#6484, #6482, etc.), not these

## Investigation Findings

### Overlap Analysis

Three natural groupings emerged:

1. **Exec Script Schema Patterns** (#6512 + #6505): Both document the same TypedDict/cast() pattern for exec script JSON schemas. Merged into unified documentation steps.

2. **erkdesk Testing & CI** (#6509 + #6506): #6506 docs are fully implemented on P6506 branch. #6509 CI-specific docs are NOT implemented. Cherry-pick P6506, then create the missing CI docs.

3. **Verbatim Code / Source Pointers** (#6495 + #6493): #6493 docs are fully implemented on P6493 branch. #6495 source-pointers guide NOT created. Cherry-pick P6493, then create the missing guide.

### Corrections to Original Plans

- **#6512**: Promised 13 doc items, only 3-4 exist. Most were never created.
- **#6509**: All 9 items unimplemented. Learning docs on P6506 cover different scope (testing vs CI patterns).
- **#6505**: All 5 doc items unimplemented. Code fix is solid.
- **#6495**: source-pointers.md guide never created. Category A/B/C system undocumented.

## Implementation Steps

### Phase 1: Cherry-Pick Existing Documentation Branches

#### Step 1: Cherry-pick P6506 branch docs (from #6506)

**Action:** Cherry-pick commit from `origin/P6506-erk-learn-set-up-vitest-r-02-01-1134` to master branch.

**Files added (10 files, +1042 lines):**
- `docs/learned/cli/erkdesk-makefile-targets.md` (191 lines)
- `docs/learned/desktop-dash/vitest-setup.md` (225 lines)
- `docs/learned/testing/erkdesk-component-testing.md` (317 lines)
- `docs/learned/testing/vitest-jsdom-stubs.md` (116 lines)
- `docs/learned/testing/window-mock-patterns.md` (181 lines)
- Updates to `docs/learned/cli/index.md`, `docs/learned/desktop-dash/index.md`, `docs/learned/testing/index.md`, `docs/learned/testing/tripwires.md`, `docs/learned/tripwires-index.md`

**Verification:** `erk docs sync` should report no drift for these files.

#### Step 2: Cherry-pick P6493 branch docs (from #6493)

**Action:** Cherry-pick commit from `origin/P6493-erk-learn-learn-plan-lear-02-01-1100` to master branch.

**Files added (7 files, +415 lines):**
- `docs/learned/ci/review-spec-format.md` (249 lines)
- `docs/learned/review/learned-docs-review.md` (125 lines)
- Updates to `docs/learned/ci/convention-based-reviews.md` (+41 lines - tool constraints section, review table update)
- Updates to `docs/learned/ci/index.md`, `docs/learned/review/index.md`, `docs/learned/review/tripwires.md`, `docs/learned/tripwires-index.md`

**Verification:** Check for merge conflicts in `docs/learned/tripwires-index.md` (modified by both branches).

### Phase 2: Create New Documentation

#### Step 3: Create `docs/learned/cli/exec-script-schema-patterns.md` _(from #6512, #6505)_

**File:** `docs/learned/cli/exec-script-schema-patterns.md`

**Content outline:**
1. **Problem**: Silent failures from dict `.get()` with wrong field names in exec scripts
2. **Pattern**: Define TypedDict in `erk_shared`, use `cast()` for type-safe consumption
3. **Example**: `GetLearnSessionsResultDict` and `SessionSourceDict` (source pointers to `packages/erk-shared/src/erk_shared/learn/extraction/get_learn_sessions_result.py` and `session_source.py`)
4. **Consumer pattern**: `cast(GetLearnSessionsResultDict, result)` then typed access
5. **Session type determination**: Compare `session_id == planning_session_id` (not schema field)
6. **Empty output handling**: When preprocessing returns empty, treat as valid (not error)
7. **LBYL guards**: type check -> value check -> presence check pattern

**Source:** Investigation of #6512 and #6505 found the TypedDict extraction pattern in PR #6504 and field name fixes in PR #6500.

**Verification:** References match actual code in `src/erk/cli/commands/exec/scripts/trigger_async_learn.py`.

#### Step 4: Add exec script tripwires to `docs/learned/cli/tripwires.md` _(from #6512, #6505)_

**File:** `docs/learned/cli/tripwires.md` (UPDATE)

**Add 3 tripwires:**
1. `action: "using dict .get() to access fields from exec script JSON output without a TypedDict schema"` -> Warning about silent filtering failures, link to exec-script-schema-patterns.md
2. `action: "adding a new exec script that produces JSON consumed by another exec script"` -> Warning to define shared TypedDict in erk_shared
3. `action: "filtering session sources without logging which sessions were skipped and why"` -> Warning about silent filtering making debugging impossible

**Source:** #6505 plan identified these tripwires. Investigation confirmed none exist in current tripwires.md.

**Verification:** Grep tripwires.md for new entries after edit.

#### Step 5: Add CI autofix tripwire to `docs/learned/ci/tripwires.md` _(from #6509)_

**File:** `docs/learned/ci/tripwires.md` (UPDATE)

**Add 1 CRITICAL tripwire:**
- `action: "adding a new CI job to the autofix job's needs list"` -> Warning: Only add jobs whose failures can be auto-fixed (format, lint, prettier). Test jobs (erkdesk-tests, unit-tests, integration-tests) should NOT block autofix. Adding them causes the entire pipeline to block on test failures that autofix cannot resolve.

**Source:** Investigation of #6509 confirmed erkdesk-tests correctly excluded from autofix needs. Pattern is non-obvious and needs documentation.

**Verification:** Check `.github/workflows/ci.yml` autofix job needs list matches documented pattern.

#### Step 6: Create `docs/learned/documentation/source-pointers.md` _(from #6495)_

**File:** `docs/learned/documentation/source-pointers.md`

**Content outline:**
1. **When to use**: Code blocks >5 lines that copy implementation details from source
2. **Format**: `<!-- Source: path/to/file.py:START-END -->` + `See \`ClassName.method_name()\` in \`path/to/file.py:START-END\`.`
3. **Category system**:
   - Category A (Remove): Full method bodies, constructor signatures, class definitions
   - Category B (Keep): Short illustrative snippets, external library patterns, config examples
   - Category C (Transform): Partial copies that can become source pointers
4. **Decision checklist**: Is it >5 lines? Does it copy erk source? Will it go stale?
5. **Maintenance**: Pointers may go stale when line numbers change. Acceptable trade-off vs verbatim code rot.
6. **Tooling**: `.github/reviews/learned-docs.md` automatically detects violations in PRs

**Source:** Investigation of #6495 found 235 lines removed, 90 lines of pointers added across 5 files. Pattern proven effective.

**Verification:** Document accurately describes format used in `docs/learned/testing/testing.md` and `docs/learned/architecture/erk-architecture.md`.

#### Step 7: Update `docs/learned/desktop-dash/erkdesk-project-structure.md` _(from #6509)_

**File:** `docs/learned/desktop-dash/erkdesk-project-structure.md` (UPDATE)

**Add Testing section:**
- Vitest + React Testing Library + jsdom
- Test command: `pnpm test` / `make erkdesk-test`
- CI integration: `erkdesk-tests` job in `.github/workflows/ci.yml`
- Link to `docs/learned/desktop-dash/vitest-setup.md` for configuration details

**Source:** Investigation confirmed this section is missing from erkdesk-project-structure.md.

**Verification:** Section accurately reflects CI job configuration in `.github/workflows/ci.yml`.

### Phase 3: Update Indexes and Sync

#### Step 8: Update documentation indexes

**Files:** Various `index.md` files and `docs/learned/tripwires-index.md`

**Actions:**
- Add `exec-script-schema-patterns.md` to `docs/learned/cli/index.md`
- Add `source-pointers.md` to `docs/learned/documentation/index.md`
- Run `erk docs sync` to regenerate auto-generated files
- Verify tripwire counts are correct in `docs/learned/tripwires-index.md`

**Verification:** `erk docs sync` reports no drift.

## Attribution

Items by source:
- **#6512**: Steps 3, 4 (exec script schema docs and tripwires)
- **#6509**: Steps 5, 7 (CI autofix tripwire, erkdesk project structure update)
- **#6506**: Step 1 (cherry-pick P6506 branch - Vitest/testing docs)
- **#6505**: Steps 3, 4 (exec script schema docs and tripwires - merged with #6512)
- **#6495**: Step 6 (source-pointers.md guide)
- **#6493**: Step 2 (cherry-pick P6493 branch - learned docs review)

## Verification

1. Cherry-picks apply cleanly (Steps 1-2)
2. New documentation files created with proper frontmatter (Steps 3, 6)
3. Tripwires added to correct files (Steps 4, 5)
4. `erk docs sync` reports no drift (Step 8)
5. All cross-references and links resolve correctly