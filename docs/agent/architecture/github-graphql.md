---
title: GitHub GraphQL API Patterns
read_when:
  - "using gh api graphql"
  - "writing GraphQL queries for GitHub"
  - "writing GraphQL mutations for GitHub"
  - "passing variables to GraphQL queries"
  - "fetching data not available in REST API"
  - "modifying GitHub data (resolving threads, adding comments)"
tripwires:
  - action: "passing variables to gh api graphql as JSON blob"
    warning: "Variables must be passed individually with -f (strings) and -F (typed). The syntax `-f variables={...}` does NOT work."
---

# GitHub GraphQL API Patterns

This document describes patterns for using GitHub's GraphQL API via `gh api graphql`.

## When to Use GraphQL vs REST

**Use GraphQL when:**

- Data is only available via GraphQL (e.g., PR review thread resolution status)
- You need to traverse relationships in a single query
- REST would require multiple round trips

**Use REST when:**

- The data is readily available via `gh api` REST endpoints
- Simple CRUD operations
- You need pagination that's easier with REST

## Variable Passing Syntax

**CRITICAL**: The `gh api graphql` command does NOT support passing variables as a JSON blob. Variables must be passed individually.

### Correct Syntax

```bash
# -f for string values
# -F for typed values (integers, booleans)
gh api graphql \
  -f query='...' \
  -f owner=dagster-io \
  -f repo=erk \
  -F number=123
```

### Wrong Syntax (Does Not Work)

```bash
# ❌ WRONG: -f variables={...} does not work
gh api graphql \
  -f query='...' \
  -f 'variables={"owner": "dagster-io", "repo": "erk", "number": 123}'
```

The `gh` CLI documentation states: "For GraphQL requests, all fields other than `query` and `operationName` are interpreted as GraphQL variables."

### Variable Type Flags

| Flag | Type                 | Example                          |
| ---- | -------------------- | -------------------------------- |
| `-f` | String               | `-f owner=dagster-io`            |
| `-F` | Integer/Boolean/JSON | `-F number=123`, `-F draft=true` |

The `-F` flag performs type conversion:

- `true`/`false` → boolean
- Integer strings → integers
- JSON syntax → parsed JSON

## Query Organization

Store GraphQL queries in a dedicated module rather than inline strings:

```python
# packages/erk-shared/src/erk_shared/github/graphql_queries.py

GET_PR_REVIEW_THREADS_QUERY = """query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          ...
        }
      }
    }
  }
}"""
```

Benefits:

- Queries are easier to read and maintain
- Syntax highlighting in editors
- Reusable across multiple methods
- Easier to test query structure

## Implementation Pattern

```python
from erk_shared.github.graphql_queries import GET_PR_REVIEW_THREADS_QUERY
from erk_shared.github.parsing import execute_gh_command

def get_pr_review_threads(self, repo_root: Path, pr_number: int) -> list[PRReviewThread]:
    repo_info = self.get_repo_info(repo_root)

    # Pass variables individually: -f for strings, -F for typed values
    cmd = [
        "gh",
        "api",
        "graphql",
        "-f",
        f"query={GET_PR_REVIEW_THREADS_QUERY}",
        "-f",
        f"owner={repo_info.owner}",
        "-f",
        f"repo={repo_info.name}",
        "-F",
        f"number={pr_number}",
    ]

    stdout = execute_gh_command(cmd, repo_root)
    response = json.loads(stdout)
    return self._parse_response(response)
```

## Common Pitfalls

### 1. Dollar Sign Shell Escaping

When testing GraphQL queries in the shell, `$` characters in variable names like `$owner` may be interpreted by the shell:

```bash
# In shell, single quotes prevent variable expansion
gh api graphql -f query='query($owner: String!) { ... }'

# In Python subprocess, no shell escaping needed
cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
subprocess.run(cmd)  # Works correctly
```

### 2. Variable Type Mismatch

GraphQL is strictly typed. Ensure your variable types match the query signature:

```graphql
query($number: Int!) {  # Expects integer
  ...
}
```

```bash
# ✅ Correct: -F converts to integer
gh api graphql -f query='...' -F number=123

# ❌ Wrong: -f passes as string, type mismatch
gh api graphql -f query='...' -f number=123
```

### 3. Null Variable Values

If a variable is null, the GraphQL API returns an error like:

```
Variable $owner of type String! was provided invalid value
```

This usually means the variable wasn't passed correctly, not that it's actually null.

## Testing GraphQL Queries

Test queries manually before implementing:

```bash
# Test with heredoc for readability
gh api graphql -F owner=dagster-io -F repo=erk -F number=123 -f query='
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      title
    }
  }
}'
```

## GraphQL-Only Features

