# Plan: Scope Session XML Storage by Plan Number

## Problem

The `/erk:learn` command stores preprocessed session XML files in `.erk/scratch/sessions/*.xml`. This path is **not plan-scoped**, creating collision risk when learning from multiple plans in the same worktree.

Current:
```
.erk/scratch/sessions/*.xml  # All plans mixed together
```

Desired:
```
.erk/scratch/plans/{issue-number}/processed_session_xmls/*.xml  # Plan-scoped
```

## Implementation

### 1. Update `/erk:learn` Command

**File:** `.claude/commands/erk/learn.md`

Update Step 4 to use plan-scoped paths:

**Before (lines 68-76):**
```bash
mkdir -p .erk/scratch/sessions
erk exec preprocess-session <session-path> --stdout > .erk/scratch/sessions/<session-id>.xml
# ...
erk exec extract-session-from-issue <issue-number> --stdout > .erk/scratch/sessions/plan-issue-<issue-number>.xml
```

**After:**
```bash
mkdir -p .erk/scratch/plans/<issue-number>/processed_session_xmls
erk exec preprocess-session <session-path> --stdout > .erk/scratch/plans/<issue-number>/processed_session_xmls/<session-id>.xml
# ...
erk exec extract-session-from-issue <issue-number> --stdout > .erk/scratch/plans/<issue-number>/processed_session_xmls/plan-issue.xml
```

**Gist creation (line 83):**
```bash
gh gist create --desc "Learn materials for plan #<issue-number>" .erk/scratch/plans/<issue-number>/processed_session_xmls/*.xml
```

**Learn plan file path (lines 193, 212):**
```bash
# Old path reference in Step 8:
.erk/scratch/sessions/<session-id>/learn-plan.md

# New:
.erk/scratch/plans/<issue-number>/learn-plan.md
```

### 2. Update Learn Plan File Path in Step 8

The learn plan file itself should also be plan-scoped:
- Old: `.erk/scratch/sessions/<session-id>/learn-plan.md`
- New: `.erk/scratch/plans/<issue-number>/learn-plan.md`

This makes the entire plan scratch directory self-contained:
```
.erk/scratch/plans/<issue-number>/
├── processed_session_xmls/
│   ├── <session-id>.xml
│   └── plan-issue.xml
└── learn-plan.md
```

## Verification

1. Run `/erk:learn` on a plan issue
2. Verify files are created under `.erk/scratch/plans/{issue}/processed_session_xmls/`
3. Verify gist upload includes correct files
4. Verify no files remain in `.erk/scratch/sessions/` from learn workflow