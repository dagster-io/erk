---
title: Gateway Inventory
read_when:
  - "understanding available gateways"
  - "adding a new gateway"
  - "creating test doubles for external services"
---

# Gateway Inventory

Catalog of all ABC/Fake gateway packages in the erk codebase. Each gateway follows the ABC/Real/Fake pattern for dependency injection and testing.

## Core Gateways

Located in `packages/erk-shared/src/erk_shared/`:

### Git (`git/`)

Git operations abstraction. See `git/abc.py` for full method list.

**Fake Features**: In-memory worktree state, branch tracking, configurable return values.

### GitHub (`github/`)

GitHub PR and repository operations.

**Fake Features**: In-memory PR state, configurable PR responses, label tracking, mutation tracking via `added_labels` property.

### GitHub Issues (`github/issues/`)

GitHub issue operations.

**Fake Features**: In-memory issue storage, comment tracking, state management.

### PromptExecutor (`prompt_executor/`)

Claude CLI single-shot prompt execution for kit commands.

**Key Methods**:

- `execute_prompt()`: Execute a single prompt and return the result

**Fake Features**: Configurable responses, prompt tracking.

### GitHubAdmin (`github_admin/`)

GitHub Actions admin operations.

**Key Methods**:

- `get_workflow_permissions()`: Get current workflow permissions from GitHub API
- `set_workflow_pr_permissions()`: Enable or disable PR creation via workflow permissions API
- `check_auth_status()`: Check GitHub CLI authentication status
- `secret_exists()`: Check if a repository secret exists

**Fake Features**: Configurable permissions, auth state.

## Higher-Level Abstractions

Located in `packages/erk-shared/src/erk_shared/gateway/`:

### BranchManager (`branch_manager/`)

Dual-mode abstraction for branch operations that works transparently regardless of Graphite availability.

**Purpose**: Provides consistent interface for operations that behave differently depending on whether Graphite is installed/enabled.

**Key Methods**:

- `get_pr_for_branch()`: Uses Graphite cache (fast) or GitHub API (fallback)
- `create_branch()`: Uses `gt create` (Graphite) or `git branch` (Git)
- `delete_branch()`: Delete branch with mode-appropriate cleanup
- `submit_branch()`: Push branch to remote (`git push` or `gt submit`)
- `get_branch_stack()`: Get full stack for a branch (Graphite) or None (Git)
- `track_branch()`: Register branch with parent (Graphite) or no-op (Git)
- `get_parent_branch()`: Get parent branch (Graphite) or None (Git)
- `get_child_branches()`: Get child branches (Graphite) or empty list (Git)
- `is_graphite_managed()`: Check which mode is active

**Implementations**:

- `GraphiteBranchManager`: Uses Graphite gateway for stack-aware operations
- `GitBranchManager`: Uses Git + GitHub gateways as fallback

**Factory**: Use `create_branch_manager(git=git, github=github, graphite=graphite)` to get the appropriate implementation.

**Fake Features**: `FakeBranchManager` provides in-memory PR tracking and branch creation recording.

**Related**: [Gateway Hierarchy](gateway-hierarchy.md) for architecture overview.

## Domain Gateways

Located in `packages/erk-shared/src/erk_shared/gateway/`:

### Browser (`browser/`)

System browser launch abstraction.

**Fake Features**: Success mode toggle, launch call tracking via `launched_urls` property.

### Console (`console/`)

User interaction abstraction combining TTY detection, mode-aware output, and user prompts.

**Key Methods**:

- `is_stdin_interactive()` / `is_stdout_tty()` / `is_stderr_tty()`: TTY detection
- `confirm()`: User confirmation prompts with yes/no response
- `info()` / `success()` / `error()`: Mode-aware diagnostic output

**Implementations**:

- `InteractiveConsole`: Full TTY interaction with styled output
- `ScriptConsole`: Suppressed diagnostics for shell integration (--script mode)

**Fake Features**: Configurable TTY states, pre-programmed `confirm_responses` list, prompt tracking via `confirm_prompts` property.

**When to use**: Any code that needs TTY detection or user confirmation should use `ctx.console` instead of direct stdin/stdout checks or click.confirm().

### ClaudeInstallation (`learn/extraction/claude_installation/`)

Gateway for `~/.claude/` filesystem operations (sessions, settings, plans).

**Fake Features**: Configurable session data, project directory injection, in-memory settings.

**When to use**: Any code that needs to read from or write to `~/.claude/` paths should use this gateway instead of `Path.home()` directly.

### Clipboard (`clipboard/`)

System clipboard abstraction.

**Fake Features**: Success mode toggle, copy call tracking via `copied_texts` property.

### Time (`time/`)

Time operations abstraction for testable delays.

**Fake Features**: Fixed time injection, sleep call tracking via `sleep_calls` property, instant returns (no actual sleeping).

### Graphite (`graphite/`)

