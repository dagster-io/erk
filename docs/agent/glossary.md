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

---

## Git & Graphite Concepts

**For comprehensive gt documentation**: See [tools/gt.md](tools/gt.md)

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

---

## Architecture Terms

### Repo Context

A frozen dataclass containing repository information.

**Definition**:

```python
@dataclass(frozen=True)
class RepoContext:
    root: Path        # Repo root directory
    repo_name: str    # Repository name
    erks_dir: Path    # Erks directory for this repo
```

**Creation**: `discover_repo_context(ctx, Path.cwd())`

**File**: `src/erk/cli/core.py`

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

## Abbreviations

- **ABC**: Abstract Base Class (Python's `abc` module)
- **CLI**: Command Line Interface
- **DI**: Dependency Injection
- **EAFP**: Easier to Ask for Forgiveness than Permission (exception-based error handling)
- **LBYL**: Look Before You Leap (check-before-operation error handling)
- **PR**: Pull Request (GitHub)
- **TOML**: Tom's Obvious Minimal Language (configuration file format)

---

## Related Documentation

- [AGENTS.md](../../AGENTS.md) - Coding standards
