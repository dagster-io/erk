# Plan: Consolidated Documentation from 6 Learn Plans

> **Consolidates:** #6420, #6419, #6418, #6417, #6414, #6409

## Source Plans

| #    | Title                                                       | Items Merged |
| ---- | ----------------------------------------------------------- | ------------ |
| 6420 | Fix /erk:pr-address-remote command syntax                   | 2 items      |
| 6419 | Rename /local:todos-clear to /local:tasks-clear             | 1 item       |
| 6418 | Close Review PR When Plan Implementation Starts             | 0 items      |
| 6417 | Embed Plan in PR Description via \<details\> Tag            | 4 items      |
| 6414 | Copy-Pasteable Commands for Plan Issues and Plan-Review PRs | 0 items      |
| 6409 | Add 'Save and submit for review' option to plan mode menu   | 2 items      |

## What Changed Since Original Plans

- **#6418**: ALL items fully implemented (code + docs + tests). No remaining work.
- **#6414**: ALL items fully implemented (code + docs + tests). No remaining work.
- **#6420**: Command artifact fixed (PR #6416), but 5+ documentation files still contain deprecated `erk pr address-remote` syntax.
- **#6419**: Core rename complete (PR #6412). Proposed new documentation files not created.
- **#6417**: Feature code implemented (PR #6407), but 4 documentation files need creation/updates.
- **#6409**: Feature code implemented, but workflow diagram and markers doc need updates.

## Investigation Findings

### Fully Implemented Plans (No Remaining Work)

- **#6418** (Close Review PR): `cleanup_review_pr()` implemented, integrated in both close_cmd.py and land_pipeline.py, lifecycle.md fully documented, fail-open-patterns.md and metadata-archival-pattern.md complete.
- **#6414** (Copy-Pasteable Commands): `format_plan_commands_section()` implemented, Quick Start in review PRs implemented, learn plan exclusion working, comprehensive tests exist.

### Overlap Analysis

- **#6420 + #6419**: Both involve documentation updates after command renames/migrations. Merged into a "command migration documentation" theme.
- **#6417 + #6409**: Both involve documenting recently-implemented plan workflow features. Merged into "plan workflow documentation" theme.

## Remaining Gaps

### Theme A: Deprecated Command Syntax in Documentation (from #6420)

7 files contain deprecated `erk pr address-remote` syntax:
1. `docs/learned/erk/pr-address-workflows.md` - Multiple instances (lines 6, 15, 99-111)
2. `docs/learned/cli/local-remote-command-groups.md` - Multiple instances (lines 20, 40, 82, 96)
3. `docs/learned/architecture/command-boundaries.md` - One instance
4. `docs/learned/erk/remote-workflow-template.md` - One instance
5. `docs/learned/tui/adding-commands.md` - One example instance
6. `docs/learned/erk/index.md` - One read_when reference
7. `docs/learned/cli/workflow-commands.md` - Has migration table (correct, but verify)

### Theme B: Plan Embedding Documentation (from #6417)

- `docs/learned/pr-operations/plan-embedding-in-pr.md` - Does NOT exist (needs creation)
- `docs/learned/architecture/pr-body-formatting.md` - Does NOT exist (needs creation)
- `docs/learned/pr-operations/pr-submit-phases.md` - Exists but Phase 6 lacks plan embedding details
- `docs/learned/planning/tripwires.md` line 35 - Contradicts working implementation (\<details\> tags DO work after checkout footer)

### Theme C: Plan Mode Workflow Documentation (from #6409)

- `docs/learned/planning/workflow.md` - Flow diagram shows 4 options, missing Option 5 ("Save and submit for review")
- `docs/learned/planning/workflow-markers.md` - Missing `plan-saved-issue` marker documentation

### Theme D: Command Rename Pattern (from #6419)

- `docs/learned/commands/command-rename-pattern.md` - Does NOT exist (pattern worth documenting)

## Implementation Steps

### Step 1: Update deprecated `erk pr address-remote` syntax in docs _(from #6420)_

**Files to modify:**

1. **`docs/learned/erk/pr-address-workflows.md`**
   - Line 6: Update read_when from `erk pr address-remote` to `erk launch pr-address`
   - Line 15: Change `Remote` (`erk pr address-remote`) to `Remote` (`erk launch pr-address --pr <number>`)
   - Lines 99-111: Rename section "Remote Workflow: erk pr address-remote" to "Remote Workflow: erk launch pr-address" and update all command examples
   - Lines 107, 110: Replace `erk pr address-remote 123` with `erk launch pr-address --pr 123`

2. **`docs/learned/cli/local-remote-command-groups.md`**
   - Add historical note at top indicating the Click-based pattern is superseded by `erk launch`
   - Lines 20, 40, 82, 96: Update or annotate deprecated command examples

3. **`docs/learned/architecture/command-boundaries.md`**
   - Update the mapping table entry from `erk pr address-remote <pr>` to `erk launch pr-address --pr <pr>`

