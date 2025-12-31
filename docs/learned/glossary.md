---
title: Erk Glossary
read_when:
  - "understanding project terminology"
  - "confused about domain-specific terms"
  - "working with worktrees, plans, or stacks"
  - "working with objectives or turns"
---

# Erk Glossary

Definitive terminology reference for the erk project.

**Purpose**: Eliminate confusion about domain-specific terms. When in doubt about terminology, consult this document.

---

## Core Concepts

### Worktree

Git's native feature for creating additional working directories for a repository.

**Technical**: Created with `git worktree add`, allows working on multiple branches simultaneously without switching branches in a single directory.

**Example**:

```bash
git worktree add ../feature-branch feature-branch
```

### Erk

A **managed worktree** created and maintained by the erk tool.

**Distinction from worktree**:

- **Worktree** = git's feature (any directory managed by git worktree)
- **Erk** = worktree + configuration + environment setup + lifecycle management

**Features**:

- Stored in standardized location (`~/erks/<repo>/<name>`)
- Automatic `.env` file generation
- Post-creation hook execution
- Integration with graphite/GitHub

**Example**: `erk create my-feature` creates both a git worktree and an erk.

### Repo Root

The main git repository directory containing `.git/` directory.

**Location**: Where you originally cloned the repository.

**Example**: If you cloned to `/Users/you/projects/erk`, that's the repo root.

**Note**: In a worktree, `git rev-parse --git-common-dir` points back to the repo root's `.git` directory.

### Root Worktree

The primary git worktree where the `.git` directory lives (as opposed to linked worktrees which have `.git` files pointing elsewhere).

**Terminology Note**: Use "root worktree" (not "main worktree") to avoid confusion with the "main" branch. This ensures "main" unambiguously refers to the branch name.

**In Code**: `WorktreeInfo.is_root` field identifies the root worktree. Always use this instead of path comparison.

**Detection**:

- ✅ Correct: `if wt.is_root:`
- ❌ Wrong: `if wt.path == repo_root:` (fails from non-root worktrees)

