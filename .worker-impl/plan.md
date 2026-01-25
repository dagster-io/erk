# Plan: Consolidated erk-learn Documentation Plan

> **Consolidates:** #6021, #6020, #6019, #6012, #6011, #6006

## Source Plans

| #     | Title                                                       | Items Merged | Status                 |
| ----- | ----------------------------------------------------------- | ------------ | ---------------------- |
| #6021 | Add create_issue Method to BeadsGateway                     | 3 items      | FULLY IMPLEMENTED      |
| #6020 | PR Review with Task Pattern for Context Isolation           | 5 items      | SUBSTANTIALLY COMPLETE |
| #6019 | Improve Remote Rebase Agent PR Comments                     | 4 items      | PARTIALLY COMPLETE     |
| #6012 | Add erk-consolidated Label to Prevent Re-consolidation      | 4 items      | DOCS MISSING           |
| #6011 | Convert Roadmap Updater to LLM Inference                    | 5 items      | DOCS MISSING           |
| #6006 | Phase 4 Plan Generation and Submission for Objective Reconciler | 6 items  | DOCS MISSING           |

## What Changed Since Original Plans

- **#6021**: All code items fully implemented in PR #6018; documentation already exists
- **#6020**: Task context isolation docs created; `context: fork` feature documented (PR #6014)
- **#6019**: Remote rebase improvements implemented in PR #6016; docs still missing
- **#6012**: `erk-consolidated` label implemented in commands but undocumented
- **#6011**: PromptExecutor gateway fully implemented but undocumented
- **#6006**: Objectives modules fully implemented but documentation incomplete

## Investigation Findings

### Corrections to Original Plans

- **#6021**: No corrections needed - plan was accurate and fully implemented
- **#6020**: Comment classification model embedded in skills rather than standalone doc (acceptable alternative)
- **#6019**: Original plan mentioned docs that don't exist yet
- **#6012**: Implementation exists but all 4 documentation items missing
- **#6011**: Code complete; 3 proposed docs don't exist
- **#6006**: "Phase 4" is not a lifecycle phase - it's part of objective reconciliation (naming correction)

### Additional Details Discovered

1. **Existing Documentation**:
   - `docs/learned/architecture/task-context-isolation.md` (250 lines) - comprehensive
   - `docs/learned/claude-code/context-fork-feature.md` (134 lines) - complete
   - `docs/learned/architecture/gateway-abc-implementation.md` - BeadsGateway as reference

2. **Discriminated Union Patterns** in active use:
   - `NextStepResult | InferenceError`
   - `GeneratedPlan | PlanGenerationError`
   - `RoadmapUpdateResult` with success field
   - Not documented as a unified pattern

3. **Label State Machine Pattern** implemented but undocumented:
   - `erk-consolidated` prevents re-consolidation
   - Used in `/erk:replan` and `/local:replan-learn-plans`

### Overlap Analysis

| Documentation Item                       | Source Plans   | Priority |
| ---------------------------------------- | -------------- | -------- |
| Discriminated union error handling       | #6006, #6011   | HIGH     |
| GitHub Actions output patterns           | #6019          | MEDIUM   |
| Plan generation workflow                 | #6006          | HIGH     |
| Roadmap updates                          | #6006          | MEDIUM   |
| PromptExecutor gateway                   | #6011          | HIGH     |
| Consolidation labels/state machines      | #6012          | MEDIUM   |
| FakePromptExecutor transient failures    | #6011          | LOW      |
| JSON parsing in workflows                | #6019          | LOW      |

## Remaining Gaps

### HIGH Priority