4. **`docs/learned/erk/remote-workflow-template.md`**
   - Update command reference from `erk pr address-remote` to `erk launch pr-address --pr <number>`

5. **`docs/learned/tui/adding-commands.md`**
   - Update the display name example from `erk pr address-remote` to `erk launch pr-address --pr`

6. **`docs/learned/erk/index.md`**
   - Update the read_when reference for pr-address-workflows.md

**Verification:** `grep -r "erk pr address-remote\|erk pr address remote" docs/learned/` returns no results (excluding CHANGELOG)

### Step 2: Create plan embedding documentation _(from #6417)_

**File:** `docs/learned/pr-operations/plan-embedding-in-pr.md` (CREATE)

**Content outline:**
1. Feature overview: `<details>` collapsible sections embed plan in PR body
2. Implementation: `_build_plan_details_section()` at `src/erk/cli/commands/pr/submit_pipeline.py:587-599`
3. Critical separation: `pr_body` (git commit, no HTML) vs `pr_body_for_github` (GitHub rendering, with plan)
4. Safe placement: `<details>` blocks appended AFTER checkout footer
5. Issue number in summary for bidirectional navigation
6. Example HTML structure from the test at `test_finalize_pr.py:249-293`

**Verification:** File exists with frontmatter, read_when conditions, and accurate code references

### Step 3: Create PR body formatting pattern doc _(from #6417)_

**File:** `docs/learned/architecture/pr-body-formatting.md` (CREATE)

**Content outline:**
1. Two-target pattern: `pr_body` vs `pr_body_for_github`
2. When to use: Any GitHub-specific enhancement (badges, metadata, embedded plans)
3. Anti-pattern: Putting HTML in git commit messages
4. Implementation reference: `submit_pipeline.py:633-636`
5. Tripwire: Never mix GitHub-specific HTML into commit messages

**Verification:** File exists with frontmatter and accurate references

### Step 4: Update pr-submit-phases.md Phase 6 _(from #6417)_

**File:** `docs/learned/pr-operations/pr-submit-phases.md` (UPDATE)

**Changes:**
- Add to Phase 6 section: Plan embedding via `_build_plan_details_section()` when `plan_context` is present
- Clarify commit message uses `pr_body`, GitHub PR uses `pr_body_for_github`
- Cross-reference to new `plan-embedding-in-pr.md`

**Verification:** Phase 6 mentions plan embedding with correct function name

### Step 5: Fix `<details>` tag tripwire contradiction _(from #6417)_

**File:** `docs/learned/planning/tripwires.md` (UPDATE line 35)

**Change from:**
> HTML `<details>` tags will fail `has_checkout_footer_for_pr()` validation. Use plain text backtick format.

**Change to:**
> HTML `<details>` tags placed BEFORE checkout footer will fail `has_checkout_footer_for_pr()` validation. Safe pattern: append `<details>` blocks AFTER checkout footer. See [Plan Embedding](../pr-operations/plan-embedding-in-pr.md) for the validated approach.

**Verification:** Tripwire no longer contradicts the working implementation

### Step 6: Update workflow.md flow diagram _(from #6409)_

**File:** `docs/learned/planning/workflow.md` (UPDATE lines 118-154)

**Changes:**
- Add 5th option branch "Save and submit for review (E)" to the ASCII flow diagram
- Add a new section "Option E: Save and Submit for Review" describing the 4-step workflow:
  1. Run `/erk:plan-save`
  2. Read `plan-saved-issue` marker
  3. Run `/erk:plan-review <issue_number>`
  4. STOP - stay in plan mode

**Verification:** Flow diagram shows 5 options; Option E section exists with accurate steps

### Step 7: Add `plan-saved-issue` marker to workflow-markers.md _(from #6409)_

**File:** `docs/learned/planning/workflow-markers.md` (UPDATE)

**Changes:**
- Add new use case section "Plan Issue Tracking"
- Document `plan-saved-issue` marker: created by `/erk:plan-save`, read for `/erk:plan-review`
- Show example usage pattern

**Verification:** `plan-saved-issue` marker documented with creation/reading lifecycle

### Step 8: Create command rename pattern doc _(from #6419)_

**File:** `docs/learned/commands/command-rename-pattern.md` (CREATE)

**Content outline:**
1. Workflow: read old -> create new -> delete old -> verify -> CI
2. Quality checklist: command invocation, body text, external references
3. Anti-pattern: mechanical rename without terminology update (issue #6410 example)
4. Grep verification patterns for completeness

**Verification:** File exists with frontmatter and actionable checklist

### Step 9: Run `erk docs sync` to regenerate index files

**Command:** `erk docs sync`

**Verification:** `docs/learned/index.md` and category index files updated with new documents

## Attribution

Items by source:
- **#6420**: Steps 1, 8
- **#6419**: Step 8
- **#6418**: No remaining items (fully implemented)
- **#6417**: Steps 2, 3, 4, 5
- **#6414**: No remaining items (fully implemented)
- **#6409**: Steps 6, 7