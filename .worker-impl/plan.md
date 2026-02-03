# Plan: Doc Audit Cleanup — Remove phantom content, fix broken references, stamp 10 docs

## Summary

Adversarial audit of the top 10 highest-priority `docs/learned/` documents revealed widespread phantom content (types/classes that don't exist in the codebase), broken file references, and duplicative sections. This plan applies all audit findings: major rewrites for 2 docs, targeted fixes for 5 docs, and clean stamps for 3 docs.

## Key Codebase Facts (for agent verification)

**Types that DO exist** (verify before editing):
- `SubmitState | SubmitError` in `src/erk/cli/commands/pr/submit_pipeline.py`
- `LandState | LandError` in `src/erk/cli/commands/land_pipeline.py` (LandError has `details: dict[str, str]`, NOT `dict[str, Any] | None`)
- `BranchCreated | BranchAlreadyExists` in `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/types.py`
- `PushResult | PushError` in `packages/erk-shared/src/erk_shared/gateway/git/remote_ops/types.py`
- `MergeResult | MergeError` in `packages/erk-shared/src/erk_shared/gateway/github/types.py`
- `NonIdealState` protocol in `packages/erk-shared/src/erk_shared/non_ideal_state.py`

**Types that DO NOT exist** (phantom — remove all references):
- `GeneratedPlan`, `PlanGenerationError`
- `RoadmapUpdateResult`, `NextStepResult`, `InferenceError`
- `WorktreeAdded`, `WorktreeAddError`, `WorktreeRemoved`, `WorktreeRemoveError`
- `BranchCreateError` (the real type is `BranchAlreadyExists`)
- `CreateBranchResult` (the real type is `BranchCreated`)

**Worktree operations** still use exceptions (`RuntimeError`), NOT discriminated unions. See `packages/erk-shared/src/erk_shared/gateway/git/worktree/abc.py`.

## Implementation Steps

### Step 1: Rewrite `docs/learned/architecture/discriminated-union-error-handling.md`

**Verdict: SIMPLIFY (784 → ~231 lines)**

This doc had massive phantom content — entire sections with fake types.

Actions:
1. Read the current file
2. Remove all phantom type examples (GeneratedPlan, PlanGenerationError, RoadmapUpdateResult, NextStepResult, InferenceError, WorktreeAdded, WorktreeAddError, WorktreeRemoved, WorktreeRemoveError, BranchCreateError)
3. Remove the entire "Worktree/Branch Gateway Conversions" section — worktree ops still use exceptions
4. Fix LandError definition: change `details: dict[str, Any] | None` to `details: dict[str, str]`
5. Remove non-existent file reference `git/worktree/types.py`
6. Keep: "When to Use" decision framework, consumer patterns, exec command error pattern, naming conventions table (but update with real types only), comparison tables
7. Update naming conventions table to reference only real types (BranchCreated, BranchAlreadyExists, PushResult, PushError, etc.)
8. Add frontmatter: `last_audited: "2026-02-03 15:05 PT"` and `audit_result: edited`

The rewritten doc should be ~231 lines focused on the pattern description, real examples, and decision guidance.

### Step 2: Edit `docs/learned/architecture/gateway-abc-implementation.md`

**Verdict: SIMPLIFY (991 → ~746 lines)**

Actions:
1. Read the current file
2. Remove lines ~194-391: entire "Canonical Examples: Worktree Gateway Conversions" section (phantom — worktree ops use exceptions not discriminated unions)
3. Remove "Integration with Fake-Driven Testing" section (duplicative of testing docs)
4. Remove "Reference Implementation: Git Remote Ops" section (restates source code)
5. Remove "Reference: PR #6300" and "Reference: PR #6348" sections (phantom types)
6. Fix `CreateBranchResult` → `BranchCreated` (actual type name)
7. Fix `WorktreeError` → `RuntimeError` (actual exception type)
8. Fix NonIdealState protocol location to `packages/erk-shared/src/erk_shared/non_ideal_state.py`
9. Update worktree sub-gateway description to note it uses exceptions, not discriminated unions
10. Add frontmatter: `last_audited: "2026-02-03 15:15 PT"` and `audit_result: edited`

### Step 3: Fix `docs/learned/architecture/git-graphite-quirks.md`

**Verdict: KEEP with minor fixes (~90% high value)**

Actions:
1. Read the current file
2. Fix broken path: `restack_finalize.py` → use generic `gateway/gt/operations/` reference
3. Fix `branch_manager/graphite.py` → `gateway/branch_manager/graphite.py` (all occurrences)
4. Remove broken link to `restack-operations.md`
5. Add frontmatter: `last_audited: "2026-02-03 15:20 PT"` and `audit_result: edited`

### Step 4: Fix `docs/learned/cli/command-organization.md`

**Verdict: KEEP with minor fixes**

Actions:
1. Read the current file
2. Remove broken link to `../kits/cli-commands.md`
3. Remove broken link to `script-mode.md`
4. Add frontmatter: `last_audited: "2026-02-03 15:25 PT"` and `audit_result: edited`

### Step 5: Fix `docs/learned/cli/output-styling.md`

**Verdict: KEEP with minor fix**

Actions:
1. Read the current file
2. Remove broken link to `script-mode.md`
3. Add frontmatter: `last_audited: "2026-02-03 15:30 PT"` and `audit_result: edited`

### Step 6: Stamp `docs/learned/desktop-dash/forge-vite-setup.md`

**Verdict: KEEP (clean)**

Actions:
1. Read the current file
2. Add frontmatter: `last_audited: "2026-02-03 15:30 PT"` and `audit_result: clean`

### Step 7: Stamp `docs/learned/glossary.md`

**Verdict: KEEP (clean)**

Actions:
1. Read the current file
2. Add frontmatter: `last_audited: "2026-02-03 15:30 PT"` and `audit_result: clean`

### Step 8: Fix `docs/learned/hooks/hooks.md`

**Verdict: KEEP with minor fixes**

Actions:
1. Read the current file
2. Remove broken link to `../../packages/erk-kits/docs/HOOKS.md`
3. Remove broken link to `../../.erk/kits/README.md`
4. Add frontmatter: `last_audited: "2026-02-03 15:30 PT"` and `audit_result: edited`

### Step 9: Stamp `docs/learned/planning/gateway-consolidation-checklist.md`

**Verdict: KEEP (clean)**

Actions:
1. Read the current file
2. Add frontmatter: `last_audited: "2026-02-03 15:30 PT"` and `audit_result: clean`

### Step 10: Rewrite `docs/learned/architecture/claude-cli-progress.md`

**Verdict: SIMPLIFY (231 → ~131 lines)**

Actions:
1. Read the current file
2. Remove duplicative ProgressEvent/CompletionEvent class definitions (these are in the source code)
3. Remove drifted code examples that no longer match source
4. Remove broken reference to `submit_cmd.py`
5. Keep: architecture overview, event flow description, integration guidance
6. Add frontmatter: `last_audited: "2026-02-03 15:00 PT"` and `audit_result: edited`

## Verification

After all edits:
1. Verify all 10 docs have `last_audited` and `audit_result` in frontmatter
2. Verify no broken internal links remain in edited docs
3. Grep for any remaining phantom type references across edited docs
4. Run `ruff check` on any Python code blocks if applicable

## Notes

- All timestamps use `2026-02-03` date with PT timezone
- Steps 1-2 are the largest changes (major rewrites); steps 3-9 are small targeted fixes
- Step 10 was audited in a previous session and may already be partially done — verify current state before editing