1. **Plan Generation Workflow** _(from #6006)_
   - Location: `docs/learned/objectives/plan-generation-workflow.md`
   - Document `generate_plan_for_step()` function and prompt design
   - Reference: `packages/erk-shared/src/erk_shared/objectives/plan_generator.py`

2. **PromptExecutor Gateway Documentation** _(from #6011)_
   - Location: `docs/learned/architecture/prompt-executor-gateway.md`
   - Document 3-file simplified pattern, FakePromptExecutor test patterns
   - Reference: `packages/erk-shared/src/erk_shared/prompt_executor/`

3. **Discriminated Union Error Handling** _(from #6006, #6011)_
   - Location: `docs/learned/architecture/discriminated-union-error-handling.md`
   - Unify documentation of `T | ErrorType` pattern used in objectives module
   - Cross-reference existing `not-found-sentinel.md`

### MEDIUM Priority

4. **Consolidation Labels** _(from #6012)_
   - Location: `docs/learned/planning/consolidation-labels.md`
   - Document `erk-consolidated` label purpose and workflow
   - Add tripwire for label usage
   - Add glossary entry

5. **Roadmap Updates** _(from #6006)_
   - Location: `docs/learned/planning/roadmap-updates.md`
   - Document `update_roadmap_with_plan()` function
   - Reference: `packages/erk-shared/src/erk_shared/objectives/roadmap_updater.py`

6. **GitHub Actions Output Patterns** _(from #6019)_
   - Location: `docs/learned/ci/github-actions-output-patterns.md`
   - Document GITHUB_OUTPUT heredoc pattern
   - Document JSON parsing from workflow outputs

### LOW Priority (Optional)

7. **FakePromptExecutor Transient Failures** _(from #6011)_
   - Could be folded into PromptExecutor gateway doc
   - Document `transient_failure_count` parameter for retry testing

8. **JSON Parsing in Workflows** _(from #6019)_
   - Could be folded into GitHub Actions output patterns doc

## Implementation Steps

1. **Create `plan-generation-workflow.md`** _(from #6006)_
   - Document function signature and behavior
   - Include prompt template explanation
   - Show integration with reconciliation workflow
   - Add read_when triggers

2. **Create `prompt-executor-gateway.md`** _(from #6011)_
   - Document 3-file simplified gateway pattern
   - FakePromptExecutor usage patterns
   - Sequential response simulation
   - Transient failure injection _(folds in #6011 low-priority item)_

3. **Create `discriminated-union-error-handling.md`** _(from #6006, #6011)_
   - Document pattern: `T | ErrorType` unions
   - Show `isinstance(result, ErrorType)` consumer pattern
   - Reference sentinel pattern doc
   - Examples from objectives module

4. **Create `consolidation-labels.md`** _(from #6012)_
   - Document `erk-consolidated` label
   - Explain state machine pattern
   - Show workflow integration

5. **Add tripwire entry** _(from #6012)_
   - Add to `tripwires.md` frontmatter for consolidated label usage

6. **Add glossary entry** _(from #6012)_
   - Add `erk-consolidated` to `glossary.md`

7. **Create `roadmap-updates.md`** _(from #6006)_
   - Document LLM-based roadmap updating
   - Show update rules and validation

8. **Create `github-actions-output-patterns.md`** _(from #6019)_
   - GITHUB_OUTPUT heredoc pattern
   - Multi-line content handling
   - JSON parsing patterns _(folds in #6019 low-priority item)_

## Attribution

Items by source:

- **#6021**: No remaining items (fully complete)
- **#6020**: No remaining items (substantially complete)
- **#6019**: Steps 8
- **#6012**: Steps 4, 5, 6
- **#6011**: Steps 2 (with transient failure content)
- **#6006**: Steps 1, 3, 7

## Related Documentation

Skills to load:

- `learned-docs` - for documentation structure and frontmatter
- `dignified-python` - if documenting code patterns

Docs to reference:

- `docs/learned/architecture/gateway-abc-implementation.md`
- `docs/learned/architecture/not-found-sentinel.md`
- `docs/learned/architecture/task-context-isolation.md`
- `docs/learned/objectives/index.md`
- `docs/learned/planning/lifecycle.md`

## Verification

1. Run `erk docs sync` to regenerate index files after adding new docs
2. Check all new docs appear in appropriate index.md files
3. Verify tripwire entry appears in generated `tripwires.md`
4. Verify glossary entry appears correctly
5. Run `make format` to ensure markdown formatting is correct