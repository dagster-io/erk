# Documentation Plan: Branch Tracking Inconsistency Fix for Remote Refs [erk-learn]

## Context

This learn plan documents insights discovered during the implementation of issue #5509 ("Fix: Branch Tracking Inconsistency in erk submit"), which identified and fixed a subtle bug in how branches are tracked when using Graphite alongside Git.

**Original Issue #5509**: Erk's submit command was failing when processing remote refs because `BranchManager.create_branch()` was calling `graphite.track_branch()` with branch names that included the `origin/` prefix (e.g., `origin/main`). Graphite's `gt track` command **only accepts local branch names**, not remote refs—this limitation was not previously documented.

**Plan #5528 Objective**: Document this edge case to prevent future agents from debugging the same issue, and to guide developers on the correct abstraction pattern.

## Raw Materials

https://gist.github.com/schrockn/69c30919d180f2cb8b90561355de65c0

## Implementation Summary

**Documentation Added** (PR #5569):

1. **New Section in `docs/learned/architecture/git-graphite-quirks.md`**: "Graphite track_branch Remote Ref Limitation"
   - Explains the surprising behavior and why it's surprising (Git's flexibility creates incorrect expectations)
   - Shows the concrete code pattern used in `GraphiteBranchManager.create_branch()` to normalize refs
   - Demonstrates the design principle: tool quirks absorbed at abstraction boundaries
   - Documents the anti-pattern and location in codebase

2. **New Tripwire in `docs/learned/tripwires.md`**:
   - Added critical warning for calling `graphite.track_branch()` with remote refs
   - Links to the full documentation for context

## What Was Learned

**[Impl]** From the implementation of #5509, the team discovered that Graphite has a surprising limitation compared to Git:
- Git commands (`git branch`, `git checkout`) accept both local branch names and remote refs transparently
- Graphite's `gt track` command **only accepts local branch names**
- This asymmetry creates confusion when refactoring code to use Graphite
- Error messages from `gt track` don't clearly indicate "the issue is the origin/ prefix"

**[Plan]** The lesson: Tool inconsistencies should be documented when discovered, with both:
1. The "why it's surprising" context (so future developers understand the mental mismatch)
2. The resolution pattern used in the codebase (the `removeprefix("origin/")` normalization in `BranchManager`)

This prevents the next agent from rediscovering the issue and gives developers guidance on the correct abstraction pattern.

## Documentation Items

| Item | Status | Location | Action | Source |
|------|--------|----------|--------|--------|
| Graphite remote ref limitation | ✅ DOCUMENTED | `docs/learned/architecture/git-graphite-quirks.md` | New section "Graphite track_branch Remote Ref Limitation" with full explanation, code example, and design guidance | [Impl] |
| Tripwire for direct graphite.track_branch() calls | ✅ DOCUMENTED | `docs/learned/tripwires.md` | New tripwire entry linking to git-graphite-quirks.md | [Impl] |

**Inventory Coverage**: 2/2 items documented

- **Removed**: None
- **Changed Behavior**: None
- **New API/Methods**: None (existing `BranchManager.create_branch()` used correctly)
- **New Patterns**: None (existing abstraction pattern documented)
- **Quirk/Edge Case**: ✅ Graphite's remote ref limitation (fully documented)

## Validation

✅ **Documentation Completeness**: All insights from the implementation are captured
✅ **No Contradictions**: New documentation aligns with existing architecture docs
✅ **Tripwire Coverage**: Critical safety warning added for developers
✅ **Abstraction Integrity**: Documentation reinforces the correct pattern (use `BranchManager`, don't call `graphite.track_branch()` directly)

## Next Steps for Agents

Future agents encountering branch tracking issues should:
1. Read `docs/learned/architecture/git-graphite-quirks.md` (includes this new section)
2. Use `BranchManager.create_branch()` for branch creation (handles normalization automatically)
3. Avoid calling `graphite.track_branch()` directly when branch names may contain `origin/` prefix