Some GitHub features are only available via GraphQL:

| Feature                            | Why GraphQL                        |
| ---------------------------------- | ---------------------------------- |
| PR review thread resolution status | `isResolved` field not in REST     |
| Resolve/unresolve review threads   | Mutation only available in GraphQL |
| PR timeline events                 | Richer data than REST              |
| Minimized comments                 | Status not exposed in REST         |

## Mutation Patterns

### Mutation Structure

GraphQL mutations follow a similar pattern to queries but with `mutation` keyword:

```graphql
mutation ($threadId: ID!, $body: String!) {
  addPullRequestReviewThreadReply(
    input: { pullRequestReviewThreadId: $threadId, body: $body }
  ) {
    comment {
      id
      body
    }
  }
}
```

Key differences from queries:

- Use `mutation` keyword instead of `query`
- Input arguments wrapped in `input: {...}` object
- Return the created/modified object for confirmation

### Mutation Organization

Store mutations in `graphql_queries.py` alongside queries:

```python
# packages/erk-shared/src/erk_shared/github/graphql_queries.py

# Mutation to resolve a PR review thread
RESOLVE_REVIEW_THREAD_MUTATION = """mutation($threadId: ID!) {
  resolveReviewThread(input: {threadId: $threadId}) {
    thread {
      id
      isResolved
    }
  }
}"""

# Mutation to add a reply comment to a PR review thread
ADD_REVIEW_THREAD_REPLY_MUTATION = """mutation($threadId: ID!, $body: String!) {
  addPullRequestReviewThreadReply(input: {pullRequestReviewThreadId: $threadId, body: $body}) {
    comment {
      id
      body
    }
  }
}"""
```

### Mutation Implementation Pattern

```python
from erk_shared.github.graphql_queries import RESOLVE_REVIEW_THREAD_MUTATION
from erk_shared.github.parsing import execute_gh_command

def resolve_review_thread(self, repo_root: Path, thread_id: str) -> bool:
    """Resolve a PR review thread via GraphQL mutation."""
    # Pass variables individually with -f for strings
    cmd = [
        "gh",
        "api",
        "graphql",
        "-f",
        f"query={RESOLVE_REVIEW_THREAD_MUTATION}",
        "-f",
        f"threadId={thread_id}",
    ]

    stdout = execute_gh_command(cmd, repo_root)
    response = json.loads(stdout)

    # Check if the mutation succeeded by examining returned data
    thread_data = response.get("data", {}).get("resolveReviewThread", {}).get("thread")
    if thread_data is None:
        return False

    return thread_data.get("isResolved", False)
```

### Mutation Response Validation

Always validate mutation responses by checking the returned object:

```python
# ✅ Correct: Check returned data confirms mutation succeeded
comment_data = response.get("data", {}).get("addPullRequestReviewThreadReply", {}).get("comment")
return comment_data is not None

# ❌ Wrong: Assuming success without checking response
return True  # Don't assume - always verify
```

### Common Mutations

| Mutation                          | Use Case                     | Input Field Name              |
| --------------------------------- | ---------------------------- | ----------------------------- |
| `resolveReviewThread`             | Mark review thread resolved  | `threadId`                    |
| `addPullRequestReviewThreadReply` | Add comment to review thread | `pullRequestReviewThreadId`   |
| `unresolveReviewThread`           | Reopen resolved thread       | `threadId`                    |
| `addComment`                      | Add PR/issue comment         | `subjectId`, `body`           |
| `updatePullRequest`               | Update PR fields             | `pullRequestId`, field values |

### Mutation Error Handling

GraphQL mutations may return partial success. Check for errors in the response:

```python
response = json.loads(stdout)

# Check for GraphQL errors
if "errors" in response:
    error_messages = [e.get("message", "Unknown error") for e in response["errors"]]
    raise RuntimeError(f"GraphQL mutation failed: {', '.join(error_messages)}")

# Then check mutation-specific data
data = response.get("data", {}).get("mutationName", {})
```

## Related Topics

- [GitHub Interface Patterns](github-interface-patterns.md) - REST API patterns
- [Subprocess Wrappers](subprocess-wrappers.md) - Running `gh` commands safely
- [Gateway ABC Implementation](gateway-abc-implementation.md) - Adding new GitHub methods

## Additional Resources

The `gh` skill (`.claude/skills/gh/`) provides comprehensive GraphQL resources:

- **`references/graphql.md`** - Complete GraphQL guide (~1000 lines) with use cases, patterns, and examples
- **`references/graphql-schema-core.md`** - Core schema types (~500 lines) with detailed field definitions
- **`references/gh.md`** - Full gh CLI reference including API access patterns

Load the `gh` skill when working with complex GraphQL queries or when you need schema details.
