# Plan: Consolidated Documentation from 11 erk-learn Plans

> **Consolidates:** #7420, #7417, #7414, #7413, #7412, #7407, #7403, #7402, #7396, #7392, #7386

## Context

11 erk-learn plans accumulated from recent implementation sessions (all Feb 18, 2026). Each documents lessons learned from PRs that are already merged. The code is complete; only documentation remains. Deep investigation of all 11 plans identified significant overlap -- particularly around phantom references to renamed files, tripwire candidates, and TUI/testing patterns.

## Source Plans

| # | Title | Items | Key Themes |
|---|-------|-------|------------|
| #7420 | Rename 'step' to 'node' documentation | 14 | Phantom refs, LibCST tripwire, terminology scope |
| #7417 | Filter local session fallback by branch | 14 | Session discovery docs, architecture patterns |
| #7414 | Objective check falsely flags done steps | 12 | Stale refs, terminal states, never-edit-master |
| #7413 | find_graph_next_step fallback | 11 | Function semantics, .worker-impl, discriminated unions |
| #7412 | PR feedback classifier alignment | 14 | Classifier schema, informational_count, prettier |
| #7407 | Unresolved comments modal | 20 | TUI patterns, modal screens, testing actions |
| #7403 | plan_header.py privatization | 21 | Migration docs, FakeGitHubIssues, replace_all |
| #7402 | Remove .worker-impl/ before implementation | 10 | Force-with-lease, root cause chain, divergence |
| #7396 | Merge objective inspect into view | 12 | Alias table, JSON schema, command merge |
| #7392 | Eliminate subprocess mocks | 25 | exec keyword, DI patterns, rebase conflicts |
| #7386 | One-shot planning in TUI dashboard | 8 | Context wiring, YAML assertions, closing ref |

## Overlap Analysis

Major overlaps merged in this plan:

| Theme | Source Plans | Merged Into |
|-------|-------------|-------------|
| Phantom refs to `update_roadmap_step.py` | #7420, #7414, #7413 | Step 1.1 |
| `.worker-impl/` cleanup tripwire | #7413, #7407, #7402 | Step 2.2 |
| FakeGitHubIssues context wiring | #7403, #7386 | Step 2.3 |
| `replace_all` gotchas | #7403, #7392 | Steps 2.7, 2.8 |
| find_graph_next_node() docs | #7413, #7414 | Step 3.3 |
| Prettier enforcement | #7412, #7407 | Step 2.10 |
| PR closing reference timing | #7386, #7403 | Step 2.11 |
| Step/node terminology | #7420, #7413, #7414 | Steps 1.1-1.5 |

---

## Implementation Steps

### Phase 1: Phantom Reference Fixes (Quick Wins)

Fix stale file/function references that contradict current code.

#### Step 1.1: Fix `update_roadmap_step.py` phantom references _(from #7420, #7414)_

**Files to update (4 files, ~12 locations):**

- `docs/learned/objectives/roadmap-parser.md` (line 116)
  - Change `update_roadmap_step.py` to `update_objective_node.py`

- `docs/learned/objectives/roadmap-parser-api.md` (lines 28, 31, 33, 55)
  - Replace all `update_roadmap_step.py` with `update_objective_node.py`
  - Replace `_replace_step_refs_in_body` with `_replace_node_refs_in_body`

- `docs/learned/objectives/roadmap-validation.md` (lines 55, 57, 83, 85)
  - Replace all `update_roadmap_step.py` with `update_objective_node.py`
  - Replace `_replace_step_refs_in_body` with `_replace_node_refs_in_body`

- `docs/learned/objectives/roadmap-format-versioning.md` (line 46)
  - Replace `_replace_step_refs_in_body()` with `_replace_node_refs_in_body()`

- `docs/learned/objectives/plan-reference-preservation.md` (lines 21, 23)
  - Replace `update_roadmap_step` with `update_objective_node`

**Verification:** `grep -r "update_roadmap_step" docs/learned/` returns no results

#### Step 1.2: Fix stale section heading in roadmap-parser.md _(from #7420)_

