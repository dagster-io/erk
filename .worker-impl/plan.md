# Plan: Document GitHub Token Scopes in CI

## Goal

Create a new documentation file explaining the distinction between `github.token` and PATs (`ERK_QUEUE_GH_PAT`) in GitHub Actions workflows, so developers understand when to use which token.

## Background

GitHub separates API operations by scope:
- **Repository-scoped**: Issues, PRs, comments, workflow runs (automatic token works)
- **User-scoped**: Gists, user identity, SSH keys (PAT required)

The automatic `github.token` provided by GitHub Actions is intentionally limited to repository operations for security. Operations that create user-owned resources (like gists) require a PAT with explicit scopes.

## File to Create

**`docs/learned/ci/github-token-scopes.md`**

## Document Structure

```yaml
---
title: "GitHub Token Scopes in CI"
read_when:
  - "deciding which token to use in GitHub Actions workflows"
  - "encountering permission errors with github.token"
  - "understanding why gist creation or user API calls fail"
---
```

### Content Sections

1. **Overview** - Brief explanation of the two token types
2. **The Key Distinction** - Repository-scoped vs user-scoped operations
3. **Operation Reference Table** - Which token to use for common operations
4. **When to Use Each Token** - Decision framework
5. **Error Symptoms** - Common errors and their causes
6. **Related Documentation** - Links to rate limits doc, security patterns doc

### Key Content Points

**`github.token` (automatic)**:
- Ephemeral, created per workflow run
- Repository-scoped only
- Works for: issues, PRs, comments, workflow status
- Fails for: gists, `gh api user`, workflow triggering

**`ERK_QUEUE_GH_PAT` (PAT)**:
- Persistent, stored as repository secret
- User-scoped with `repo` + `gist` scopes
- Required for: gists, user identity, cross-workflow triggers
- Higher rate limits than automatic token

**Common errors to document**:
- `HTTP 403: Resource not accessible by integration` - gist creation with wrong token
- `Could not get GitHub username` - user API call with wrong token

## Files to Reference

- `.github/workflows/erk-impl.yml` - Shows both tokens used appropriately
- `.github/workflows/learn-async.yml` - Recently fixed to use PAT
- `docs/learned/ci/github-actions-security.md` - Related security patterns
- `docs/learned/architecture/github-api-rate-limits.md` - Rate limit context

## Verification

1. Run `make fast-ci` to validate markdown formatting
2. Run `erk docs sync` to regenerate index files
3. Verify the new doc appears in `docs/learned/ci/index.md`