**Related**: [Root Worktree Detection](architecture/erk-architecture.md#root-worktree-detection)

### Erks Dir

The directory containing all erks for a specific repository.

**Path structure**: `{erks_root}/{repo_name}/`

**Example**: If `erks_root = ~/erks` and repo is named `erk`, then `erks_dir = ~/erks/erk/`

**Contents**:

- Individual erk directories
- `config.toml` (repo-specific configuration)

### Erks Root

The top-level directory containing all managed repositories' erk directories.

**Configuration**: Set in `~/.erk/config.toml`:

```toml
erks_root = "/Users/you/erks"
```

**Structure**:

```
~/erks/                    ← erks root
  ├── erk/                ← erks dir for "erk" repo
  │   ├── feature-a/           ← individual erk
  │   ├── feature-b/           ← individual erk
  │   └── config.toml
  ├── other-project/            ← erks dir for another repo
  │   └── ...
```

### Worktree Path

The absolute path to a specific erk directory.

**Construction**: `{erks_dir}/{worktree_name}`

**Example**: `~/erks/erk/my-feature/`

**Code**: `worktree_path_for(repo.erks_dir, "my-feature")`

### Branch Naming Convention

Erk branches follow the pattern `P{issue_number}-{slug}-{timestamp}`:

- **P** - Prefix indicating a "plan" branch (linked to a GitHub issue)
- `{issue_number}` - GitHub issue number (extracted by `extract_leading_issue_number()`)
- `{slug}` - Kebab-case description of the work (max 31 chars before timestamp)
- `{timestamp}` - Creation timestamp in `MM-DD-HHMM` format

**Examples**:

- `P2843-add-p-prefix-to-branch-nam-12-09-0934`
- `P123-fix-auth-bug-01-15-1430`

**Why the "P" prefix?**: Distinguishes erk-managed plan branches from manually-created branches, making it easy to identify which branches are linked to GitHub issues.

**Backwards Compatibility**: `extract_leading_issue_number()` supports both formats via the pattern `^[Pp]?(\d+)-`:

- New format: `P123-feature` → extracts `123`
- Legacy format: `123-feature` → extracts `123`

**Automatic extraction**: `get_branch_issue()` uses this pattern to determine which GitHub issue a branch relates to, without requiring git config setup.

### Claude Code Project Directory

The directory where Claude Code stores session data for a specific project. Located at `~/.claude/projects/<encoded-path>` where the path is encoded by replacing `/` and `.` with `-`.

**Contents**:

- `<session-id>.jsonl` - Main session logs (UUID format)
- `agent-<agent-id>.jsonl` - Subagent logs from Task tool invocations

**Walk-up discovery**: When looking up a project from a working directory, the session store checks if an exact match exists for the current path, then walks up to parent directories until finding a match or hitting the filesystem root. This enables running erk commands from subdirectories of a Claude project.

**See**: [Claude Code Session Layout](sessions/layout.md)

---

## Path Hierarchy in CLI Commands

When writing CLI commands, use the correct path level for file lookups:

| Path                      | What it represents             | When to use                                            |
| ------------------------- | ------------------------------ | ------------------------------------------------------ |
| `ctx.cwd`                 | Where the user ran the command | **Rarely correct** - only for user-relative operations |
| `repo.root` / `repo_root` | Git worktree root              | `.erk/`, `.impl/` lookups, git operations              |

### Common Pattern: `.impl/` Lookup

`.impl/` lives at the worktree root:

```python
impl_dir = repo_root / ".impl"
```

### Common Mistake

**❌ Wrong**: Using `ctx.cwd` for `.impl/` lookup

```python
impl_dir = ctx.cwd / ".impl"  # Wrong - user may run from any subdirectory
```

**✅ Correct**: Using worktree root

```python
impl_dir = repo_root / ".impl"
```

---

## Shell Concepts

### Shell Integration

A mechanism that allows erk commands to change the parent shell's working directory and environment.

**Why needed**: A subprocess cannot change its parent's cwd (Unix process isolation). Without shell integration, commands that delete the current worktree leave the shell stranded in a deleted directory.

**Components**:

1. **Wrapper function** (`erk()`): Intercepts erk commands and sources activation scripts
2. **`--script` flag**: Commands output activation script paths instead of diagnostics
3. **Activation scripts**: Shell scripts that `cd` and set environment variables
4. **Init scripts**: `~/.erk/shell/init.zsh` and `init.bash` define the wrapper function

**Setup**:

```bash
erk init --shell
source ~/.erk/shell/init.zsh  # or init.bash
```

**Verification**:

```bash
type erk
# Expected: erk is a function (not a file path)
```

**⚠️ Alias Warning**: Direct aliases like `alias land='erk pr land'` bypass shell integration. Use functions or go through the `erk` wrapper. See [Shell Aliases](cli/shell-aliases.md) for safe patterns.

**Related**: [Shell Integration Constraint](architecture/shell-integration-constraint.md) explains the Unix process model limitation.

---

## Git & Graphite Concepts

**For comprehensive gt documentation**: See [tools/gt.md](tools/gt.md)

### Force-Push After Squash

When squashing commits on a branch that already has a PR:

1. **Why it's needed**: Squashing rewrites git history, causing the local branch to diverge from remote
2. **Why it's safe**: The PR already exists on remote - you're updating it, not creating it
3. **Pattern**: After `gt squash`, use `gt submit` with `--force` (or equivalent)

This pattern applies to:

- `erk pr sync` (automatically uses force after squash)
- Manual squash + submit workflows
- Any workflow that rewrites history on an existing PR branch

### Trunk Branch

The default branch of the repository (typically `main` or `master`).

The base branch from which all feature branches grow (trunk of the stack tree).

**Detection**: `git symbolic-ref refs/remotes/origin/HEAD`

### Stack

A linear chain of dependent branches managed as worktrees by erk.

**Erk concept**: A stack represents branches that depend on each other, where each branch's changes build on the parent branch. Erk manages these as separate worktrees for parallel development.

**Underlying**: Uses Graphite for branch dependency tracking (`gt` commands).

**Example**:

```
main (trunk)
  └─> feature-a (adds user model)
       └─> feature-a-2 (adds user controller)
            └─> feature-a-3 (adds user views)
```

**Purpose**: Break large features into reviewable chunks while maintaining dependencies, with each branch in its own worktree.

### Default Branch

See: [Trunk Branch](#trunk-branch)

---

## Configuration Terms

### Global Config

Configuration stored in `~/.erk/config.toml`.

**Scope**: Applies to all repositories managed by erk.

**Location**: `~/.erk/config.toml`

**Contents**:

```toml
erks_root = "/Users/you/worktrees"
use_graphite = true
show_pr_info = true
shell_setup_complete = true
```

**Access**: Via `ConfigStore` interface.

### Repo Config

Configuration stored in `{erks_dir}/config.toml`.

**Scope**: Applies to all erks for a specific repository.

**Location**: `{erks_root}/{repo_name}/config.toml`

**Contents**:

```toml
[env]
DATABASE_URL = "postgresql://localhost/dev_db"
API_KEY = "${SECRET_API_KEY}"

[[post_create]]
command = ["uv", "sync"]
working_dir = "."
```

**Access**: Via `load_config(erks_dir)` function.

---

## Architecture Terms

### Repo Context

A frozen dataclass containing repository information.

**Key Fields**:

- `root: Path` - Working tree root for git commands (worktree or main repo)
- `main_repo_root: Path` - Main repository root (consistent across worktrees)
- `repo_name: str` - Repository name
- `repo_dir: Path` - Path to erk metadata directory (`~/.erk/repos/<repo-name>`)
- `worktrees_dir: Path` - Path to worktrees directory (`~/.erk/repos/<repo-name>/worktrees`)
- `github: GitHubRepoId | None` - GitHub repository identity, if available

**Creation**: `discover_repo_or_sentinel(git, Path.cwd())`

See `src/erk/core/repo_discovery.py` for the canonical definition.

#### root vs main_repo_root

- **`root`**: The working tree root where git commands should run. For worktrees, this is the worktree directory. For main repos, equals `main_repo_root`.

- **`main_repo_root`**: The main repository root (consistent across all worktrees). Used for:
  - Deriving `repo_name` for metadata paths
  - Operations that need the root worktree (e.g., escaping from a worktree being deleted)
  - Resolving "root" as a target in commands like `stack move root`

**Key insight:** When running from a worktree, git commands use `root` (the worktree), but metadata and escaping use `main_repo_root` (the main repo).

### Erk Context

A frozen dataclass containing all injected dependencies.

**Purpose**: Dependency injection container passed to all commands. Created at CLI entry point and threaded through the application.

**Key Integration Fields**:

- `git: Git` - Git operations
- `github: GitHub` - GitHub PR operations
- `graphite: Graphite` - Graphite CLI operations
- `shell: Shell` - Shell detection
- `completion: Completion` - Shell completion generation
- `script_writer: ScriptWriter` - Activation script generation

**Configuration Fields**:

- `global_config: GlobalConfig | None` - Global configuration (may be None during init)
- `local_config: LoadedConfig | None` - Repository-specific configuration
- `dry_run: bool` - Whether to print operations instead of executing

**Path Fields**:

- `cwd: Path` - Current working directory
- `repo: RepoContext | NoRepoSentinel` - Repository context

**Factory Methods**:

- `create_context(dry_run=False)` - Production context with real implementations
- `ErkContext.for_test(...)` - Test context with configurable fakes

See `src/erk/core/context.py` for the canonical definition.

### PRDetails

A frozen dataclass containing comprehensive PR information from a single GitHub API call.

**Location**: `packages/erk-shared/src/erk_shared/github/types.py`

**Purpose**: Implements the "Fetch Once, Use Everywhere" pattern - fetch all commonly-needed PR fields in one API call to reduce rate limit consumption.

**Fields**:

| Category     | Fields                                                                  |
| ------------ | ----------------------------------------------------------------------- |
| Identity     | `number`, `url`                                                         |
| Content      | `title`, `body`                                                         |
| State        | `state` ("OPEN"/"MERGED"/"CLOSED"), `is_draft`                          |
| Structure    | `base_ref_name`, `head_ref_name`, `is_cross_repository`                 |
| Mergeability | `mergeable` ("MERGEABLE"/"CONFLICTING"/"UNKNOWN"), `merge_state_status` |
| Metadata     | `owner`, `repo`, `labels`                                               |

**Design Pattern**:

When multiple call sites need different PR fields, create a comprehensive type that fetches everything once:

```python
# Instead of multiple narrow fetches:
title = github.get_pr_title(pr_number)
state = github.get_pr_state(pr_number)
base = github.get_pr_base(pr_number)

# Use one comprehensive fetch:
pr = github.get_pr(owner, repo, pr_number)
# pr.title, pr.state, pr.base_ref_name all available
```

**Related**: [GitHub Interface Patterns](architecture/github-interface-patterns.md)

### PRNotFound

A sentinel class returned when a PR lookup fails to find a PR.

**Location**: `packages/erk-shared/src/erk_shared/github/types.py`

**Purpose**: Provides LBYL-style error handling for PR lookups. Instead of returning `None` (which loses context) or raising an exception (which violates LBYL), methods return this sentinel that can preserve lookup context.

**Fields**:

| Field       | Type          | Description                    |
| ----------- | ------------- | ------------------------------ |
| `branch`    | `str \| None` | Branch name that was looked up |
| `pr_number` | `int \| None` | PR number that was looked up   |

**Usage Pattern**:

```python
from erk_shared.github.types import PRNotFound

pr = github.get_pr_for_branch(repo_root, branch)
if isinstance(pr, PRNotFound):
    # No PR exists for this branch
    click.echo(f"No PR found for branch: {pr.branch}")
else:
    # pr is PRDetails
    click.echo(f"Found PR #{pr.number}")
```

**Why Sentinel, Not None?**:

1. **Type safety**: `PRDetails | PRNotFound` is explicit about possible returns
2. **Context preservation**: Can inspect which branch/PR was looked up
3. **LBYL compliance**: Explicit isinstance check, not try/except

**Related**: [Not-Found Sentinel Pattern](architecture/not-found-sentinel.md)

### will_close_target

A boolean field on `PullRequestInfo` indicating whether a PR will automatically close its linked issue when merged.

**Location**: `packages/erk-shared/src/erk_shared/github/types.py`

**Source**: Derived from GitHub's `CrossReferencedEvent.willCloseTarget` GraphQL field.

**Values**:

| Value   | Meaning                                                                                      |
| ------- | -------------------------------------------------------------------------------------------- |
| `true`  | PR was created with "Closes #N" (or equivalent) in initial body                              |
| `false` | PR merely references the issue without closing keywords, or keyword was added after creation |

**Display**: In `erk plan list`, PRs with `will_close_target: true` show a 🔗 indicator.

**Critical Timing**: This field is determined at PR creation time. Editing the PR body afterward to add "Closes #N" does **not** update `willCloseTarget`. This is why `erk plan submit` must include the closing keyword in the initial `create_pr()` call.

**Related**: [GitHub Issue-PR Linkage API Patterns](architecture/github-pr-linkage-api.md), [Issue-PR Linkage Storage](erk/issue-pr-linkage-storage.md)

---

## Event Types

### ProgressEvent

A frozen dataclass for emitting progress notifications during long-running operations.

**Location**: `packages/erk-shared/src/erk_shared/gateway/gt/events.py`

**Purpose**: Decouple progress reporting from rendering. Operations yield events; CLI layer renders them.

**Fields**:

- `message: str` - Human-readable progress message
- `style: Literal["info", "success", "warning", "error"]` - Visual style hint (default: "info")

**Example**:

```python
yield ProgressEvent("Analyzing changes with Claude...")
yield ProgressEvent("Complete", style="success")
```

**Related**: [Claude CLI Progress Feedback Pattern](architecture/claude-cli-progress.md)

### CompletionEvent

A generic frozen dataclass wrapping the final result of a generator-based operation.

**Location**: `packages/erk-shared/src/erk_shared/gateway/gt/events.py`

**Purpose**: Signal operation completion and provide the result to the consumer.

**Type Parameter**: `CompletionEvent[T]` where `T` is the result type.

**Example**:

```python
yield CompletionEvent(MyResult(success=True, data=data))
```

**Related**: [Claude CLI Progress Feedback Pattern](architecture/claude-cli-progress.md)

### ClaudeEvent

A union type of frozen dataclasses representing events from Claude CLI streaming execution.

**Location**: `src/erk/core/claude_executor.py`

**Purpose**: Typed events enabling pattern matching for Claude CLI output processing.

**Event Types**:

| Event                | Field(s)          | Description                                       |
| -------------------- | ----------------- | ------------------------------------------------- |
| `TextEvent`          | `content: str`    | Text content from Claude                          |
| `ToolEvent`          | `summary: str`    | Tool usage summary                                |
| `SpinnerUpdateEvent` | `status: str`     | Status update for spinner display                 |
| `PrUrlEvent`         | `url: str`        | Pull request URL                                  |
| `PrNumberEvent`      | `number: int`     | Pull request number (proper int)                  |
| `PrTitleEvent`       | `title: str`      | Pull request title                                |
| `IssueNumberEvent`   | `number: int`     | GitHub issue number (proper int)                  |
| `ErrorEvent`         | `message: str`    | Error with non-zero exit code                     |
| `NoOutputEvent`      | `diagnostic: str` | Claude CLI produced no output                     |
| `NoTurnsEvent`       | `diagnostic: str` | Claude completed with num_turns=0 (hook blocking) |
| `ProcessErrorEvent`  | `message: str`    | Failed to start or timeout                        |

**Union Type**:

```python
ClaudeEvent = (
    TextEvent | ToolEvent | SpinnerUpdateEvent |
    PrUrlEvent | PrNumberEvent | PrTitleEvent | IssueNumberEvent |
    ErrorEvent | NoOutputEvent | NoTurnsEvent | ProcessErrorEvent
)
```

**Example (consuming)**:

```python
for event in executor.execute_command_streaming(...):
    match event:
        case TextEvent(content=text):
            print(text)
        case ToolEvent(summary=summary):
            print(f"  > {summary}")
        case PrNumberEvent(number=num):
            pr_number = num  # Already int, no conversion needed
        case ErrorEvent(message=msg):
            handle_error(msg)
```

**Related**: [Claude CLI Integration](architecture/claude-cli-integration.md)

---

## Gateway Terms

### Gateway

An ABC (Abstract Base Class) defining gateways for external systems.

**Pattern**:

```python
class Git(ABC):
    @abstractmethod
    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        ...
```

**Examples**:

- `Git` - Git operations
- `GitHub` - GitHub API operations
- `Graphite` - Graphite CLI operations
- `ConfigStore` - Configuration operations
- `Shell` - Shell detection and tool availability
- `Completion` - Shell completion generation
- `ScriptWriter` - Activation script generation

**Purpose**: Abstraction enabling testing with fakes.

**Related**: [Gateway Inventory](architecture/gateway-inventory.md)

### Real Implementation

Production implementation of a gateway interface that executes actual commands.

**Naming**: `Real<Interface>` (e.g., `RealGit`)

**Pattern**:

```python
class RealGit(Git):
    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        result = subprocess.run(["git", "worktree", "list", ...])
        return parse_worktrees(result.stdout)
```

**Usage**: Instantiated in `create_context()` for production.

### Fake Implementation

In-memory implementation of a gateway interface for testing.

**Naming**: `Fake<Interface>` (e.g., `FakeGit`)

**Location**: `tests/fakes/<interface>.py`

**Pattern**:

```python
class FakeGit(Git):
    def __init__(self, *, worktrees: list[WorktreeInfo] | None = None):
        self._worktrees = worktrees or []

    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        return self._worktrees
```

**Key Rule**: All state via constructor, NO public setup methods.

**Purpose**: Fast, deterministic tests without filesystem I/O.

### Dry Run Wrapper

A wrapper around a real implementation that prints messages instead of executing destructive operations.

**Naming**: `DryRun<Interface>` (e.g., `DryRunGit`)

**Pattern**:

```python
class DryRunGit(Git):
    def __init__(self, wrapped: Git) -> None:
        self._wrapped = wrapped

    def remove_worktree(self, repo_root: Path, path: Path, force: bool) -> None:
        click.echo(f"[DRY RUN] Would remove worktree: {path}")
```

**Usage**: Wrapped around real implementations when `--dry-run` flag is used.

---

## Command-Specific Terms

### Plan Folder

A `.impl/` folder containing implementation plans and progress tracking for a feature.

**Usage**: `erk create --from-plan-file my-plan.md my-feature`

**Behavior**:

- Plan file is converted to `.impl/` folder structure in the new worktree
- Contains two files:
  - `plan.md` - Immutable implementation plan
  - `progress.md` - Mutable progress tracking with checkboxes
- `.impl/` is gitignored (not committed)
- Useful for keeping implementation notes with the working code

**Benefits**:

- Separation of concerns: plan content vs progress tracking
- No risk of corrupting plan while updating progress
- Progress visible in `erk status` output

**Example**:

```bash
# Create plan
echo "## Implementation Plan\n1. Step 1\n2. Step 2" > plan.md

# Create worktree from plan file
erk create --from-plan-file plan.md my-feature

# Plan structure created:
# ~/erks/erk/my-feature/.impl/
#   ├── plan.md        (immutable)
#   └── progress.md    (mutable, with checkboxes)
```

**Legacy Format**: Old worktrees may still use `.PLAN.md` single-file format. These will continue to work but won't show progress tracking.

### Dry Run

Mode where commands print what they would do without executing destructive operations.

**Activation**: `--dry-run` flag on commands

**Behavior**:

- Read-only operations execute normally
- Destructive operations print messages prefixed with `[DRY RUN]`

**Example**:

```bash
erk delete my-feature --dry-run
# Output: [DRY RUN] Would delete worktree: /Users/you/worktrees/erk/my-feature
```

---

## Documentation System

### Front Matter

YAML metadata block at the beginning of agent documentation files.

**Required fields**:

- `title`: Human-readable document title
- `read_when`: List of conditions when agents should read this doc

**Optional fields**:

- `tripwires`: List of action-triggered warnings

**Example**:

```yaml
---
title: Scratch Storage
read_when:
  - "writing temp files for AI workflows"
tripwires:
  - action: "writing to /tmp/"
    warning: "Use .erk/scratch/<session-id>/ instead."
---
```

### read_when

A front matter field listing conditions that trigger documentation routing.

**Purpose**: Powers the agent documentation index. When an agent's task matches a `read_when` condition, the index routes them to the relevant doc.

**Distinction from tripwires**:

- `read_when` = Agent actively searches for guidance (pull model)
- `tripwires` = Agent is about to perform action (push model)

**Example**:

```yaml
read_when:
  - "creating a plan"
  - "closing a plan"
```

### Tripwire

An action-triggered rule that routes agents to documentation when specific behavior patterns are detected.

**Format**: Defined in doc frontmatter with `action` (pattern to detect) and `warning` (guidance message).

**Purpose**: Catches agents _before_ they make mistakes, complementing the `read_when` index which requires agents to actively seek guidance.

**Example**:

```yaml
tripwires:
  - action: "writing to /tmp/"
    warning: "AI workflow files belong in .erk/scratch/<session-id>/, NOT /tmp/."
```

**See also**: [Tripwires System](commands/tripwires.md)

---

## Testing Terms

### Isolated Filesystem

A temporary directory created by Click's test runner for unit tests.

**Usage**:

```python
runner = CliRunner()
with runner.isolated_filesystem():
    # Operations here happen in temporary directory
    # Automatically cleaned up after test
```

**Purpose**: Prevent tests from affecting actual filesystem.

### Integration Test

Test that uses real implementations and filesystem operations.

**Location**: `tests/integration/`

**Characteristics**:

- Uses `RealGit`, actual git commands
- Slower than unit tests
- Tests real integration with external tools

**Example**: `tests/integration/test_git_integration.py`

### Unit Test

Test that uses fake implementations and isolated filesystem.

**Location**: `tests/commands/`, `tests/core/`

**Characteristics**:

- Uses `FakeGit`, `FakeGitHub`, etc.
- Fast (no subprocess calls)
- Majority of test suite

**Example**: `tests/commands/test_rm.py`

---

## Plan & Extraction Concepts

### Extraction Plan

A special type of implementation plan created by `/erk:create-extraction-plan`. Extraction plans capture documentation improvements and learnings discovered during implementation sessions.

**Characteristics**:

- Created from session analysis to capture valuable insights
- Contains documentation items rather than code changes
- Marked with `plan_type: extraction` in the plan-header metadata
- PRs from extraction plans receive the `erk-skip-extraction` label

**Purpose**: Prevent valuable learnings from being lost after implementation sessions by systematically documenting patterns, decisions, and discoveries.

**Related**: [erk-skip-extraction](#erk-skip-extraction), [Plan Lifecycle](planning/lifecycle.md)

### erk-skip-extraction

A GitHub label added to PRs that originate from extraction plans. When `erk pr land` detects this label, it automatically skips creating the pending-extraction marker and deletes the worktree immediately.

**Purpose**: Prevents infinite extraction loops where extracting insights from an extraction-originated PR would lead to another extraction plan.

**Applied by**:

- `erk plan submit` when the source issue has `plan_type: extraction`
- `gt finalize` when the `.impl/plan.md` has `plan_type: extraction`

**Checked by**:

- `erk pr land` - Skips insight extraction if label present

**Design Decision**: Labels are used instead of PR body markers because:

1. **Visibility** - Labels are visible in GitHub UI, making extraction PRs easy to identify
2. **Simplicity** - Label checks are simpler than parsing PR body content
3. **Separation** - PR body remains focused on the actual PR description
4. **Flexibility** - Labels can be manually added/removed for edge cases

**Related**: [Extraction Plan](#extraction-plan), [pending-extraction](#pending-extraction), [Extraction Origin Tracking](architecture/extraction-origin-tracking.md)

### pending-extraction

A marker state indicating a merged PR is queued for insight extraction. When `erk pr land` completes successfully (and the PR is not from an extraction plan), it leaves the worktree in a "pending extraction" state for later session analysis.

**Purpose**: Queue merged PRs for documentation extraction to capture learnings.

**Lifecycle**:

1. PR merges via `erk pr land`
2. If not extraction-originated → worktree marked as pending-extraction
3. User runs extraction workflow later to capture insights
4. Worktree deleted after extraction complete

**Skip condition**: PRs with `erk-skip-extraction` label bypass this marking.

**Related**: [erk-skip-extraction](#erk-skip-extraction), [Extraction Plan](#extraction-plan)

---

## Abbreviations

- **ABC**: Abstract Base Class (Python's `abc` module)
- **CLI**: Command Line Interface
- **DI**: Dependency Injection
- **EAFP**: Easier to Ask for Forgiveness than Permission (exception-based error handling)
- **LBYL**: Look Before You Leap (check-before-operation error handling)
- **PR**: Pull Request (GitHub)
- **TOML**: Tom's Obvious Minimal Language (configuration file format)

---

## Streaming & Execution Terms

### Bypass PR Commands (Historical)

A set of now-removed commands (`pr-prep`, `pr-update`, `prepare-local`) that allowed preparing PR branches locally without GitHub CLI. Removed in favor of the streamlined `gt` workflow.

### Streaming Subprocess

An execution pattern where subprocess output is streamed to the UI in real-time via background threads and cross-thread callbacks.

**Key components**:

- Background thread reads subprocess stdout
- `app.call_from_thread()` safely updates UI from background thread
- Event queue buffers parsed output

**Related**: [TUI Streaming Output Patterns](tui/streaming-output.md)

### Capability Marker

A parameter (like `repo_root`) whose presence/absence determines which execution path or feature set is available. Used to gracefully degrade functionality.

**Example**: `PlanDetailScreen` uses `repo_root` to decide whether streaming execution is available or commands are disabled.

**Related**: [Command Execution Strategies](tui/command-execution.md)

---

## Objectives System

The objectives system enables incremental, bounded progress toward long-running goals. Objectives act as "plan factories" - they generate focused implementation plans rather than being implemented directly.

### Objective

A long-running goal that produces bounded plans when evaluated against the codebase.

**Purpose**: Break large, complex goals into reviewable, implementable chunks. Instead of tackling "migrate all errors to Ensure class" in one massive PR, an objective evaluates the codebase, identifies a manageable subset of violations, and creates a plan for that subset.

**Storage**: `.erk/objectives/<name>/`

### Turn

A single evaluation cycle where Claude assesses current state against the objective's desired state.

**Output**: Either `STATUS: COMPLETE` (objective fully achieved) or `STATUS: GAPS_FOUND` (work remaining).

**Mechanism**:

1. Claude receives objective definition + accumulated notes + codebase access
2. Evaluates current state vs desired state
3. Reports status with optional gap description
4. If gaps found, creates bounded implementation plan

**CLI**: `erk objective turn <objective-name>`

### ObjectiveType

Discriminator for objective behavior:

| Type          | Description                       | Example                        |
| ------------- | --------------------------------- | ------------------------------ |
| `COMPLETABLE` | Finite end state exists           | "Migrate all errors to Ensure" |
| `PERPETUAL`   | Ongoing guard, never fully "done" | "No direct time.sleep() calls" |

**Impact**: `COMPLETABLE` objectives can report `STATUS: COMPLETE`. `PERPETUAL` objectives always find gaps or report nothing to do in this turn.

### ObjectiveDefinition

A frozen dataclass containing the static configuration for an objective.

**Location**: `.erk/objectives/<name>/definition.yaml`

**Fields**:

| Field                | Purpose                                       |
| -------------------- | --------------------------------------------- |
| `name`               | Unique identifier (kebab-case)                |
| `objective_type`     | COMPLETABLE or PERPETUAL                      |
| `desired_state`      | What "done" looks like                        |
| `rationale`          | Why this objective matters                    |
| `examples`           | Before/after patterns showing desired changes |
| `scope_includes`     | Directories/patterns to examine               |
| `scope_excludes`     | Directories/patterns to skip                  |
| `evaluation_prompt`  | Instructions for assessing gaps               |
| `plan_sizing_prompt` | Guidelines for bounding plan size             |

**File**: `packages/erk-shared/src/erk_shared/objectives/types.py`

### ObjectiveNotes

Accumulated knowledge from previous turns. Notes persist across future turns, building institutional memory about edge cases, patterns, and decisions.

**Location**: `.erk/objectives/<name>/notes.yaml`

**Entry fields**:

- `timestamp`: ISO 8601 format
- `content`: The insight or observation
- `source_turn`: Optional reference to generating turn

**Purpose**: Prevent rediscovering the same insights. If a previous turn learned "files in vendor/ should be excluded", that knowledge persists.

### TurnResult

A frozen dataclass capturing the outcome of running a turn.

**Fields**:

| Field               | Type          | Description                   |
| ------------------- | ------------- | ----------------------------- |
| `objective_name`    | `str`         | Which objective was evaluated |
| `gap_found`         | `bool`        | Whether work remains          |
| `gap_description`   | `str \| None` | Human-readable gap summary    |
| `plan_issue_number` | `int \| None` | GitHub issue created for plan |
| `plan_issue_url`    | `str \| None` | URL to the created issue      |
| `timestamp`         | `str`         | ISO 8601 format               |

**File**: `packages/erk-shared/src/erk_shared/objectives/types.py`

### Key Files

| Concern | Location                                                   |
| ------- | ---------------------------------------------------------- |
| Types   | `packages/erk-shared/src/erk_shared/objectives/types.py`   |
| Turn    | `packages/erk-shared/src/erk_shared/objectives/turn.py`    |
| Storage | `packages/erk-shared/src/erk_shared/objectives/storage.py` |
| CLI     | `src/erk/cli/commands/objective/`                          |

---

## Related Documentation

- [AGENTS.md](../../AGENTS.md) - Coding standards
