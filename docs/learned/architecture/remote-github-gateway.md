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

| Method                                                             | Returns | Description    |
| ------------------------------------------------------------------ | ------- | -------------- |
| `create_pull_request(owner, repo, head, base, title, body, draft)` | `int`   | PR number      |
| `update_pull_request_body(owner, repo, pr_number, body)`           | `None`  | Update PR body |
| `close_pr(owner, repo, number)`                                    | `None`  | Close a PR     |

### Issues

| Method                                                    | Returns                      | Description          |
| --------------------------------------------------------- | ---------------------------- | -------------------- |
| `get_issue(owner, repo, number)`                          | `IssueInfo \| IssueNotFound` | Fetch issue          |
| `get_issue_comments(owner, repo, number)`                 | `list[str]`                  | All comment bodies   |
| `get_prs_referencing_issue(owner, repo, number)`          | `list[PRReference]`          | PRs via timeline API |
| `list_issues(owner, repo, labels, state, limit, creator)` | `list[IssueInfo]`            | Filtered issue list  |
| `add_labels(owner, repo, issue_number, labels)`           | `None`                       | Add labels           |
| `add_issue_comment(owner, repo, issue_number, body)`      | `None`                       | Add comment          |
| `close_issue(owner, repo, number)`                        | `None`                       | Close issue          |

### Workflows

| Method                                                  | Returns | Description     |
| ------------------------------------------------------- | ------- | --------------- |
| `dispatch_workflow(owner, repo, workflow, ref, inputs)` | `str`   | Workflow run ID |

## Implementation

- **Real**: `RealRemoteGitHub` uses `HttpClient` for REST API calls and `Time` for polling delays
- **Fake**: `FakeRemoteGitHub` uses constructor injection for data + mutation tracking lists for assertions

## Shared `--repo` Infrastructure

`src/erk/cli/commands/pr/repo_resolution.py` provides:

| Function                               | Purpose                                      |
| -------------------------------------- | -------------------------------------------- |
| `resolve_owner_repo(ctx, target_repo)` | Parse "owner/repo" or extract from local git |
| `get_remote_github(ctx)`               | Get or construct RemoteGitHub instance       |
| `is_remote_mode(ctx, target_repo)`     | Check if command should use remote path      |
| `repo_option`                          | Click `--repo` option decorator              |

## Remote vs Local Mode

Commands branch on `is_remote_mode()`:

- **Remote mode** (`--repo` provided or no local git): uses `RemoteGitHub` gateway via REST API
- **Local mode** (local git available): uses existing `GitHub` gateway via `gh` CLI
