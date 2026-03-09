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

| Method                                                             | Returns                            | Description    |
| ------------------------------------------------------------------ | ---------------------------------- | -------------- |
| `get_pr(owner, repo, number)`                                      | `RemotePRInfo \| RemotePRNotFound` | Fetch PR       |
| `create_pull_request(owner, repo, head, base, title, body, draft)` | `int`                              | PR number      |
| `update_pull_request_body(owner, repo, pr_number, body)`           | `None`                             | Update PR body |
| `close_pr(owner, repo, number)`                                    | `None`                             | Close a PR     |

#### `get_pr()` Return Types

Defined in `packages/erk-shared/src/erk_shared/gateway/remote_github/types.py`:

**`RemotePRInfo`** — PR fields from the GitHub REST API pulls endpoint:

| Field           | Type        | Description                         |
| --------------- | ----------- | ----------------------------------- |
| `number`        | `int`       | PR number                           |
| `title`         | `str`       | PR title                            |
| `state`         | `str`       | `"OPEN"`, `"CLOSED"`, or `"MERGED"` |
| `url`           | `str`       | Full PR URL                         |
| `head_ref_name` | `str`       | Head branch name                    |
| `base_ref_name` | `str`       | Base branch name                    |
| `owner`         | `str`       | Repository owner                    |
| `repo`          | `str`       | Repository name                     |
| `labels`        | `list[str]` | Label names                         |

**`RemotePRNotFound`** — sentinel with `pr_number: int` field.

State mapping: GitHub API `open` / `closed` / `merged` maps to `OPEN` / `CLOSED` / `MERGED`.

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

See `RealRemoteGitHub` and `FakeRemoteGitHub` in `packages/erk-shared/src/erk_shared/gateway/remote_github/`.

## Shared `--repo` Infrastructure

`src/erk/cli/repo_resolution.py` provides:

| Function                               | Purpose                                        |
| -------------------------------------- | ---------------------------------------------- |
| `resolve_owner_repo(ctx, target_repo)` | Parse "owner/repo" or extract from local git   |
| `get_remote_github(ctx)`               | Get or construct RemoteGitHub instance         |
| `repo_option`                          | Click `--repo` option decorator                |
| `resolved_repo_option`                 | Decorator resolving --repo into `GitHubRepoId` |

See [Repo Resolution Pattern](../cli/repo-resolution-pattern.md) for detailed documentation.

## Remote vs Local Mode

Commands branch on whether `--repo` was provided:

- **Remote mode** (`--repo` provided or no local git): uses `RemoteGitHub` gateway via REST API
- **Local mode** (local git available): uses existing `GitHub` gateway via `gh` CLI
