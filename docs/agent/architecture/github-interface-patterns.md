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

## GraphQL API via `gh api graphql`

### When to Use GraphQL

Use GraphQL instead of REST when:

- **Data not available in REST**: Some GitHub data is only exposed via GraphQL (e.g., review thread resolution status)
- **Complex nested queries**: Need to fetch related data in a single request with precise field selection
- **Mutations**: Performing state changes that require GraphQL mutations (e.g., resolving review threads)

### Query Structure with Variables

GraphQL queries support parameterization via variables for safer, reusable queries:

```bash
# Query with variables
gh api graphql \
  -f query='query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          path
        }
      }
    }
  }
}' \
  -f variables='{"owner":"dagster-io","repo":"erk","number":123}'
```

**Pattern in Python code:**

```python
query = """query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
        }
      }
    }
  }
}"""

variables = json.dumps({
    "owner": repo_info.owner,
    "repo": repo_info.name,
    "number": pr_number
})

cmd = [
    "gh", "api", "graphql",
    "-f", f"query={query}",
    "-f", f"variables={variables}",
]
stdout = execute_gh_command(cmd, repo_root)
response = json.loads(stdout)
```

### Mutation Pattern for State Changes

Mutations modify GitHub state (e.g., resolving review threads, updating issues):

```bash
# Mutation with variables
gh api graphql \
  -f query='mutation($threadId: ID!) {
  resolveReviewThread(input: {threadId: $threadId}) {
    thread {
      id
      isResolved
    }
  }
}' \
  -f variables='{"threadId":"RT_kwDOABcD...xyz"}'
```

**Pattern in Python code:**

```python
mutation = """mutation($threadId: ID!) {
  resolveReviewThread(input: {threadId: $threadId}) {
    thread {
      id
      isResolved
    }
  }
}"""

variables = json.dumps({"threadId": thread_id})

cmd = [
    "gh", "api", "graphql",
    "-f", f"query={mutation}",
    "-f", f"variables={variables}",
]

try:
    stdout = execute_gh_command(cmd, repo_root)
    response = json.loads(stdout)

    # Verify mutation succeeded
    thread_data = response.get("data", {}).get("resolveReviewThread", {}).get("thread")
    return thread_data is not None and thread_data.get("isResolved") is True
except subprocess.CalledProcessError:
    return False
```

### Example: Review Thread Query

**Use case**: Fetching PR review threads with resolution status (not available in REST API).

```python
def get_pr_review_threads(
    self,
    repo_root: Path,
    pr_number: int,
    *,
    include_resolved: bool = False,
) -> list[PRReviewThread]:
    """Get review threads for a pull request via GraphQL."""
    repo_info = self.get_repo_info(repo_root)

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

    variables = json.dumps({
        "owner": repo_info.owner,
        "repo": repo_info.name,
        "number": pr_number
    })

    cmd = ["gh", "api", "graphql", "-f", f"query={query}", "-f", f"variables={variables}"]
    stdout = execute_gh_command(cmd, repo_root)
    response = json.loads(stdout)

    return self._parse_review_threads_response(response, include_resolved)
```

**Key patterns:**

- Use GraphQL node IDs (`id` field) for mutations and cross-referencing
- Use `databaseId` when you need the numeric ID compatible with REST API
- Nest field selection to fetch related data in one query
- Specify connection limits (`first: 100`) to control response size

### Example: Resolve Review Thread Mutation

**Use case**: Marking a review thread as resolved (mutation-only operation).

```python
def resolve_review_thread(
    self,
    repo_root: Path,
    thread_id: str,
) -> bool:
    """Resolve a PR review thread via GraphQL mutation."""
    mutation = """mutation($threadId: ID!) {
  resolveReviewThread(input: {threadId: $threadId}) {
    thread {
      id
      isResolved
    }
  }
}"""

    variables = json.dumps({"threadId": thread_id})

    cmd = ["gh", "api", "graphql", "-f", f"query={mutation}", "-f", f"variables={variables}"]

    try:
        stdout = execute_gh_command(cmd, repo_root)
        response = json.loads(stdout)

        # Check if the thread was resolved
        thread_data = response.get("data", {}).get("resolveReviewThread", {}).get("thread")
        return thread_data is not None and thread_data.get("isResolved") is True
    except subprocess.CalledProcessError:
        return False
```

**Key patterns:**

- Mutations use `input` object for parameters
- Return the modified object to verify success
- Use try/except for mutation error handling
- Check both response structure and expected field values

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

- [GitHub URL Parsing Architecture](github-parsing.md) - Parsing URLs and identifiers
- [Subprocess Wrappers](subprocess-wrappers.md) - Running `gh` commands safely
- [GitHub ABC Extension Workflow](github-abc-extension.md) - Adding new GitHub methods