**File:** `docs/learned/objectives/roadmap-parser.md` (line 108)
- Change `## Next Step Discovery` to `## Next Node Discovery`

#### Step 1.3: Fix stale API field example _(from #7420)_

**File:** `docs/learned/objectives/objective-lifecycle.md`
- Change `"next_step"` to `"next_node"` in example JSON

#### Step 1.4: Fix stale CSS path _(from #7407)_

**File:** `docs/learned/textual/widget-development.md` (line 23)
- Change `src/erk/tui/css/` to `src/erk/tui/styles/`

#### Step 1.5: Fix stale alias table and view section _(from #7396)_

**File:** `docs/learned/cli/objective-commands.md`
- Lines 95-101: Remove `inspect: i` row, add `view: v` row
- Lines 103-116: Add documentation for `depends_on` column, `(unblocked)` annotation, unblocked count in summary, `--json-output` flag

#### Step 1.6: Fix code comment _(from #7420)_

**File:** `src/erk/cli/commands/objective/view_cmd.py` (line 221)
- Change `# Find next step` to `# Find next node`

---

### Phase 2: High-Value Tripwire Promotions (Score >= 5)

Add tripwires to existing tripwire files. Organized by target file.

#### Step 2.1: Add to `docs/learned/architecture/tripwires.md` _(from #7402, #7417)_

