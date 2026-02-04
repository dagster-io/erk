# Plan: Consolidated Documentation from 7 Learn Plans

> **Consolidates:** #6701, #6698, #6693, #6690, #6689, #6679, #6675

## Source Plans

| # | Title | Items Merged | Status |
| --- | --- | --- | --- |
| 6701 | Preserve Thinking Blocks and Metadata in Session Preprocessor | 7 items | NOT IMPLEMENTED - preprocessor drops metadata |
| 6698 | Extract objective-next-plan data fetching into forked Task | 7 items | Code done (PR #6691), docs NOT done |
| 6693 | Fix doc-audit to allow inlined constants | 3 items | NOT IMPLEMENTED |
| 6690 | Fix codespace creation: REST API bypass | 6 items | Code done (PR #6663), docs ~25% done |
| 6689 | PR Address: Wrap constants behind @cache | 4 items | FULLY IMPLEMENTED by PR #6692 (open) |
| 6679 | Abstract os.execvp Behind Gateway | ~5 items | Code done (#6677), docs NOT done |
| 6675 | Doc Audit Review Implementation | 6 items | 1/6 done, 3 NOT done |

## What Changed Since Original Plans

- PR #6663 merged (codespace REST API fix) - code complete, docs needed
- PR #6691 merged (objective-next-plan refactor) - code complete, docs needed
- PR #6692 open (learn pipeline resilience + codex registries docs) - implements #6689 fully
- Commit 51c9bef70 landed (constants exception in doc-audit) - code complete, docs needed
- AgentLauncher gateway fully implemented (#6677) - docs needed

## Investigation Findings

### Plans Already Implemented (can be closed without new work)
- **#6689**: Fully implemented by PR #6692 (awaiting merge). All items verified.

### Plans with Code Done but Docs Needed
- **#6698**: 5 tripwires + 1 new doc + 1 doc update
- **#6690**: github-cli-limits, codespace-patterns, github-interface-patterns updates
- **#6679**: AgentLauncher gateway documentation

### Plans with All Work Remaining
- **#6701**: Session preprocessor metadata documentation (code changes + docs)
- **#6693**: Doc-audit constants exception documentation
- **#6675**: Review development guide, taxonomy, integration patterns

### Overlap Analysis
- **#6690 and #6693** both reference codespace REST API and github-cli-limits.md - MERGED into single step
- **#6689 and #6692** are the same work (PR implements plan) - #6689 ALREADY DONE
- **#6698 and #6675** both touch review/documentation patterns - kept separate (different domains)

## Remaining Gaps (After Filtering Out Implemented Items)

### Category A: Tripwire Additions (HIGH priority - 8 entries across 4 files)

1. **planning/tripwires.md** - Add 3 entries _(from #6698)_
   - Objective context marker `--associated-objective` flag requirement
   - Raw JSON bloat prevention via Task agent delegation
   - Roadmap step marker `--content` field requirement

2. **hooks/tripwires.md** - Add 1 entry _(from #6698)_
   - `${CLAUDE_SESSION_ID}` not available in plain Bash tool contexts

3. **cli/tripwires.md** - Add 1 entry _(from #6698)_
   - Prettier formatting enforced in CI for `**/*.md`

4. **documentation/audit-methodology.md** - Add 1 tripwire to frontmatter _(from #6693)_
   - Broad exclusion rules need explicit exceptions

5. **architecture/tripwires.md** - Add 2 entries _(from #6679)_
   - os.execvp abstraction through AgentLauncher gateway
   - 3-file simplified gateway pattern for NoReturn operations

### Category B: New Documentation Files (MEDIUM priority - 4 files)

6. **reference/objective-summary-format.md** _(from #6698)_
   - Task agent structured output format specification
   - Required sections: OBJECTIVE, STATUS, ROADMAP table, PENDING_STEPS, RECOMMENDED
   - Status mapping (ACTIVE/PLANNING/COMPLETED to pending/done/in_progress/blocked/skipped)

7. **architecture/github-api-diagnostics.md** _(from #6690)_
   - Repository-specific API failure diagnostic methodology
   - Control-repo testing pattern (Step 1-3)
   - GitHub machines endpoint HTTP 500 case study

8. **reviews/development.md** _(from #6675)_
   - Unified guide for creating new GitHub review workflows
   - YAML schema, marker naming, tool restrictions
   - Step-by-step creation checklist
   - When to create new review vs extend existing

9. **ci/review-types-taxonomy.md** _(from #6675)_
   - Decision framework for choosing review types
   - Code quality vs test coverage vs documentation reviews
   - Complementary vs overlapping scope guidelines

### Category C: Existing File Updates (MEDIUM priority - 6 updates)

10. **planning/token-optimization-patterns.md** - Add objective-next-plan worked example _(from #6698)_
    - Task agent prompt structure, model selection (haiku), output format, token savings

11. **architecture/github-cli-limits.md** - Add machines endpoint section _(from #6690, #6693)_
    - `gh codespace create` machines endpoint HTTP 500 bug
    - REST API direct POST workaround with `_get_repo_id()` helper
    - Code reference: `src/erk/cli/commands/codespace/setup_cmd.py`

12. **cli/codespace-patterns.md** - Add setup command flow _(from #6690)_
    - REST API creation flow, DEFAULT_MACHINE_TYPE constant
    - Repository ID lookup via `gh api repos/{owner}/{repo} --jq .id`

13. **review/doc-audit-review.md** - Add constants HIGH VALUE section _(from #6693)_
    - Constants/defaults in prose are HIGH VALUE not DUPLICATIVE
    - Exception rule with rationale

14. **documentation/audit-methodology.md** - Add classification edge cases _(from #6693)_
    - Constants and defaults in prose context
    - Key distinction: scannability vs code duplication

15. **reviews/index.md** - Complete review entries _(from #6675)_
    - Add entries for all 6 reviews (currently only 1/6 documented)

### Category D: Session Preprocessor Work (LOW priority - deferred)

16. **#6701 items** - Session preprocessor thinking blocks and metadata
    - This plan requires CODE CHANGES (not just documentation)
    - Preprocessor actively deletes usage tokens, doesn't handle thinking blocks
    - Recommend: Create a new implementation plan for code changes, not just docs
    - Documentation updates depend on code changes landing first

### Category E: Gateway Documentation (LOW priority - 2 updates)

17. **architecture/gateway-inventory.md** - Add AgentLauncher entry _(from #6679)_
    - 3-file simplified pattern (abc.py, real.py, fake.py)
    - NoReturn type annotation rationale
    - Context integration at 3 locations

18. **architecture/gateway-abc-implementation.md** - Add simplified pattern section _(from #6679)_
    - When to use 3-file vs 5-file pattern
    - Process replacement operations with no dry-run

## Implementation Steps

### Step 1: Add tripwires (Category A)

**Files to modify:**
- `docs/learned/planning/tripwires.md` - Add 3 entries after existing entries
- `docs/learned/hooks/tripwires.md` - Add 1 entry
- `docs/learned/cli/tripwires.md` - Add 1 entry
- `docs/learned/architecture/tripwires.md` - Add 2 entries
- `docs/learned/documentation/audit-methodology.md` - Add frontmatter tripwire

**Verification:** `grep -c "CRITICAL" docs/learned/planning/tripwires.md` count increases by 3

### Step 2: Create new documentation files (Category B)

**Files to create:**
- `docs/learned/reference/objective-summary-format.md`
- `docs/learned/architecture/github-api-diagnostics.md`
- `docs/learned/reviews/development.md`
- `docs/learned/ci/review-types-taxonomy.md`

**Verification:** All 4 files exist with proper frontmatter (title, read_when, tripwires)

### Step 3: Update existing documentation (Category C)

**Files to modify:**
- `docs/learned/planning/token-optimization-patterns.md`
- `docs/learned/architecture/github-cli-limits.md`
- `docs/learned/cli/codespace-patterns.md`
- `docs/learned/review/doc-audit-review.md`
- `docs/learned/documentation/audit-methodology.md`
- `docs/learned/reviews/index.md`

**Verification:** Each file contains the new section/content

### Step 4: Update gateway documentation (Category E)

**Files to modify:**
- `docs/learned/architecture/gateway-inventory.md`
- `docs/learned/architecture/gateway-abc-implementation.md`

### Step 5: Update index files and tripwires-index.md

**Files to modify:**
- `docs/learned/reference/index.md` - Add objective-summary-format entry
- `docs/learned/architecture/index.md` - Add github-api-diagnostics entry
- `docs/learned/reviews/index.md` - Already updated in Step 3
- `docs/learned/ci/index.md` - Add review-types-taxonomy entry
- `docs/learned/tripwires-index.md` - Update tripwire counts

**Verification:** `erk docs sync` runs without errors (if available)

### Step 6: Handle deferred items

- **#6701 (Session preprocessor)**: Create a SEPARATE implementation plan issue for code changes. The documentation can only be written after the code changes land.
- Close #6701 with note linking to new implementation plan.

## Items NOT Included (Already Done)

- **#6689**: Fully implemented by PR #6692 - close with link to PR

## Attribution

Items by source:
- **#6701**: Deferred to new implementation plan (Step 6)
- **#6698**: Steps 1 (tripwires), 2 (objective-summary-format), 3 (token-optimization-patterns)
- **#6693**: Steps 1 (audit-methodology tripwire), 3 (doc-audit-review, audit-methodology, github-cli-limits)
- **#6690**: Steps 2 (github-api-diagnostics), 3 (github-cli-limits, codespace-patterns)
- **#6689**: Already done - close only
- **#6679**: Steps 1 (architecture tripwires), 4 (gateway docs)
- **#6675**: Steps 2 (development.md, review-types-taxonomy), 3 (reviews/index.md)

## Verification

1. Run `make prettier` to format all markdown
2. Run CI checks to verify no formatting issues
3. Confirm all new files have proper frontmatter
4. Verify tripwire counts match in tripwires-index.md