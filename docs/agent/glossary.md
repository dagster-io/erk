---
title: Erk Glossary
read_when:
  - "understanding project terminology"
  - "confused about domain-specific terms"
  - "working with worktrees, plans, or stacks"
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

Erk branches follow the pattern `{issue_number}-{slug}-{timestamp}`:

- `{issue_number}` - GitHub issue number (extracted by `extract_leading_issue_number()`)
- `{slug}` - Kebab-case description of the work
- `{timestamp}` - Creation timestamp in `MM-DD-HHMM` format

**Examples**:

- `2382-convert-erk-create-raw-ext-12-05-2359`
- `123-fix-auth-bug-01-15-1430`

**Automatic extraction**: `get_branch_issue()` uses this pattern to determine which GitHub issue a branch relates to, without requiring git config setup.

### Project

A subdirectory within a git repository that has its own erk configuration context.

**Identification**: Contains `.erk/project.toml` file

**Purpose**: Enables monorepo support where different subdirectories can have their own:

- Environment variables
- Post-create commands
- Claude Code context (via `.claude/` directory in project)

**Example structure**:

```
repo-root/
├── .erk/config.toml              ← Repo-level config
├── python_modules/
│   └── my-project/
│       ├── .erk/project.toml     ← Project config (identifies this as a project)
│       └── .claude/CLAUDE.md     ← Project-specific Claude context
```

**Discovery**: `discover_project(cwd, repo_root)` walks up from current directory looking for `.erk/project.toml`

**File**: `src/erk/core/project_discovery.py`

### Project Context

A frozen dataclass containing project information.

**Definition**:

```python
@dataclass(frozen=True)
class ProjectContext:
    root: Path          # Absolute path to project directory
    name: str           # Project name (defaults to directory name)
    path_from_repo: Path  # Relative path from repo root
```

**Creation**: `discover_project(cwd, repo_root)`

**File**: `src/erk/core/project_discovery.py`

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

**Graphite terminology**: The "trunk" of the stack tree - the base from which all feature branches grow.

**Detection**: `git symbolic-ref refs/remotes/origin/HEAD`

### Stack

**Graphite concept**: A linear chain of dependent branches.

**Example**:

```
main (trunk)
  └─> feature-a (adds user model)
       └─> feature-a-2 (adds user controller)
            └─> feature-a-3 (adds user views)
```

**Purpose**: Break large features into reviewable chunks while maintaining dependencies.

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

### Project Config

Configuration stored in `{project_root}/.erk/project.toml`.

**Scope**: Applies to worktrees created from this project directory.

**Location**: `{repo_root}/{project_path}/.erk/project.toml`

**Contents**:

```toml
# Optional: custom name (defaults to directory name)
# name = "dagster-open-platform"

[env]
# Project-specific env vars (merged with repo-level)
DAGSTER_HOME = "{project_root}"

[post_create]
# Runs AFTER repo-level commands, FROM project directory
shell = "bash"
commands = [
  "source .venv/bin/activate",
]
```

**Merge Rules** (when both repo and project config exist):

| Field                  | Merge Behavior                                 |
| ---------------------- | ---------------------------------------------- |
| `env`                  | Project values override repo values            |
| `post_create.commands` | Repo commands run first, then project commands |
| `post_create.shell`    | Project shell overrides repo shell if set      |

**File**: `src/erk/cli/config.py`

---

## Architecture Terms

### Repo Context

A frozen dataclass containing repository information.

**Definition**:

```python
@dataclass(frozen=True)
class RepoContext:
    root: Path            # Working tree root for git commands
    main_repo_root: Path  # Main repository root (consistent across worktrees)
    repo_name: str        # Repository name
    erks_dir: Path        # Erks directory for this repo
```

**Creation**: `discover_repo_context(ctx, Path.cwd())`

**File**: `src/erk/cli/core.py`

#### root vs main_repo_root

- **`root`**: The working tree root where git commands should run. For worktrees, this is the worktree directory. For main repos, equals `main_repo_root`.

- **`main_repo_root`**: The main repository root (consistent across all worktrees). Used for:
  - Deriving `repo_name` for metadata paths
  - Operations that need the root worktree (e.g., escaping from a worktree being deleted)
  - Resolving "root" as a target in commands like `stack move root`

**Key insight:** When running from a worktree, git commands use `root` (the worktree), but metadata and escaping use `main_repo_root` (the main repo).

### Erk Context

A frozen dataclass containing all injected dependencies.

**Definition**:

```python
@dataclass(frozen=True)
class ErkContext:
    git: Git
    config_store: ConfigStore
    github: GitHub
    graphite: Graphite
    shell: Shell
    completion: Completion
    script_writer: ScriptWriter
    dry_run: bool
```

**Purpose**: Dependency injection container passed to all commands.

**Creation**: `create_context(dry_run=False)` in `src/erk/core/context.py`

**Usage**: Commands receive via `@click.pass_obj` decorator.

**File**: `src/erk/core/context.py`

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

---

## Event Types

### ProgressEvent

A frozen dataclass for emitting progress notifications during long-running operations.

**Location**: `packages/erk-shared/src/erk_shared/integrations/gt/events.py`

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

**Location**: `packages/erk-shared/src/erk_shared/integrations/gt/events.py`

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

## Integration Layer Terms

### Integration Class

An ABC (Abstract Base Class) defining integration classes for external systems.

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

### Real Implementation

Production implementation of an integration interface that executes actual commands.

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

In-memory implementation of an integration interface for testing.

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

**Usage**: `erk create --from-plan my-plan.md my-feature`

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

# Create worktree from plan
erk create --from-plan plan.md my-feature

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

- `erk submit` when the source issue has `plan_type: extraction`
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

## Kit Concepts

### Kit CLI Command

A Python Click command registered in a kit's `kit.yaml` and invoked via `dot-agent run <kit-name> <command>`.

**Location**: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/<kit-name>/kit_cli_commands/<kit-name>/`

**Example**:

```bash
dot-agent run erk check-impl --dry-run
```

**See also**: [Kit CLI Command Development](kits/cli-command-development.md)

---

## Kit Maintenance

### Kit Consolidation

When merging multiple kits into a unified kit:

**Checklist**:

1. ✅ Create unified `data/kits/{new-kit}/kit.yaml` with all artifacts
2. ✅ Update `data/registry.yaml` - replace old entries with single new entry
3. ✅ Delete orphaned kit directories (old kit dirs without kit.yaml)
4. ✅ Verify: `dot-agent kit search` shows new unified kit
5. ✅ Verify: All skills from old kits are loadable from new kit

**Common failure mode**: Forgetting to update `registry.yaml` after consolidation causes old kit IDs to fail resolution (no `kit.yaml` in expected location).

---

## Streaming & Execution Terms

### Bypass PR Commands (Historical)

A set of now-removed commands (`pr-prep`, `pr-update`, `prepare-local`) that allowed preparing PR branches locally without GitHub CLI. Removed in favor of the streamlined `gt` workflow.

### Kit Artifact

A file (command, tool, etc.) bundled within a kit. Must be declared in the kit manifest to pass synchronization validation.

**Validation**: Kit sync tests verify every manifest entry has a corresponding file and vice versa.

**Related**: [Kit Artifact Synchronization](kits/artifact-synchronization.md)

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

## Related Documentation

- [AGENTS.md](../../AGENTS.md) - Coding standards
