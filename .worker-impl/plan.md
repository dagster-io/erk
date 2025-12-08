# Documentation Extraction Plan

## Objective

Add documentation for kit CLI scratch path patterns and testing patterns discovered during scratch directory path fix implementation.

## Source Information

- **Session ID**: 2e249419-b147-4869-bda2-63f9f54044cd
- **Context**: Fix for scratch directory path issues in dot-agent-kit (#2657)

## Documentation Items

### Item 1: Kit CLI Scratch Path Patterns (Category A - Learning Gap)

**Type**: Category A (Learning Gap)
**Location**: docs/agent/kits/dependency-injection.md (update)
**Action**: Add section on scratch storage access
**Priority**: Medium

**Rationale**: Kit CLI commands in `dot-agent-kit` run outside the main `erk` context and cannot access `ErkContext`. When they need scratch storage, they must:
1. Import directly from `erk_shared.scratch.scratch` (not `erk_shared.scratch`)
2. Resolve repo root via `git rev-parse --show-toplevel`
3. Use `get_scratch_dir(session_id, repo_root=repo_root)` for session-scoped paths

**Draft Content**:

```markdown
## Scratch Storage in Kit CLI Commands

Kit CLI commands cannot access `ErkContext`, so they need explicit scratch storage handling.

### Correct Pattern

```python
import subprocess
from pathlib import Path
from erk_shared.scratch.scratch import get_scratch_dir

def _get_repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())

# Session-scoped files: .erk/scratch/sessions/<session_id>/
scratch_dir = get_scratch_dir(session_id, repo_root=_get_repo_root())

# Worktree-scoped files: .erk/scratch/
repo_root = _get_repo_root()
worktree_file = repo_root / ".erk" / "scratch" / "current-session-id"
```

### Common Mistakes

```python
# WRONG: Relative path writes to cwd, not repo root
Path(".erk/scratch/current-session-id")

# WRONG: Missing sessions/ segment
repo_root / ".erk" / "scratch" / session_id

# RIGHT: Session-scoped with sessions/ segment
repo_root / ".erk" / "scratch" / "sessions" / session_id
```
```

### Item 2: DotAgentContext.for_test() repo_root Parameter (Category A - Learning Gap)

**Type**: Category A (Learning Gap)
**Location**: packages/dot-agent-kit/docs/GLOSSARY.md or testing docs (update)
**Action**: Document repo_root parameter requirement
**Priority**: Low

**Rationale**: Tests that use `DotAgentContext.for_test()` and trigger scratch file creation will fail with `OSError(30, 'Read-only file system')` if they don't provide `repo_root=tmp_path`. The default `repo_root=Path("/fake/repo")` is on a read-only filesystem.

**Draft Content**:

```markdown
## Testing with Scratch Storage

When testing kit CLI commands that create scratch files, always provide a writable `repo_root`:

```python
result = runner.invoke(
    my_command,
    obj=DotAgentContext.for_test(
        github_issues=fake_gh,
        git=fake_git,
        session_store=fake_store,
        cwd=tmp_path,
        repo_root=tmp_path,  # Required for scratch file creation
    ),
)
```

Without `repo_root=tmp_path`, the default `/fake/repo` path causes read-only filesystem errors.
```