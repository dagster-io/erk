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

This creates your global config and prompts for shell integration setup.

### Shell Integration

`erk init` will display shell integration instructions to add to your `.zshrc` or `.bashrc`. Copy these instructions manually - erk doesn't modify your shell config automatically.

**Why manual setup?** Shell integration is essential for the core workflow: it enables `erk checkout` to change your terminal's directory and activate the correct Python environment. Without it, these commands run in a subprocess and have no effect on your shell. We ask you to add it manually so you stay in control of your shell configuration.

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
erk pr auto-restack
```

Or from Claude Code: `/erk:auto-restack`

To fix merge conflicts during a rebase:

```
/erk:merge-conflicts-fix
```

## Documentation Extraction

Erk supports extracting reusable documentation from implementation sessions into the `docs/agent/` folder—a directory of **agent-generated, agent-consumed documentation**.

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
   erk submit <issue-number>
   ```

The agent runs in GitHub Actions and creates a PR automatically.

## Debugging Remote PRs

When a remote implementation needs local iteration:

```bash
erk pr checkout <pr-number>
erk pr sync
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
