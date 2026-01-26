---
title: GitHub Token Requirements
read_when:
  - "setting up GitHub authentication for erk"
  - "debugging 403 errors from GitHub API"
  - "troubleshooting permission denied errors with gh CLI"
---

# GitHub Token Requirements

This document specifies the OAuth scopes required for erk's GitHub operations.

## Required Scopes

The following OAuth scopes are required for erk's GitHub operations:

| Scope      | Required For                                 |
| ---------- | -------------------------------------------- |
| `repo`     | Reading/writing issues, PRs, comments        |
| `workflow` | Triggering GitHub Actions workflows          |
| `gist`     | Creating and reading gists (session uploads) |

## Optional Scopes

| Scope      | Required For                                   |
| ---------- | ---------------------------------------------- |
| `read:org` | Reading organization membership (if in an org) |

## Setup

To authenticate with the required scopes:

```bash
gh auth login --scopes repo,workflow,gist
```

Or refresh an existing token with additional scopes:

```bash
gh auth refresh --scopes repo,workflow,gist
```

## Verification

Check current authentication status:

```bash
gh auth status
```

Check token scopes:

```bash
gh auth status --show-token 2>&1 | grep -i scope
```

## Common Errors

### 403 Forbidden on Workflow Dispatch

**Symptom**: `gh workflow run` fails with 403.

**Cause**: Missing `workflow` scope.

**Fix**: `gh auth refresh --scopes workflow`

### Cannot Create Gists

**Symptom**: `gh gist create` fails with permission error.

**Cause**: Missing `gist` scope.

**Fix**: `gh auth refresh --scopes gist`

## Related Documentation

- [GitHub API Rate Limits](github-api-rate-limits.md) - Rate limit quotas and REST vs GraphQL
- [GitHub CLI Quirks](github-cli-quirks.md) - gh CLI edge cases
