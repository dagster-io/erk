---
title: GitHub Interface Patterns
read_when:
  - "calling GitHub API from erk"
  - "working with gh api command"
  - "fetching PR or issue data efficiently"
  - "understanding PRDetails type"
---

# GitHub Interface Patterns

This document describes patterns for efficient GitHub API access in the erk codebase.

## REST API via `gh api`

Prefer `gh api` for direct REST API access over `gh pr view --json` when you need comprehensive data in a single call.

### Why Use `gh api`

- **Single call efficiency**: Fetch all needed fields in one API request
- **Rate limit friendly**: Reduces number of API calls vs multiple `gh pr view --json` invocations
- **Field access**: Direct access to REST API fields that may not be exposed via `gh pr view`

### REST API Endpoints

| Operation           | Endpoint                                                      |
| ------------------- | ------------------------------------------------------------- |
| Get PR by number    | `/repos/{owner}/{repo}/pulls/{pr_number}`                     |
| Get PR by branch    | `/repos/{owner}/{repo}/pulls?head={owner}:{branch}&state=all` |
| Get issue by number | `/repos/{owner}/{repo}/issues/{issue_number}`                 |

### Example Usage

```bash
# Get PR by number
gh api repos/owner/repo/pulls/123

# Get PR by branch (returns array, may be empty)
gh api "repos/owner/repo/pulls?head=owner:feature-branch&state=all"
```

## Field Mapping: REST API to Internal Types

The REST API returns field names that differ from GraphQL and internal conventions. Use this mapping when parsing REST responses:

### PR State

| REST API Fields                  | Internal Value |
| -------------------------------- | -------------- |
| `state="open"`                   | `"OPEN"`       |
| `state="closed"`, `merged=false` | `"CLOSED"`     |
| `state="closed"`, `merged=true`  | `"MERGED"`     |

**Logic**: Check `merged` boolean first when `state="closed"` to distinguish merged from closed-without-merge.

### Mergeability

| REST API `mergeable` | Internal Value  |
| -------------------- | --------------- |
| `true`               | `"MERGEABLE"`   |
| `false`              | `"CONFLICTING"` |
| `null`               | `"UNKNOWN"`     |

**Note**: `mergeable` may be `null` if GitHub hasn't computed mergeability yet. Retry after a short delay if you need this value.

### Draft Status

| REST API Field | Internal Field |
| -------------- | -------------- |
| `draft`        | `is_draft`     |

### Fork Detection

| REST API Field   | Internal Field        |
| ---------------- | --------------------- |
| `head.repo.fork` | `is_cross_repository` |

## Implementation in erk

The `RealGitHub.get_pr()` method in `packages/erk-shared/src/erk_shared/github/real.py` implements this pattern, returning a `PRDetails` dataclass with all commonly-needed fields.

```python
from erk_shared.github.types import PRDetails

# Single API call gets everything
pr = github.get_pr(owner, repo, pr_number)

# Access fields directly
if pr.state == "MERGED":
    click.echo(f"PR #{pr.number} was merged into {pr.base_ref_name}")
```

## Design Pattern: Fetch Once, Use Everywhere

When designing API interfaces:

1. **Identify all needed fields** across call sites
2. **Create a comprehensive type** (`PRDetails`) containing all fields
3. **Fetch everything in one call** rather than multiple narrow fetches
4. **Pass the full object** to downstream functions

This pattern:

- Reduces API rate limit consumption
- Simplifies call site code (no need to make additional fetches)
- Makes the data contract explicit via the type definition

## Related Topics

- [GitHub GraphQL API Patterns](github-graphql.md) - GraphQL queries and mutations
- [GitHub URL Parsing Architecture](github-parsing.md) - Parsing URLs and identifiers
- [Subprocess Wrappers](subprocess-wrappers.md) - Running `gh` commands safely
