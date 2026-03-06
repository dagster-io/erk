---
title: "GitHub Token Scopes in CI"
last_audited: "2026-02-17 16:00 PT"
audit_result: clean
read_when:
  - "deciding which token to use in GitHub Actions workflows"
  - "encountering permission errors with github.token"
  - "understanding why user API calls or git push fail in CI"
---

# GitHub Token Scopes in CI

GitHub provides two types of tokens for CI workflows, each with different permission scopes.

## The Key Distinction

| Scope Type       | Token              | Operations                                            |
| ---------------- | ------------------ | ----------------------------------------------------- |
| Repository-scope | `github.token`     | Issues, PRs, comments, workflow status, repo contents |
| User-scope       | `ERK_QUEUE_GH_PAT` | Git push, user identity, cross-workflow triggers      |

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

- Triggering workflow events when pushing (security feature to prevent loops)
- Fetching user identity (`gh api user`)
- Triggering workflows in other repositories

### `ERK_QUEUE_GH_PAT` (Personal Access Token)

- Persistent: stored as a repository secret
- Configured with `repo` scope
- Can perform user-level operations
- Higher rate limits than automatic token

**Required for:**

- Pushing session data to branches (`push-session`)
- Operations that need user identity
- Cross-repository workflow triggers

## Operation Reference

| Operation                        | Token to Use       | Why                                       |
| -------------------------------- | ------------------ | ----------------------------------------- |
| Create/comment on issues         | `github.token`     | Repository-scoped operation               |
| Create/update PRs                | `github.token`     | Repository-scoped operation               |
| Push commits                     | `github.token`     | Repository-scoped operation               |
| Create gists                     | `ERK_QUEUE_GH_PAT` | Gists are user-owned resources            |
| Upload session to gist           | `ERK_QUEUE_GH_PAT` | Gists are user-owned resources            |
| Get current user (`gh api user`) | `ERK_QUEUE_GH_PAT` | User identity is user-scoped              |
| Checkout (normal workflows)      | `github.token`     | Standard checkout for most operations     |
| Checkout (auto-fix CI)           | `ERK_QUEUE_GH_PAT` | Enables push that re-triggers CI checks   |
| Trigger CI workflows             | `ERK_QUEUE_GH_PAT` | PAT needed for `gh workflow run` dispatch |

## Auto-Commit Re-Triggering Pattern

When CI auto-commits fixes (e.g., the `markdown-fix` job running Prettier), the push must trigger a new CI run to validate the fixed code. Pushes made with `github.token` do not trigger workflow events (a GitHub security measure to prevent infinite loops).

**Solution:** Use `ERK_QUEUE_GH_PAT` for checkout in `ci.yml` only, so that `git push` triggers a new CI run:

```yaml
- uses: actions/checkout@v4
  with:
    ref: ${{ github.head_ref || github.ref }}
    token: ${{ secrets.ERK_QUEUE_GH_PAT }}
```

### Loop Safety

Infinite loops are prevented by two guarantees:

1. **Idempotent formatters**: Prettier and `erk docs sync` produce stable output. Running them twice yields no diff.
2. **`git diff --quiet` exit guard**: The auto-commit step checks for changes before committing. If the formatter produced no changes (because the previous run already fixed them), the step exits early.

### Concurrency Cancellation

The CI workflow uses `cancel-in-progress: true` concurrency:

```yaml
concurrency:
  group: ci-${{ github.head_ref || github.ref }}
  cancel-in-progress: true
```

When the auto-commit push triggers a new CI run, the original (now-stale) run is cancelled automatically. The new run validates the fixed code from a clean state.

### Safety Constraints

- Auto-commits only run on PR events (fail on push to master)
- Fork PRs are rejected (cannot push to fork repositories)
- Only same-repo PRs are eligible for auto-fix

## Error Symptoms

### `HTTP 403: Resource not accessible by integration`

```
HTTP 403: Resource not accessible by integration
```

**Cause:** Attempting git push or user-scoped operation with `github.token`
**Fix:** Use `ERK_QUEUE_GH_PAT` instead:

```yaml
- name: Push session
  env:
    GH_TOKEN: ${{ secrets.ERK_QUEUE_GH_PAT }} # Not github.token
  run: erk exec push-session ...
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
- name: Push session to branch
  env:
    GH_TOKEN: ${{ secrets.ERK_QUEUE_GH_PAT }} # Required: push needs PAT
  run: erk exec push-session ...
```

### Checkout for Push Access

```yaml
- uses: actions/checkout@v4
  with:
    token: ${{ secrets.ERK_QUEUE_GH_PAT }} # Enables git push
    fetch-depth: 0
```

## Triggering Workflows from CI

When you need CI to dispatch another workflow, you cannot use a push event because pushes with `github.token` don't trigger events. Instead, use `gh workflow run` with PAT:

```yaml
- name: Trigger CI workflows
  env:
    GH_TOKEN: ${{ secrets.ERK_QUEUE_GH_PAT }}
    BRANCH_NAME: ${{ steps.find_pr.outputs.branch_name }}
  run: |
    gh workflow run ci.yml --ref "$BRANCH_NAME"
```

This uses the GitHub CLI to explicitly dispatch a workflow, which bypasses the push-event limitation. The `gh workflow run` command requires PAT authentication.

## PAT Configuration

The `ERK_QUEUE_GH_PAT` secret must be configured with these scopes:

- `repo` - Full control of private repositories

Configure at: Repository Settings > Secrets and variables > Actions

## Related Documentation

- [GitHub API Rate Limits](../architecture/github-api-rate-limits.md) - REST vs GraphQL rate limit distinctions
- [GitHub Actions Security Patterns](github-actions-security.md) - Secure handling of dynamic values in workflows
