---
read-when: exiting plan mode, choosing plan workflow options, understanding exit-plan-mode hook behavior, deciding between save and implement
tripwires: 0
---

# Exit-Plan-Mode Hook Decision Flow

## The Five Options

When exiting plan mode, the exit-plan-mode hook presents five workflow options:

### 1. Save the plan (Recommended)

**Action**: Creates a GitHub issue with `erk-plan` label

**Use when**:

- Default choice for most plans
- Want to implement asynchronously (later session or remote workflow)
- Need issue tracking and PR linkage
- Plan is ready but you're not implementing now

**What happens**:

- Runs `erk exec plan-save-to-issue --session-id "${CLAUDE_SESSION_ID}"`
- Creates GitHub issue
- Archives plan to `.erk/scratch/`
- Deletes `~/.claude/plans/*.md` file

### 2. Implement here

**Action**: Implements the plan immediately in the current session (no issue creation)

**Use when**:

- Quick fixes that don't need issue tracking
- Experimental changes
- You're ready to implement right now
- Don't want the overhead of GitHub issue management

**What happens**:

- Skips issue creation
- Proceeds directly to implementation
- Plan stays in `~/.claude/plans/` (not archived)

### 3. Save + implement

**Action**: Creates issue AND implements immediately

**Use when**:

- Want both tracking and immediate completion
- Need PR linked to issue for future reference
- Plan is ready and you want to finish it now
- Important work that needs audit trail

**What happens**:

- Creates GitHub issue (same as option 1)
- Then proceeds to implementation
- Plan is archived
- PR will reference the issue

### 4. View/Edit plan

**Action**: Returns to plan mode for review or modifications

**Use when**:

- Want to review the plan before deciding
- Need to make adjustments
- Uncertain about the current plan quality
- Want to add more context or details

**What happens**:

- Re-enters plan mode
- No state changes
- Can edit and re-exit with a different choice

### 5. Save + submit for review

**Action**: Queues the plan for external review workflow

**Use when**:

- Using erk's remote implementation feature
- Want another agent/person to implement
- Plan requires review before implementation
- Using GitHub Actions workflow dispatch

**What happens**:

- Creates GitHub issue
- Adds plan to review queue
- External workflow picks up for implementation

## Decision Tree

```
Are you implementing now?
├─ Yes
│  ├─ Need issue tracking?
│  │  ├─ Yes → (3) Save + implement
│  │  └─ No → (2) Implement here
│  └─ Not sure → (4) View/Edit plan
└─ No
   ├─ Want remote implementation?
   │  └─ Yes → (5) Save + submit for review
   ├─ Want to implement later yourself?
   │  └─ Yes → (1) Save the plan
   └─ Not sure → (4) View/Edit plan
```

## Common Patterns

**Default workflow**: (1) Save → Review issue later → `/erk:plan-implement <issue-number>`

**Quick iteration**: (2) Implement here → Test → Commit

**Production features**: (3) Save + implement → Issue tracking + immediate work

**Team collaboration**: (5) Save + submit → Remote agent implements

**Second thoughts**: (4) View/Edit → Refine → Choose again

## Session ID Context

Options 1, 3, and 5 all use `--session-id` flag to enable:

- Idempotent issue creation
- Session correlation for analysis
- Plan deduplication

The hook provides session ID via stdin JSON, which the hook script interpolates into the command.

## Related Documentation

- [Plan Persistence](plan-persistence.md) - How plans move from local to GitHub
- [Plan Lifecycle](lifecycle.md) - Complete workflow from creation to merge
- [Session-Based Plan Deduplication](session-deduplication.md) - Why session ID matters
