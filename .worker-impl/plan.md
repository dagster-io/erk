# Plan: Consolidate Duplicative GitHub ABC Methods

## Overview

After consolidating `GitHubGtKit` into the main `GitHub` ABC (PR #1877), the ABC now contains duplicative methods that serve the same purpose with different signatures. This plan consolidates these into cleaner, unified interfaces.

## Consolidation 1: Mergeability Methods

### Current State
Two methods exist for checking PR mergeability:
- `get_pr_mergeability(repo_root, pr_number) -> PRMergeability` - Returns dataclass with `is_mergeable` and `reason`
- `get_pr_mergeability_status(repo_root, pr_number) -> tuple[bool, str]` - Returns tuple of (mergeable, reason)

### Target State
Keep only `get_pr_mergeability()` which returns the structured `PRMergeability` dataclass.

### Implementation Steps

1. **Update all callers of `get_pr_mergeability_status`**
   - Search for usage in `packages/dot-agent-kit/`
   - Replace calls with `get_pr_mergeability()` and access `.is_mergeable`, `.reason`

2. **Remove `get_pr_mergeability_status` from ABC**
   - File: `packages/erk-shared/src/erk_shared/github/abc.py`
   - Remove abstract method definition

3. **Remove implementations from all GitHub classes**
   - `packages/erk-shared/src/erk_shared/github/real.py` - Remove `get_pr_mergeability_status`
   - `packages/erk-shared/src/erk_shared/github/fake.py` - Remove `get_pr_mergeability_status`
   - `src/erk/core/github/dry_run.py` - Remove `get_pr_mergeability_status`
   - `src/erk/core/github/printing.py` - Remove `get_pr_mergeability_status`

4. **Update test fakes**
   - `packages/dot-agent-kit/tests/unit/kits/gt/fake_ops.py` - Remove `get_pr_mergeability_status`

5. **Run CI to verify**

## Consolidation 2: Branch→PR Lookup Methods

### Current State
Three methods for getting PR info from a branch:
- `get_pr_for_branch(repo_root, branch) -> PRInfo | None` - Full PR info dataclass
- `get_pr_info_for_branch(repo_root, branch) -> dict | None` - Raw dict from CLI
- `get_pr_state_for_branch(repo_root, branch) -> str | None` - Just state string

### Target State
Keep only `get_pr_for_branch()` which returns the typed `PRInfo` dataclass. Callers needing just state can access `.state` attribute.

### Implementation Steps

1. **Audit callers of `get_pr_info_for_branch`**
   - Used in `packages/dot-agent-kit/src/dot_agent_kit/kits/gt/real_ops.py`
   - Used for checking `reviewDecision` field - may need to add this to PRInfo dataclass

2. **Audit callers of `get_pr_state_for_branch`**
   - Find all usages and replace with `get_pr_for_branch().state`

3. **Extend `PRInfo` dataclass if needed**
   - File: `packages/erk-shared/src/erk_shared/github/types.py`
   - Add any missing fields that callers need (e.g., `review_decision`)

4. **Update all callers to use `get_pr_for_branch`**
   - Replace `get_pr_info_for_branch(...)["state"]` with `get_pr_for_branch(...).state`
   - Replace `get_pr_state_for_branch(...)` with `get_pr_for_branch(...).state` (with None check)

5. **Remove `get_pr_info_for_branch` from ABC and implementations**
   - `packages/erk-shared/src/erk_shared/github/abc.py`
   - `packages/erk-shared/src/erk_shared/github/real.py`
   - `packages/erk-shared/src/erk_shared/github/fake.py`
   - `src/erk/core/github/dry_run.py`
   - `src/erk/core/github/printing.py`

6. **Remove `get_pr_state_for_branch` from ABC and implementations**
   - Same files as above

7. **Update test fakes**
   - `packages/dot-agent-kit/tests/unit/kits/gt/fake_ops.py`

8. **Run CI to verify**

## Files to Modify

### Core ABC and Types
- `packages/erk-shared/src/erk_shared/github/abc.py` - Remove 3 abstract methods
- `packages/erk-shared/src/erk_shared/github/types.py` - Potentially extend PRInfo

### Implementations
- `packages/erk-shared/src/erk_shared/github/real.py` - Remove 3 methods
- `packages/erk-shared/src/erk_shared/github/fake.py` - Remove 3 methods
- `src/erk/core/github/dry_run.py` - Remove 3 methods
- `src/erk/core/github/printing.py` - Remove 3 methods

### Callers (need investigation)
- `packages/dot-agent-kit/src/dot_agent_kit/kits/gt/real_ops.py`
- Other callers TBD during implementation

### Test Fakes
- `packages/dot-agent-kit/tests/unit/kits/gt/fake_ops.py` - Remove 3 methods

## NOT Consolidating

**PR Update Methods** - These remain separate:
- `edit_pr(repo_root, pr_number, title, body)` - Full replacement
- `update_pr_title_and_body(repo_root, pr_number, title, body)` - Partial update

Rationale: These have different semantics. `edit_pr` does full replacement (empty string clears field), while `update_pr_title_and_body` only updates provided values. Both are needed.

## Verification

After each consolidation:
1. Run `make format`
2. Run `/fast-ci` to verify types and tests
3. Run `/all-ci` for full test suite