Graphite stack management operations.

**Fake Features**: Extensive state injection (branch relationships, PR info), parent/child tracking, submit call tracking.

### ErkInstallation (`gateway/erk_installation/`)

Consolidated gateway for all `~/.erk/` filesystem operations. Provides config management, version tracking, and pool state persistence.

**Key Methods**:

- `config_exists()` / `load_config()` / `save_config()`: Global config operations
- `load_pool_state()` / `save_pool_state()`: Pool state persistence
- `get_last_seen_version()` / `update_last_seen_version()`: Version tracking
- `root()`: Installation root path access

**Fake Features**: In-memory config/pool state, mutation tracking via `saved_configs`, `pool_saves`, `version_updates` properties.

**When to use**: Any code that needs to read from or write to `~/.erk/` paths should use this gateway instead of `Path.home()` directly.

### Shell (`gateway/shell/`)

Shell detection and tool availability.

**Key Methods**:

- `detect_shell()`: Detect current shell and return configuration file path
- `get_installed_tool_path()`: Check if a tool is installed and get its path
- `get_tool_version()`: Get version string of an installed CLI tool
- `spawn_subshell()`: Spawn an interactive subshell that executes a command

**Fake Features**: Configurable shell type, tool availability.

### Completion (`gateway/completion/`)

Shell completion script generation.

**Key Methods**:

- `generate_bash()`: Generate bash completion script
- `generate_zsh()`: Generate zsh completion script
- `generate_fish()`: Generate fish completion script
- `get_erk_path()`: Get path to erk executable

**Fake Features**: Configurable script output.

### HttpClient (`gateway/http/`)

HTTP client for TUI operations (avoids subprocess overhead).

**Key Methods**:

- `get()`: Send a GET request to the API
- `post()`: Send a POST request to the API
- `patch()`: Send a PATCH request to the API

**Fake Features**: Configurable responses, request tracking.

### Codespace (`gateway/codespace/`)

Codespace SSH operations.

**Key Methods**:

- `exec_ssh_interactive()`: Replace current process with SSH session to codespace
- `run_ssh_command()`: Run SSH command in codespace and return exit code

**Fake Features**: Exit code control, command tracking.

### CodespaceRegistry (`gateway/codespace_registry/`)

Codespace registration and configuration abstraction.

**Purpose**: Manages lookup of registered GitHub Codespaces for remote Claude execution. Stores codespace configurations in `~/.erk/codespaces.toml`.

**Key Methods**:

- `list_codespaces()`: List all registered codespaces
- `get()`: Get a codespace by name
- `get_default()`: Get the default codespace
- `get_default_name()`: Get the name of the default codespace

**Mutation Functions** (standalone, not on ABC):

- `register_codespace()`: Register a new codespace
- `unregister_codespace()`: Remove a codespace registration
- `set_default_codespace()`: Set the default codespace

**Type**: `RegisteredCodespace` frozen dataclass with `name`, `gh_name`, `created_at` fields.

**Fake Features**: In-memory codespace storage, configurable default.

**When to use**: Any code that needs to work with registered codespaces should use this gateway instead of directly reading `~/.erk/codespaces.toml`.

### CommandExecutor (`gateway/command_executor/`)

TUI command execution abstraction for test isolation.

**Purpose**: Provides interface for palette commands to perform actions like opening URLs, copying to clipboard, closing plans, and submitting to queue.

**Key Methods**:

- `open_url()`: Open URL in browser
- `copy_to_clipboard()`: Copy text to clipboard
- `close_plan()`: Close plan and linked PRs
- `notify()`: Show notification to user
- `refresh_data()`: Trigger data refresh
- `submit_to_queue()`: Submit plan to queue for remote AI implementation

**Fake Features**: Pre-programmed responses, action tracking via properties.

**When to use**: TUI palette commands should use this gateway instead of direct gateway calls.

### PlanDataProvider (`gateway/plan_data_provider/`)

TUI plan data access abstraction.

**Purpose**: Provides interface for TUI plan table to fetch and manipulate plan data.

**Key Methods**:

- `fetch_plans()`: Fetch plans matching given filters
- `close_plan()`: Close a plan and its linked PRs
- `submit_to_queue()`: Submit a plan to the implementation queue
- `fetch_branch_activity()`: Fetch branch activity for plans with local worktrees
- `fetch_plan_content()`: Fetch plan content from issue comment

**Properties**:

- `repo_root`: Repository root path
- `clipboard`: Clipboard interface
- `browser`: Browser launcher interface

**Fake Features**: In-memory plan storage, action tracking.

**When to use**: TUI plan table should use this gateway instead of direct GitHub/Git access.

### ClaudeInstallation (`gateway/claude_installation/`)

Claude Code installation filesystem operations abstraction.

**Purpose**: Gateway for `~/.claude/` filesystem operations (sessions, settings, plans).

