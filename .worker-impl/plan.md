# Documentation Plan: Branch Tracking Inconsistency Fix for Remote Refs

## Context

**Issue**: #5509  
**PR**: #5512  
**Title**: Fix branch tracking inconsistency in BranchManager.create_branch() for remote refs

This was a bug fix that addressed an inconsistency between Git's branch creation semantics and Graphite's branch tracking requirements.

### The Problem
- Graphite's `gt track --parent <branch>` command **only accepts local branch names** (e.g., `main`)
- It rejects remote refs like `origin/main`
- Git's `git branch` and `git checkout` commands accept both local and remote refs transparently
- The code was passing remote refs directly to Graphite, causing tracking to fail or create incorrect parent relationships

### The Solution
- Centralized branch creation logic in `BranchManager.create_branch()`
- Added logic to strip `origin/` prefix before calling Graphite's `track_branch()` method
- Simplified the submit command to use a single unified operation instead of separate git + track calls
- Updated tests to clarify that Graphite receives local branch names

## PR Analysis Summary

**Files Changed**: 3  
**Additions**: +12  
**Deletions**: -9

### Modified Files
1. `packages/erk-shared/src/erk_shared/branch_manager/graphite.py` - Core fix
2. `src/erk/cli/commands/submit.py` - Simplified caller code
3. `tests/commands/submit/test_basic_submission.py` - Updated test comments

### Key Code Changes

**Before (submit.py)**:
```python
ctx.git.create_branch(repo.root, branch_name, f"origin/{base_branch}")
ctx.branch_manager.track_branch(repo.root, branch_name, base_branch)  # Separate calls
```

**After (submit.py)**:
```python
ctx.branch_manager.create_branch(repo.root, branch_name, f"origin/{base_branch}")  # Unified
```

**Before (graphite.py)**:
```python
self.graphite.track_branch(repo_root, branch_name, base_branch)  # Direct pass
```

**After (graphite.py)**:
```python
parent_for_graphite = base_branch
if base_branch.startswith("origin/"):
    parent_for_graphite = base_branch.removeprefix("origin/")
self.graphite.track_branch(repo_root, branch_name, parent_for_graphite)  # Normalized
```

## Design Insights

### Pattern: Centralize Tool-Specific Quirks at Abstraction Boundaries
- **Discovery**: Graphite has tool-specific requirements that differ from Git
- **Solution**: Hide this in the BranchManager abstraction layer
- **Benefit**: Callers (like submit command) don't need to understand Graphite's limitations
- **Lesson**: Abstractions should absorb tool quirks, not expose them upward

### Pattern: Consolidate Related Operations
- **Before**: Two separate operations (git create + track)
- **After**: Single unified operation (BranchManager.create_branch)
- **Benefit**: Clearer intent, reduced error surface, atomic operation
- **Lesson**: When you always do X then Y, combine them into a single method

### Python Idiom: Use removeprefix() Without Conditional
- **Discovery**: Code initially had `if base_branch.startswith("origin/"):` before removeprefix
- **Insight**: `str.removeprefix()` returns the string unchanged if prefix doesn't exist
- **Refactoring**: Later simplified to just `base_branch.removeprefix("origin/")`
- **Lesson**: Prefer idiomatic Python methods over explicit conditionals when equivalent

## Documentation Needs Analysis

### Inventory of What Was Built

| Item | Type | New? | Documentation Needed |
|------|------|------|---------------------|
| `GraphiteBranchManager.create_branch()` normalized logic | Method enhancement | No - existing method | **YES** - Quirk documentation |
| `_submit_single_issue()` refactored to use unified API | Function refactoring | No - internal detail | No - internal change only |
| Test comment clarification about Graphite tracking | Test documentation | Yes - new comment | **YES** - Part of quirk doc |
| Remote ref normalization pattern | Pattern discovery | Not code | **YES** - Architectural pattern |
| Graphite `gt track` remote ref limitation | Tool quirk | Not code | **YES** - Critical gotcha |

### Documentation Opportunities

**HIGH PRIORITY:**
1. **Document Graphite's remote ref limitation** - This is a gotcha that could easily cause bugs if someone bypasses BranchManager and calls Graphite directly
2. **Update git-graphite-quirks.md** - This limitation belongs in the existing quirks catalog
3. **Consider adding tripwire** - Warn agents before calling graphite.track_branch() with potentially remote refs

**LOWER PRIORITY:**
1. **BranchManager abstraction benefit** - Document why BranchManager centralizes this (defensive layering)
2. **Test expectations** - Already documented in test comments, no separate doc needed

### Existing Documentation Check

Searched `docs/learned/` for references to:
- `origin/` prefix handling
- `removeprefix` patterns
- Graphite remote ref limitations

**Result**: No existing documentation covers Graphite's remote ref limitation. This is a documentation gap.

## Teaching Gap Assessment

**"Self-documenting code" is not valid here because:**
- The limitation is not visible in method signatures
- Callers have no indication that remote refs will fail
- The fix is defensive (works silently) and easy to bypass
- Future agents might add code that calls Graphite directly, bypassing BranchManager

**Code shows WHAT (strip origin/) but not WHY (Graphite doesn't accept remote refs)**

## Outdated Documentation Check

No existing documentation references removed or changed features. This was a pure internal refactoring with no behavioral changes from a user perspective.

## Raw Materials

Analysis conducted on:
- Planning session: 253fa2d7-6959-4bdb-a828-f002204f6b2d
- Implementation session: c89a2c18-cf04-4b6a-a408-9e26ea895339
- PR #5512 diff analysis
- Session preprocessing with token reduction

## Recommendations

### Documentation to Create/Update

1. **Expand git-graphite-quirks.md with new section**
   - **Title**: "Graphite track_branch Remote Ref Limitation"
   - **Content**: Document that `gt track` only accepts local branch names
   - **Why**: Prevent future bugs from developers bypassing BranchManager
   - **Location**: `docs/learned/architecture/git-graphite-quirks.md`

2. **Optional: Add tripwire**
   - **Trigger**: Before calling `graphite.track_branch()` with any string parameter
   - **Warning**: Check that branch name is local, not remote ref
   - **Location**: Update `docs/learned/tripwires.md`

### Files to Create/Update

| File | Action | Content |
|------|--------|---------|
| `docs/learned/architecture/git-graphite-quirks.md` | Update existing | Add "Remote Ref Limitation" section |
| `docs/learned/tripwires.md` | Update existing | Optional tripwire about graphite.track_branch() |

## Session Analysis Notes

Both preprocessing sessions completed successfully:
- Planning session: 38.4% token reduction (44,180 → 27,193 chars)
- Implementation session: Minimal content (99.2% reduction - essentially empty/test only)

Code diff analyzer identified this as a pure bug fix with one significant architectural insight: **tool quirks belong in abstraction boundaries, not scattered across callers**.