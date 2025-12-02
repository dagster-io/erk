# Plan: `/gt:pr-prep` - Prepare Branch for PR Submission

## Problem

PR body becomes stale after force pushes. The AI-generated summary describes files/changes from the original submission, not the current PR state.

Example: PR #1893 body mentioned `.worker-impl/plan.md` and `.worker-impl/progress.md` files that weren't in the actual PR diff.

## Solution

Create a new slash command `/gt:pr-prep` in `.claude/commands/` that:
1. Checks for restack conflicts (abort if any - do NOT resolve)
2. Squashes commits
3. Generates AI commit message (reusing `commit-message-generator` agent)
4. Amends the commit with that message
5. **Stops there** (no push, no PR creation/update)

**Design principle:** Use kit-cli-push-down pattern - mechanical work in Python CLI, semantic work (AI message generation) in agent.

## Workflow

```
User runs: /gt:pr-prep
    ↓
Kit CLI: dot-agent run gt pr-prep --session-id <id>
    ↓
Check restack conflicts → ABORT if any (do NOT resolve)
    ↓
Squash commits (if 2+)
    ↓
Get diff, write to scratch file
    ↓
Return JSON {success, diff_file, repo_root, branches...}
    ↓
Slash command: Delegate to commit-message-generator agent
    ↓
Agent returns AI commit message
    ↓
Slash command: git commit --amend -m "<message>"
    ↓
DONE - User can now push
```

## Implementation

### Step 1: Create kit CLI command `pr_prep.py`

**File:** `packages/erk-shared/src/erk_shared/integrations/gt/kit_cli_commands/gt/pr_prep.py`

Reuse code from `submit_branch.py`:
- Auth checks (gt/gh) - reuse from `execute_pre_analysis()`
- Squash logic - reuse `ops.main_graphite().squash_branch()`
- Parent branch detection - reuse from `execute_pre_analysis()`

**New logic:**
- Check restack conflicts FIRST (before squash)
- Get local diff (`git diff {parent}...HEAD`) instead of PR diff
- Do NOT submit or push

```python
@dataclass
class PrepResult:
    success: bool
    diff_file: str
    repo_root: str
    current_branch: str
    parent_branch: str
    message: str

@dataclass
class PrepError:
    success: bool
    error_type: str  # restack_conflict, no_branch, no_parent, etc.
    message: str
    details: dict[str, str]

def execute_prep(session_id: str, ops: GtKit | None = None) -> PrepResult | PrepError:
    """Prepare branch for PR (squash + diff extraction, NO submit)."""
    # 1. Check restack conflicts FIRST
    # 2. Squash if needed (reuse from submit_branch)
    # 3. Get local diff and write to scratch
    # 4. Return result JSON
```

### Step 2: Create slash command `/gt:pr-prep`

**File:** `.claude/commands/gt/pr-prep.md`

Follow same pattern as `pr-submit.md`:

```markdown
---
description: Prepare branch for PR (squash + AI commit message, no push)
---

# Prepare Branch for PR

Squashes commits, generates AI commit message, amends commit.
Does NOT push - lets you review/edit before pushing.

## Implementation

### Step 1: Run Prep Phase (Kit CLI)

dot-agent run gt pr-prep --session-id "<session-id>" 2>&1

Returns JSON with diff_file, repo_root, current_branch, parent_branch.

If `success: false` with `error_type: "restack_conflict"`:
- Display: "❌ Restack conflicts detected. Run `gt restack` to resolve first."
- STOP immediately. Do NOT attempt to resolve.

### Step 2: Generate Commit Message via AI

Reuse commit-message-generator agent (same as pr-submit):

Task(
    subagent_type="commit-message-generator",
    prompt="Analyze the git diff and generate a commit message.

Diff file: {diff_file}
Repository root: {repo_root}
Current branch: {current_branch}
Parent branch: {parent_branch}

Use the Read tool to load the diff file."
)

Parse output: First line = title, rest = body.

### Step 3: Amend Commit

Write full message to scratch file, then:

git commit --amend -F ".erk/scratch/<session-id>/commit-msg.txt"

### Step 4: Report Results

✓ Branch prepared for submission
  Commit message updated with AI-generated summary

Next steps:
  - Review: git log -1
  - Edit:   git commit --amend
  - Push:   gt submit --publish
```

### Step 3: Register kit CLI in kit.yaml

**File:** `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/kit.yaml`

Add `pr-prep` under `kit_cli_commands`.

## Code Reuse from submit_branch.py

| Function/Logic | Reuse? | Notes |
|----------------|--------|-------|
| Auth checks (gt/gh) | ✅ Yes | From `execute_pre_analysis()` |
| `get_current_branch()` | ✅ Yes | Direct reuse |
| `get_parent_branch()` | ✅ Yes | Direct reuse |
| `squash_branch()` | ✅ Yes | Direct reuse |
| `count_commits_ahead()` | ✅ Yes | Direct reuse |
| PR submission (`gt submit`) | ❌ No | Not needed for prep |
| PR diff (`gh pr diff`) | ❌ No | Use local git diff instead |
| Finalize phase | ❌ No | Not needed for prep |

## Files to Create/Modify

| File | Action |
|------|--------|
| `packages/erk-shared/src/erk_shared/integrations/gt/kit_cli_commands/gt/pr_prep.py` | **NEW** - Kit CLI |
| `.claude/commands/gt/pr-prep.md` | **NEW** - Slash command |
| `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/kit.yaml` | Add kit CLI reference |
| `packages/dot-agent-kit/tests/unit/kits/gt/test_pr_prep.py` | **NEW** - Tests |

## Error Handling

| Error Type | Behavior |
|------------|----------|
| `restack_conflict` | ABORT immediately. Do NOT auto-resolve. Display: "Run `gt restack` first" |
| `no_branch` | ABORT - not on a valid branch |
| `no_parent` | ABORT - can't determine parent branch |
| `no_commits` | ABORT - no commits to prepare |
| `squash_conflict` | ABORT - conflicts during squash |

## Testing

1. Clean branch → verify squash + message update works
2. Restack conflicts → verify abort with helpful message
3. Single commit → verify no squash, just message update
4. Verify message matches what `/gt:pr-submit` would produce