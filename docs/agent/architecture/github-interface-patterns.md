---
title: GitHub Interface Patterns
read_when:
  - "calling GitHub API from erk"
  - "working with gh api command"
  - "fetching PR or issue data efficiently"
  - "understanding PRDetails type"
  - "using GraphQL API for GitHub data"
  - "fetching review thread resolution status"
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

## GraphQL API via `gh api graphql`

Some GitHub data is only available via GraphQL. Use GraphQL when:

- **Data not exposed in REST API**: Review thread resolution status, certain connection fields
- **Batch queries**: Fetching multiple objects by node ID efficiently
- **Mutations**: Resolving review threads, updating draft state

### Query Syntax with Variables

**IMPORTANT:** Variables must be passed individually using `-f` (strings) and `-F` (typed values like integers). The syntax `-f variables='{...}'` does **NOT** work with `gh api graphql`.

```bash
gh api graphql \
  -f query='query($owner: String!, $repo: String!, $number: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $number) {
        reviewThreads(first: 100) {
          nodes { id isResolved path line }
        }
      }
    }
  }' \
  -f owner=cli \
  -f repo=cli \
  -F number=123
```

**Flag types:**
- `-f name=value` — String variables
- `-F name=value` — Typed variables (integers, booleans) parsed from JSON

### Query Pattern: Review Threads

Review thread resolution status is only available via GraphQL. The REST API does not expose `isResolved`.

```python
query = """query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          isOutdated
          path
          line
          comments(first: 20) {
            nodes {
              databaseId
              body
              author { login }
              path
              line: originalLine
              createdAt
            }
          }
        }
      }
    }
  }
}"""

# Pass variables individually: -f for strings, -F for typed values
cmd = [
    "gh", "api", "graphql",
    "-f", f"query={query}",
    "-f", f"owner={repo_info.owner}",
    "-f", f"repo={repo_info.name}",
    "-F", f"number={pr_number}",  # -F for integer
]
stdout = execute_gh_command(cmd, repo_root)
```

### Mutation Pattern: Resolve Review Thread

Mutations use the same `gh api graphql` command with individual variable flags:

```python
mutation = """mutation($threadId: ID!) {
  resolveReviewThread(input: {threadId: $threadId}) {
    thread {
      id
      isResolved
    }
  }
}"""

# Pass variables individually with -f for strings
cmd = [
    "gh", "api", "graphql",
    "-f", f"query={mutation}",
    "-f", f"threadId={thread_id}",
]
stdout = execute_gh_command(cmd, repo_root)
response = json.loads(stdout)
```

### Batch Queries with Node IDs

GraphQL's `nodes(ids: [...])` interface fetches multiple objects efficiently:

```python
def _build_workflow_runs_nodes_query(node_ids: list[str]) -> str:
    node_ids_json = json.dumps(node_ids)

    query = f"""query {{
  nodes(ids: {node_ids_json}) {{
    ... on WorkflowRun {{
      id
      databaseId
      checkSuite {{
        status
        conclusion
      }}
    }}
  }}
}}"""
    return query
```

### When to Use GraphQL vs REST

| Use Case                         | API to Use | Reason                                 |
| -------------------------------- | ---------- | -------------------------------------- |
| Get PR details                   | REST       | `gh api /repos/{owner}/{repo}/pulls/N` |
| Get review thread resolution     | GraphQL    | `isResolved` not in REST               |
| Resolve review thread            | GraphQL    | `resolveReviewThread` mutation         |
| Batch fetch by node ID           | GraphQL    | `nodes(ids: [...])` efficient batching |
| Get PR by branch                 | REST       | `?head=owner:branch&state=all`         |
| Get workflow run status          | REST       | Simple, well-documented                |
| Complex timeline/connection data | GraphQL    | Better for nested connections          |

### Error Handling

GraphQL errors are returned in the response body, not via HTTP status:

```python
response = json.loads(stdout)

# Check for GraphQL errors
if "errors" in response:
    errors = response["errors"]
    # Handle errors...

# Access data
data = response.get("data", {})
```

## Related Topics

- [GitHub GraphQL API Patterns](github-graphql.md) - GraphQL queries and mutations
- [GitHub URL Parsing Architecture](github-parsing.md) - Parsing URLs and identifiers
- [Subprocess Wrappers](subprocess-wrappers.md) - Running `gh` commands safely
- [GitHub ABC Extension Guide](github-abc-extension.md) - Adding new GitHub methods
