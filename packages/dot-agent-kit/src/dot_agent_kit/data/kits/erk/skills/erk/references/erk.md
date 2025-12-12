---
description: "Worktree management and parallel development"
url: "https://github.com/dagster-io/erk"
---

# Erk Mental Model

**Last Updated**: 2025-10-13

A comprehensive guide to understanding erk's mental model, command structure, and workflow patterns for managing git worktrees.

---

## Table of Contents

- [What is Erk?](#what-is-erk)
- [Core Mental Model](#core-mental-model)
- [Terminology](#terminology)
- [Configuration](#configuration)
- [Command Reference](#command-reference)
- [Workflow Patterns](#workflow-patterns)
- [Integration Points](#integration-points)
- [Practical Examples](#practical-examples)
- [Key Insights for AI Agents](#key-insights-for-ai-agents)
- [Additional Resources](#additional-resources)

---

## What is Erk?

Erk is a CLI tool that manages git worktrees in a centralized location with automatic environment setup and integration with modern development tools.

### The Problem It Solves

Without erk, parallel feature development requires:

1. Constant branch switching in a single directory
2. Manual environment reconfiguration per branch
3. Lost context when switching between features
4. Risk of accidental commits to wrong branch
5. Slow context switching (IDE reindexing, etc.)

With erk, you can:

- Work on multiple features simultaneously without branch switching
- Each feature has its own isolated directory with configured environment
- Instant switching between features
- Track PR status alongside worktrees
- Integrate with Graphite for stacked diffs

### Core Philosophy

**Separate workspaces for separate work.** Each feature branch gets its own directory (worktree) with proper environment configuration, eliminating the cognitive overhead of branch switching.

---

## Core Mental Model

### The Four-Layer Directory Structure

Erk organizes worktrees in a predictable hierarchy:

```
~/.erk/
└── config.toml                          ← Global config

~/erks/                             ← Erks root (configurable)
├── erk/                           ← Work dir (per repo)
│   ├── config.toml                      ← Repo-specific config
│   ├── feature-a/                       ← Individual erk
│   │   ├── .env                         ← Auto-generated env vars
│   │   ├── .plan/                       ← Optional plan folder (gitignored)
│   │   │   ├── plan.md                  ← Immutable implementation plan
│   │   │   └── progress.md              ← Mutable progress tracking
│   │   └── ... (source code)
│   └── feature-b/                       ← Another erk
└── other-repo/                          ← Work dir for another repo
    └── ...

/Users/you/projects/erk/           ← Repo root (original clone)
└── .git/                                ← Git metadata (shared by all worktrees)
```

**Key Insight**: The repo root stays clean for planning and reference, while all active development happens in isolated erks.

### The Resource Model

Erk operates on these core resources:

```
Repository Root
├── Repo Context
│   ├── root: Path to original .git directory
│   ├── repo_name: Repository name
│   └── work_dir: Directory containing all erks for this repo
└── Erks (in work_dir)
    ├── Worktree 1 (name → branch)
    ├── Worktree 2 (name → branch)
    └── ...
```

**Naming Convention**: Worktrees are identified by _name_ (directory), not branch:

```bash
# Create worktree named "auth" with branch "feature/user-auth"
erk create auth --branch feature/user-auth

# Navigate to the branch
erk checkout feature/user-auth
```

### Context Resolution

Erk is **location-aware**. It automatically detects:

1. **Repository**: Walks up from current directory to find `.git`
2. **Current worktree**: Determines which erk you're in (or root)
3. **Work directory**: Based on repo name and global config
4. **Configuration**: Combines global + repo-specific settings

This means commands adapt based on where you run them:

```bash
# In repo root
erk status    # Shows: "Currently in root worktree"

# In a erk
cd ~/erks/erk/feature-a
erk status    # Shows: "feature-a [feature-a]"
```

---

## Terminology

### Core Concepts

| Term              | Definition                                            | Example                                                |
| ----------------- | ----------------------------------------------------- | ------------------------------------------------------ |
| **Worktree**      | Git's native feature for multiple working directories | Created by `git worktree add`                          |
| **Erk**           | A configured worktree with environment setup          | Created by `erk create`                                |
| **Repo Root**     | Original git repository directory containing `.git/`  | `/Users/you/projects/erk`                              |
| **Work Dir**      | Directory containing all erks for a specific repo     | `~/erks/erk/`                                          |
| **Erks Root**     | Top-level directory for all configured repos          | `~/erks/`                                              |
| **Worktree Path** | Absolute path to a specific erk                       | `~/erks/erk/my-feature/`                               |
| **Trunk Branch**  | Default branch of the repository (main/master)        | `main`                                                 |
| **Stack**         | Graphite concept: linear chain of dependent branches  | main → feature-1 → feature-1-part-2                    |
| **Plan Folder**   | Folder containing implementation plan and progress    | `.plan/` with `plan.md` and `progress.md` (gitignored) |
| **Root Worktree** | Special name for the original repo root directory     | Original clone at `/Users/you/projects/erk`            |

### Resource Identifiers

Worktrees are identified by **name** (not branch):

```bash
# Create worktree with custom name and branch
erk create auth --branch feature/user-authentication

# Operations use branch or worktree names
erk checkout feature/user-authentication
erk delete auth
erk rename auth user-auth
```

**Branch detection:**

```bash
# Worktree name = branch name by default
erk create my-feature           # Creates worktree "my-feature" with branch "my-feature"

# Explicit branch name
erk create feat --branch my-feature  # Worktree "feat", branch "my-feature"
```

### Configuration Hierarchy

Configuration flows from global to repo-specific:

```
~/.erk/config.toml (global)
  ↓ (defines erks_root, use_graphite, etc.)
~/erks/<repo>/config.toml (repo-specific)
  ↓ (defines env vars, post_create commands)
Individual worktrees inherit combined config
```

---

## Configuration

### Global Configuration

**Location**: `~/.erk/config.toml`

**Created by**: `erk init`

```toml
erks_root = "/Users/you/worktrees"
use_graphite = true              # Auto-detected if gt CLI installed
show_pr_info = true              # Display PR status (requires gh CLI)
shell_setup_complete = true      # Shell integration configured
```

### Repo Configuration

**Location**: `{erks_root}/{repo_name}/config.toml`

**Created by**: `erk init` (when run inside a repo)

```toml
[env]
# Template variables: {worktree_path}, {repo_root}, {name}
DATABASE_URL = "postgresql://localhost/{name}_db"
API_KEY = "${SECRET_API_KEY}"
WORKTREE_PATH = "{worktree_path}"  # Auto-provided
REPO_ROOT = "{repo_root}"          # Auto-provided

[[post_create]]
command = ["uv", "venv"]
working_dir = "."

[[post_create]]
command = ["uv", "pip", "install", "-e", "."]
working_dir = "."
```

### Environment Variables

Automatically exported when switching worktrees:

- `WORKTREE_PATH` - Absolute path to current worktree
- `REPO_ROOT` - Absolute path to repository root
- `WORKTREE_NAME` - Name of current worktree

Plus any variables defined in `[env]` section.

### Configuration Presets

Use presets for common project types:

```bash
# List available presets
erk init --list-presets

# Use a preset
erk init --preset dagster

# Common presets:
# - auto: Auto-detect project type
# - generic: Minimal setup
# - dagster: Dagster-specific setup
```

**Dagster preset example:**

```toml
[env]
DAGSTER_GIT_REPO_DIR = "{worktree_path}"

[[post_create]]
command = ["uv", "venv"]
[[post_create]]
command = ["uv", "run", "make", "dev_install"]
```

---

## Command Reference

### Initialization & Configuration

#### `erk init`

Initialize erk for a repository.

```bash
# Full setup (global + repo + shell integration)
erk init

# Repo config only
erk init --repo

# Shell integration only
erk init --shell

# With preset
erk init --preset dagster

# List available presets
erk init --list-presets

# Force overwrite existing config
erk init --force
```

**What it does:**

1. Creates `~/.erk/config.toml` (if not exists)
2. Creates `{work_dir}/config.toml` (repo-specific)
3. Sets up shell integration (optional)
4. Adds `.plan/` to `.gitignore`

#### `erk config`

Manage configuration.

```bash
# List all configuration
erk config list

# Get specific value
erk config get erks_root
erk config get use_graphite

# Set value
erk config set erks_root /custom/path
erk config set use_graphite false
erk config set show_pr_info true
```

#### `erk completion`

Generate shell completion scripts.

```bash
# Bash
erk completion bash > ~/.erk-completion.bash
source ~/.erk-completion.bash

# Zsh
erk completion zsh > ~/.erk-completion.zsh
source ~/.erk-completion.zsh

# Fish
erk completion fish > ~/.config/fish/completions/erk.fish
```

### Creating Worktrees

#### `erk create`

Create a new worktree.

```bash
# Basic creation (name = branch)
erk create my-feature

# Custom branch name
erk create feat --branch feature/my-feature

# From existing branch
erk create --from-branch existing-feature
erk create my-work --from-branch feature/existing

# Move current branch to new worktree
erk create --from-current-branch

# Create from plan file
erk create --from-plan implementation-plan.md
erk create auth --plan add-auth.md

# Skip post-create commands
erk create my-feature --no-post

# Custom base ref
erk create my-feature --ref develop
```

**Branch creation logic:**

- `create NAME`: Creates new branch `NAME` from current HEAD
- `create NAME --branch BRANCH`: Creates new branch `BRANCH`
- `create --from-branch BRANCH`: Uses existing branch `BRANCH`
- `create --from-current-branch`: Moves current branch to worktree

**Plan folder behavior:**

```bash
erk create --from-plan plan.md my-feature
# 1. Creates worktree ~/erks/repo/my-feature/
# 2. Creates .plan/ folder with:
#    - plan.md (immutable - original plan content)
#    - progress.md (mutable - checkboxes for tracking)
# 3. .plan/ is gitignored (not committed)
```

#### `erk checkout`

Navigate to a branch by finding which worktree contains it and checking it out.

```bash
# Navigate to a branch (finds the worktree containing it)
erk checkout feature/user-auth

# Auto-create worktree if branch not found locally
erk checkout my-feature --auto-create

# With script output for shell integration
erk checkout my-feature --script
```

**How it works:**

1. Searches all worktrees for the specified branch in their Graphite stack lineage
2. If exactly one worktree contains the branch, navigates to it and checks out the branch
3. If branch not found locally but exists on remote (with `--auto-create`), creates new worktree
4. If multiple worktrees contain the branch:
   - If exactly one has it directly checked out, uses that one
   - Otherwise, shows disambiguation error

**Requirements:**

- Graphite must be enabled (for stack lineage search)
- Branch must exist in at least one worktree's stack (or on remote with `--auto-create`)

**Use cases:**

- "I know the branch name, find me the right worktree"
- Quick navigation when you don't remember which worktree has a branch
- Navigating between features by branch name
- Creating worktrees on-demand from remote branches

### Listing & Viewing

#### `erk list` / `erk ls`

List all worktrees.

```bash
# Basic list
erk list
# Output:
# root [main]
# feature-a [feature-a]
# feature-b [feature/bug-fix]

# With Graphite stacks and PR info
erk list --stacks
# Output:
# root [main]
#   ◉  main
#
# feature-a [feature-a]
#   ◯  main
#   ◉  feature-a ✅ #123
#
# feature-b [feature/bug-fix]
#   ◯  main
#   ◉  feature/bug-fix 🚧 #456

# With detailed CI checks
erk list --checks
```

**PR Status Indicators:**

- ✅ All checks passing
- ❌ Some checks failing
- 🟣 Merged
- 🚧 Draft
- ⭕ Closed
- ◯ Open (no checks)

**Stack Indicators:**

- ◉ Current branch
- ◯ Parent branch
- ├─ Stack relationship

#### `erk status`

Show current worktree status.

```bash
erk status

# Output (in root):
# Currently in root worktree

# Output (in erk):
# feature-a [feature-a]
# PR: #123 ✅
```

### Stack Navigation (via Graphite)

For navigating through stacks of dependent branches, use Graphite's native commands:

#### `gt up` / `gt down`

Navigate through your stack using Graphite's built-in commands:

```bash
# Navigate to child branch in stack
gt up

# Navigate to parent branch in stack
gt down
```

**These commands:**

- Use Graphite's native stack traversal
- Automatically checkout the appropriate branch
- Work within the current worktree (no worktree switching)

**Example:**

```bash
# Current stack: main -> feature-1 -> feature-2 -> feature-3
# You are in: feature-2

gt up       # → Checks out feature-3
gt down     # → Checks out feature-2 again
gt down     # → Checks out feature-1
```

**Use case:** Moving through dependent features within a single worktree.

For navigating to branches in different worktrees, use `erk checkout <branch>` instead.

### Managing Worktrees

#### `erk move`

Move or swap branches between worktrees.

```bash
# Move current branch to target worktree
erk move target-wt

# Move from specific worktree to target
erk move --worktree source-wt target-wt

# Swap branches (current ↔ target)
erk move --current target-wt

# Auto-detect source from branch name
erk move --branch feature-x target-wt

# Force without confirmation
erk move source-wt target-wt --force
```

**Use cases:**

- Move branch to different worktree
- Swap branches between two worktrees
- Consolidate work from multiple worktrees

#### `erk rename`

Rename a worktree (move directory).

```bash
# Rename worktree
erk rename old-name new-name

# Dry run
erk rename old-name new-name --dry-run
```

**Note**: Renames the worktree directory, not the branch.

#### `erk delete` / `erk del`

Delete a worktree.

```bash
# Delete single worktree
erk delete my-feature

# Force deletion (skip confirmation)
erk delete my-feature --force

# Delete worktree and entire Graphite stack
erk delete my-feature --delete-stack

# Dry run
erk delete my-feature --dry-run
```

**Safety checks:**

- Prompts for confirmation (unless `--force`)
- Warns if branch has unpushed changes
- Offers to delete local branch
- With `--delete-stack`: Deletes all dependent branches in Graphite stack

### Cleanup & Maintenance

---

## Workflow Patterns

### Pattern 1: Basic Feature Development

**Standard workflow:**

```bash
# Create new feature
erk create user-auth
erk checkout user-auth

# Work on feature
# ... make changes, commit ...

# Navigate to another feature without losing context
erk create bug-fix
erk checkout bug-fix

# Navigate back instantly
erk checkout user-auth
```

### Pattern 2: Plan-Based Development

**Opinionated workflow separating planning from implementation:**

```bash
# 1. Plan in repo root
cd /path/to/repo/root
# Create plan file: Add_User_Auth.md

# 2. Create worktree from plan
erk create --from-plan Add_User_Auth.md
# Creates worktree "add-user-auth"
# Creates .plan/ folder with plan.md and progress.md

# 3. Navigate and implement
erk checkout add-user-auth
# Your plan is at .plan/plan.md for reference during implementation
# Progress tracked in .plan/progress.md

# 4. Commit only code (not plan)
git add .
git commit -m "Implement user authentication"
# .plan/ stays local (gitignored)
```

**Why this works:**

- Plans don't clutter PR reviews
- Each worktree has its own planning context
- Clean separation between thinking and doing
- No maintenance burden for planning artifacts

### Pattern 3: Working with Existing Branches

```bash
# Create worktree from existing branch
erk create --from-branch feature/existing-work

# Or with custom name
erk create my-work --from-branch feature/existing-work
```

### Pattern 4: Stacked Development with Graphite

```bash
# Create base feature
erk create feature-base

# Create dependent feature
erk checkout feature-base
gt create feature-base-part-2
erk create feature-base-part-2 --from-current-branch

# Navigate stack
erk list --stacks

erk checkout feature-base
gt up                  # Move to feature-base-part-2 (within same worktree)
gt down                # Back to feature-base
```

### Pattern 5: Parallel Development

```bash
# Start multiple features
erk create feature-a
erk create feature-b
erk create feature-c

# List all worktrees
erk ls

# Navigate between them instantly
erk checkout feature-a   # Work on A
erk checkout feature-b   # Navigate to B
erk checkout feature-a   # Back to A
```

### Pattern 6: Moving Work Between Worktrees

```bash
# Started work in wrong worktree
erk checkout wrong-branch

# Move current branch to correct worktree
erk move correct-worktree

# Or create new worktree from current branch
erk create --from-current-branch
```

### Pattern 7: Cleanup After Merging

```bash
# After merging several PRs on GitHub

# Manual cleanup
erk delete feature-a
erk delete feature-b
```

### Pattern 8: Environment-Specific Worktrees

```bash
# Configure repo with environment variables
cat > ~/erks/myrepo/config.toml << 'EOF'
[env]
DATABASE_URL = "postgresql://localhost/{name}_db"
API_PORT = "808{name}"
LOG_LEVEL = "debug"
EOF

# Each worktree gets unique environment
erk create feature-a   # DATABASE_URL=postgresql://localhost/feature-a_db
erk create feature-b   # DATABASE_URL=postgresql://localhost/feature-b_db
```

### Pattern 9: Custom Post-Create Setup

```bash
# Configure repo with post-create commands
cat > ~/erks/myrepo/config.toml << 'EOF'
[[post_create]]
command = ["npm", "install"]

[[post_create]]
command = ["npm", "run", "db:migrate"]
EOF

# Commands run automatically on worktree creation
erk create my-feature
# Automatically runs: npm install && npm run db:migrate
```

---

## Integration Points

### Git Integration

Erk uses git's native worktree feature:

```bash
# Erk commands map to git commands:
erk create feature     # → git worktree add -b feature path
erk delete feature     # → git worktree remove path
```

**Git operations erk uses:**

- `git worktree list --porcelain` - List all worktrees
- `git worktree add` - Create new worktree
- `git worktree remove` - Remove worktree
- `git worktree move` - Move worktree directory
- `git symbolic-ref refs/remotes/origin/HEAD` - Detect default branch
- `git rev-parse --git-common-dir` - Find repo root from worktree

### Graphite Integration

**For comprehensive Graphite documentation**: See `.agent/tools/gt.md`

When `use_graphite = true`, erk integrates with Graphite:

```bash
# Stack navigation
gt up                  # Navigate to child branch (within worktree)
gt down                # Navigate to parent branch (within worktree)
erk checkout <branch>  # Navigate to specific branch (across worktrees)

# Stack visualization
erk list --stacks      # Show stack structure
```

**Graphite commands used:**

- `gt parent` - Get parent branch
- `gt children` - Get child branches
- `gt branch info` - Get complete branch metadata
- `gt repo sync` - Sync with remote
- `gt ls` - List tracked branches

**Recommended practice**: For parent/child relationships and branch metadata, use native `gt` commands (`gt parent`, `gt children`, `gt branch info`). These commands are optimized for scripting contexts and provide machine-readable output that is easy to parse for automation and AI tools.

**Auto-detection**: Erk automatically detects if `gt` CLI is installed and enables Graphite features.

### GitHub Integration

Requires GitHub CLI (`gh`) installed and authenticated:

```bash
# PR status in listings
erk list --stacks
# Shows: ✅ #123, 🚧 #456, 🟣 #789
```

**GitHub commands used:**

- `gh pr list --state all --json number,headRefName,url,state,isDraft,statusCheckRollup` - Get PR info

**Graceful degradation**: If `gh` is not available, erk continues without PR info.

### Shell Integration

Shell integration enables directory navigation:

```bash
# Set up shell integration
erk init --shell

# Adds function to ~/.zshrc or ~/.bashrc:
# Enables 'erk checkout' to actually change directory
```

**What it provides:**

- `erk checkout` command that actually changes directory
- Environment activation on navigation
- Tab completion for branch names

**Without shell integration**: `erk checkout` only prints commands, doesn't execute them.

---

## Practical Examples

### Example 1: Daily Development Flow

```bash
# Morning: Check current worktrees
erk ls --stacks

# Work on feature A
erk checkout feature-a
# ... make changes, commit ...

# Navigate to urgent bug fix
cd /path/to/repo/root  # Navigate to root
erk create hotfix-urgent
erk checkout hotfix-urgent
# ... fix bug, commit, push ...

# Back to feature A
erk checkout feature-a

# Check status
erk status
```

### Example 2: Plan → Implement → PR

```bash
# 1. Plan in root
cd /path/to/repo/root
# Create plan: Add_Authentication.md

# 2. Create worktree from plan
erk create --from-plan Add_Authentication.md

# 3. Implement
erk checkout add-authentication
cat .plan/plan.md         # Reference plan
cat .plan/progress.md     # Check progress
# ... implement ...
git commit -m "Add authentication"

# 4. Create PR
git push -u origin add-authentication
gh pr create --fill

# 5. Check status
erk ls --stacks     # See PR #123 ✅
```

### Example 3: Stacked Features

```bash
# Base feature
erk create api-v2
erk checkout api-v2
# ... implement base API ...
git commit -m "Add API v2 base"

# Dependent feature
gt create api-v2-auth
erk create api-v2-auth --from-current-branch
erk checkout api-v2-auth
# ... implement auth on top of API v2 ...
git commit -m "Add authentication to API v2"

# Navigate stack
erk list --stacks

erk checkout api-v2    # Base
gt up                  # → api-v2-auth (within worktree)
```

### Example 4: Environment Isolation

```bash
# Configure repo for environment isolation
cat > ~/erks/myapp/config.toml << 'EOF'
[env]
DATABASE_URL = "postgresql://localhost/{name}_db"
REDIS_URL = "redis://localhost/{name}"
API_PORT = "300{name}"
EOF

# Each worktree gets unique environment
erk create user-service
erk checkout user-service
echo $DATABASE_URL  # postgresql://localhost/user-service_db
echo $API_PORT      # 300user-service (would need numeric hashing in real use)

erk create payment-service
erk checkout payment-service
echo $DATABASE_URL  # postgresql://localhost/payment-service_db
```

### Example 5: Cleanup Workflow

```bash
# After merging several PRs on GitHub

# Manual cleanup
erk delete feature-a
erk delete feature-b
```

### Example 6: Moving Work

```bash
# Started feature in wrong worktree
erk checkout old-feature
# ... did work ...
git status  # Uncommitted changes

# Oops, should be in different worktree
git add .
git commit -m "WIP"

# Move to correct worktree
erk move correct-feature
erk checkout correct-feature
# Branch is now here
```

### Example 7: Custom Setup

```bash
# Configure Python project
cat > ~/erks/myproject/config.toml << 'EOF'
[[post_create]]
command = ["uv", "venv"]

[[post_create]]
command = ["uv", "pip", "install", "-e", ".[dev]"]

[[post_create]]
command = ["pre-commit", "install"]

[env]
PYTHONPATH = "{worktree_path}/src"
ENV = "dev"
EOF

# New worktrees automatically set up
erk create new-feature
# Runs: uv venv && uv pip install -e .[dev] && pre-commit install
erk checkout new-feature
# Environment already configured
```

---

## Key Insights for AI Agents

### Architecture Understanding

**3-Layer Architecture:**

```
CLI Commands (commands/*.py)
    ↓ uses
Core Business Logic (core.py, config.py, tree.py)
    ↓ uses
Operations Layer (gitops.py, github_ops.py, graphite_ops.py)
```

**Key Principle**: Commands never directly execute subprocess or filesystem operations. All external I/O goes through injected operations interfaces.

### Dependency Injection Pattern

Erk uses ABC-based dependency injection:

```python
@dataclass(frozen=True)
class ErkContext:
    git_ops: GitOps                  # ABC interface
    github_ops: GitHubOps            # ABC interface
    graphite_ops: GraphiteOps        # ABC interface
    global_config_ops: GlobalConfigOps
    dry_run: bool

# Real implementations
ctx = ErkContext(
    git_ops=RealGitOps(),
    github_ops=RealGitHubOps(),
    # ...
)

# Test implementations
ctx = ErkContext(
    git_ops=FakeGitOps(worktrees=[...]),
    github_ops=FakeGitHubOps(prs=[...]),
    # ...
)
```

**For testing**: Use `FakeGitOps`, `FakeGitHubOps`, etc. from `tests/fakes/`.

### Key Design Patterns

1. **LBYL (Look Before You Leap)**: Check conditions before operations

   ```python
   # ✅ CORRECT
   if key in mapping:
       value = mapping[key]

   # ❌ WRONG
   try:
       value = mapping[key]
   except KeyError:
       pass
   ```

2. **Frozen Dataclasses**: All contexts and data structures are immutable

   ```python
   @dataclass(frozen=True)
   class RepoContext:
       root: Path
       repo_name: str
       work_dir: Path
   ```

3. **Pure Functions**: Core logic has no side effects

   ```python
   def discover_repo_context(ctx: ErkContext, start: Path) -> RepoContext:
       # Pure function - takes inputs, returns output
       # All side effects through ctx
   ```

### Common Operations

**Discover repository context:**

```python
from erk.cli.core import discover_repo_context

repo = discover_repo_context(ctx, Path.cwd())
# Returns: RepoContext(root, repo_name, work_dir)
```

**List worktrees:**

```python
worktrees = ctx.git_ops.list_worktrees(repo.root)
# Returns: list[WorktreeInfo]
```

**Load configuration:**

```python
from erk.config import load_config

config = load_config(repo.work_dir)
# Returns: Config with env vars and post_create commands
```

### Error Handling

Exceptions bubble up to CLI boundary:

```python
# In operations layer
def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
    result = subprocess.run([...], check=True)  # May raise
    return parse_worktrees(result.stdout)

# No try/except in business logic
# Errors caught by Click at CLI boundary
```

### Testing Guidelines

1. **Use fakes for unit tests**: `FakeGitOps`, `FakeGitHubOps`
2. **Use isolated filesystem**: `CliRunner().isolated_filesystem()`
3. **Configure fakes via constructor**: No setup methods
4. **Integration tests**: Use real git in temporary repos

**Example test:**

```python
from tests.fakes.gitops import FakeGitOps
from erk.core.context import ErkContext

def test_list_worktrees():
    git_ops = FakeGitOps(
        worktrees=[
            WorktreeInfo(path=Path("/repo/main"), branch="main", ...),
            WorktreeInfo(path=Path("/repo/feature"), branch="feature", ...),
        ]
    )
    ctx = ErkContext(git_ops=git_ops, ...)

    worktrees = ctx.git_ops.list_worktrees(Path("/repo"))
    assert len(worktrees) == 2
```

### Location-Aware Commands

Commands behave differently based on current directory:

```python
# Discover current context
repo = discover_repo_context(ctx, Path.cwd())

# Different behavior in root vs worktree
current_branch = ctx.git_ops.get_current_branch(Path.cwd())
if current_branch == repo.default_branch:
    # In root worktree
else:
    # In feature worktree
```

### Graphite Integration

Check if Graphite is available:

```python
if ctx.global_config and ctx.global_config.use_graphite:
    # Use Graphite features
    parent = ctx.graphite_ops.get_parent_branch(branch)
```

### GitHub Integration

PR status gracefully degrades:

```python
prs = ctx.github_ops.get_prs(repo.root)
if prs is None:
    # gh not available or not authenticated
    # Continue without PR info
else:
    # Show PR status
```

---

## Additional Resources

- **GitHub Repository**: https://github.com/dagster-io/erk
- **Issues**: https://github.com/dagster-io/erk/issues
- **Git Worktree Docs**: https://git-scm.com/docs/git-worktree
- **Graphite CLI**: https://graphite.com/
- **GitHub CLI**: https://cli.github.com/

### Internal Documentation (for contributors)

- **[AGENTS.md](AGENTS.md)** - Coding standards
- **[tests/AGENTS.md](tests/AGENTS.md)** - Testing guidelines
