# Plan: Update remaining .impl references and tripwires in docs/learned/

**Part of Objective #8197, Nodes 4.3 + 4.4**

## Context

Objective #8197 consolidates `.impl/` into branch-scoped `.erk/impl-context/<branch>/`. Phases 1-3 updated all source code, tests, CI, commands, and skills. Phase 4 nodes 4.1 and 4.2 (PR #8335) rewrote the two core docs (`impl-context.md` and `impl-folder-lifecycle.md`). Nodes 4.3 and 4.4 address the remaining ~60 docs that still reference `.impl` and the auto-generated tripwire files.

**Key finding from analysis:** Most `.impl/` references are *correct* — they describe the local working directory, which still uses `.impl/`. The primary stale pattern is **`issue.json` references** (~40 occurrences across ~15 docs) where `plan-ref.json` is now the primary file and `issue.json` is only a legacy fallback.

## Phase 1: Update `issue.json` → `plan-ref.json` in docs (Node 4.3 core)

Update ~15 docs that treat `.impl/issue.json` as the primary plan metadata file. The code now uses `plan-ref.json` as primary with `issue.json` as legacy fallback.

**Pattern:** Replace `.impl/issue.json` with `.impl/plan-ref.json` as primary reference. Where the legacy fallback is relevant (e.g., in validation docs), note it: "`.impl/plan-ref.json` (or legacy `issue.json`)"

### Files to update:

1. **`docs/learned/pr-operations/checkout-footer-syntax.md`** — Lines 8, 36, 41: Update tripwire and table from `issue.json` to `plan-ref.json`
2. **`docs/learned/pr-operations/pr-validation-rules.md`** — Lines 8, 36, 39: Update tripwire and description
3. **`docs/learned/pr-operations/pr-submit-phases.md`** — Line 62: Update file reference
4. **`docs/learned/erk/pr-commands.md`** — Lines 10, 55, 60: Update tripwire, table, and explanation
5. **`docs/learned/erk/issue-pr-linkage-storage.md`** — Lines 6, 49, 112, 121, 129: Update read_when, section title, and examples
6. **`docs/learned/erk/index.md`** — Line 14: Update index entry description
7. **`docs/learned/cli/pr-submission.md`** — Lines 62, 64, 81, 113: Update validation rule descriptions
8. **`docs/learned/cli/pr-submit-pipeline.md`** — Lines 33, 70, 74: Update prepare_state description and auto-repair section
9. **`docs/learned/cli/pr-rewrite.md`** — Line 41: Update issue discovery reference
10. **`docs/learned/cli/optional-arguments.md`** — Line 23: Update discovery step description
11. **`docs/learned/planning/pr-submission-patterns.md`** — Lines 11, 58, 61: Update tripwire and table
12. **`docs/learned/architecture/pr-finalization-paths.md`** — Lines 13, 19, 26, 31, 35: Update all `issue.json` references
13. **`docs/learned/architecture/issue-reference-flow.md`** — Line 65: Update fallback table
14. **`docs/learned/architecture/state-threading-pattern.md`** — Line 102: Update prepare_state description
15. **`docs/learned/architecture/plan-ref-architecture.md`** — Line 24: Already documents the legacy format, verify accuracy

## Phase 2: Update tripwire source frontmatter (Node 4.4)

Tripwire index files are **auto-generated** (`<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->`). Update source doc frontmatter, then run `erk docs sync`.

### Source docs with stale `issue.json` tripwires to update:

1. **`docs/learned/pr-operations/checkout-footer-syntax.md`** — Tripwire line 8: `"writing checkout footer with issue number from .impl/issue.json"` → update to `plan-ref.json`
2. **`docs/learned/pr-operations/pr-validation-rules.md`** — Tripwire: `"using issue number from .impl/issue.json"` → update
3. **`docs/learned/erk/pr-commands.md`** — Tripwire line 10: `"from .impl/issue.json"` → update
4. **`docs/learned/planning/pr-submission-patterns.md`** — Tripwire line 11: `"from .impl/issue.json"` → update

After updating frontmatter, run: `erk docs sync`

This regenerates 6 tripwire index files:
- `docs/learned/planning/tripwires.md`
- `docs/learned/pr-operations/tripwires.md`
- `docs/learned/erk/tripwires.md`
- `docs/learned/integrations/tripwires.md`
- `docs/learned/cli/tripwires.md`
- `docs/learned/workflows/tripwires.md`

## Phase 3: Audit and verify remaining `.impl/` references

Quick scan of remaining ~45 files to confirm their `.impl/` references correctly describe the local working directory (not the staging directory). Most should be correct based on sampling analysis.

**Files needing special attention** (lifecycle/workflow docs that should mention both directories):
- `docs/learned/planning/lifecycle.md` — Already mentions both; verify accuracy
- `docs/learned/planning/workflow.md` — Verify it doesn't imply `.impl/` is committed
- `docs/learned/glossary.md` — Verify "Plan Folder" definition is current

## Verification

1. `grep -r '\.impl/issue\.json' docs/learned/` — Should return 0 results (except legacy-context mentions)
2. `erk docs sync` — Should succeed with no errors
3. `make fast-ci` — Lint/format checks pass (prettier for .md files)
4. Grep for remaining `.impl` references and manually confirm each is correct (refers to working directory)