- **Force-with-lease in multi-step workflows** (8/10): In workflows where earlier steps push to the branch, force-push silently overwrites intermediate commits. Always `git pull --rebase` before pushing. _(#7402)_
- **Grep all callers before changing erk_shared function signatures** (7/10): Missed call sites cause CI failures. Run `grep -r "function_name"` across full repo before committing. _(#7417)_

#### Step 2.2: Add to `docs/learned/planning/tripwires.md` _(from #7402, #7407, #7413)_

- **.worker-impl/ directory must be removed before CI** (5/10): Prettier checks all tracked files. `.worker-impl/plan.md` fails validation. Run `git rm -rf .worker-impl/` before first CI run. _(#7407, #7402)_
- **${CLAUDE_SESSION_ID} not expanded by shell** (4/10): Token is Claude Code substitution, not shell variable. Use skill/command mechanism instead of raw Bash. _(#7407)_
- **Rename plan path accuracy verification** (4/10): Verify each file path exists before delegating batch renames. Wrong paths cause silent coverage gaps. _(#7420)_
- Update existing tripwire line 137 to reference the workflow pre-implementation exception in worktree-cleanup.md _(#7402)_

#### Step 2.3: Add to `docs/learned/testing/tripwires.md` _(from #7386, #7403, #7392, #7417)_

- **FakeGitHubIssues context wiring** (8/10): Always pass `issues=issues` to `build_workspace_test_context` when using custom `FakeGitHubIssues`. Without it, plan_backend operates on a different instance; metadata writes are invisible. _(#7386, #7403)_
- **exec keyword breaks import/monkeypatch** (8/10): `exec` in module paths blocks direct import and string-path monkeypatch. Use `importlib.import_module()` + object-form `setattr`. _(#7392)_
- **replace_all collapses lines with trailing comments** (7/10): Edit tool's `replace_all` removes surrounding whitespace; causes SyntaxError. _(#7392)_
- **replace_all underscore doubling** (5/10): Using replace_all to rename `foo` → `_foo` corrupts existing `_foo` → `__foo`. Grep for existing underscored forms first. _(#7403)_
- **FakeSessionData must include gitBranch JSONL** (5/10): Missing `gitBranch` field causes silent empty results from branch-filtered discovery. _(#7417)_
- **YAML metadata assertion format** (5/10): Assert on `'field_name:'` (key-only), not `'field_name: "value"'`. YAML serialization differs from Python repr. _(#7386)_
- **libcst-refactor completeness** (4/10): After bulk rename, grep entire codebase for old symbol name. Subagent may miss files outside its scope. _(#7403)_

#### Step 2.4: Add to `docs/learned/tui/tripwires.md` _(from #7407, #7420)_

- **DOM element unique IDs per lifecycle phase** (6/10): Reusing same `id` across loading/empty/content states causes `query_one()` to return wrong element silently. _(#7407)_
- **@work(thread=True) requires call_from_thread()** (6/10): Direct widget calls from background threads cause silent UI corruption. Must use `self.app.call_from_thread(callback, ...)`. _(#7407)_
- **PlanDataProvider ABC extension requires 3-file update** (5/10): abc.py + real.py + fake.py. Fake must initialize dict in `__init__`. Missing init causes AttributeError at test time, not class definition. _(#7407)_
- **TUI column key is a data binding contract** (4/10): `add_column(key=)` must match data field name. Silent failure when mismatched. _(#7420)_

#### Step 2.5: Add to `docs/learned/objectives/tripwires.md` _(from #7414, #7396)_

- **inspect command removed** (6/10): `erk objective inspect` deleted in PR #7385. Use `erk objective view` or `/local:objective-view`. _(#7396)_
- **Terminal states in allowed-status tuples** (5/10): Always include `done`, `skipped` in allowed-status checks. Omitting produces false positives. _(#7414)_
- **objective-fetch-context requires --branch on master** (4/10): Auto-discovery fails on non-plan branches. Pass `--branch` explicitly. _(#7414)_

#### Step 2.6: Add to `docs/learned/commands/tripwires.md` _(from #7412)_

- **informational_count field semantics** (7/10): Covers ONLY discussion comments, not review threads. All unresolved review threads must appear individually in `actionable_threads`. _(#7412)_
- **All review threads must appear in actionable_threads** (6/10): Thread count in classifier output must equal erk dash count. Missing threads are silently dropped. _(#7412)_
- **Prettier enforcement on .claude/ markdown** (5/10): Run `prettier --write <file>` immediately after editing. `make fast-ci` fails otherwise. _(#7412, #7407)_

#### Step 2.7: Add to `docs/learned/refactoring/tripwires.md` _(from #7420)_

- **LibCST dict-key string limitation** (7/10): `leave_Name` visitor does NOT rename string literals used as dict keys. After LibCST batch rename, grep for old identifier as string key. _(#7420)_
- **Rename test assertion grep** (5/10): After display-string renames, search test assertions: `grep -r '"old_term"' tests/`. Not caught by linters or type checkers. _(#7420)_

#### Step 2.8: Add to `docs/learned/uncategorized/tripwires.md` _(from #7414)_

- **Never edit source files on master** (6/10): Even for one-line fixes, use plan-first workflow. Bypasses review, CI gates, and worktree isolation. _(#7414)_

#### Step 2.9: Add to `docs/learned/ci/tripwires.md` _(from #7417)_

- **statusCheckRollup stale results** (4/10): After push, results show completed runs only, not in-progress. Wait for new check suite. _(#7417)_

#### Step 2.10: Add to `docs/learned/pr-operations/tripwires.md` _(from #7417)_

- **Post-erk-pr-submit branch divergence** (4/10): Squash-force-push requires `git pull --rebase`. _(#7417)_

---

### Phase 3: Existing Documentation Updates

#### Step 3.1: Update session discovery docs _(from #7417)_

**File:** `docs/learned/sessions/discovery-fallback.md`
- Update hierarchy table (lines 73-80) to show exact branch filtering
- Add "Branch Filtering in Local Fallback" subsection

**File:** `docs/learned/sessions/lifecycle.md`
- Revise "The Local Fallback Decision" section (lines 72-76)
- Add worktree slot reuse contamination explanation

#### Step 3.2: Update one-shot workflow docs _(from #7386, #7402)_

**File:** `docs/learned/planning/one-shot-workflow.md`
- Rewrite "Registration Step" section (lines 104-112): metadata now primary from CLI, CI is fallback
- Add "PR Closing Reference (Timing Constraint)" section: closing ref in initial body, not post-creation
- Add "Dispatch Metadata Two-Phase Write" section
- Add "Divergence Risk: One-Shot vs Plan-Submit" section _(from #7402)_

#### Step 3.3: Update objective system docs _(from #7413, #7414)_

**File:** `docs/learned/objectives/dependency-graph.md`
- Add "Fallback Behavior: Pending -> In-Progress" section for `find_graph_next_node()`
- Add three-function comparison table: `find_next_node()` vs `find_graph_next_node()` vs `graph.next_node()`

**File:** `docs/learned/objectives/roadmap-parser.md`
- Add comparison table to "Next Node Discovery" section (same three functions)

**File:** `docs/learned/objectives/roadmap-status-system.md`
- Add "Inference Rules vs Validity Constraints" clarification section
- Add "Valid Plan Reference States" list: in_progress, done, planning, skipped

**File:** `docs/learned/objectives/objective-roadmap-check.md`
- Extend Check 3 description to document allowed statuses for plan references
- Note: `done + plan-ref` is the expected end state after PR lands

#### Step 3.4: Update TUI docs _(from #7407)_

**File:** `docs/learned/tui/textual-async.md`
- Add "Exception Handling in Background Workers (Error Boundary Pattern)" section
- Document approved EAFP exception for UI error boundaries with `@work(thread=True)`

**File:** `docs/learned/tui/action-inventory.md`
- Add `view_comments` / `c` key binding entry
- Add "Guard Pattern: Three-Layer LBYL" section with example from `action_view_comments`

**File:** `docs/learned/tui/architecture.md`
- Add `fetch_unresolved_comments` method to PlanDataProvider table
- Add PRReviewThread and PRReviewComment type field tables

#### Step 3.5: Update testing docs _(from #7407, #7403)_

**File:** `docs/learned/testing/testing.md`
- Add "Legitimate Test Coverage Exclusions" section (ABC files, fakes, thin delegators, help-only)
- Add "Private Module-Level Formatters Require Unit Tests" section
- Add "Integration Tests Not in make fast-ci" note

**File:** `docs/learned/testing/cli-testing.md`
- Add "Pattern 6: FakeGitHub with Shared FakeGitHubIssues" section

#### Step 3.6: Update architecture docs _(from #7413, #7417, #7403)_

**File:** `docs/learned/architecture/discriminated-union-error-handling.md`
- Add "When isinstance() Is NOT Required: Plain Optionals" section for `T | None`

**File:** `docs/learned/architecture/erk-architecture.md`
- Add "Constructor Call Site Inlining" subsection to single-use locals rule
- Add "Hoist Scalar Derivation Above Branching Calls" pattern
- Add "Always Get Current Branch Unconditionally at Function Top" pattern

**File:** `docs/learned/architecture/github-cli-limits.md`
- Add "PR Closing Reference Timing" section (willCloseTarget only at creation)
- Add "Hardcoded --repo Flag Returns Empty Output" section

#### Step 3.7: Update PR/classifier docs _(from #7412)_

**File:** `docs/learned/erk/pr-address-workflows.md`
- Add "Classifier-to-Dash Alignment Invariant" section
- Add "Bot Thread Inflation" section (expected behavior)
- Add `informational_count` field semantics clarification

#### Step 3.8: Update planning docs _(from #7403, #7413)_

**File:** `docs/learned/planning/plan-backend-migration.md`
- Add "get_metadata_field Returns object | PlanNotFound" type narrowing section
- Add "Error Handling Asymmetry" section (get vs update semantics)
- Add "Plan.header_fields over extract for loaded Plans" section

**File:** `docs/learned/cli/exec-script-patterns.md`
- Add forward-looking migration note for plan_header.py privatization

**File:** `docs/learned/planning/reliability-patterns.md`
- Add root cause chain case study for .worker-impl/ master pollution _(#7402)_

#### Step 3.9: Update CLI docs _(from #7396)_

**File:** `docs/learned/cli/click-framework-conventions.md`
- Add `is_flag=True` carve-out: the "no non-None defaults" rule applies only to value options, not flags

#### Step 3.10: Update conventions _(from #7407)_

**File:** `docs/learned/conventions.md`
- Add single-use locals line-length exception: shorten variable name instead of ignoring rule

---

### Phase 4: New Documentation Creation

#### Step 4.1: Create TUI modal screen pattern _(from #7407)_

**File:** `docs/learned/tui/modal-screen-pattern.md`
- 7-element checklist: ModalScreen, CSS, BINDINGS, @work(), call_from_thread(), error boundary, loading placeholder
- Reference: UnresolvedCommentsScreen, IssueBodyScreen

#### Step 4.2: Create PR feedback classifier schema _(from #7412)_

**File:** `docs/learned/erk/pr-feedback-classifier-schema.md`
- Authoritative JSON schema reference with field descriptions
- Classifier-to-dash alignment invariant
- Batch type definitions

#### Step 4.3: Create systematic terminology rename guide _(from #7420)_

**File:** `docs/learned/refactoring/systematic-terminology-renames.md`
- Three-phase workflow: display strings -> LibCST identifiers -> dict key strings
- Verification with type checker
- Scope boundary checking

#### Step 4.4: Create Click context DI pattern _(from #7392)_

**File:** `docs/learned/architecture/click-context-di-pattern.md`
- `@click.pass_context` -> `require_*()` helper -> impl function
- Testing via `ErkContext.for_test()`
- Examples from validate_claude_credentials.py

#### Step 4.5: Create rebase conflict patterns _(from #7392, #7413)_

**File:** `docs/learned/architecture/rebase-conflict-patterns.md`
- Hidden regressions in non-conflicted files
- Prevention: grep for old symbols before running tests
- Auto-generated file resolution

#### Step 4.6: Create test context composition doc _(from #7403)_

**File:** `docs/learned/architecture/test-context-composition.md`
- `issues_explicitly_passed` flag in context_for_test()
- When issues is auto-created vs explicitly shared
- Cross-reference to FakeGitHubIssues tripwire

#### Step 4.7: Create objective view JSON schema _(from #7396)_

**File:** `docs/learned/objectives/objective-view-json.md`
- Complete schema from `--json-output` flag
- Fields: issue_number, phases, graph.nodes, graph.unblocked, graph.next_node, summary

#### Step 4.8: Create plan-header privatization umbrella doc _(from #7403)_

**File:** `docs/learned/planning/plan-header-privatization.md`
- Migration phases (Phase 1 complete, Phase 2-3 pending)
- External callers inventory
- PlanBackend migration patterns

---

## Attribution

Items by source (showing only items with unique contributions):

- **#7420**: Steps 1.1-1.3, 1.6, 2.7, 4.3 (phantom refs, rename patterns, LibCST tripwire)
- **#7417**: Steps 2.1b, 2.3e, 2.9, 2.10, 3.1, 3.6b (session discovery, architecture patterns)
- **#7414**: Steps 2.5b-c, 2.8, 3.3b-d (terminal states, never-edit-master, status system)
- **#7413**: Steps 3.3a, 3.6a, 3.8b (function semantics, discriminated unions)
- **#7412**: Steps 2.6, 3.7, 4.2 (classifier schema, informational_count)
- **#7407**: Steps 1.4, 2.2a, 2.4, 3.4, 3.5a, 4.1 (TUI patterns, modal screens)
- **#7403**: Steps 2.3a, 2.3d, 3.5b, 3.8a, 4.6, 4.8 (context wiring, replace_all, migration)
- **#7402**: Steps 2.1a, 3.2d, 3.8c (force-with-lease, root cause chain)
- **#7396**: Steps 1.5, 2.5a, 3.9, 4.7 (alias table, inspect removal, JSON schema)
- **#7392**: Steps 2.3b-c, 4.4, 4.5 (exec keyword, DI patterns, rebase)
- **#7386**: Steps 2.3a, 2.3f, 3.2a-c, 3.5b (context wiring, YAML format, one-shot)

## Verification

After implementation:
1. Run `grep -r "update_roadmap_step" docs/learned/` -- should return 0 results
2. Run `grep -r "find_graph_next_step\b" docs/learned/` -- should return 0 results
3. Run `grep -r "src/erk/tui/css/" docs/learned/` -- should return 0 results
4. Run `erk docs sync` to regenerate auto-generated tripwires-index.md
5. Verify all new docs have proper frontmatter (title, read-when, tripwires count)
6. Run `make fast-ci` to verify no formatting violations in new/modified docs