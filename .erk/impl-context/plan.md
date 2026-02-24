# Plan: Consolidated Documentation from Feb 23-24 Learn Sessions

> **Consolidates:** #8016, #8013, #8012, #8007, #7996, #7983, #7977, #7960, #7959, #7958, #7957, #7954, #7953, #7951

## Context

14 open erk-learn plans were created from implementation sessions on Feb 22-24, 2026. Each plan captured documentation needs discovered during PRs. Investigation found:

- **1 plan fully complete** (#7977 - stacked PR emoji): All 8 items implemented. Close without consolidation.
- **13 plans with documentation gaps**: Code implementations are complete, but ~130+ documentation items remain unimplemented across the plans.

This consolidated plan deduplicates overlapping items (e.g., Graphite divergence tripwire appears in 3 plans), prioritizes by impact, and organizes into implementable steps.

## Source Plans

| # | Title | Items Merged | Key Themes |
| --- | --- | --- | --- |
| 8016 | Consolidate PR validation into --stage=impl flag | 9 of 13 | PR validation, LBYL, NamedTuple patterns |
| 8013 | Simplify plan-implement workflow with setup-impl | 8 of 12 | Setup-impl command, cwd injection, LBYL ternary |
| 8012 | Fix impl-signal started lifecycle_stage transition | 7 of 8 | YAML metadata, lifecycle stage terminology |
| 8007 | Collapse implementing/implemented into impl stage | 8 of 10 | Lifecycle consolidation, backward compat, write discipline |
| 7996 | Rename prepare properties to checkout in next_steps | 3 of 4 | API naming, format function testing |
| 7983 | Convert submit pipeline to git plumbing | 17 of 19 | Git plumbing, equivalence testing, review system |
| 7960 | Move plan-header metadata to bottom of PR descriptions | 7 of 9 | PR body structure, backward compatibility |
| 7959 | Extract and update PR titles in ci-update-pr-body | 12 of 14 | CI script architecture, merge base detection |
| 7958 | Clear error when trigger_workflow finds skipped run | 6 of 6 | Fail-fast patterns, test-behavior sync |
| 7957 | Fix plan-save branch_name in skipped_duplicate | 9 of 11 | Session markers, dedup response schema |
| 7954 | Restore --oauth flag and refactor plan listing | 6 of 8 | GitHubAdmin variables, OAuth management |
| 7953 | Align plan list with dash layout | 21 of 21 | CLI-TUI data sharing, Rich markup |
| 7951 | Fix _cleanup_no_worktree crash | 7 of 10 | Multi-worktree state, branch deletion |

**Plan #7977 (stacked PR emoji)**: FULLY COMPLETE. Close with comment only.

## Investigation Findings

### Overlap Analysis

These items appeared in multiple plans and are merged:

1. **Graphite divergence after rebase** (3 plans: #7957, #7958, #7959): Merged into single tripwire + doc
2. **Lifecycle stage terminology** (3 plans: #8007, #8012, #8016): Merged into lifecycle.md update + migration guide
3. **YAML metadata format** (2 plans: #8012, #8007): Merged into metadata-blocks.md update
4. **LBYL ternary conversion** (2 plans: #8013, #8016): Merged into conventions.md update
5. **Impl-context cleanup** (2 plans: #7958, #7959): Merged into single doc
6. **Force push after rebase** (2 plans: #7958, #7959): Merged into existing force-push-decision-tree.md

### Corrections to Original Plans

- **#8016**: Exec scripts were NOT removed (plan claimed removal). Skip "exec-to-command migration" doc.
- **#7954**: TUI `copy_implement_local` was NOT removed (plan claimed removal). Skip removal doc.
- **#8007**: lifecycle.md line 179 says "3 locations" but should be "2 locations" after consolidation.
- **#8012**: lifecycle.md Write Points table references `mark-impl-started` instead of `impl-signal started`.
- **#7960**: Plan described "two-tier polling" but implementation uses uniform intervals.

## Implementation Steps

### Step 1: Update lifecycle.md (HIGH PRIORITY)

**File:** `docs/learned/planning/lifecycle.md`

Updates from #8007, #8012, #8016:

1. **Lines 83-85**: Replace `implementing`/`implemented` with `impl` in "Which Phase Am I In?" table
2. **Line 1050**: Replace `mark-impl-started` with `impl-signal started` in Write Points table
3. **After line 1039**: Add "Storage Values vs Display Names" section explaining `impl` (storage) vs `implementing`/`implemented` (display)
4. **Line 179 (tripwire)**: Change "Update 3 locations" to "Update 2 locations"

**Source:** #8007 investigation (lifecycle.py:58, schemas.py:404-409), #8012 investigation (impl_signal.py:252)
**Verification:** Grep for "implementing" and "implemented" in lifecycle.md - should only appear in backward-compat context

### Step 2: Add Critical Tripwires to planning/tripwires.md (HIGH PRIORITY)

**File:** `docs/learned/planning/tripwires.md`

Add these tripwires (all score >= 5):

1. **lifecycle_stage field requirement** (Score 8/10, from #8012): "ALL signal handlers must set `lifecycle_stage` in metadata dict. Missing field causes plans to silently appear stuck at 'planned'."
2. **Write discipline for "impl"** (Score 6/10, from #8007): "Always write `lifecycle_stage: 'impl'` (not 'implementing' or 'implemented'). Schema accepts old values for backward compat but new code must use canonical 'impl'."
3. **Non-fast-forward push during impl-context cleanup** (Score 4/10, from #7959): "Remote branch may have CI commits. Run `git pull --rebase` before retrying cleanup push."

**Source:** #8012 investigation (impl_signal.py:248-261), #8007 investigation (schemas.py:775-788)
**Verification:** `erk docs sync` to regenerate tripwires-index.md

### Step 3: Add Critical Tripwires to testing/tripwires.md (HIGH PRIORITY)

**File:** `docs/learned/testing/tripwires.md`

Add these tripwires:

1. **YAML assertion pattern** (Score 6/10, from #8012): "GitHub issue metadata serializes as YAML, not JSON. Use `'lifecycle_stage: impl\n'` (with trailing newline), not `'\"lifecycle_stage\": \"impl\"'`."
2. **Test-behavior synchronization** (Score 5/10, from #7958): "When changing behavior from 'silent continue' to 'explicit raise', test updates are atomic with code changes. Rename test and update assertions immediately."
3. **Package-specific pytest working directory** (Score 6/10, from #7996): "Running pytest from repo root may fail for packages/erk-shared/ tests with ModuleNotFoundError. Use `pytest packages/erk-shared/` explicitly."

**Source:** #8012 investigation (test_impl_signal.py:340), #7958 investigation (test_real_github.py:628-673)
**Verification:** `erk docs sync` to regenerate

### Step 4: Add Critical Tripwires to erk/tripwires.md (HIGH PRIORITY)

**File:** `docs/learned/erk/tripwires.md`

Add/verify:

1. **Graphite divergence after rebase** (Score 6/10, from #7957, #7958, #7959): "After `git pull --rebase` or `git rebase`, Graphite tracking metadata becomes stale. Run `gt track <branch> --no-interactive` before `gt submit`. Error: 'Cannot perform this operation on diverged branch'."

**Source:** Appears in 3 separate plan investigations
**Verification:** Check existing tripwires.md line 43 - may already partially cover this

### Step 5: Add Tripwires to Other Category Files (HIGH PRIORITY)

**Files:** Various tripwires.md files

1. **`docs/learned/architecture/tripwires.md`**: Add duplicate function definitions tripwire (Score 6/10, from #7957): "Python silently shadows earlier function definitions. No import error when a module contains two `def` with the same name."
2. **`docs/learned/cli/tripwires.md`**: Add Click `\b` literal block tripwire (Score 5/10, from #7957): "String formatting doesn't work inside Click's `\b` literal blocks. Must inline constants."
3. **`docs/learned/cli/tripwires.md`**: Add Rich console URL quoting (Score 6/10, from #7953): "Rich Console `[link=...]` uses unquoted URLs. Quoting the URL breaks the link."
4. **`docs/learned/pr-operations/tripwires.md`**: Add stale merge base detection (Score 6/10, from #7959): "Before addressing bot comments, check merge base distance. If >10 commits behind master, rebase first."

**Source:** Multiple investigations
**Verification:** `erk docs sync` after all tripwire additions

### Step 6: Document YAML Metadata Serialization (HIGH PRIORITY)

**File:** `docs/learned/architecture/metadata-blocks.md` (UPDATE)

Add "Serialization Format" section explaining:
- Metadata renders as YAML (not JSON) via `render_metadata_block()`
- Correct test assertion: `"lifecycle_stage: impl\n"` (YAML with trailing newline)
- Wrong patterns: `'"lifecycle_stage": "impl"'` (JSON), `"lifecycle_stage: impl"` (no newline)

**Source:** #8012 investigation (impl_signal.py:264-270, test_impl_signal.py:340)
**Verification:** Read metadata-blocks.md to confirm section added

### Step 7: Update pr-validation-rules.md with --stage=impl (MEDIUM PRIORITY)

**File:** `docs/learned/pr-operations/pr-validation-rules.md` (UPDATE)

Add "Stage-Specific Checks" section documenting:
- `--stage=impl` flag adds impl-context cleanup validation
- PrCheck NamedTuple pattern (`check_cmd.py:23-25`)
- Impl-context directory existence check

**Source:** #8016 investigation (check_cmd.py:28-92)
**Verification:** Read updated doc

### Step 8: Create Lifecycle Stage Consolidation Guide (MEDIUM PRIORITY)

**File:** `docs/learned/planning/lifecycle-stage-consolidation.md` (CREATE)

Content from #8007 investigation:
- Three-phase backward compatibility pattern (schemas.py:404-409, 775-788)
- Write point consolidation (mark_impl_started.py, impl_signal.py, handle_no_changes.py)
- Display logic normalization (lifecycle.py:58)
- Why old values exist in metadata

**Source:** #8007 investigation
**Verification:** File exists and accurately describes pattern in schemas.py

### Step 9: Create PR Body Structure Documentation (MEDIUM PRIORITY)

**File:** `docs/learned/pr-operations/pr-body-structure.md` (CREATE)

Content from #7960 investigation:
- NEW format (post-#7934): content -> header -> metadata -> footer
- LEGACY format (pre-#7934): header -> content -> footer
- Fallback extraction pattern (`pr_footer.py:105-158`)
- Migration detection API (`is_header_at_legacy_position()` at `pr_footer.py:161-197`)
- Double-separator prevention pattern (3 callers strip `PLAN_CONTENT_SEPARATOR`)

**Source:** #7960 investigation (pr_footer.py, shared.py:243-295, ci_update_pr_body.py:275-294)
**Verification:** File exists with accurate layout diagrams

### Step 10: Update conventions.md (MEDIUM PRIORITY)

**File:** `docs/learned/conventions.md` (UPDATE)

Add sections from #7996, #7957, #7953:

1. **API Naming: Internal/External Alignment**: Internal property names should match user-facing labels (example: `prepare` -> `checkout` from next_steps.py)
2. **Three Similar Lines Principle**: Concrete examples of when NOT to abstract (from AGENTS.md)
3. **Conditional Dict Field Construction**: Build dicts incrementally with LBYL checks (from plan_save.py:326-334)

**Source:** #7996 investigation (next_steps.py:18-89), #7957 investigation (plan_save.py:326-334)
**Verification:** Read conventions.md to confirm sections added

### Step 11: Create ci-update-pr-body Implementation Doc (MEDIUM PRIORITY)

**File:** `docs/learned/cli/ci-update-pr-body-implementation.md` (CREATE)

Content from #7959 investigation:
- Script architecture (ci_update_pr_body.py)
- Title extraction via `_parse_title_and_summary()` (lines 94-104)
- Draft PR handling with metadata preservation (lines 275-294)
- `update_pr_title_and_body()` gateway method (abc.py:442-459)
- JSON output schema change (added `title` field)

**Source:** #7959 investigation
**Verification:** File exists with accurate function references

### Step 12: Create Setup-Impl Command Documentation (MEDIUM PRIORITY)

**File:** `docs/learned/planning/setup-impl-command.md` (CREATE)

Content from #8013 investigation:
- Decision tree priority ordering (setup_impl.py:175-262)
- Source resolution: explicit args -> existing .impl/ -> file-based -> branch detection
- JSON output protocol
- Auto-detection of issue numbers from branch names

**Source:** #8013 investigation (setup_impl.py:175-262)
**Verification:** File exists

### Step 13: Document Remaining Architecture Patterns (LOWER PRIORITY)

Create or update these docs:

1. **`docs/learned/architecture/git-plumbing-patterns.md`** (CREATE, from #7983): Git plumbing vs porcelain decision framework. `commit_files_to_branch()` eliminates checkout-based race conditions.
2. **`docs/learned/architecture/backward-compatibility.md`** (CREATE, from #7960): Fallback scanning pattern, extract-and-rebuild migration, passive migration without explicit command.
3. **`docs/learned/architecture/early-error-detection-patterns.md`** (CREATE, from #7958): Match-first-then-evaluate pattern in trigger_workflow polling.
4. **Update `docs/learned/planning/impl-context.md`**: Add section on `build_impl_context_files()` function (impl_context.py:128-166).

**Source:** Various investigations
**Verification:** Files exist

### Step 14: Document Testing Patterns (LOWER PRIORITY)

Create these docs:

1. **`docs/learned/testing/format-function-testing.md`** (CREATE, from #7996): Pattern for testing user-facing output strings survive refactoring.
2. **`docs/learned/testing/equivalence-testing.md`** (CREATE, from #7983): Pattern for testing in-memory vs filesystem equivalence (test_impl_context.py:352-386).
3. **`docs/learned/testing/plumbing-commit-testing.md`** (CREATE, from #7983): No-checkout verification pattern (test_submit.py:537-609).

**Source:** Various investigations
**Verification:** Files exist

### Step 15: Document CI & Workflow Patterns (LOWER PRIORITY)

Create these docs:

1. **`docs/learned/ci/ci-failure-triage.md`** (CREATE, from #7958): Triage guide for determining if CI failure is from PR changes vs pre-existing master issue.
2. **`docs/learned/planning/impl-context-cleanup-failures.md`** (CREATE, from #7958): Push failure recovery when remote branch advanced during cleanup.
3. **Update `docs/learned/planning/workflow-markers.md`**: Add `plan-saved-branch` marker to catalog (from #7957).
4. **Update `docs/learned/planning/session-deduplication.md`**: Add "Deduplication Response Schema" section (from #7957).

**Source:** #7958, #7957 investigations
**Verification:** Files exist or are updated

### Step 16: Document Remaining CLI & Integration Patterns (LOWER PRIORITY)

Create or update:

1. **`docs/learned/cli/rich-console-markup.md`** (CREATE, from #7953): Rich Console vs Textual markup, URL quoting rules, OSC 8 sequences.
2. **`docs/learned/integrations/github-variables.md`** (CREATE, from #7954): GitHubAdmin get_variable/set_variable 5-place pattern.
3. **`docs/learned/cli/admin-oauth-token.md`** (CREATE, from #7954): OAuth token management, _SecretConfig, precedence behavior, enable-deletes-alternative pattern.

**Source:** #7953, #7954 investigations
**Verification:** Files exist

## Attribution

Items by source (step numbers):

- **#8016**: Steps 1, 2, 5, 7
- **#8013**: Steps 3, 10, 12
- **#8012**: Steps 1, 2, 3, 6, 8
- **#8007**: Steps 1, 2, 8
- **#7996**: Steps 3, 10, 14
- **#7983**: Steps 13, 14
- **#7977**: COMPLETE - close only
- **#7960**: Steps 5, 9, 13
- **#7959**: Steps 2, 4, 5, 11
- **#7958**: Steps 3, 4, 13, 15
- **#7957**: Steps 4, 5, 10, 15
- **#7954**: Steps 16
- **#7953**: Steps 5, 10, 16
- **#7951**: Steps 5, 13

## Verification

After implementation:
1. Run `erk docs sync` to regenerate tripwires-index.md and index.md
2. Verify all new files have proper frontmatter (title, read-when, tripwires where applicable)
3. Grep for stale references to "implementing"/"implemented" in docs/learned/
4. Confirm all tripwire scores match the investigation findings
