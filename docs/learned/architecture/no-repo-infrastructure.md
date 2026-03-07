---
title: No-Repo Infrastructure
read_when:
  - "adding a command that works outside git repositories"
  - "using NoRepoSentinel or @no_repo_required"
  - "implementing remote dispatch without local repo context"
tripwires:
  - action: "accessing ctx.git or ctx.repo without checking for NoRepoSentinel"
    warning: "Commands decorated with @no_repo_required may have sentinel gateways. Check isinstance(ctx.repo, NoRepoSentinel) before repo operations."
---

# No-Repo Infrastructure

Erk commands normally require a git repository context. The no-repo infrastructure allows specific commands to run outside repositories by providing sentinel gateways that raise user-friendly errors instead of crashing.

## NoRepoSentinel Pattern

Sentinel gateways implement the same ABC interfaces as real gateways but raise `NoRepoError` with guidance when called. This means commands can be wired up normally — the error only fires if the command actually tries to use repo-dependent functionality.

## `@no_repo_required` Decorator

Commands decorated with `@no_repo_required` skip repository detection during context construction. Instead of failing at startup when no repo is found, the context is built with sentinel gateways for repo-dependent services.

## RemoteGitHub Consolidation

<!-- Source: src/erk/cli/commands/one_shot.py -->

The one-shot dispatch command demonstrates the full no-repo pattern. It supports both local repo mode and remote-only mode via `--repo owner/name`:

### Context Injection Pattern

`_get_remote_github()` in `one_shot.py` provides a factory for `RemoteGitHub`:

1. If `ctx.remote_github` is already set (test injection), return it
2. If no `ctx.http_client` available, raise `UserFacingCliError`
3. Otherwise, construct `RealRemoteGitHub(http_client=ctx.http_client, time=ctx.time)`

### Repo Resolution

The repo resolution section handles the `--repo` flag:

- Validates format: must contain exactly one `/` (owner/repo)
- Falls back to local repo detection if `--repo` not provided
- Guards with `isinstance(ctx.repo, NoRepoSentinel)` when no `--repo` flag

### Error Handling

- `--repo` format validation: rejects malformed `owner/repo` strings
- Mutual exclusivity: `--repo` and `--ref-current` cannot be used together (current ref requires a local repo)

## Related Documentation

- [Codespace Remote Execution](../erk/codespace-remote-execution.md) — NoRepoSentinel guard in codespace connect
