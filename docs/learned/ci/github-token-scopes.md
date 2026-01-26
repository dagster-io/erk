---
title: "GitHub Token Scopes in CI"
read_when:
  - "deciding which token to use in GitHub Actions workflows"
  - "encountering permission errors with github.token"
  - "understanding why gist creation or user API calls fail"
---

# GitHub Token Scopes in CI

GitHub provides two types of tokens for CI workflows, each with different permission scopes.

## The Key Distinction

| Scope Type       | Token              | Operations                                            |
| ---------------- | ------------------ | ----------------------------------------------------- |
| Repository-scope | `github.token`     | Issues, PRs, comments, workflow status, repo contents |
| User-scope       | `ERK_QUEUE_GH_PAT` | Gists, user identity, cross-workflow triggers         |

The automatic `github.token` is intentionally limited to repository operations for security. Operations that create user-owned resources require a PAT.

## Token Details

### `github.token` (Automatic)

- Ephemeral: created fresh for each workflow run
- Scoped to the repository only
- Cannot perform user-level operations
- Used for most repository interactions

**Works for:**

- Creating/updating issues and PRs
- Posting comments
- Reading repository contents
- Triggering workflow status checks

**Fails for:**

- Creating gists (`gh api gists`)
- Fetching user identity (`gh api user`)
- Triggering workflows in other repositories

### `ERK_QUEUE_GH_PAT` (Personal Access Token)

- Persistent: stored as a repository secret
- Configured with `repo` + `gist` scopes
- Can perform user-level operations
- Higher rate limits than automatic token

**Required for:**

- Creating gists for session uploads
- Operations that need user identity
- Cross-repository workflow triggers

## Operation Reference

| Operation                        | Token to Use       | Why                            |
| -------------------------------- | ------------------ | ------------------------------ |
| Create/comment on issues         | `github.token`     | Repository-scoped operation    |
| Create/update PRs                | `github.token`     | Repository-scoped operation    |
| Push commits                     | `github.token`     | Repository-scoped operation    |
| Create gists                     | `ERK_QUEUE_GH_PAT` | Gists are user-owned resources |
| Upload session to gist           | `ERK_QUEUE_GH_PAT` | Gists are user-owned resources |
| Get current user (`gh api user`) | `ERK_QUEUE_GH_PAT` | User identity is user-scoped   |
| Checkout with PAT                | `ERK_QUEUE_GH_PAT` | Enables pushing back to repo   |

## Error Symptoms

### `HTTP 403: Resource not accessible by integration`

```
gh api gists: HTTP 403: Resource not accessible by integration
```

**Cause:** Attempting gist creation with `github.token`
**Fix:** Use `ERK_QUEUE_GH_PAT` instead:

```yaml
- name: Upload session
  env:
    GH_TOKEN: ${{ secrets.ERK_QUEUE_GH_PAT }} # Not github.token
  run: erk exec upload-session ...
```

### `Could not get GitHub username`

**Cause:** Calling `gh api user` with `github.token`
**Fix:** Use PAT when user identity is needed

## Workflow Examples

### Using Both Tokens Appropriately

From `plan-implement.yml`:

```yaml
# Repository operations use github.token
- name: Post workflow started comment
  env:
    GH_TOKEN: ${{ github.token }} # OK: issues are repo-scoped
  run: erk exec post-workflow-started-comment ...

# User operations use PAT
- name: Upload session to gist
  env:
    GH_TOKEN: ${{ secrets.ERK_QUEUE_GH_PAT }} # Required: gists are user-scoped
  run: erk exec upload-session ...
```

### Checkout for Push Access

```yaml
- uses: actions/checkout@v4
  with:
    token: ${{ secrets.ERK_QUEUE_GH_PAT }} # Enables git push
    fetch-depth: 0
```

## PAT Configuration

The `ERK_QUEUE_GH_PAT` secret must be configured with these scopes:

- `repo` - Full control of private repositories
- `gist` - Create and update gists

Configure at: Repository Settings > Secrets and variables > Actions

## Related Documentation

- [GitHub API Rate Limits](../architecture/github-api-rate-limits.md) - REST vs GraphQL rate limit distinctions
- [GitHub Actions Security Patterns](github-actions-security.md) - Secure handling of dynamic values in workflows
