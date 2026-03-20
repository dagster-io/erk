---
title: Remote Paths Testing
read_when:
  - "testing commands that use RemoteGitHub"
  - "testing commands with --repo flag (remote mode)"
  - "writing tests for launch command workflows"
  - "testing without local git context"
tripwires:
  - action: "constructing RealRemoteGitHub in tests"
    warning: "Use FakeRemoteGitHub injected via context_for_test(remote_github=...). Never instantiate RealRemoteGitHub in tests. See remote-paths-testing.md."
---

# Remote Paths Testing

Tests for commands using `RemoteGitHub` (the `--repo` flag remote mode) follow a consistent injection pattern.

## Core Pattern

```python
from tests.fakes.gateway.remote_github import FakeRemoteGitHub
from tests.test_utils.test_context import context_for_test
from erk_shared.context.types import NoRepoSentinel

def _build_remote_context(fake_remote: FakeRemoteGitHub):
    return context_for_test(
        repo=NoRepoSentinel(),      # No local git
        remote_github=fake_remote,  # Injected via ctx.remote_github
    )
```

`get_remote_github(ctx)` checks `ctx.remote_github is not None` first, so `FakeRemoteGitHub` is used instead of `RealRemoteGitHub`.

## `FakeRemoteGitHub` Construction

```python
FakeRemoteGitHub(
    authenticated_user="test-user",
    default_branch_name="main",
    default_branch_sha="abc123",
    next_pr_number=1,
    dispatch_run_id="run-123",
    issues=None,
    issue_comments=None,
    prs=prs,  # dict[int, RemotePRInfo] | None
)
```

## `RemotePRInfo` Construction

```python
from erk_shared.gateway.remote_github.types import RemotePRInfo

RemotePRInfo(
    number=123,
    title="Test PR",
    state="OPEN",  # "OPEN", "CLOSED", or "MERGED"
    url="https://github.com/owner/repo/pull/123",
    head_ref_name="feature-branch",
    base_ref_name="main",
    owner="owner",
    repo="repo",
    labels=[],  # list[str], never None
)
```

## Verifying Dispatch Calls

```python
assert len(fake_remote.dispatched_workflows) == 1
dispatched = fake_remote.dispatched_workflows[0]
assert dispatched.workflow == WORKFLOW_COMMAND_MAP["pr-rebase"]
assert dispatched.inputs["branch_name"] == "feature-branch"
assert dispatched.inputs["pr_number"] == "123"
assert dispatched.ref == "main"  # default branch when no --ref
```

## Test File Locations

- **launch command remote paths**: `tests/commands/launch/test_launch_remote_paths.py`
- **objective plan remote paths**: `tests/commands/objective/test_plan_remote_paths.py`

## Common Test Scenarios

| Scenario               | Setup                                                                                        |
| ---------------------- | -------------------------------------------------------------------------------------------- |
| Valid dispatch         | `prs={123: RemotePRInfo(..., state="OPEN")}`                                                 |
| PR not found           | `prs={}` or `prs={}` (empty dict)                                                            |
| Closed PR rejected     | `RemotePRInfo(..., state="CLOSED")`                                                          |
| Custom ref             | `runner.invoke(..., ["--ref", "custom-ref"])`                                                |
| Default ref uses API   | No `--ref`; assert `dispatched.ref == "main"`                                                |
| Model threaded through | `runner.invoke(..., ["--model", "claude-opus-4"])`; assert `dispatched.inputs["model_name"]` |

## Isolated Filesystem Tests

For tests that need filesystem state (e.g., `--file` flag):

```python
def test_one_shot_with_file(tmp_path: Path) -> None:
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("fix the bug", encoding="utf-8")
    # ...invoke with ["-f", str(prompt_file)]
```

For exec script tests that need repo context, use `erk_isolated_fs_env()`:

```python
from tests.test_utils.isolated_fs import erk_isolated_fs_env

with erk_isolated_fs_env() as env:
    ctx = env.build_context()
    # ctx is a fully initialized ErkContext with fake gateways
```

## Related Documentation

- [Repo Resolution Pattern](../cli/repo-resolution-pattern.md) — `get_remote_github(ctx)` factory
- [RemoteGitHub Gateway](../architecture/remote-github-gateway.md) — gateway methods and types
