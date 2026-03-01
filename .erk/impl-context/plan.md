# Plan: Refactor download_remote_session.py to use read_file_from_ref gateway

**Part of Objective #7813, Node 3.1**: Add read_file_from_ref() to git gateway ABC and implementations

## Context

Objective #7813 eliminates unnecessary git checkouts by converting direct subprocess calls to gateway plumbing methods. The `read_file_from_ref()` method already exists in the gateway ABC and all 4 implementations (real, fake, dry-run, printing). Three callers (`fetch_sessions.py`, `push_session.py`, `get_learn_sessions.py`) already use it.

One caller remains with a direct `subprocess.run(["git", "show", ...])` call: `download_remote_session.py`. This plan converts it to use the gateway, completing node 3.1.

## Changes

### 1. Refactor `_download_from_branch` in download_remote_session.py

**File:** `src/erk/cli/commands/exec/scripts/download_remote_session.py`

Replace the direct subprocess call (lines 78-86) with the gateway method:

```python
# Before (direct subprocess):
result = subprocess.run(
    ["git", "show", f"origin/{session_branch}:.erk/session/{session_id}.jsonl"],
    cwd=str(repo_root),
    capture_output=True,
)
if result.returncode != 0:
    return f"Failed to extract session from branch: {result.stderr.decode().strip()}"
session_file.write_bytes(result.stdout)

# After (gateway):
content = git.commit.read_file_from_ref(
    repo_root,
    ref=f"origin/{session_branch}",
    file_path=f".erk/session/{session_id}.jsonl",
)
if content is None:
    return "Failed to extract session from branch: file not found at ref"
session_file.write_bytes(content)
```

Also remove the now-unused `import subprocess` from the file.

### 2. Update tests to use FakeGit's `ref_file_contents`

**File:** `tests/unit/cli/commands/exec/scripts/test_download_remote_session.py`

The existing test `test_error_download_fails_when_branch_not_found` currently relies on subprocess `git show` failing because `tmp_path` is not a git repo. After the refactoring, the gateway returns `None` when no content is configured. The test's assertion (`exit_code == 1`, error message contains "Failed to extract session from branch"`) will still pass since `read_file_from_ref` returns `None` for unconfigured refs in the fake. Verify the test still passes and update the error message assertion if needed.

Add a new **success test** using `ref_file_contents`:

```python
def test_success_downloads_session_from_branch(tmp_path: Path) -> None:
    """Test successful session download via gateway."""
    session_content = b'{"type":"message","role":"user"}\n'
    fake_git = FakeGit(
        current_branches={tmp_path: "main"},
        ref_file_contents={
            ("origin/async-learn/42", ".erk/session/test-session-123.jsonl"): session_content,
        },
    )

    exit_code, output = _execute_download(
        repo_root=tmp_path,
        session_branch="async-learn/42",
        session_id="test-session-123",
        git=fake_git,
    )

    assert exit_code == 0
    assert output["success"] is True
    assert output["source"] == "branch"
    session_file = Path(output["path"])
    assert session_file.read_bytes() == session_content
```

## Files to modify

| File | Change |
|------|--------|
| `src/erk/cli/commands/exec/scripts/download_remote_session.py` | Replace subprocess with gateway call, remove subprocess import |
| `tests/unit/cli/commands/exec/scripts/test_download_remote_session.py` | Add success test, verify error test still passes |

## Verification

1. Run unit tests: `uv run pytest tests/unit/cli/commands/exec/scripts/test_download_remote_session.py -v`
2. Run type checker: `uv run ty check src/erk/cli/commands/exec/scripts/download_remote_session.py`
3. Verify no remaining direct `subprocess` usage in the file
4. Run broader test suite for regressions: `uv run pytest tests/unit/cli/commands/exec/scripts/ -v`
