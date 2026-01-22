---
title: "GitHub Token Scopes in CI"
read_when:
  - "deciding which token to use in GitHub Actions workflows"
  - "encountering permission errors with github.token"
  - "understanding why gist creation or user API calls fail"
  - "seeing 'Resource not accessible by integration' errors"
---

# GitHub Token Scopes in CI

## Overview

GitHub Actions provides two token mechanisms with different scopes:

| Token                    | Source            | Scope           | Persistence |
| ------------------------ | ----------------- | --------------- | ----------- |
| `github.token`           | Automatic per-run | Repository only | Ephemeral   |
| `ERK_QUEUE_GH_PAT` (PAT) | Repository secret | User + repo     | Persistent  |

## The Key Distinction

GitHub separates API operations by scope:

- **Repository-scoped**: Operations on repository resources (issues, PRs, comments, workflow runs)
- **User-scoped**: Operations that create user-owned resources or access user identity

The automatic `github.token` is intentionally limited to repository operations for security. Operations that create user-owned resources (like gists) require a PAT with explicit scopes.

## Operation Reference Table

| Operation                      | `github.token` | PAT Required | Why                                  |
| ------------------------------ | -------------- | ------------ | ------------------------------------ |
| Create/edit issues             | Yes            | No           | Repository resource                  |
| Create/edit PRs                | Yes            | No           | Repository resource                  |
| Add PR/issue comments          | Yes            | No           | Repository resource                  |
| Trigger workflow runs          | No             | Yes          | Prevents recursive workflow triggers |
| Create gists                   | No             | Yes          | User-owned resource                  |
| `gh api user`                  | No             | Yes          | User identity endpoint               |
| Upload SSH keys                | No             | Yes          | User-scoped resource                 |
| Push to protected branches     | No             | Yes          | Requires explicit authorization      |
| Checkout with `fetch-depth: 0` | Partial        | Recommended  | May need history from other forks    |

## When to Use Each Token

### Use `github.token` (default)

- Creating or updating issues and PRs in the current repository
- Posting comments on issues and PRs
- Reading repository content and metadata
- Updating workflow status checks

```yaml
- name: Comment on issue
  env:
    GH_TOKEN: ${{ github.token }}
  run: |
    gh api repos/${{ github.repository }}/issues/${{ github.event.issue.number }}/comments \
      -X POST \
      -f body="Processing complete"
```

### Use `ERK_QUEUE_GH_PAT`

- Creating gists
- Triggering other workflows (prevents infinite loops with `github.token`)
- Accessing user identity (`gh api user`)
- Operations requiring specific OAuth scopes beyond `repo`
- Checkout when full history or fork access is needed

```yaml
- name: Create gist
  env:
    GH_TOKEN: ${{ secrets.ERK_QUEUE_GH_PAT }}
  run: |
    gh api gists \
      -X POST \
      -f "files[results.txt][content]=..."
```

## Error Symptoms

### "Resource not accessible by integration"

```
HTTP 403: Resource not accessible by integration
```

**Cause**: Using `github.token` for a user-scoped operation (typically gist creation).

**Fix**: Switch to `ERK_QUEUE_GH_PAT`:

```yaml
env:
  GH_TOKEN: ${{ secrets.ERK_QUEUE_GH_PAT }}
```

### "Could not get GitHub username"

```
error getting current user: failed to determine GitHub username
```

**Cause**: Using `github.token` with `gh api user` endpoint.

**Fix**: Use PAT for user identity operations.

### "Workflow triggered but not running"

**Cause**: Using `github.token` to trigger `workflow_dispatch`. GitHub prevents this to avoid recursive triggers.

**Fix**: Use PAT to trigger workflows.

## PAT Configuration

The `ERK_QUEUE_GH_PAT` secret should be configured with these scopes:

- `repo` - Full repository access
- `gist` - Gist creation (if needed)
- `workflow` - Workflow triggering (if needed)

To configure: Settings > Secrets and variables > Actions > Repository secrets

## Related Documentation

- [GitHub API Rate Limits](../architecture/github-api-rate-limits.md) - REST vs GraphQL quotas
- [GitHub Actions Security Patterns](github-actions-security.md) - Safe variable interpolation
