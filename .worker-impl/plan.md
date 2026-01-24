# Consolidated Plan: [erk-learn] Documentation Gaps

> **Consolidates:** #5798, #5797, #5796, #5795, #5786, #5785, #5784, #5775, #5774, #5773

## Source Plans

| #     | Title                                                              | Items Merged |
|-------|--------------------------------------------------------------------|--------------|
| #5798 | Learn Plan: Fix erk plan list not displaying [erk-learn] prefix    | 2 items      |
| #5797 | Documentation Plan: TUI DataTable Rich Markup Escaping             | 0 items (ALREADY COMPLETE) |
| #5796 | Documentation Plan: Create erk sync divergence command             | 3 items      |
| #5795 | Documentation Plan: Add --plan-file option to validate-plan-content| 2 items      |
| #5786 | Documentation Plan: Fix TUI not displaying [erk-learn] prefix      | 0 items (duplicate of #5797) |
| #5785 | Documentation Plan: Fix: erk br co None                            | 2 items      |
| #5784 | Learn Plan: Mtime-Based Cache Invalidation                         | 2 items      |
| #5775 | Learn Plan: Add --verbose to learn-dispatch                        | 2 items      |
| #5774 | Documentation Plan: Fix Replan to Carry Forward objective_issue    | 0 items (ALREADY DOCUMENTED) |
| #5773 | Documentation Plan: Add plan/objective context to PR summary       | 3 items      |

## What Changed Since Original Plans

1. **TUI DataTable markup escaping is fully documented** - `docs/learned/textual/datatable-markup-escaping.md` and `docs/learned/tui/plan-title-rendering-pipeline.md` now exist with comprehensive guidance
2. **Session tracking is documented** - `docs/learned/architecture/session-discovery.md` covers local vs remote session sources
3. **4 tripwires already exist** for DataTable markup, plan title rendering, and title-stripping functions
4. Plans #5797, #5786, and #5774 are now obsolete (work complete)

## Investigation Findings

### Plans to Close (No Remaining Gaps)

- **#5797** - Explicitly states "Status: DOCUMENTATION COMPLETE" with zero gaps
- **#5786** - Duplicate of #5797, same TUI markup escaping (already in datatable-markup-escaping.md)
- **#5774** - Session tracking documented in session-discovery.md

### Overlap Analysis

- **#5798, #5797, #5786** - All cover Rich markup escaping; TUI portion done, CLI portion remains
- **#5795, #5785** - Both touch validation patterns (dual input vs null guards)
- **#5775, #5784** - Both about infrastructure (CLI flags vs caching)
- **#5773, #5796** - Both about new command/feature documentation

## Remaining Gaps

### HIGH Priority (4 items)

