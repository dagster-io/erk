---
title: GitHub Interface Patterns
last_audited: "2026-02-16 00:00 PT"
audit_result: edited
read_when:
  - "calling GitHub API from erk"
  - "working with gh api command"
  - "fetching PR or issue data efficiently"
  - "understanding PRDetails type"
tripwires:
  - action: "adding a field to PullRequestInfo in types.py"
    warning: "Must update all three parsers in real.py: _parse_pr_from_timeline_event(), list_prs(), and _parse_plan_prs_with_details(). See PullRequestInfo Field Addition Protocol in this doc."
    score: 7
  - action: "adding a field to a GraphQL query that uses ISSUE_PR_LINKAGE_FRAGMENT"
    warning: "Check GET_PLAN_PRS_WITH_DETAILS_QUERY for divergence. Both queries fetch PR fields but are defined separately in graphql_queries.py. A field in one but not the other causes None values in some code paths."
    score: 5
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

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/real.py, RealLocalGitHub.get_pr -->

The `RealLocalGitHub.get_pr()` method in `packages/erk-shared/src/erk_shared/gateway/github/real.py` implements this pattern, returning a `PRDetails` dataclass with all commonly-needed fields.

```python
from erk_shared.gateway.github.types import PRDetails

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

## PullRequestInfo Field Addition Protocol

When adding a new field to `PullRequestInfo` in `types.py`, three parsers in `real.py` must be updated to extract the field:

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/real.py, RealLocalGitHub._parse_pr_from_timeline_event -->

1. **`_parse_pr_from_timeline_event()`** — Parses PRs from GraphQL timeline cross-reference events (used by `get_prs_for_issue()`). Uses the `ISSUE_PR_LINKAGE_FRAGMENT` GraphQL fragment.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/real.py, RealLocalGitHub.list_prs -->

2. **`list_prs()`** — Parses PRs from REST API responses. Field names differ from GraphQL (e.g., `base.ref` vs `baseRefName`).

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/real.py, RealLocalGitHub._parse_plan_prs_with_details -->

3. **`_parse_plan_prs_with_details()`** — Parses PRs from the `GET_PLAN_PRS_WITH_DETAILS_QUERY` GraphQL query (used by `list_plan_prs_with_details()`).

### GraphQL Fragment Divergence Risk

The `ISSUE_PR_LINKAGE_FRAGMENT` and `GET_PLAN_PRS_WITH_DETAILS_QUERY` are separate GraphQL definitions that both fetch PR fields. When adding a field to one, check whether the other also needs the field. Divergence between these two queries causes fields to be available in one code path but `None` in another.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/graphql_queries.py, ISSUE_PR_LINKAGE_FRAGMENT -->

See `ISSUE_PR_LINKAGE_FRAGMENT` and `GET_PLAN_PRS_WITH_DETAILS_QUERY` in `graphql_queries.py` for the two GraphQL definitions.

**Example**: The `base_ref_name` field was added to `PullRequestInfo` in PR #7964, requiring updates to all three parsers.

## Related Topics

- [GitHub GraphQL API Patterns](github-graphql.md) - GraphQL queries and mutations
- [GitHub URL Parsing Architecture](github-parsing.md) - Parsing URLs and identifiers
- [Subprocess Wrappers](subprocess-wrappers.md) - Running `gh` commands safely