**Fake Features**: Configurable session data, project directory injection, in-memory settings.

**When to use**: Any code that needs to read from or write to `~/.claude/` paths should use this gateway instead of `Path.home()` directly.

### LiveDisplay (`gateway/live_display/`)

TUI display abstraction for live updates.

**Purpose**: Provides interface for displaying live status updates in the TUI.

**Fake Features**: Display call tracking, message capture.

**When to use**: TUI components that need to show live updates should use this gateway.

### CIRunner (`gateway/ci_runner/`)

CI check execution abstraction for automated verification workflows.

**Key Methods**:

- `run_check()`: Execute a CI check command and return result

**Result Type**: `CICheckResult` with fields:

- `passed`: Whether the check succeeded
- `error_type`: Error type if failed (`"command_not_found"`, `"command_failed"`), None on success

**Fake Features**: Configurable check failures via `failing_checks` set, missing command simulation via `missing_commands` set, execution tracking via `run_calls` property.

**Factory Method**: `FakeCIRunner.create_passing_all()` creates a fake where all checks pass.

**When to use**: Any code running CI checks (pytest, ruff, prettier) should use `ctx.ci_runner` instead of subprocess.run() directly.

### Parallel Task Runner (`parallel/`)

Parallel execution abstraction.

**Note**: No fake implementation - uses real ThreadPoolExecutor. Mock at task level instead.

## Sub-Gateways

Sub-gateways are specialized interfaces extracted from main gateways to enforce architectural boundaries (e.g., mutations only through BranchManager).

### GitBranchOps (`git/branch_ops/`)

Git branch mutation operations extracted from the main Git gateway.

**Purpose**: Makes BranchManager the enforced abstraction for branch mutations.

**Key Methods**:

- `create_branch()`: Create a new branch without checking it out
- `delete_branch()`: Delete a local branch
- `checkout_branch()`: Checkout a branch
- `checkout_detached()`: Checkout a detached HEAD at a ref
- `create_tracking_branch()`: Create a local tracking branch from a remote branch

**Note**: Query operations (get_current_branch, list_local_branches, etc.) remain on the main Git ABC.

### Worktree (`git/worktree/`)

Git worktree operations.

**Key Methods**:

- `list_worktrees()`: List all worktrees in the repository
- `add_worktree()`: Add a new git worktree
- `move_worktree()`: Move a worktree to a new location
- `remove_worktree()`: Remove a worktree
- `prune_worktrees()`: Prune stale worktree metadata
- `find_worktree_for_branch()`: Find worktree path for a given branch
- `is_branch_checked_out()`: Check if a branch is checked out in any worktree
- `is_worktree_clean()`: Check if worktree has uncommitted changes

**Fake Features**: In-memory worktree state, path existence tracking.

### GraphiteBranchOps (`gateway/graphite/branch_ops/`)

Graphite branch mutation operations extracted from the main Graphite gateway.

**Purpose**: Makes BranchManager the enforced abstraction for Graphite branch mutations.

**Key Methods**:

- `track_branch()`: Register a branch with Graphite (uses `gt track`)
- `delete_branch()`: Delete a branch using Graphite (uses `gt delete -f`)
- `submit_branch()`: Submit (force-push) a branch to GitHub (uses `gt submit`)

**Note**: Query operations (get_all_branches, get_branch_stack, etc.) remain on the main Graphite ABC.

## Implementation Layers

Each gateway typically has these implementations:

| Layer    | File          | Purpose                                          |
| -------- | ------------- | ------------------------------------------------ |
| ABC      | `abc.py`      | Abstract interface definition                    |
| Real     | `real.py`     | Production implementation (subprocess/API calls) |
| Fake     | `fake.py`     | In-memory test implementation                    |
| DryRun   | `dry_run.py`  | No-op wrapper for dry-run mode (optional)        |
| Printing | `printing.py` | Logs operations before delegating (optional)     |

## Usage Pattern

```python
# Production code uses ABC types
def my_command(git: Git, github: GitHub, time: Time) -> None:
    worktrees = git.list_worktrees(repo_root)
    pr = github.get_pr_for_branch(repo_root, branch)
    time.sleep(2.0)  # Instant in tests!

# Tests inject fakes
def test_my_command() -> None:
    fake_git = FakeGit(worktrees=[...])
    fake_github = FakeGitHub(prs={...})
    fake_time = FakeTime()

    my_command(fake_git, fake_github, fake_time)

    assert fake_time.sleep_calls == [2.0]
```

## Adding New Gateways

When adding a new gateway:

1. Create `abc.py` with interface definition
2. Create `real.py` with production implementation
3. Create `fake.py` with in-memory test implementation
4. Create `dry_run.py` if operations are destructive (optional)
5. Add to `__init__.py` with re-exports
6. Update `ErkContext` to include new gateway

**Related**: [Erk Architecture Patterns](erk-architecture.md#gateway-directory-structure)
