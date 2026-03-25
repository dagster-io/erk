---
title: RemoteGitHub Gateway
read_when:
  - "working with RemoteGitHub"
  - "adding --repo support"
  - "implementing remote PR operations"
  - "making GitHub API calls without local git clone"
tripwires:
  - action: "calling gh CLI for GitHub API operations in remote mode"
    warning: "use RemoteGitHub gateway instead. Remote mode has no local git/gh CLI."
---

# RemoteGitHub Gateway

REST API-based GitHub operations without a local git or `gh` CLI dependency. Enables erk commands to operate on repositories without a local clone.

## ABC Location

`packages/erk-shared/src/erk_shared/gateway/remote_github/abc.py`

## Methods

### Authentication

| Method                     | Returns                                 | Description                         |
| -------------------------- | --------------------------------------- | ----------------------------------- |
| `get_authenticated_user()` | `str`                                   | Username of authenticated user      |
| `check_auth_status()`      | `tuple[bool, str \| None, str \| None]` | (is_authenticated, username, error) |

### Repository

| Method                                 | Returns | Description                        |
| -------------------------------------- | ------- | ---------------------------------- |
| `get_default_branch_name(owner, repo)` | `str`   | Default branch name (e.g., "main") |
| `get_default_branch_sha(owner, repo)`  | `str`   | SHA of default branch HEAD         |

### Git References & Commits

| Method                                                            | Returns | Description                   |
| ----------------------------------------------------------------- | ------- | ----------------------------- |
| `create_ref(owner, repo, ref, sha)`                               | `None`  | Create a git reference/branch |
| `create_file_commit(owner, repo, path, content, message, branch)` | `str`   | Commit SHA                    |

### Pull Requests

| Method                                                             | Returns                            | Description        |
| ------------------------------------------------------------------ | ---------------------------------- | ------------------ |
| `get_pr(owner, repo, number)`                                      | `RemotePRInfo \| RemotePRNotFound` | Fetch PR by number |
| `create_pull_request(owner, repo, head, base, title, body, draft)` | `int`                              | PR number          |
| `update_pull_request_body(owner, repo, pr_number, body)`           | `None`                             | Update PR body     |
| `close_pr(owner, repo, number)`                                    | `None`                             | Close a PR         |

## PR Types

Defined in `packages/erk-shared/src/erk_shared/gateway/remote_github/types.py`.

### `RemotePRInfo`

<!-- Source: packages/erk-shared/src/erk_shared/gateway/remote_github/types.py, RemotePRInfo -->

See `RemotePRInfo` in `packages/erk-shared/src/erk_shared/gateway/remote_github/types.py`.

This frozen dataclass holds complete PR metadata: number, title, state (uppercase strings like `"OPEN"`, `"CLOSED"`, `"MERGED"` from GitHub REST API), URL, source and target branch names, repository owner and name, and a guaranteed list of label strings.

### `RemotePRNotFound`

<!-- Source: packages/erk-shared/src/erk_shared/gateway/remote_github/types.py, RemotePRNotFound -->

See `RemotePRNotFound` in `packages/erk-shared/src/erk_shared/gateway/remote_github/types.py`.

Sentinel frozen dataclass used in discriminated union returns from `get_pr()` to indicate that a pull request with the requested number does not exist. The `pr_number` field stores the number that was queried.

### LBYL Pattern for PR Lookup

<!-- Source: src/erk/cli/commands/launch_cmd.py, launch -->

See the LBYL lookup pattern in `src/erk/cli/commands/launch_cmd.py`, `launch` command. Cross-reference [discriminated-union-error-handling.md](discriminated-union-error-handling.md) for the complete error handling pattern.

The pattern checks the discriminated union return value using `isinstance()` before accessing PR fields, ensuring type safety when a PR lookup may fail.

### Issues

| Method                                                    | Returns                      | Description         |
| --------------------------------------------------------- | ---------------------------- | ------------------- |
| `get_issue(owner, repo, number)`                          | `IssueInfo \| IssueNotFound` | Fetch issue         |
| `get_issue_comments(owner, repo, number)`                 | `list[str]`                  | All comment bodies  |
| `list_issues(owner, repo, labels, state, limit, creator)` | `list[IssueInfo]`            | Filtered issue list |
| `add_labels(owner, repo, issue_number, labels)`           | `None`                       | Add labels          |
| `add_issue_comment(owner, repo, issue_number, body)`      | `None`                       | Add comment         |
| `close_issue(owner, repo, number)`                        | `None`                       | Close issue         |

### Workflows

| Method                                                  | Returns | Description     |
| ------------------------------------------------------- | ------- | --------------- |
| `dispatch_workflow(owner, repo, workflow, ref, inputs)` | `str`   | Workflow run ID |

## Implementation

See `RealRemoteGitHub` and `FakeRemoteGitHub` in `packages/erk-shared/src/erk_shared/gateway/remote_github/`.

## Shared `--repo` Infrastructure

`src/erk/cli/repo_resolution.py` provides:

| Function                               | Purpose                                      |
| -------------------------------------- | -------------------------------------------- |
| `resolve_owner_repo(ctx, target_repo)` | Parse "owner/repo" or extract from local git |
| `get_remote_github(ctx)`               | Get or construct RemoteGitHub instance       |
| `repo_option`                          | Click `--repo` option decorator              |

## Remote vs Local Mode

Commands branch on whether `--repo` was provided:

- **Remote mode** (`--repo` provided or no local git): uses `RemoteGitHub` gateway via REST API
- **Local mode** (local git available): uses existing `GitHub` gateway via `gh` CLI
