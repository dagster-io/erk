# Plan: Fix `issue_number` references in docs/learned/ (Node 6.3)

Part of Objective #8381, Node 6.3

## Context

Objective #8381 standardizes "plan-as-PR" terminology across the codebase. Phases 1-5 and nodes 6.1-6.2 are complete. Node 6.3 fixes `issue_number` references (now `plan_number`) across docs in 6 directories. Node 6.4+ handles other terminology fixes in specific files.

## Scope

**39 files** across 6 directories with **~126 occurrences** of `issue_number`:

| Directory | Files | Occurrences |
|-----------|-------|-------------|
| architecture/ | 20 | ~40 |
| cli/ | 10 | ~30 |
| testing/ | 4 | ~12 |
| pr-operations/ | 2 | ~3 |
| erk/ | 2 | ~2 |
| textual/ | 1 | ~1 |

Note: `desktop-dash/` doesn't exist (already removed).

## Replacement Rules

Each `issue_number` occurrence falls into one of these categories:

### 1. Conceptual/prose references → `plan_number`
- "the issue number of the plan" → "the plan number"
- `issue_number` in JSON output examples → `plan_number` (if the actual CLI output has been updated)
- Conceptual field names in explanatory text

### 2. Code references that match current source → keep as-is or update to match source
- The source code has **both** `issue_number` (141 occurrences, mainly in objective/issue-handling code) and `plan_number` (135 occurrences, newer plan terminology)
- If docs reference code that still uses `issue_number` in source (e.g., `state.issue_number`, `parse_issue_number_from_url`), keep matching the actual code
- If docs reference code that has been renamed to `plan_number`, update to match

### 3. Branch naming patterns → keep as-is
- `P{issue_number}-` is the actual branch naming convention in code — but contextually these refer to plan numbers, so update prose around them (e.g., "plan's issue number prefix" → "plan number prefix")

### 4. JSON output keys in examples
- Check actual CLI output; if key has been renamed, update the example
- `update-objective-node` output still uses `"issue_number"` in its JSON → keep as-is (that's objective issue number, not plan)

## Implementation

### Phase 1: architecture/ docs (20 files)

Edit each file, applying replacement rules above. Key files:
- `state-threading-pattern.md` (5 occurrences)
- `selection-preservation-by-value.md` (3 occurrences)
- `gateway-abc-implementation.md` (3 occurrences)
- `plan-ref-architecture.md` (4 occurrences)
- Remaining 16 files (1-2 occurrences each)

### Phase 2: cli/ docs (10 files)

- `output-styling.md` (6 occurrences)
- `pr-submit-pipeline.md` (5 occurrences)
- `ambiguity-resolution.md` (3 occurrences)
- `commands/update-objective-node.md` (3 occurrences — these are objective `issue_number`, may keep)
- Remaining 6 files (1-2 occurrences each)

### Phase 3: testing/ docs (4 files)

- `import-conflict-resolution.md` (6 occurrences — these reference actual function names like `parse_issue_number`, keep)
- `fake-github-mutation-tracking.md` (4 occurrences — these describe fake API tuple fields)
- `cli-testing.md` (1 occurrence)
- `fake-api-migration-pattern.md` (1 occurrence)

### Phase 4: Remaining directories (5 files)

- `pr-operations/plan-implementation-auto-force.md` (2 occurrences)
- `pr-operations/checkout-footer-syntax.md` (1 occurrence)
- `erk/graphite-divergence-detection.md` (1 occurrence)
- `erk/pr-address-workflows.md` (1 occurrence)
- `textual/datatable-markup-escaping.md` (1 occurrence)

## Verification

1. Run `rg issue_number docs/learned/{architecture,cli,testing,pr-operations,erk,textual}/` to confirm remaining references are intentional (actual code references or objective-related)
2. Run `make fast-ci` to ensure no doc generation or test breakage
