# Plan: Consolidated Documentation from 8 Learn Plans

> **Consolidates:** #6626, #6623, #6622, #6621, #6620, #6617, #6589, #6586

## Source Plans

| #    | Title                                                      | Items Merged | Key Status |
| ---- | ---------------------------------------------------------- | ------------ | ---------- |
| 6626 | /local:audit-doc Command                                   | 3 items      | Command on branch (PR #6625), docs not started |
| 6623 | Document Codex CLI Research Findings                       | 2 items      | PR #6616 OPEN, meta-docs not created |
| 6622 | Embed Implementation Plan in Remote Queue Draft PRs        | 0 items      | FULLY COMPLETE - all docs exist |
| 6621 | Codex Support - Core Plumbing (Phases 1-4)                 | 3 items      | Code on branch, docs not created |
| 6620 | Gate Learn/Docs on learned-docs Capability                 | 2 items      | Code implementation needed + docs |
| 6617 | Click Help Text Formatting for Erk CLI Commands            | 3 items      | Pattern exists (21/74), docs missing |
| 6589 | Rename ClaudeExecutor -> PromptExecutor (Merge Two ABCs)   | 4 items      | Code merged, docs 40% complete |
| 6586 | Fix: trigger-async-learn crashes when no branch_name       | 3 items      | Code merged, docs 25% complete |

## What Changed Since Original Plans

- **#6622 is fully complete** - All implementation and documentation already exist on master. No remaining work.
- **#6621 and #6623 overlap** on Codex documentation - both reference Codex reference docs on PR branches.
- **#6589 code already merged** (PR #6587) - only documentation gaps remain.
- **#6586 code already merged** (PR #6585) - tripwire done, 4 doc items remain.
- **#6620 is a code change plan** (capability gating) - out of scope for a learn/docs consolidation.

## Overlap Analysis

- **#6623 + #6621**: Both reference Codex integration. #6623 has meta-documentation items (learn pipeline, session preprocessing). #6621 has architecture items (SandboxMode, InteractiveAgentConfig). Merged into separate sections.
- **#6589 + #6621**: Both touch PromptExecutor patterns. #6589 documents the rename/consolidation. #6621 documents multi-backend extensions. Kept separate as they address different aspects.
- **#6626 + #6617**: Both involve CLI documentation patterns. Kept separate - different concerns (audit command vs help text formatting).

## Excluded Plans

### #6622 - Embed Implementation Plan in Remote Queue Draft PRs
**Reason:** Fully implemented and documented. All 6 HIGH priority items exist on master. No remaining work.

### #6620 - Gate Learn/Docs on learned-docs Capability
**Reason:** This is primarily a **code implementation plan** (add capability gating, modify CLI registration, update sync filtering), not a documentation plan. The code changes (LearnedDocsCapability artifacts, _sync_commands filtering, conditional CLI registration) should be a separate implementation plan, not part of a docs consolidation.

## Remaining Gaps (20 items)

### Category A: Architecture Documentation (7 items)

**A1. Create `docs/learned/architecture/sandbox-modes.md`** _(from #6621)_
- SandboxMode abstraction and mapping table (SandboxMode -> Claude -> Codex)
- Document the two `_sandbox_to_permission_mode()` functions that must stay in sync
- Code refs: `packages/erk-shared/src/erk_shared/context/types.py`, `src/erk/core/interactive_claude.py`, `src/erk/core/prompt_executor.py`
- Verification: File exists with mapping table, frontmatter includes tripwire

**A2. Create `docs/learned/architecture/interactive-agent-config.md`** _(from #6621)_
- InteractiveAgentConfig fields, config file format, backward compat ([interactive-agent] with [interactive-claude] fallback)
- Code refs: `packages/erk-shared/src/erk_shared/context/types.py`, `packages/erk-shared/src/erk_shared/gateway/erk_installation/real.py`
- Verification: File exists with config file example

**A3. Create `docs/learned/architecture/gateway-removal-pattern.md`** _(from #6589)_
- When/how to delete a gateway after consolidation
- Reference the prompt_executor gateway consolidation as example
- Verification: File exists with decision framework

**A4. Create `docs/learned/architecture/re-export-pattern.md`** _(from #6589)_
- Document `# noqa: F401` re-export pattern
- Evidence: `src/erk/core/prompt_executor.py:24` (CommandResult re-export)
- Verification: File exists with ruff interaction guidance

**A5. Update `docs/learned/architecture/prompt-executor-patterns.md`** _(from #6589)_
- Fix outdated "PromptExecutor vs PromptExecutor" comparison section
- Clarify core PromptExecutor != gateway PromptExecutor using fully-qualified names
- Verification: No outdated references remain

**A6. Create `docs/learned/planning/branch-name-inference.md`** _(from #6586)_
- Why branch_name is intentionally omitted at creation time
- Recovery mechanism: P{issue}- pattern matching from current git branch
- Code refs: `src/erk/cli/commands/exec/scripts/get_pr_for_plan.py:88-99`
- Verification: File exists, linked from plan-metadata-fields.md

**A7. Update `docs/learned/architecture/fail-open-patterns.md`** _(from #6586)_
- Add trigger-async-learn as real-world example of defense-in-depth
- Two-layer approach: lenient handler + root cause recovery
- Verification: File updated with new example section

### Category B: CLI Documentation (3 items)

**B1. Create `docs/learned/cli/help-text-formatting.md`** _(from #6617)_
- Click `\b` escape sequence: what it does, why needed, when to use
- Before/after comparison showing formatting difference
- List of 21 commands with pattern, 53 commands missing it
- Verification: File exists with read-when triggers for "docstring" and "Examples sections"

**B2. Add help text tripwire to `docs/learned/cli/tripwires.md`** _(from #6617)_
- CRITICAL: Before writing Examples sections in CLI docstrings without `\b`
- Link to B1 documentation
- Verification: Tripwire appears in cli/tripwires.md

**B3. Add cross-references from `docs/learned/cli/click-patterns.md` and `docs/learned/cli/output-styling.md`** _(from #6617)_
- Link to B1 help-text-formatting.md from related CLI docs
- Verification: Cross-links exist in both files

### Category C: Testing/Refactoring Documentation (2 items)

**C1. Create `docs/learned/testing/fake-api-migration-pattern.md`** _(from #6589)_
- Old pattern: `FakePromptExecutor(output="...", should_fail=True)`
- New pattern: `FakePromptExecutor(prompt_results=[PromptResult(...)])`
- Verification: File exists with before/after examples

**C2. Update `docs/learned/refactoring/libcst-systematic-imports.md`** _(from #6589)_
- Add ABC consolidation as example use case
- Verification: New example section added

### Category D: Audit/Documentation Methodology (3 items)

**D1. Create `docs/learned/commands/audit-doc.md`** _(from #6626)_
- When to use /local:audit-doc, typical workflow, value categories
- Reference the command spec at `.claude/commands/local/audit-doc.md`
- Verification: File exists with usage guide

**D2. Add Prettier tripwire to `docs/learned/ci/tripwires.md`** _(from #6626)_
- CRITICAL: Before creating .claude/ markdown commands without running Prettier
- Verification: Tripwire appears in ci/tripwires.md

**D3. Add PR checkout footer format tripwire to `docs/learned/architecture/tripwires.md`** _(from #6626)_
- CRITICAL: Before modifying PR footer format validation
- Verification: Tripwire appears in architecture/tripwires.md

### Category E: Glossary/Reference Updates (3 items)

**E1. Update `docs/learned/glossary.md`** _(from #6589)_
- Add entries for: PromptExecutor, ClaudePromptExecutor, FakePromptExecutor
- Verification: Three new glossary entries exist

**E2. Update `docs/learned/planning/plan-metadata-fields.md`** _(from #6586)_
- Add "Recovery Mechanism" subsection for branch_name inference
- Verification: Recovery section exists linking to A6

**E3. Update `docs/learned/architecture/subprocess-wrappers.md`** _(from #6586)_
- Add "Lenient vs. Strict Handlers" subsection with decision matrix
- Reference trigger-async-learn's _get_pr_for_plan_direct() pattern
- Verification: New subsection exists

### Category F: Meta-Documentation (2 items) _(from #6623)_

**F1. Create `docs/learned/planning/learn-pipeline-workflow.md`**
- Document the complete learn pipeline with agent orchestration
- Verification: File exists with pipeline stages

**F2. Create `docs/learned/documentation/frontmatter-tripwire-format.md`**
- YAML schema for tripwire frontmatter in docs/learned/ files
- Verification: File exists with schema spec

## Implementation Steps

1. **Create new architecture docs** (A1, A2, A3, A4, A6) - 5 new files
2. **Update existing architecture docs** (A5, A7) - 2 file updates
3. **Create CLI docs** (B1) and add tripwire (B2) and cross-refs (B3) - 1 new file, 3 updates
4. **Create testing/refactoring docs** (C1, C2) - 1 new file, 1 update
5. **Create audit/methodology docs** (D1) and add tripwires (D2, D3) - 1 new file, 2 updates
6. **Update glossary and references** (E1, E2, E3) - 3 updates
7. **Create meta-documentation** (F1, F2) - 2 new files
8. **Run `erk docs sync`** to regenerate index and tripwires-index
9. **Run CI** to verify formatting and docs validation

## Attribution

Items by source:
- **#6626**: D1, D2, D3
- **#6623**: F1, F2
- **#6622**: (none - fully complete)
- **#6621**: A1, A2
- **#6620**: (excluded - code implementation plan)
- **#6617**: B1, B2, B3
- **#6589**: A3, A4, A5, C1, C2, E1
- **#6586**: A6, A7, E2, E3

## Verification

1. All new files have proper frontmatter with `read_when` conditions
2. All tripwires have proper `CRITICAL:` format
3. `erk docs sync` runs without errors
4. `make prettier` passes
5. Index files regenerated correctly