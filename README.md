# erk

`erk` is a CLI tool for plan-oriented agentic engineering.

For the philosophy and design principles behind erk, see [The TAO of erk](TAO.md).

## User Setup

### Prerequisites

Ensure you have these tools installed:

- `python` (3.10+)
- `claude` - Claude Code CLI
- `uv` - Fast Python environment management
- `gt` - Graphite for stacked PRs
- `gh` - GitHub CLI

### Initialize Erk

```bash
erk init
```

This command:

- Prompts for worktrees root directory (where all worktrees are stored)
- Creates global config at `~/.erk/config.toml`
- Detects Graphite (`gt`) availability for branch creation
- Creates repo-specific `config.toml` with preset selection (`auto`, `generic`, `dagster`)
- Offers to add `.env`, `.erk/scratch/`, and `.impl/` to `.gitignore`
- Shows shell integration setup instructions (completion + auto-activation)

### Shell Integration

`erk init` will display shell integration instructions to add to your `.zshrc` or `.bashrc`. Copy these instructions manually - erk doesn't modify your shell config automatically.

**Why manual setup?** Shell integration is essential for the core workflow: it enables commands such as `erk br co` and `erk wt co` to change your terminal's directory and activate the correct Python environment. Without it, these commands run in a subprocess and have no effect on your shell. We ask you to add it manually so you stay in control of your shell configuration.

To view the instructions again later: `erk init --shell`

Or append directly:

```bash
erk init --shell >> ~/.zshrc  # or ~/.bashrc
```

### Verify Setup

Run the doctor command to verify your environment:

```bash
erk doctor
```

This checks that all prerequisites are installed and configured correctly.

## Local Plan-Driven Workflow

The primary workflow: create a plan, save it, implement it, ship it. **Often completes without touching an IDE.**

### Planning Phase

1. Start a Claude Code session:

   ```bash
   claude
   ```

2. Enter plan mode and develop your plan

3. Save plan to GitHub issue (system prompts automatically after plan mode)

### Implementation

4. Execute the plan:

   ```bash
   erk implement <issue-number>
   ```

   This creates a worktree, activates the environment, and runs Claude Code with the plan.

### PR Submission

5. Submit the PR:

   ```bash
   erk pr submit
   ```

   Or from within Claude Code: `/erk:pr-submit`

### Code Review Iteration

6. Review PR feedback in GitHub

7. Address feedback:

   ```
   /erk:pr-address
   ```

8. Repeat until approved

### Landing

9. Merge and clean up:
   ```bash
   erk pr land
   ```

> **Note:** This entire workflow—from planning through shipping—can happen without opening an IDE. You create plans, submit code, review feedback in GitHub, address it via Claude Code, and land.

## Iteration Patterns

### Quick Iteration

For rapid commits within a worktree:

```
/quick-submit
```

Commits all changes and submits with Graphite.

### Rebasing and Stack Management

When your stack needs rebasing:

```bash
erk pr auto-restack --dangerous
```

Or from Claude Code: `/erk:auto-restack`

To fix merge conflicts during a rebase:

```
/erk:merge-conflicts-fix
```

## Common Workflows

### Auto-Restack: Intelligent Conflict Resolution

When working with stacked PRs, rebasing is a frequent operation. `erk pr auto-restack` automates this process with intelligent conflict resolution.

**What it does:**

1. Runs `gt restack` to rebase your stack onto the latest trunk
2. If conflicts occur, launches Claude Code with the `/erk:merge-conflicts-fix` command
3. After resolution, automatically continues the restack process
4. Repeats until the entire stack is cleanly rebased

**Basic usage:**

```bash
erk pr auto-restack --dangerous
```

**From within Claude Code:**

```
/erk:auto-restack
```

> Note: The `--dangerous` flag acknowledges that auto-restack invokes Claude with `--dangerously-skip-permissions`.

**When to use it:**

- After merging a PR that's below yours in the stack
- When trunk has been updated and you need to incorporate changes
- When Graphite shows your stack needs rebasing
- After running `erk pr land` on a parent branch

**How conflict resolution works:**

When conflicts are detected, erk spawns a Claude Code session that:

