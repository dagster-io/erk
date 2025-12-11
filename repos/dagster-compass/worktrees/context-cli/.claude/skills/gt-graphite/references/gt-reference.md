---
description: "Graphite CLI for stacked pull requests"
url: "https://graphite.com/"
__dot_agent:
  kit_id: gt
  kit_version: 0.1.0
  artifact_type: skill
  artifact_path: skills/gt-graphite/references/gt-reference.md
---

# Graphite (gt) Mental Model

**Last Updated**: 2025-10-11

A comprehensive guide to understanding Graphite's mental model, command structure, and integration patterns.

---

## Table of Contents

- [What is Graphite?](#what-is-graphite)
- [Core Mental Model](#core-mental-model)
- [Terminology](#terminology)
- [Metadata Storage](#metadata-storage)
- [Command Reference](#command-reference)
- [Workflow Patterns](#workflow-patterns)
- [Erk Integration](#erk-integration)
- [Practical Examples](#practical-examples)

---

## What is Graphite?

Graphite is a CLI tool (`gt`) that implements **stacked pull requests** - a development workflow where large features are broken down into small, incremental changes built on top of each other.

### The Problem It Solves

Without Graphite, working on dependent features requires:

1. Waiting for PR #1 to be reviewed before starting PR #2
2. OR creating feature branches off feature branches (messy)
3. OR squashing everything into one giant PR (hard to review)

With Graphite, you can:

- Create multiple dependent branches immediately
- Submit each as a separate PR for easier review
- Continue building upstack while earlier PRs are in review
- Automatically rebase everything when changes are requested

### Core Philosophy

**Think in stacks, not branches.** A stack is a linear chain of dependent changes, each reviewable independently, but building on previous work.

```
main (trunk)
  └─ feature/phase-1     ← PR #123: Add API endpoints
       └─ feature/phase-2     ← PR #124: Update frontend (depends on #123)
            └─ feature/phase-3     ← PR #125: Add docs (depends on #124)
```

Each PR can be reviewed and merged independently (in order), keeping changes small and focused.

---

## Core Mental Model

### Stacks are Linear Chains

A **stack** is a sequence of branches where each branch (except trunk) has exactly one parent.

```
VALID STACK (linear):
main → feature-a → feature-b → feature-c

INVALID (not a stack, this is branching):
main → feature-a → feature-b
            └─────→ feature-x
```

While gt's internal data structure supports branching (a branch can have multiple children), **stack operations treat each chain linearly**.

### Parent-Child Relationships

Every branch tracked by gt (except trunk) has a **parent branch**:

- **Parent**: The branch this one builds upon
- **Children**: Branches that build upon this one

```
feature-b:
  parent: feature-a
  children: [feature-c, feature-d]
```

When you modify feature-b, gt **automatically restacks** feature-c and feature-d to include your changes.

### Directional Navigation

gt uses directional terminology:

- **Downstack** / **Down**: Toward trunk (toward the base)
  - `gt down` moves from feature-b → feature-a → main

- **Upstack** / **Up**: Away from trunk (toward the tip)
  - `gt up` moves from feature-a → feature-b → feature-c

- **Bottom**: The branch closest to trunk in your stack

- **Top**: The tip of your stack (the leaf node)

### Trunk Branch

The **trunk** is the main branch that all stacks build upon:

- Usually `main` or `master`
- Configured via `gt repo init`
- Stored in `.git/.graphite_repo_config`

Trunk is special:

- Has no parent
- `validationResult: "TRUNK"` in metadata
- Target for merging all PRs

---

## Terminology

### Essential Terms

| Term          | Definition                                | Example                                           |
| ------------- | ----------------------------------------- | ------------------------------------------------- |
| **Stack**     | Linear chain of dependent branches        | `main → feat-1 → feat-2 → feat-3`                 |
| **Trunk**     | Primary branch (main/master)              | `main`                                            |
| **Parent**    | Branch this one builds upon               | feat-2's parent is feat-1                         |
| **Children**  | Branches building upon this one           | feat-1's children: [feat-2]                       |
| **Downstack** | Branches between current and trunk        | From feat-3: [feat-2, feat-1, main]               |
| **Upstack**   | Branches above current branch             | From feat-1: [feat-2, feat-3]                     |
| **Restack**   | Rebase branches to include parent changes | After modifying feat-1, restack feat-2 and feat-3 |
| **Track**     | Register a branch with gt                 | `gt track` sets parent relationship               |
| **Submit**    | Push branches and create/update PRs       | `gt submit` → creates GitHub PRs                  |

### Command Aliases

gt provides short aliases for common commands:

| Alias   | Full Command        | Description              |
| ------- | ------------------- | ------------------------ |
| `gt c`  | `gt create`         | Create new branch        |
| `gt m`  | `gt modify`         | Modify current branch    |
| `gt s`  | `gt submit`         | Submit PRs               |
| `gt ss` | `gt submit --stack` | Submit full stack        |
| `gt u`  | `gt up`             | Move up stack            |
| `gt d`  | `gt down`           | Move down stack          |
| `gt t`  | `gt top`            | Move to top              |
| `gt b`  | `gt bottom`         | Move to bottom           |
| `gt l`  | `gt log`            | Show stack visualization |
| `gt co` | `gt checkout`       | Checkout branch          |
| `gt r`  | `gt restack`        | Restack branches         |

---

## Metadata Storage

gt stores all metadata in the `.git` directory (shared across worktrees).

### `.git/.graphite_repo_config`

**Purpose**: Repository-level configuration

```json
{
  "trunk": "main",
  "trunks": [
    {
      "name": "main"
    }
  ],
  "lastFetchedPRInfoMs": 1760216173225,
  "lastFetchedFeatureFlagsInMs": 1760216173226
}
```

**Key Fields**:

- `trunk`: Current trunk branch name
- `trunks`: Array of configured trunk branches
- `lastFetchedPRInfoMs`: Timestamp of last PR info fetch

### `.git/.graphite_pr_info`

**Purpose**: Cached GitHub PR information

```json
{
  "prInfos": [
    {
      "prNumber": 66,
      "title": "Feature ideas",
      "body": "...",
      "state": "OPEN",
      "reviewDecision": "REVIEW_REQUIRED",
      "url": "https://app.graphite.com/github/pr/owner/repo/66",
      "headRefName": "feature-ideas",
      "baseRefName": "main",
      "isDraft": false,
      "versions": [
        {
          "headSha": "5427b9e...",
          "baseSha": "04b7b00...",
          "baseName": "main",
          "createdAt": "2025-10-11T12:52:29.240Z",
          "authorGithubHandle": "schrockn",
          "isGraphiteGenerated": true
        }
      ]
    }
  ],
  "mergeabilityStatuses": [
    {
      "prNumber": 66,
      "mergeabilityStatus": "READY_TO_MERGE"
    }
  ]
}
```

**Key Fields**:

- `prNumber`: GitHub PR number
- `state`: OPEN, MERGED, CLOSED
- `reviewDecision`: REVIEW_REQUIRED, APPROVED, etc.
- `headRefName`: Branch name for this PR
- `baseRefName`: Target branch (usually trunk or parent)
- `versions`: History of PR submissions
- `mergeabilityStatus`: READY_TO_MERGE, MERGED, etc.

**Usage**: gt caches PR info to display status without constant GitHub API calls.

### `.git/.graphite_cache_persist`

**Purpose**: The core metadata file containing branch relationships

```json
{
  "sha": "ccb6703cb1e4518437d3eec2b15714453bf34633",
  "branches": [
    [
      "main",
      {
        "validationResult": "TRUNK",
        "branchRevision": "04b7b00...",
        "children": ["feature-ideas", "status-command-implementation"]
      }
    ],
    [
      "feature-ideas",
      {
        "children": [],
        "parentBranchName": "main",
        "branchRevision": "5427b9e...",
        "parentBranchRevision": "04b7b00...",
        "lastSubmittedVersion": {
          "headSha": "5427b9e...",
          "baseSha": "04b7b00...",
          "baseName": "main"
        },
        "validationResult": "VALID"
      }
    ]
  ]
}
```

**Structure**:

- `sha`: Cache version identifier
- `branches`: Array of `[branchName, metadata]` tuples

**Branch Metadata Fields**:

| Field                  | Description                 | Example                             |
| ---------------------- | --------------------------- | ----------------------------------- |
| `validationResult`     | Branch status               | "VALID", "TRUNK", "BAD_PARENT_NAME" |
| `branchRevision`       | Current commit SHA          | "5427b9e..."                        |
| `parentBranchName`     | Parent branch               | "main"                              |
| `parentBranchRevision` | Parent's commit SHA         | "04b7b00..."                        |
| `children`             | Array of child branch names | ["feat-2", "feat-3"]                |
| `lastSubmittedVersion` | Last PR submission info     | {headSha, baseSha, baseName}        |

**Key Insight**: This file is a **directed acyclic graph (DAG)** of branch relationships. Each branch knows its parent and children, allowing gt to traverse the stack in any direction.

### File Locations

All metadata is stored in the **common git directory**:

```bash
# Get common git directory (works in worktrees too)
git rev-parse --git-common-dir

# Typical locations:
# Main repo:     /path/to/repo/.git/
# Worktree:      /path/to/repo/.git/  (same!)
```

**Important**: Because metadata is in the shared `.git` directory, **all worktrees see the same gt metadata**. This is how erk can read stack information from any worktree.

---

## Command Reference

### Setup Commands

#### `gt auth`

Authenticate with Graphite for PR management.

```bash
# Get token from https://app.graphite.com/settings/cli
gt auth --token <your-token>
```

#### `gt init`

Initialize Graphite in a repository by selecting trunk branch.

```bash
gt init                  # Interactive: select trunk
gt init                  # Change trunk branch later
```

**What it does**:

- Creates `.git/.graphite_repo_config`
- Sets trunk branch
- Initializes cache files

### Core Workflow Commands

#### `gt create [name]`

Create a new branch stacked on top of the current branch and commit staged changes.

```bash
gt create my-feature              # Create branch + commit staged changes
gt create my-feature -m "Message" # With commit message
gt create my-feature --all        # Stage all changes first
gt create --insert                # Insert between current and child
```

**Behavior**:

- Creates new branch off current branch
- Sets current branch as parent
- Commits staged changes (or prompts to stage)
- Optionally generates branch name from commit message
- Updates `.graphite_cache_persist`

**Options**:

- `-m, --message`: Commit message
- `-a, --all`: Stage all changes including untracked
- `-u, --update`: Stage updates to tracked files
- `-i, --insert`: Insert between current and its child
- `--ai`: AI-generate branch name and commit message

#### `gt modify`

Modify the current branch by amending its commit or creating a new commit. Automatically restacks descendants.

```bash
gt modify                         # Amend current commit
gt modify --commit                # Create new commit instead
gt modify -m "Updated message"    # Amend with new message
gt modify --edit                  # Open editor for message
```

**Behavior**:

- Amends HEAD commit (or creates new commit with `--commit`)
- Automatically restacks all upstack branches
- Prompts to stage unstaged changes

**Important**: This is safer than `git commit --amend` because it handles restacking for you.

**Options**:

- `-c, --commit`: Create new commit instead of amending
- `-m, --message`: Commit message
- `-a, --all`: Stage all changes
- `-e, --edit`: Open editor
- `--interactive-rebase`: Start interactive rebase

#### `gt submit`

Push branches to GitHub and create/update pull requests.

```bash
gt submit                         # Submit current branch + downstack
gt submit --stack                 # Submit entire stack (up + down)
gt submit --draft                 # Create as draft PRs
gt submit --publish               # Publish draft PRs
gt submit --dry-run               # Preview without submitting
```

**Behavior**:

1. Validates stack is properly restacked
2. Force-pushes branches to GitHub (with safety checks)
3. Creates PRs for new branches
4. Updates existing PRs with new commits
5. Opens interactive prompt for PR metadata

**PR Relationships**:

- Each branch gets its own PR
- PR base is set to parent branch (not trunk!)
- GitHub shows diffs relative to parent
- When parent merges, base auto-updates to new parent

**Options**:

- `-s, --stack`: Include upstack branches
- `-d, --draft`: Create as drafts
- `-n, --no-edit`: Don't prompt for PR metadata
- `--dry-run`: Preview only
- `-c, --confirm`: Ask before pushing
- `-u, --update-only`: Only update existing PRs
- `--reviewers`: Set reviewers

**Alias**: `gt ss` = `gt submit --stack`

#### `gt sync`

Sync all branches from remote and prompt to delete merged branches.

```bash
gt sync                           # Interactive sync
gt sync -f                        # Force sync, no prompts
```

**Behavior**:

1. Fetches latest trunk from remote
2. Rebases all open stacks on latest trunk
3. Identifies merged/closed branches from GitHub
4. Prompts to delete stale branches
5. Updates `.graphite_pr_info` cache

**Important**: This is the primary "cleanup" command. Run after PRs merge.

### Stack Navigation

#### `gt up [steps]`

Move up the stack (toward the tip, away from trunk).

```bash
gt up                             # Move to child branch
gt up 2                           # Move up 2 branches
```

**Behavior**:

- Checks out the child branch
- If multiple children, prompts to select
- Errors if at top of stack

#### `gt down [steps]`

Move down the stack (toward trunk).

```bash
gt down                           # Move to parent branch
gt down 2                         # Move down 2 branches
```

**Behavior**:

- Checks out parent branch
- Errors if at trunk (no parent)

#### `gt top`

Move to the tip of the stack (furthest from trunk).

```bash
gt top                            # Jump to stack tip
```

**Behavior**:

- Finds the leaf node in the stack
- If multiple tips, prompts to select

#### `gt bottom`

Move to the bottom of the stack (closest to trunk).

```bash
gt bottom                         # Jump to stack bottom
```

**Behavior**:

- Traverses down to branch closest to trunk
- Useful for starting at the beginning of a stack

#### `gt checkout [branch]`

Interactive branch checkout.

```bash
gt checkout                       # Interactive selector
gt checkout feature-name          # Direct checkout
```

**Behavior**:

- If no branch specified, opens interactive fuzzy finder
- Works with both tracked and untracked branches

### Branch Info Commands

#### `gt log [command]`

Visualize your stacks.

```bash
gt log                            # Full visualization
gt log short                      # Compact view
gt log long                       # Detailed view
```

**Example output**:

```
◯ 01-metadata-headers
│
│  ◯ feature-ideas
│  │ 8 hours ago
│  │ PR #66 (Ready to merge) Feature ideas
│  │ https://app.graphite.com/github/pr/schrockn/erk/66
│  │
│  │  ◯ status-command-implementation
│  │  │ 8 minutes ago
│  │  │ PR #67 (Merged) Implement status feature
│  │  │
├──┴──┘
◉ main (current)
│ 10 hours ago
```

**Legend**:

- `◉` Current branch
- `◯` Other branches
- Indentation shows parent-child relationships
- Shows PR status, age, and URLs

#### `gt branch info` / `gt info [branch]`

Display information about a branch. **This is the recommended way to get parent branch information programmatically.**

```bash
gt branch info                    # Current branch
gt info                           # Alias for current branch
gt info feature-name              # Specific branch
```

**Output format**:

```
Branch: feature-branch
Parent: main
Children: feature-child-1, feature-child-2
Commit: abc1234567890abcdef1234567890abcdef12
PR: #123 (https://app.graphite.com/github/pr/owner/repo/123)
```

**Key insight**: The "Parent:" line provides explicit, machine-readable parent branch information without requiring tree visualization parsing or heuristics. This is the most reliable way to determine a branch's parent.

**Parsing parent branch**:

```bash
# Get parent branch name
parent=$(gt branch info | grep "Parent:" | awk '{print $2}')

# Use for diff operations
git diff "$parent...HEAD"
```

**Why this approach is superior**:

- Direct output from Graphite's metadata
- No ambiguity or tree-parsing heuristics needed
- Clear error handling when parent cannot be determined
- More maintainable than parsing `gt log short` visualization

#### `gt parent`

Show the parent of the current branch (shorthand).

```bash
gt parent                         # Show parent branch name only
```

**Note**: `gt parent` provides just the name, while `gt branch info` provides full context. Use `gt branch info` when you need reliable parent information for automation.

#### `gt children`

Show children of the current branch.

```bash
gt children                       # List child branches
```

### Stack Management Commands

#### `gt restack`

Ensure each branch in the stack has its parent in its git history.

```bash
gt restack                        # Restack current stack
gt restack --no-interactive       # Auto-resolve if possible
```

**When to use**:

- After making changes to a parent branch
- After resolving merge conflicts
- When gt warns "needs restacking"

**Behavior**:

- Rebases each branch onto its parent
- Prompts for conflict resolution if needed
- Updates `.graphite_cache_persist`

**Important**: `gt modify` and `gt sync` do this automatically!

#### `gt move`

Rebase current branch onto a different parent.

```bash
gt move                           # Interactive: select new parent
gt move target-branch             # Move onto target-branch
```

**Behavior**:

- Rebases current branch onto new parent
- Updates parent relationship in metadata
- Restacks all upstack branches

**Use case**: Reorganizing your stack structure.

#### `gt fold`

Fold a branch's changes into its parent and restack dependencies.

```bash
gt fold                           # Fold current branch into parent
```

**Behavior**:

1. Squashes branch commits into parent
2. Deletes the branch
3. Updates children to point to parent
4. Restacks all upstack branches

**Use case**: Combining related commits after review feedback.

#### `gt split`

Split the current branch into multiple single-commit branches.

```bash
gt split                          # Interactive: split commits
```

**Behavior**:

- Each commit becomes its own branch
- Creates a linear stack of branches
- Useful for breaking up large changes

### Branch Management Commands

#### `gt track [branch]`

Start tracking a branch with Graphite by selecting its parent.

```bash
gt track                          # Track current branch
gt track feature-name             # Track specific branch
gt track -p main                  # Set parent explicitly
```

**When to use**:

- After creating branch with regular `git checkout -b`
- To add existing branches to gt management

**Behavior**:

- Prompts to select parent branch
- Adds branch to `.graphite_cache_persist`
- Branch now appears in `gt log`

#### `gt untrack [branch]`

Stop tracking a branch with Graphite.

```bash
gt untrack                        # Untrack current branch
gt untrack feature-name           # Untrack specific branch
```

**Behavior**:

- Removes from `.graphite_cache_persist`
- Branch remains in git
- Children unaffected (re-parented to trunk if needed)

#### `gt delete [name]`

Delete a branch and its Graphite metadata.

```bash
gt delete feature-name            # Delete branch
gt delete feature-name --force    # Skip confirmation
```

**Behavior**:

1. Checks if branch is merged/closed
2. Prompts for confirmation if not
3. Deletes branch locally
4. Removes from metadata
5. Re-parents children to deleted branch's parent

**Important**: Does not delete remote branch or close PR.

#### `gt rename [name]`

Rename a branch and update metadata referencing it.

```bash
gt rename new-name                # Rename current branch
gt rename old-name new-name       # Rename specific branch
```

**Behavior**:

- Renames branch in git
- Updates all parent/child references
- Updates PR metadata (if exists)

### Interactive Commands

#### `gt continue`

Continue after resolving rebase conflicts.

```bash
gt continue                       # After fixing conflicts
```

**When to use**:

- After resolving conflicts during `gt restack`
- After conflicts during `gt modify`

#### `gt abort`

Abort the current Graphite command halted by conflicts.

```bash
gt abort                          # Cancel operation
```

---

## Workflow Patterns

### Pattern 1: Creating a New Stack

**Goal**: Build a feature in multiple reviewable chunks.

```bash
# 1. Start from trunk
gt checkout main
git pull

# 2. Create first branch
gt create phase-1 -m "Add API endpoints"
# ... make changes ...
git add .
gt modify -m "Add API endpoints"

# 3. Create second branch on top
gt create phase-2 -m "Update frontend"
# ... make changes ...
git add .
gt modify -m "Update frontend"

# 4. Create third branch
gt create phase-3 -m "Add documentation"
# ... make changes ...
git add .
gt modify -m "Add documentation"

# 5. Submit entire stack
gt submit --stack

# Result: 3 PRs created
# PR #101: phase-1 (base: main)
# PR #102: phase-2 (base: phase-1)
# PR #103: phase-3 (base: phase-2)
```

### Pattern 2: Responding to Review Feedback

**Goal**: Update a branch in the middle of a stack.

```bash
# You're on phase-3, reviewer requests changes to phase-1

# 1. Navigate down to phase-1
gt down                           # → phase-2
gt down                           # → phase-1

# 2. Make changes
# ... edit files ...
git add .

# 3. Modify the branch (auto-restacks upstack)
gt modify -m "Address review feedback"

# Behind the scenes:
# - phase-1 commit amended
# - phase-2 rebased onto new phase-1
# - phase-3 rebased onto new phase-2

# 4. Resubmit stack
gt submit --stack

# Result: All 3 PRs updated with new commits
```

### Pattern 3: Adding to Existing Stack

**Goal**: Insert a new branch in the middle of a stack.

```bash
# Current stack: main → phase-1 → phase-2 → phase-3
# Want to insert: main → phase-1 → phase-1.5 → phase-2 → phase-3

# 1. Checkout the parent
gt checkout phase-1

# 2. Create new branch with --insert flag
gt create phase-1.5 --insert -m "Add validation"

# 3. Select which child to move
# Interactive prompt: "Select child to move onto phase-1.5"
# Choose: phase-2

# Result: main → phase-1 → phase-1.5 → phase-2 → phase-3
#         (phase-2 and phase-3 automatically restacked)

# 4. Submit new PR
gt submit
```

### Pattern 4: Working Across Stack

**Goal**: Make changes to multiple branches in one session.

```bash
# View your stack
gt log

# Work on bottom branch
gt bottom
# ... make changes ...
gt modify

# Jump to top
gt top
# ... make changes ...
gt modify

# Go back to middle
gt down 2
# ... make changes ...
gt modify

# Submit everything
gt submit --stack
```

### Pattern 5: Syncing After Merges

**Goal**: Clean up after PRs merge on GitHub.

```bash
# After phase-1 PR merges on GitHub

# 1. Run sync
gt sync

# Output:
# "Fetching latest from origin..."
# "Rebasing stacks on latest main..."
# "Found merged branches: phase-1"
# "Delete phase-1? [y/n]"

# 2. Confirm deletion
y

# Result:
# - phase-1 deleted locally
# - phase-2 rebased onto main (becomes bottom of stack)
# - phase-3 rebased onto phase-2
# - phase-2 PR base updated to main on GitHub
```

### Pattern 6: Splitting Large Changes

**Goal**: Break up a large commit into reviewable pieces.

```bash
# You made a large commit with multiple concerns

# 1. Checkout branch
gt checkout large-feature

# 2. Split into single-commit branches
gt split

# Interactive:
# "Split large-feature into branches? [y/n]"
# Creates: large-feature-1, large-feature-2, large-feature-3

# 3. Rename branches meaningfully
gt rename add-api-endpoints
gt up
gt rename add-frontend
gt up
gt rename add-tests

# 4. Submit
gt submit --stack

# Result: 3 PRs instead of 1 large one
```

### Pattern 7: Folding Branches

**Goal**: Combine approved branches before merging.

```bash
# phase-1 and phase-2 both approved, combine them

# 1. Checkout the child
gt checkout phase-2

# 2. Fold into parent
gt fold

# Behind the scenes:
# - phase-2 commits squashed into phase-1
# - phase-2 branch deleted
# - phase-3 re-parented to phase-1

# 3. Update PRs
gt submit --stack

# Result:
# - PR #101 (phase-1) now includes phase-2 changes
# - PR #102 (phase-2) closed
# - PR #103 (phase-3) base updated to phase-1
```

---

## Erk Integration

### How Erk Uses gt

Erk integrates with Graphite to enhance the worktree workflow:

#### 1. Stack Visualization

**File**: `src/erk/cli/graphite.py`

```python
def get_branch_stack(ctx: ErkContext, repo_root: Path, branch: str) -> list[str] | None:
    """Get the linear stack for a branch by reading .graphite_cache_persist."""
```

**What it does**:

- Reads `.git/.graphite_cache_persist`
- Builds parent-child graph
- Traverses to find linear chain
- Returns: `["main", "feature-1", "feature-2", "feature-3"]`

**Used by**:

- `erk list --stacks`: Shows stack relationships

#### 2. PR Information Cache

**File**: `src/erk/core/graphite_ops.py`

```python
def get_prs_from_graphite(git_ops: GitOps, repo_root: Path) -> dict[str, PullRequestInfo]:
    """Read .graphite_pr_info for PR data."""
```

**What it does**:

- Reads `.git/.graphite_pr_info`
- Extracts PR state, number, URLs
- Returns same format as GitHubOps for compatibility

**Used by**:

- `erk list --stacks`: Shows PR status
- `erk sync`: Identifies merged PRs

#### 3. Sync Integration

**File**: `src/erk/core/graphite_ops.py`

```python
def sync(repo_root: Path, *, force: bool) -> None:
    """Run gt sync to synchronize with remote."""
    subprocess.run(["gt", "sync", "-f" if force else ""], cwd=repo_root)
```

**What it does**:

- Executes `gt sync` subprocess
- Passes through stdout/stderr
- Used by `erk sync` command

#### 4. Branch Tracking

**Erk assumes**:

- All branches are tracked by gt
- `.graphite_cache_persist` exists
- Metadata is up-to-date

**Graceful degradation**:

- If gt not installed: `use_graphite = false`
- If cache missing: Returns None from functions
- Commands work without gt, just no stack info

### Configuration

**Global config** (`~/.erk/config.toml`):

```toml
use_graphite = true     # Auto-detected if gt CLI installed
```

**When enabled**:

- `erk list --stacks` shows stack relationships
- `erk sync` runs `gt sync`

**When disabled**:

- Regular git operations only
- No stack visualization
- Still fully functional

---

## Practical Examples

### Example 1: Building a Feature Stack

**Scenario**: You're adding a new user authentication system. You want to split it into reviewable chunks.

```bash
# Start from main
git checkout main
gt sync  # Ensure up-to-date

# Phase 1: Add user model
gt create auth-user-model
# ... implement User model ...
git add .
gt modify -m "Add User model with email/password fields"

# Phase 2: Add authentication service
gt create auth-service
# ... implement AuthService ...
git add .
gt modify -m "Add AuthService for login/logout"

# Phase 3: Add API endpoints
gt create auth-api-endpoints
# ... implement REST endpoints ...
git add .
gt modify -m "Add /login and /logout endpoints"

# Phase 4: Add frontend components
gt create auth-frontend
# ... implement login form ...
git add .
gt modify -m "Add Login and Register components"

# View the stack
gt log short
# Output:
# ◯ auth-frontend
# │  ◯ auth-api-endpoints
# │  │  ◯ auth-service
# │  │  │  ◯ auth-user-model
# ◉─┴──┴──┘ main (current)

# Submit all PRs
gt submit --stack

# Result: 4 PRs created, each reviewable independently
```

### Example 2: Responding to Feedback Mid-Stack

**Scenario**: Reviewer asks for changes to auth-service (middle of stack).

```bash
# You're on auth-frontend, need to update auth-service

# Navigate down
gt down     # → auth-api-endpoints
gt down     # → auth-service

# Make requested changes
# ... edit AuthService ...
git add .
gt modify -m "Add password validation as requested"

# gt automatically:
# 1. Amends auth-service commit
# 2. Rebases auth-api-endpoints on new auth-service
# 3. Rebases auth-frontend on new auth-api-endpoints

# Resubmit affected PRs
gt submit --stack

# Navigate back to where you were
gt top  # → auth-frontend
```

### Example 3: Inserting a Missed Step

**Scenario**: After creating the stack, you realize auth-service needs tests.

```bash
# Current: main → auth-user-model → auth-service → auth-api-endpoints → auth-frontend
# Want:    main → auth-user-model → auth-service → auth-service-tests → auth-api-endpoints → auth-frontend

# Go to auth-service
gt checkout auth-service

# Create tests branch with --insert
gt create auth-service-tests --insert
# Prompt: "Select child to move onto auth-service-tests"
# Select: auth-api-endpoints

# Add tests
# ... write tests ...
git add .
gt modify -m "Add comprehensive tests for AuthService"

# Submit new PR
gt submit

# View updated stack
gt log short
# Output:
# ◯ auth-frontend
# │  ◯ auth-api-endpoints
# │  │  ◯ auth-service-tests  ← NEW
# │  │  │  ◯ auth-service
# │  │  │  │  ◯ auth-user-model
# ◉─┴──┴──┴──┘ main
```

### Example 4: Handling Merge Conflicts

**Scenario**: Main branch updated while you were working, causing conflicts.

```bash
# Run sync to get latest
gt sync

# Output:
# "Fetching origin..."
# "Rebasing auth-user-model on main... CONFLICT"
# "Resolve conflicts and run: gt continue"

# View conflicts
git status

# Resolve conflicts
# ... edit files ...
git add .

# Continue restack
gt continue

# gt automatically:
# 1. Finishes rebasing auth-user-model
# 2. Rebases auth-service on new auth-user-model
# 3. Rebases auth-service-tests on new auth-service
# 4. Rebases auth-api-endpoints on new auth-service-tests
# 5. Rebases auth-frontend on new auth-api-endpoints

# Update all PRs
gt submit --stack
```

### Example 5: Cleaning Up After Merges

**Scenario**: auth-user-model and auth-service PRs merged on GitHub.

```bash
# Run sync
gt sync

# Output:
# "Fetching origin..."
# "Rebasing stacks..."
#
# "Merged branches detected:"
# "  - auth-user-model (PR #123 merged)"
# "  - auth-service (PR #124 merged)"
#
# "Delete these branches? [y/n]"

# Confirm
y

# Behind the scenes:
# 1. Deletes auth-user-model and auth-service locally
# 2. Rebases auth-service-tests onto main
# 3. Rebases auth-api-endpoints onto auth-service-tests
# 4. Rebases auth-frontend onto auth-api-endpoints
# 5. Updates PR #125 base from auth-service to main
# 6. Updates PR #126 base from auth-user-model to main

# View updated stack
gt log short
# Output:
# ◯ auth-frontend
# │  ◯ auth-api-endpoints
# │  │  ◯ auth-service-tests
# ◉─┴──┴──┘ main

# Stack is now shorter, bottom branches merged!
```

### Example 6: Using gt with Erk Worktrees

**Scenario**: Managing multiple stacks in different worktrees.

```bash
# In main worktree: Create auth stack
gt create auth-user-model
# ... work ...
gt create auth-service
# ... work ...

# Want to work on unrelated feature in parallel
# Create new worktree
erk create billing-stack

# Navigate to new worktree
erk checkout billing-stack

# In billing worktree: Create billing stack
gt create billing-model
# ... work ...
gt create billing-service
# ... work ...

# View all stacks from any worktree
gt log
# Output shows BOTH stacks:
# ◯ billing-service
# │  ◯ billing-model
# │
# ◯ auth-service
# │  ◯ auth-user-model
# ◉─┴──┘ main

# Metadata is shared via .git directory!

# List worktrees with stack info
erk list --stacks
# Output:
# root [main]
# auth-stack [auth-service]
#   ◯ main
#   ◯ auth-user-model
#   ◉ auth-service ← YOU ARE HERE
#
# billing-stack [billing-service]
#   ◯ main
#   ◯ billing-model
#   ◉ billing-service
```

---

## Key Insights for AI Agents

### Mental Model Summary

1. **Think linearly**: Stacks are linear chains, not trees
2. **Parents matter**: Every branch (except trunk) has exactly one parent
3. **Auto-restacking**: Changes propagate upstack automatically
4. **Shared metadata**: All worktrees see the same gt metadata
5. **PR mapping**: Each branch = one PR, base = parent branch

### Parent Branch Resolution (Critical Pattern)

**Best practice**: Use `gt branch info` to get parent branch information programmatically.

```bash
# Parse parent from gt branch info
parent=$(gt branch info | grep "Parent:" | awk '{print $2}')

# Use for diffs
git diff "$parent...HEAD"
```

**Why this is superior to alternatives**:

1. **Direct metadata access**: Reads from `.graphite_cache_persist` explicitly
2. **No heuristics**: Tree parsing (`gt log short`) requires interpreting visual structure
3. **No ambiguity**: "Parent:" line is always present for tracked branches
4. **Clear errors**: Missing line means branch not tracked or no parent (trunk)
5. **Maintainable**: Less brittle than parsing tree visualization

**Avoid these patterns**:

- ❌ Parsing `gt log short` tree visualization
- ❌ Using `git merge-base` when Graphite is available
- ❌ Guessing or inferring parent branches

**When to fall back to git commands**:

- Branch not tracked by Graphite (`gt track` first)
- Graphite not installed or initialized
- Need merge-base for non-stack operations

### When to Use gt Commands

| Situation           | Command                 | Why                          |
| ------------------- | ----------------------- | ---------------------------- |
| Start new work      | `gt create`             | Creates branch + sets parent |
| Edit current branch | `gt modify`             | Auto-restacks children       |
| Navigate stack      | `gt up/down/top/bottom` | Move through linear chain    |
| View structure      | `gt log`                | See stack visualization      |
| Submit PRs          | `gt submit --stack`     | Create/update all PRs        |
| After merges        | `gt sync`               | Clean up + rebase            |
| Reorganize          | `gt move`               | Change parent relationships  |
| Combine work        | `gt fold`               | Merge branch into parent     |
| Split work          | `gt split`              | Break commits into branches  |

### Common Mistakes to Avoid

1. **Don't use `git rebase` directly**: Use `gt modify` or `gt restack` instead
   - Reason: gt needs to update metadata during rebasing

2. **Don't delete branches with `git branch -d`**: Use `gt delete`
   - Reason: Metadata needs to be updated to re-parent children

3. **Don't assume `gt submit` only affects current branch**
   - Reality: Submits downstack too (all ancestors)
   - Use `gt submit --stack` to include upstack

4. **Don't forget to `gt sync` after merges**
   - Reason: Stale branches accumulate, metadata gets outdated

5. **Don't track too many branches**
   - Reason: Large stacks are harder to manage and review
   - Best practice: 3-5 branches per stack

### Reading Metadata Programmatically

If you're implementing tools that read gt metadata:

```python
import json
from pathlib import Path

def load_graphite_metadata(git_dir: Path) -> dict:
    """Load gt metadata from .git directory."""
    cache_file = git_dir / ".graphite_cache_persist"
    if not cache_file.exists():
        return {}

    data = json.loads(cache_file.read_text(encoding="utf-8"))

    # Convert branches array to dict for easier access
    branches = {}
    for branch_name, metadata in data.get("branches", []):
        branches[branch_name] = metadata

    return branches

def get_stack_for_branch(branches: dict, branch: str) -> list[str]:
    """Get linear stack for a branch."""
    if branch not in branches:
        return []

    # Traverse down to trunk
    ancestors = []
    current = branch
    while current in branches:
        ancestors.append(current)
        parent = branches[current].get("parentBranchName")
        if parent is None:
            break
        current = parent

    ancestors.reverse()  # [trunk, ..., parent, current]

    # Traverse up to tip (follow first child only)
    descendants = []
    current = branch
    while True:
        children = branches[current].get("children", [])
        if not children:
            break
        first_child = children[0]
        if first_child not in branches:
            break
        descendants.append(first_child)
        current = first_child

    return ancestors + descendants
```

---

## Additional Resources

- **Official Docs**: https://graphite.com/docs
- **Cheatsheet**: https://graphite.com/docs/cheatsheet
- **Tutorial Videos**: https://www.youtube.com/@withgraphite
- **Community Slack**: https://community.graphite.com

---

## Glossary Quick Reference

```
Stack:      Linear chain of dependent branches
Trunk:      Main branch (main/master)
Parent:     Branch this one is based on
Children:   Branches based on this one
Downstack:  Toward trunk (ancestors)
Upstack:    Away from trunk (descendants)
Restack:    Rebase to include parent changes
Track:      Register branch with gt
Submit:     Push + create/update PRs
Sync:       Update from remote + cleanup
```

---

**End of GT Mental Model Guide**

This document should provide a complete mental model for understanding and working with Graphite. When in doubt, remember: **gt manages stacks (linear chains of dependent branches), automatically handling the complexity of keeping them in sync**.
