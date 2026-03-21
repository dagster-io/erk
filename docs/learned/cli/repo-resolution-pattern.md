---
title: Repo Resolution Pattern
read_when:
  - "adding --repo support to a CLI command"
  - "resolving owner/repo from local git context"
  - "constructing RemoteGitHub for a command"
  - "using resolved_repo_option decorator"
tripwires:
  - action: "manually parsing --repo owner/repo in a command handler"
    warning: "Use resolved_repo_option decorator instead. It handles parsing, validation, and injection of GitHubRepoId. See repo-resolution-pattern.md."
  - action: "constructing RealRemoteGitHub directly in a command"
    warning: "Use get_remote_github(ctx) instead. It handles test injection via ctx.remote_github and falls back to RealRemoteGitHub. See repo-resolution-pattern.md."
---

# Repo Resolution Pattern

`src/erk/cli/repo_resolution.py` provides shared infrastructure for resolving owner/repo from either a `--repo` flag or local git context.

## Functions

### `resolve_owner_repo(ctx, *, target_repo) -> tuple[str, str]`

Resolves owner and repo name from:

1. `target_repo` string (from `--repo owner/repo` flag) — validated to contain exactly one `/`
2. `ctx.repo.github` when available (local git context)

Raises `UserFacingCliError` if format is invalid or neither source is available.

### `get_remote_github(ctx) -> RemoteGitHub`

Factory for `RemoteGitHub` instances with test injection support:

1. If `ctx.remote_github is not None` — returns it directly (test injection path)
2. If `ctx.http_client is not None` — constructs `RealRemoteGitHub(http_client=ctx.http_client, time=ctx.time)`
3. Otherwise — raises `UserFacingCliError` with authentication guidance

Tests inject `FakeRemoteGitHub` via `context_for_test(remote_github=FakeRemoteGitHub(...))`.

### `repo_option`

Click option: `--repo owner/repo` with `target_repo` parameter name. Adds `--repo` flag to a command without resolving it.

### `resolved_repo_option` decorator

Wraps a Click command handler to:

1. Add `--repo` flag via `@repo_option`
2. Call `resolve_owner_repo(ctx, target_repo=target_repo)` before the handler
3. Inject `repo_id: GitHubRepoId` into the handler (replacing `target_repo`)

```python
@click.command("launch")
@resolved_repo_option
@click.pass_obj
def launch(ctx: ErkContext, *, repo_id: GitHubRepoId, ...) -> None:
    ...
```

## Usage Example

```python
from erk.cli.repo_resolution import get_remote_github, resolved_repo_option

@click.command("my-cmd")
@resolved_repo_option
@click.pass_obj
def my_cmd(ctx: ErkContext, *, repo_id: GitHubRepoId) -> None:
    remote = get_remote_github(ctx)
    # remote is FakeRemoteGitHub in tests, RealRemoteGitHub in production
    result = remote.get_pr(owner=repo_id.owner, repo=repo_id.repo, number=123)
```

## Related Documentation

- [RemoteGitHub Gateway](../architecture/remote-github-gateway.md) — gateway methods available
- [Remote Paths Testing](../testing/remote-paths-testing.md) — test injection patterns
