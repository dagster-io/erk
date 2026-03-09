---
title: Repo Resolution Pattern
read_when:
  - "adding --repo flag to a CLI command"
  - "working with resolve_owner_repo"
  - "creating a command that operates on remote repositories"
  - "testing commands with NoRepoSentinel"
tripwires:
  - action: "adding --repo option manually to a Click command"
    warning: "Use @repo_option or @resolved_repo_option decorator from repo_resolution.py. Do NOT add --repo manually."
  - action: "parsing owner/repo string in a CLI command"
    warning: "Use resolve_owner_repo() from repo_resolution.py. It handles validation and local git fallback."
  - action: "constructing RemoteGitHub directly in a command"
    warning: "Use get_remote_github(ctx) from repo_resolution.py. It handles test injection of FakeRemoteGitHub."
---

# Repo Resolution Pattern

Shared infrastructure for CLI commands that optionally operate on remote repositories via `--repo owner/name`.

## Source

`src/erk/cli/repo_resolution.py`

## Components

### `resolve_owner_repo(ctx, *, target_repo)`

Resolves owner/repo from either the `--repo` flag or local git context.

- If `target_repo` is provided: validates `owner/repo` format (exactly one `/`), splits and returns
- If `target_repo` is `None`: extracts from `ctx.repo.github.owner` and `ctx.repo.github.repo`
- Raises `UserFacingCliError` on invalid format or missing context

### `@repo_option`

Click option decorator that adds `--repo` with `target_repo` parameter name. Apply to any command that needs optional remote operation.

### `@resolved_repo_option`

Higher-level decorator that wraps a Click command to resolve `--repo` (or local git context) into a `GitHubRepoId` before calling the handler. The handler receives `repo_id: GitHubRepoId` instead of `target_repo: str | None`.

Internally applies `@repo_option` and calls `resolve_owner_repo()`.

### `get_remote_github(ctx)`

Factory that returns a `RemoteGitHub` instance:

- Uses `ctx.remote_github` if provided (tests inject `FakeRemoteGitHub` here)
- Otherwise constructs `RealRemoteGitHub` from `ctx.http_client`
- Raises `UserFacingCliError` if no `http_client` is available

## Usage

```python
from erk.cli.repo_resolution import get_remote_github, resolved_repo_option

@click.command()
@resolved_repo_option
@click.pass_obj
def my_command(ctx: ErkContext, *, repo_id: GitHubRepoId) -> None:
    remote = get_remote_github(ctx)
    # Use repo_id.owner, repo_id.repo, and remote for API calls
```

## Testing

See [Remote Paths Testing](../testing/remote-paths-testing.md) for patterns using `NoRepoSentinel` and `FakeRemoteGitHub`.

## Related Documentation

- [RemoteGitHub Gateway](../architecture/remote-github-gateway.md) — the gateway used by remote mode
- [Remote Paths Testing](../testing/remote-paths-testing.md) — test patterns for --repo commands