1. **CLI Rich Markup Escaping** _(from #5798)_
   - **Location:** `docs/learned/cli/output-styling.md`
   - **Action:** UPDATE - add section on Rich markup in CLI tables
   - Cross-component guidance: when to use `Text()` (TUI) vs `escape_markup()` (CLI Rich) vs plain strings

2. **TUI Null Guard Patterns** _(from #5785)_
   - **Location:** `docs/learned/tui/adding-commands.md`
   - **Action:** UPDATE - add "Null Guard Patterns for Optional Fields" section
   - Three-layer validation: registry availability predicate → screen handler guard → app-level helper

3. **Mtime-Based Cache Invalidation Pattern** _(from #5784)_
   - **Location:** `docs/learned/architecture/graphite-cache-invalidation.md`
   - **Action:** CREATE
   - Triple-check guard pattern, trade-offs vs eager invalidation, reference implementation

4. **PlanContextProvider Architecture** _(from #5773)_
   - **Location:** `docs/learned/architecture/plan-context-integration.md`
   - **Action:** CREATE
   - 5-step extraction algorithm, graceful degradation, branch naming conventions

### MEDIUM Priority (4 items)

5. **erk pr sync-divergence Command Reference** _(from #5796)_
   - **Location:** `docs/learned/cli/commands/pr-sync-divergence.md`
   - **Action:** CREATE
   - Command flags, config override (`fix_conflicts_require_dangerous_flag`), streaming output pattern

6. **Context Priority Ordering for PR Generation** _(from #5773)_
   - **Location:** `docs/learned/pr-operations/commit-message-generation.md`
   - **Action:** CREATE
   - Priority: Plan Context (highest) → Objective Summary → Commit Messages (lowest)

7. **Dual Input Handling Pattern** _(from #5795)_
   - **Location:** `docs/learned/cli/exec-command-patterns.md`
   - **Action:** UPDATE - add "Dual Input Handling" section
   - Pattern for commands accepting either file or stdin input

8. **GitHub Actions Claude Integration** _(from #5775)_
   - **Location:** `docs/learned/ci/github-actions-claude-integration.md`
   - **Action:** CREATE
   - Required flags for non-interactive mode, environment setup, output capture

### LOW Priority (3 items)

9. **Type Safety Patterns for Flexible Collections** _(from #5798)_
   - **Location:** `docs/learned/architecture/type-safety-patterns.md`
   - **Action:** CREATE
   - Union type pattern (`list[str | Text]`), type narrowing, duck-typing alternatives

10. **Integration Testing Mtime Resolution** _(from #5784)_
    - **Location:** `docs/learned/testing/integration-testing-patterns.md`
    - **Action:** UPDATE - add section on filesystem mtime testing
    - Sleep patterns for cross-platform mtime resolution

11. **CLI Asymmetric Flag Requirements** _(from #5775)_
    - **Location:** `docs/learned/reference/cli-flag-patterns.md`
    - **Action:** CREATE
    - Document flags that become required in certain combinations

## Implementation Steps

### Phase 1: HIGH Priority (4 docs)

1. **Update `docs/learned/cli/output-styling.md`** _(from #5798)_
   - Add "Rich Markup Escaping in CLI Tables" section
   - Include cross-component comparison (TUI Text() vs CLI escape_markup())
   - Add tripwire for CLI table content with brackets

2. **Update `docs/learned/tui/adding-commands.md`** _(from #5785)_
   - Add "Null Guard Patterns for Optional Fields" section
   - Document three-layer validation pattern
   - Add tripwire for TUI commands depending on optional PlanRowData fields

3. **Create `docs/learned/architecture/graphite-cache-invalidation.md`** _(from #5784)_
   - Document mtime-based cache invalidation pattern
   - Include triple-check guard pattern code example
   - Reference `RealGraphite.get_all_branches()` implementation

4. **Create `docs/learned/architecture/plan-context-integration.md`** _(from #5773)_
   - Document PlanContextProvider class architecture
   - Include 5-step extraction algorithm flowchart
   - Document graceful degradation pattern

### Phase 2: MEDIUM Priority (4 docs)

5. **Create `docs/learned/cli/commands/pr-sync-divergence.md`** _(from #5796)_
   - Command usage, flags, and configuration
   - Streaming output pattern documentation
   - Update git-graphite-quirks.md with solution reference

6. **Create `docs/learned/pr-operations/commit-message-generation.md`** _(from #5773)_
   - Document context section priority ordering
   - Include code pattern from `CommitMessageGenerator._build_context_section()`

7. **Update `docs/learned/cli/exec-command-patterns.md`** _(from #5795)_
   - Add "Dual Input Handling" section
   - Pattern for `--plan-file` vs stdin input modes

8. **Create `docs/learned/ci/github-actions-claude-integration.md`** _(from #5775)_
   - Required flags: `--print`, `--verbose`, `--output-format`, `--dangerously-skip-permissions`
   - Reference learn-dispatch workflow as canonical example

### Phase 3: LOW Priority (3 docs)

9. **Create `docs/learned/architecture/type-safety-patterns.md`** _(from #5798)_
10. **Update `docs/learned/testing/integration-testing-patterns.md`** _(from #5784)_
11. **Create `docs/learned/reference/cli-flag-patterns.md`** _(from #5775)_

### Phase 4: Cleanup

12. **Run `erk docs sync`** to regenerate tripwires.md with new entries
13. **Update docs/learned/index.md** with new document entries

## Tripwires to Add

| Location | Tripwire |
|----------|----------|
| output-styling.md | "Before displaying user-provided text in Rich CLI tables" → wrap in `escape_markup()` |
| adding-commands.md | "Before generating TUI commands that depend on optional PlanRowData fields" → implement three-layer validation |
| tripwires.md | "Before implementing mtime-based cache invalidation" → Read graphite-cache-invalidation.md |
| tripwires.md | "Before using PlanContextProvider" → Read plan-context-integration.md |

## Attribution

Items by source plan:

- **#5798**: Steps 1, 9
- **#5796**: Step 5
- **#5795**: Step 7
- **#5785**: Step 2
- **#5784**: Steps 3, 10
- **#5775**: Steps 8, 11
- **#5773**: Steps 4, 6

Plans with no remaining items (close only):
- **#5797** - Already documented
- **#5786** - Duplicate of #5797
- **#5774** - Session tracking already documented

## Verification

After implementation:
1. Run `erk docs sync` and verify tripwires.md updated
2. Check that new docs appear in `docs/learned/index.md`
3. Verify cross-references between related docs work
4. Run `make format` to ensure markdown formatting