# Plan: Consolidated Documentation from 7 Learn Plans

> **Consolidates:** #6316, #6315, #6314, #6310, #6306, #6302, #6301

## Source Plans

| #    | Title                                                  | Items Merged |
| ---- | ------------------------------------------------------ | ------------ |
| 6316 | Encode Objective ID into Branch Names                  | 2 items      |
| 6315 | Convert get_issue to IssueInfo \| IssueNotFound DU     | 3 items      |
| 6314 | Tests for objective-roadmap-check                      | 2 items      |
| 6310 | Add Test Coverage Review Agent                         | 4 items      |
| 6306 | Split Ensure into Ensure + EnsureIdeal                 | 3 items      |
| 6302 | erk exec objective-roadmap-check Implementation        | 3 items      |
| 6301 | Convert merge_pr to Discriminated Union                | 3 items      |

## What Changed Since Original Plans

- All code implementations are complete and merged to master (except #6316 branch naming which is on a feature branch)
- Documentation has NOT been updated to reflect these changes
- Several plans overlap significantly (#6315 + #6301 on discriminated unions, #6314 + #6302 on objective-roadmap-check)

## Investigation Findings

### Corrections to Original Plans

- **#6316**: Code is on feature branch only, not master. Glossary and lifecycle docs confirmed as needing updates
- **#6315**: IssueNotFound does NOT exist on master yet - get_issue still raises exceptions. Plan assumed conversion was done
- **#6301**: MergeResult/MergeError ARE on master. merge_pr already returns discriminated union
- **#6306**: Both Ensure (559 lines) and EnsureIdeal (172 lines) exist on master. No documentation exists
- **#6310**: test-coverage.md review agent exists. No docs/learned/reviews/ category exists
- **#6302/#6314**: objective_roadmap_check.py (287 lines) + tests (803 lines) exist on master. No command-specific docs

### Overlap Analysis

1. **#6315 + #6301**: Both document discriminated union patterns. Merged into unified DU documentation steps
2. **#6314 + #6302**: Both document objective-roadmap-check. Merged into unified objective command docs
3. **#6306 + #6315 + #6301**: EnsureIdeal is the CLI consumer of discriminated unions - cross-referenced

## Remaining Gaps (Documentation Items)

All items below are documentation-only. No code changes needed.

### HIGH Priority (8 items)

1. Update glossary branch naming format _(from #6316)_
2. Update lifecycle.md with objective-linked branches _(from #6316)_
3. Add IssueNotFound + MergeResult/MergeError examples to discriminated-union-error-handling.md _(from #6315, #6301)_
4. Add incomplete caller migration tripwire to discriminated-union-error-handling.md _(from #6315)_
5. Add return type change section to gateway-abc-implementation.md _(from #6301)_
6. Create ensure-ideal-pattern.md _(from #6306)_
7. Update convention-based-reviews.md with test-coverage agent _(from #6310)_
8. Update erk-exec-commands.md to list objective-roadmap-check _(from #6302)_

### MEDIUM Priority (7 items)

9. Document exec script union migration pattern in exec-script-testing.md _(from #6315)_
10. Add import completeness verification tripwire to gateway-abc-implementation.md _(from #6315)_
11. Update two-phase-validation-model.md to reference EnsureIdeal _(from #6306)_
12. Create docs/learned/reviews/ directory + test-coverage-agent.md _(from #6310)_
13. Update testing/tripwires.md with untestable file detection _(from #6310)_
14. Create objective-roadmap-check.md command documentation _(from #6302, #6314)_
15. Add test naming convention for return type changes to testing.md _(from #6301)_

### LOW Priority (5 items)

16. Create agent-orchestration.md for learn workflow tiers _(from #6314)_
17. Create review-agent-tool-scoping.md _(from #6310)_
18. Update conventions.md with frozen dataclass field naming _(from #6301)_
19. Document regex markdown parsing patterns _(from #6302)_
20. Document worker-impl cleanup requirement _(from #6306)_

## Implementation Steps

### Step 1: Update glossary.md with objective branch format _(from #6316)_

**File:** `docs/learned/glossary.md`
**Action:** UPDATE lines 147-168 (Branch Naming Convention section)
**Content:** Add "With Objective ID" subsection documenting `P{plan}-O{objective}-{slug}-{timestamp}` format, extraction function reference, and backward compatibility note
**Verification:** Section includes both old and new formats with examples

### Step 2: Update lifecycle.md with objective-linked branches _(from #6316)_

**File:** `docs/learned/planning/lifecycle.md`
**Action:** UPDATE around line 719-745 (State Linking Mechanisms)
**Content:** Add subsection explaining objective-linked branch names and when they're used
**Verification:** Document explains that `plan.objective_id` affects branch format

### Step 3: Add discriminated union examples to architecture docs _(from #6315, #6301)_

**File:** `docs/learned/architecture/discriminated-union-error-handling.md`
**Action:** UPDATE - add concrete examples section after line 112
**Content:**
- Add `MergeResult | MergeError` example with before/after code showing `bool | str` to union migration
- Add `IssueNotFound` example (planned conversion pattern)
- Add migration checklist (5 gateway implementations + call sites + tests)
- Add incomplete caller migration tripwire to frontmatter
**Source:** PR #6294 (merge_pr), PR #6304 (get_issue)
**Verification:** Examples show actual type definitions from `gateway/github/types.py`

### Step 4: Add return type change section to gateway-abc-implementation.md _(from #6301, #6315)_

**File:** `docs/learned/architecture/gateway-abc-implementation.md`
**Action:** UPDATE - add "Return Type Changes" section
**Content:** Document the 5-file + call-site + test update pattern for changing gateway return types, with merge_pr as canonical example. Add import completeness verification tripwire to frontmatter
**Verification:** Section includes checklist and concrete example

### Step 5: Create ensure-ideal-pattern.md _(from #6306)_

**File:** `docs/learned/cli/ensure-ideal-pattern.md` (NEW)
**Action:** CREATE
**Content:**
- Semantic distinction: Ensure (invariant checks) vs EnsureIdeal (type narrowing)
- Decision tree: when to use each class
- All 7 EnsureIdeal methods with input/output types
- Code examples from land_cmd.py and show_cmd.py
- Frontmatter tripwire for discriminated union narrowing
**Source:** `src/erk/cli/ensure.py` (559 lines), `src/erk/cli/ensure_ideal.py` (172 lines)
**Verification:** Document covers all 7 EnsureIdeal methods

### Step 6: Update two-phase-validation-model.md _(from #6306)_

**File:** `docs/learned/cli/two-phase-validation-model.md`
**Action:** UPDATE - add EnsureIdeal cross-reference
**Content:** New section explaining EnsureIdeal as concrete implementation of type narrowing phase
**Verification:** Cross-reference to ensure-ideal-pattern.md included

### Step 7: Update convention-based-reviews.md _(from #6310)_

**File:** `docs/learned/ci/convention-based-reviews.md`
**Action:** UPDATE - add test-coverage review to list of agents
**Content:** Add test-coverage agent entry with file categorization description, legitimately untestable pattern, and marker-based deduplication
**Verification:** Test-coverage agent is listed alongside existing review agents

### Step 8: Create docs/learned/reviews/ + test-coverage-agent.md _(from #6310)_

**Files:**
- `docs/learned/reviews/index.md` (NEW)
- `docs/learned/reviews/test-coverage-agent.md` (NEW)
**Action:** CREATE directory and files
**Content:** Document test coverage review agent: purpose, file categorization (6 buckets), untestable file detection heuristics, flagging strategy, output format
**Source:** `.github/reviews/test-coverage.md` (152 lines)
**Verification:** New category appears in docs/learned/ structure

### Step 9: Update erk-exec-commands.md _(from #6302)_

**File:** `docs/learned/cli/erk-exec-commands.md`
**Action:** UPDATE - add objective-roadmap-check to command reference
**Content:** Add entry with JSON output format, exit code semantics, validation behavior
**Source:** `src/erk/cli/commands/exec/scripts/objective_roadmap_check.py` (287 lines)
**Verification:** Command appears in reference table

### Step 10: Create objective-roadmap-check.md _(from #6302, #6314)_

**File:** `docs/learned/objectives/objective-roadmap-check.md` (NEW)
**Action:** CREATE
**Content:**
- Command purpose and usage
- Markdown table parsing rules (phase headers, table columns, step rows)
- Status inference hierarchy (explicit Status > PR column > default pending)
- Validation rules and error codes
- JSON output schema
- Test coverage summary (21 tests, 803 lines)
**Source:** `objective_roadmap_check.py` (287 lines), test file (803 lines)
**Verification:** Document covers all parsing rules and status inference logic

### Step 11: Update exec-script-testing.md with union migration pattern _(from #6315)_

**File:** `docs/learned/testing/exec-script-testing.md`
**Action:** UPDATE - add section on migrating tests for discriminated union returns
**Content:** Before/after patterns for test migration, key differences table, migration checklist
**Verification:** Section shows concrete test migration example

### Step 12: Update testing/tripwires.md _(from #6310)_

**File:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE frontmatter - add untestable file detection tripwire
**Content:** "Before flagging code as untested in PR review: Code without tests may be legitimately untestable (CLI wrapper, type definitions, ABC interface)"
**Verification:** Tripwire appears in testing tripwires list

### Step 13: Add test naming convention to testing.md _(from #6301)_

**File:** `docs/learned/testing/testing.md`
**Action:** UPDATE - add section on test naming for return type refactoring
**Content:** Pattern table mapping old names to new names, renaming checklist
**Verification:** Section shows concrete naming examples

### Step 14: Update conventions.md with frozen dataclass field naming _(from #6301)_

**File:** `docs/learned/conventions.md`
**Action:** UPDATE - add frozen dataclass field naming section
**Content:** Use direct public fields, don't use leading underscores, when to use properties
**Verification:** Section covers correct and incorrect patterns

### Step 15: Create agent-orchestration.md _(from #6314)_

**File:** `docs/learned/planning/agent-orchestration.md` (NEW)
**Action:** CREATE
**Content:** Learn workflow agent graph with Tier 1 (parallel analysis) and Tier 2 (sequential synthesis) agents, implementation pattern
**Verification:** Diagram shows correct dependency ordering

### Steps 16-20 (LOW priority, implement if time permits)

16. Create `docs/learned/architecture/review-agent-tool-scoping.md` - Tool scoping security patterns _(from #6310)_
17. Create `docs/learned/cli/regex-markdown-parsing.md` - Regex patterns for markdown tables _(from #6302)_
18. Update `docs/learned/planning/implementation-workflows.md` - Worker-impl cleanup _(from #6306)_
19. Update `docs/learned/planning/session-preprocessing.md` - Non-JSON error handling _(from #6314)_
20. Create `docs/learned/ci/tool-quirks.md` - Prettier context-dependent behavior _(from #6306)_

## Attribution

Items by source plan:

- **#6316**: Steps 1, 2
- **#6315**: Steps 3, 4, 11 (shared with #6301)
- **#6314**: Steps 10, 15 (shared with #6302)
- **#6310**: Steps 7, 8, 12, 16
- **#6306**: Steps 5, 6, 18, 20
- **#6302**: Steps 9, 10, 17 (shared with #6314)
- **#6301**: Steps 3, 4, 13, 14 (shared with #6315)

## Verification

After implementation:
1. Run `erk docs sync` to regenerate tripwires index and auto-generated files
2. Grep docs/learned/ for each documented feature to confirm discoverability
3. Verify all new files have proper frontmatter with read-when and tripwire fields
4. Confirm cross-references between related docs are bidirectional