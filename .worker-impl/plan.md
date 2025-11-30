# Plan: erk audit-branches Command

## Overview

Create a Claude slash command `/erk:audit-branches` that audits git branches to identify candidates for cleanup. The command produces an interactive report where Claude analyzes branches, presents findings, and the user can confirm cleanup actions.

## Architecture

### Two Components

1. **Kit CLI Command** (`audit-branches.py`) - Python utility for reliable data gathering
   - Gathers branch metadata (commits ahead, PR status, last non-merge commit date, worktree status)
   - Outputs structured JSON for Claude to analyze
   - Replaces the shell scripts that errored in the session

2. **Slash Command** (`.claude/commands/erk/audit-branches.md`) - Claude workflow orchestration
   - Calls the kit CLI command to gather data
   - Analyzes results semantically (identifies superseded branches, duplicate approaches)
   - Presents interactive cleanup options
   - Executes confirmed cleanups

## Branch Evaluation Criteria

Based on the session transcript, branches are classified into cleanup categories:

| Category | Criteria | Action |
|----------|----------|--------|
| **Empty** | 0 commits ahead of master | Safe to delete |
| **Merged PR** | PR state = MERGED | Safe to delete |
| **Closed PR** | PR state = CLOSED (not merged) | Likely stale, prompt for deletion |
| **Stale** | Last non-merge commit > N days old | Prompt for review |
| **Superseded** | Similar work merged via different branch (semantic analysis) | Prompt for deletion |

## Implementation

### File 1: Kit CLI Command

**Path:** `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/audit_branches.py`

```python
#!/usr/bin/env python3
"""Audit git branches for cleanup candidates.

Gathers branch metadata including:
- Commits ahead of trunk
- PR status (OPEN/CLOSED/MERGED/NONE)
- Last non-merge commit date
- Whether branch is checked out in a worktree

Usage:
    dot-agent run erk audit-branches
    dot-agent run erk audit-branches --stale-days 30

Output:
    JSON object with branch analysis data
"""
```

**Data Structure:**
```python
@dataclass
class BranchInfo:
    name: str
    commits_ahead: int
    pr_state: str  # "OPEN", "CLOSED", "MERGED", "NONE"
    pr_number: int | None
    pr_title: str | None
    last_non_merge_commit_date: str | None  # ISO format
    last_non_merge_commit_sha: str | None
    last_non_merge_commit_message: str | None
    worktree_path: str | None  # Path if checked out, None otherwise
    is_trunk: bool

@dataclass
class AuditResult:
    success: bool
    trunk_branch: str
    branches: list[BranchInfo]
    errors: list[str]  # Any branches that couldn't be analyzed
```

**Key Implementation Details:**

1. **List branches:** Use `ctx.git.list_local_branches(repo_root)`
2. **Get PR status:** Use `ctx.github.get_prs_for_repo(repo_root, include_checks=False)` for batch efficiency
3. **Get commits ahead:** Use `git rev-list --count master..$branch`
4. **Get last non-merge commit:** Use `git log --no-merges -1 --format='%H|%ai|%s' $branch`
5. **Check worktree status:** Use `ctx.git.find_worktree_for_branch(repo_root, branch)`

### File 2: kit.yaml Registration

**Path:** `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit.yaml`

Add entry:
```yaml
  - name: audit-branches
    path: kit_cli_commands/erk/audit_branches.py
    description: Audit git branches for cleanup candidates (empty, merged, stale)
```

### File 3: Slash Command

**Path:** `.claude/commands/erk/audit-branches.md`

```markdown
---
description: Audit git branches for cleanup candidates
---

# /erk:audit-branches

Audit all local git branches to identify cleanup candidates.

## Usage

```bash
/erk:audit-branches
```

## Workflow

### Step 1: Gather Branch Data

Run the kit CLI command to gather branch metadata:

```bash
audit_data=$(dot-agent run erk audit-branches 2>/dev/null)
```

Parse the JSON output to get branch information.

### Step 2: Categorize Branches

Group branches into cleanup categories:

1. **Safe to Delete** (no confirmation needed):
   - Branches with 0 commits ahead AND merged into trunk

2. **Likely Stale** (confirm with user):
   - Branches with PRs that are CLOSED (not merged)
   - Branches with PRs that are MERGED but branch still exists
   - Empty branches (0 commits ahead, likely already merged elsewhere)

3. **May Be Superseded** (semantic analysis):
   - Compare branch purpose (from PR title/commit message) with recent master commits
   - Identify if similar work was done via different branch

4. **Stale** (based on date):
   - Last non-merge commit older than 30 days
   - No active PR

5. **Keep** (do not suggest deletion):
   - Open PRs with recent activity
   - Trunk branch

### Step 3: Present Findings

Present a summary table:

| Category | Count | Branches |
|----------|-------|----------|
| Empty/Merged | N | branch1, branch2, ... |
| Closed PRs | N | branch3, ... |
| Stale (>30 days) | N | branch4, ... |
| Potentially Superseded | N | branch5, ... |
| Active (keep) | N | branch6, ... |

For each category except "Active", list the branches with relevant details:

**Empty/Merged:**
- branch1: 0 commits, PR #123 MERGED
- branch2: 0 commits, no PR

**Closed PRs:**
- branch3: PR #456 CLOSED "Add feature X" (5 commits ahead)

### Step 4: Interactive Cleanup

For each cleanup category (starting with safest):

1. Present the branches to clean up
2. Ask user to confirm (using AskUserQuestion or natural conversation)
3. On confirmation, execute cleanup:
   - If branch is checked out in worktree: Remove worktree first
   - Delete branch: `gt branch delete --force $branch` (or `git branch -D $branch`)
4. Report results

### Step 5: Semantic Analysis (Optional)

For branches that weren't obviously stale, perform semantic analysis:

1. Look at PR titles/commit messages
2. Compare with recent master commits
3. Identify if the work was done via a different branch
4. Present findings and ask user if they want to clean up

## Notes

- Use `git worktree remove` before deleting branches checked out in worktrees
- Use `--force` for branch deletion since branches may not be fully merged
- Skip trunk branch (main/master) entirely
```

### File 4: Tests

**Path:** `tests/kit_cli_commands/test_audit_branches.py`

Test the kit CLI command with FakeGit and FakeGitHub:

1. Test with no branches (only trunk)
2. Test with mixed branches (some merged, some open, some closed)
3. Test with stale branches
4. Test with branches in worktrees
5. Test error handling (git failures, github API failures)

## Files to Create/Modify

| File | Action |
|------|--------|
| `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/audit_branches.py` | CREATE |
| `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit.yaml` | MODIFY (add entry) |
| `.claude/commands/erk/audit-branches.md` | CREATE |
| `tests/kit_cli_commands/test_audit_branches.py` | CREATE |

## Critical Files to Reference

- `/Users/schrockn/code/erk/packages/erk-shared/src/erk_shared/git/abc.py` - Git interface
- `/Users/schrockn/code/erk/packages/erk-shared/src/erk_shared/github/abc.py` - GitHub interface
- `/Users/schrockn/code/erk/packages/erk-shared/src/erk_shared/git/real.py` - Git implementation patterns
- `/Users/schrockn/code/erk/packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/get_pr_metadata.py` - Kit CLI command pattern
- `/Users/schrockn/code/erk/.claude/commands/git/pr-push.md` - Slash command pattern