1. Identifies all conflicting files
2. Analyzes the nature of each conflict (content vs import conflicts)
3. Resolves conflicts while preserving the intent of both changes
4. Stages resolved files and continues the rebase

**Example scenario:**

```
trunk ← feature-a ← feature-b ← feature-c (you are here)
```

If `feature-a` merges into trunk, running `erk pr auto-restack --dangerous` will:

1. Rebase `feature-b` onto the new trunk
2. Resolve any conflicts (with Claude's help if needed)
3. Rebase `feature-c` onto the updated `feature-b`
4. Resolve any conflicts at this level too

The result: your entire stack is cleanly rebased with minimal manual intervention.

### Checkout PR from GitHub

When reviewing or debugging a PR—whether from a teammate or a remote agent run—you can check it out directly using the PR number or URL from the GitHub page.

**Basic usage:**

```bash
# Using PR number
erk pr checkout 123

# Using GitHub URL (copy directly from browser)
erk pr checkout https://github.com/owner/repo/pull/123
```

This creates a local worktree for the PR branch and changes your shell to that directory.

**Syncing with Graphite:**

After checkout, sync with Graphite to enable stack management:

```bash
erk pr sync --dangerous
```

This registers the branch with Graphite so you can use standard `gt` commands (`gt pr`, `gt land`, etc.).

> Note: The `--dangerous` flag acknowledges that sync invokes Claude with `--dangerously-skip-permissions`.

**Complete workflow:**

```bash
# 1. Checkout the PR (copy URL from GitHub)
erk pr checkout https://github.com/myorg/myrepo/pull/456

# 2. Sync with Graphite
erk pr sync --dangerous

# 3. Now iterate normally
claude
# ... make changes ...
/quick-submit

# 4. Or land when approved
erk pr land
```

**When to use it:**

- Reviewing a teammate's PR locally
- Debugging a PR created by remote agent execution
- Taking over a PR that needs local iteration
- Running tests or making fixes on someone else's branch

## Documentation Extraction

Erk supports extracting reusable documentation from implementation sessions into the `docs/learned/` folder—a directory of **agent-generated, agent-consumed documentation**.

This documentation:

- Captures patterns discovered during implementation
- Gets loaded by future agent sessions via AGENTS.md routing
- Builds institutional knowledge over time

To extract documentation from a session:

```
/erk:create-extraction-plan
```

## Remote Execution

For sandboxed, parallel execution via GitHub Actions:

1. Create a plan (via Claude Code plan mode)

2. Submit for remote execution:
   ```bash
   erk plan submit <issue-number>
   ```

The agent runs in GitHub Actions and creates a PR automatically.

## Debugging Remote PRs

When a remote implementation needs local iteration:

```bash
erk pr checkout <pr-number>
erk pr sync --dangerous
```

This checks out the PR into a local worktree for debugging and iteration.

## Planless Workflow

For smaller changes that don't require formal planning:

1. Create a worktree:

   ```bash
   erk wt create <branch-name>
   ```

2. Iterate normally in Claude Code

3. Submit PR:

   ```bash
   erk pr submit
   ```

4. Merge and clean up:
   ```bash
   erk pr land
   ```

## File Locations

| Location   | Contents                                         |
| ---------- | ------------------------------------------------ |
| `.erk/`    | Erk configuration, scratch storage, session data |
| `.impl/`   | Implementation plans (at worktree root)          |
| `.claude/` | Claude Code commands, skills, hooks              |

### Gitignore

`erk init` automatically adds these entries to your `.gitignore`. If you ran `erk init`, this is already configured:

```gitignore
.erk/scratch/
.impl/
```

`.impl/` contains temporary implementation plans that shouldn't be committed. `.erk/scratch/` holds session-specific working files.

## Plan Mode GitHub Integration

By default, erk modifies Claude Code's plan mode behavior. When you exit plan mode, erk prompts you to save the plan to GitHub as an issue before proceeding. This enables the plan-driven workflow where plans become trackable issues that can be implemented via `erk implement <issue-number>`.

To disable this behavior and use standard Claude Code plan mode:

```bash
erk config set github_planning false
```

To re-enable:

```bash
erk config set github_planning true
```

When disabled, exiting plan mode works exactly as it does in standard Claude Code.
