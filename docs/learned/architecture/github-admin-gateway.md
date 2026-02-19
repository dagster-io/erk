---
title: GitHub Admin Gateway
read_when:
  - "working with GitHub repository secrets or admin operations"
  - "adding methods to the GitHubAdmin gateway"
  - "understanding the 5-place gateway pattern with security-sensitive operations"
tripwires:
  - action: "passing secret values as command-line arguments"
    warning: "Secret values must be passed via stdin (input= parameter) to avoid process list exposure. See github-admin-gateway.md."
---

# GitHub Admin Gateway

GitHubAdmin manages GitHub repository administration operations, primarily secrets management. It follows the 5-place gateway pattern.

## Location

`packages/erk-shared/src/erk_shared/gateway/github_admin/`

## 5-Place Implementation

| File          | Role                                                    |
| ------------- | ------------------------------------------------------- |
| `abc.py`      | Abstract interface defining the contract                |
| `real.py`     | Production implementation using `gh` CLI                |
| `fake.py`     | Test double with mutation tracking                      |
| `noop.py`     | No-op for dry-run mode (reads delegate, mutations skip) |
| `printing.py` | Verbose wrapper that prints then delegates              |

## Security: stdin for Secrets

The `set_secret()` method uses `input=secret_value` to pass secrets via stdin rather than command-line arguments. This prevents exposure in process lists.

In `real.py`:

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github_admin/real.py, RealGitHubAdmin.set_secret -->

See `RealGitHubAdmin.set_secret()` in `packages/erk-shared/src/erk_shared/gateway/github_admin/real.py` — uses `input=secret_value` to pass secrets via stdin.

## Fake Mutation Tracking

FakeGitHubAdmin tracks mutations via list fields exposed as tuple properties:

- `set_secret_calls` — `tuple[tuple[str, str], ...]` (name, value pairs)
- `delete_secret_calls` — `tuple[str, ...]` (secret names)
- `set_permission_calls` — `tuple[tuple[Path, bool], ...]`

Internal state uses `list[tuple[...]]` for append operations, exposed as immutable tuples via `@property` for test assertions. This is consistent with FakeGit and FakeGitHub patterns — see [fake-mutation-tracking.md](fake-mutation-tracking.md).

## Display-or-Modify Pattern

The associated CLI command (`erk admin gh-actions-api-key`) follows a display-or-modify pattern: it either shows the current state or modifies it based on flags.

## Related Topics

- [Gateway ABC Implementation](gateway-abc-implementation.md) - 5-place implementation checklist
- [Fake Mutation Tracking](fake-mutation-tracking.md) - Cross-cutting pattern for test doubles
- [Subprocess Wrappers](subprocess-wrappers.md) - Wrapper functions for subprocess calls
