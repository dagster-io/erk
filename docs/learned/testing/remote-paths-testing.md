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

<!-- Source: tests/commands/launch/test_launch_remote_paths.py, _build_remote_context -->

To set up a test context for remote paths, use `context_for_test()` with `NoRepoSentinel()` for local repo (indicating no git context) and pass the `FakeRemoteGitHub` instance via the `remote_github` parameter. See `_build_remote_context()` in tests/commands/launch/test_launch_remote_paths.py.

`get_remote_github(ctx)` checks `ctx.remote_github is not None` first, so `FakeRemoteGitHub` is used instead of `RealRemoteGitHub`.

## `FakeRemoteGitHub` Construction

<!-- Source: tests/fakes/gateway/remote_github.py, FakeRemoteGitHub -->

See `FakeRemoteGitHub` constructor in tests/fakes/gateway/remote_github.py. Key parameters: `authenticated_user` (username string), `default_branch_name` (branch name), `default_branch_sha` (commit SHA), `next_pr_number` (initial PR counter), `dispatch_run_id` (workflow run ID), and `prs` (dict mapping PR numbers to `RemotePRInfo` instances, or None for empty PRs).

## `RemotePRInfo` Construction

<!-- Source: packages/erk-shared/src/erk_shared/gateway/remote_github/types.py, RemotePRInfo -->

See `RemotePRInfo` in packages/erk-shared/src/erk_shared/gateway/remote_github/types.py. For detailed field descriptions and the RemoteGitHub gateway API, see [RemoteGitHub Gateway](../architecture/remote-github-gateway.md).

## Verifying Dispatch Calls

<!-- Source: tests/commands/launch/test_launch_remote_paths.py -->

See dispatch assertion patterns in tests/commands/launch/test_launch_remote_paths.py. Common assertions check `fake_remote.dispatched_workflows` list length, workflow type via `WORKFLOW_COMMAND_MAP`, input parameters (`inputs["branch_name"]`, `inputs["pr_number"]`), and the dispatched ref (defaults to `default_branch_name`).

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
