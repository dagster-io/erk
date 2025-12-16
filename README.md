# erk

`erk` is a CLI tool for plan-oriented agentic engineering.

For the philosophy and design principles behind erk, see [The TAO of erk](TAO.md).

## Getting Started

Choose your path:

- **Project maintainers** setting up erk for the first time → [Project Setup](docs/user/project-setup.md)
- **Developers** joining a repo with erk configured → [Developer Onboarding](docs/user/developer-onboarding.md)

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

Erk supports extracting reusable documentation from implementation sessions into the `.erk/docs/agent/` folder—a directory of **agent-generated, agent-consumed documentation**.

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

## Monorepo Support

Erk supports monorepos with multiple projects. Understanding where files live is important:

### Repo Root vs Project Root

- **Repo root**: The top-level directory containing `.git/`. This is where `.erk/` lives.
- **Project root**: A subdirectory (or the repo root itself) containing a `pyproject.toml`. This is where `.impl/` lives.

In a simple repo, these are the same directory. In a monorepo, you might have:

```
my-monorepo/           # repo root
├── .erk/              # erk config (repo-scoped)
├── .git/
├── frontend/
│   └── pyproject.toml
└── backend/           # project root (when working here)
    ├── .impl/         # implementation plans (project-scoped)
    └── pyproject.toml
```

### What Lives Where

| Location   | Scope        | Contents                                         |
| ---------- | ------------ | ------------------------------------------------ |
| `.erk/`    | Repo root    | Erk configuration, scratch storage, session data |
| `.impl/`   | Project root | Implementation plans for the current project     |
| `.claude/` | Repo root    | Claude Code commands, skills, hooks              |

When you run `erk implement`, erk detects your project root and places `.impl/` there, ensuring plans are scoped to the correct project context.

**Note:** `.claude/` is repo-scoped, but Claude Code sessions should be started from the project root. This ensures Claude has the correct working directory context for the project you're working on.

### Gitignore

`erk init` automatically adds these entries to your `.gitignore`. If you ran `erk init`, this is already configured:

```gitignore
# At repo root
.erk/scratch/

# At each project root (or repo root for single-project repos)
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
