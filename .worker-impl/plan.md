# Extraction Plan: Conflict Resolution Style Guidance

## Objective

Add minor enhancements to conflict resolution documentation covering style preference resolution and cherry-pick operations.

## Source Information

- **Session ID**: e234fd59-45e3-46f5-bb55-73cf64b4bf57
- **Branch**: quick-submit
- **Context**: Resolved cherry-pick conflict involving style/readability choices

## Documentation Items

### Item 1: Style Preference Resolution Guidance

**Type**: Category A (Learning Gap)
**Location**: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/docs/erk/includes/conflict-resolution.md`
**Action**: Update
**Priority**: Low

**Rationale**: The conflict in this session was about extracting long inline expressions into named variables for readability. While the existing docs classify conflicts as "mechanical" vs "semantic", they don't explicitly mention style/readability preferences as a resolution criterion.

**Draft Content**:

Add to the "Classify the Conflict" section after the existing decision tree:

```markdown
#### Style/Readability Conflicts

When both versions are functionally equivalent but differ in style:

- **Variable extraction**: Prefer extracting long expressions into named variables
- **Line length**: Prefer the version that stays within reasonable line lengths
- **Consistency**: Match the surrounding code's style conventions

These are mechanical conflicts - auto-resolve by choosing the more readable version.
```

### Item 2: Cherry-pick vs Rebase Note

**Type**: Category A (Learning Gap)  
**Location**: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/merge-conflicts-fix.md`
**Action**: Update
**Priority**: Low

**Rationale**: The `/erk:merge-conflicts-fix` command references `gt continue` for rebase continuation, but this session involved a cherry-pick which uses `git cherry-pick --continue`. The command should handle both cases.

**Draft Content**:

Update step 3 to detect the operation type:

```markdown
3. **After resolving all conflicts:**
   - If project memory includes a precommit check, run it and ensure no failures
   - Stage the resolved files with `git add`
   - Continue based on operation type:
     - If rebasing: `gt continue` (or `git rebase --continue`)
     - If cherry-picking: `git cherry-pick --continue`
     - Check `git status` output to determine which operation is in progress
```

## Summary

Low-priority enhancements that would slightly improve conflict resolution guidance. The existing documentation is comprehensive; these are minor refinements based on a routine session.