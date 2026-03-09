---
title: Remote Paths Testing
read_when:
  - "testing commands with --repo flag"
  - "writing tests for remote-mode CLI commands"
  - "using NoRepoSentinel or FakeRemoteGitHub in tests"
tripwires:
  - action: "testing a --repo command by mocking subprocess calls to gh CLI"
    warning: "Remote mode uses RemoteGitHub (REST API), not gh CLI. Use FakeRemoteGitHub in tests. See remote-paths-testing.md."
  - action: "setting up a full git repo fixture to test --repo flag"
    warning: "Remote-mode tests should use NoRepoSentinel() — no local repo needed. See remote-paths-testing.md."
---

# Remote Paths Testing

Patterns for testing CLI commands that operate via `--repo` flag without a local git repository.

## Core Pattern

```python
from erk.core.context import context_for_test
from erk_shared.context.types import NoRepoSentinel
from erk_shared.gateway.remote_github.fake import FakeRemoteGitHub
from erk_shared.gateway.remote_github.types import RemotePRInfo

# 1. Create FakeRemoteGitHub with test data
fake_remote = FakeRemoteGitHub(
    authenticated_user="test-user",
    default_branch_name="main",
    default_branch_sha="abc123",
    next_pr_number=1,
    dispatch_run_id="run-123",
    issues=None,
    issue_comments=None,
    pr_references=None,
    prs={123: RemotePRInfo(
        number=123,
        title="Test PR",
        state="OPEN",
        url="https://github.com/owner/repo/pull/123",
        head_ref_name="feature-branch",
        base_ref_name="main",
        owner="owner",
        repo="repo",
        labels=[],
    )},
)

# 2. Build context with NoRepoSentinel (no local repo)
ctx = context_for_test(
    repo=NoRepoSentinel(),
    remote_github=fake_remote,
)

# 3. Invoke command with --repo flag
runner = CliRunner()
result = runner.invoke(cli, ["launch", "pr-rebase", "--pr", "123", "--repo", "owner/repo"], obj=ctx)
```

## Key Components

### `NoRepoSentinel`

Signals that no local git repository is available. Commands check `isinstance(ctx.repo, NoRepoSentinel)` to determine local vs remote mode.

### `FakeRemoteGitHub`

In-memory implementation of the `RemoteGitHub` ABC. Configure with:

- `authenticated_user`: Username returned by `get_authenticated_user()`
- `default_branch_name`/`default_branch_sha`: Repository defaults
- `prs`: Dict of `{pr_number: RemotePRInfo}` for `get_pr()` lookups
- `issues`: Dict of `{issue_number: IssueInfo}` for `get_issue()` lookups
- `dispatch_run_id`: Run ID returned by `dispatch_workflow()`

### `RemotePRInfo`

Frozen dataclass with PR fields from the REST API:

- `number`, `title`, `state` (`"OPEN"`, `"CLOSED"`, `"MERGED"`)
- `url`, `head_ref_name`, `base_ref_name`
- `owner`, `repo`, `labels`

## Reference Implementations

- `tests/commands/launch/test_launch_remote_paths.py` — launch command remote tests
- `tests/commands/objective/test_plan_remote_paths.py` — objective plan remote tests

## Related Documentation

- [Repo Resolution Pattern](../cli/repo-resolution-pattern.md) — the shared --repo infrastructure being tested
- [RemoteGitHub Gateway](../architecture/remote-github-gateway.md) — ABC and real/fake implementations
