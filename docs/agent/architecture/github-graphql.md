---
title: GitHub GraphQL API Patterns
read_when:
  - "using gh api graphql"
  - "writing GraphQL queries for GitHub"
  - "passing variables to GraphQL queries"
  - "fetching data not available in REST API"
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

## Passing Arrays and Objects

For array and object variables, use `json.dumps()` with the `-f` flag:

### Arrays

```python
# Query with array variable
GET_WORKFLOW_RUNS_QUERY = """query($nodeIds: [ID!]!) {
  nodes(ids: $nodeIds) { ... }
}"""

# Pass array via -f with json.dumps
cmd = [
    "gh", "api", "graphql",
    "-f", f"query={GET_WORKFLOW_RUNS_QUERY}",
    "-f", f"nodeIds={json.dumps(node_ids)}",  # ["id1", "id2", "id3"]
]
```

### Objects

```python
# Query with optional object variable
GET_ISSUES_QUERY = """query($filterBy: IssueFilters) {
  repository(...) {
    issues(filterBy: $filterBy) { ... }
  }
}"""

# Pass object via -f with json.dumps
if creator is not None:
    cmd.extend(["-f", f"filterBy={json.dumps({'createdBy': creator})}"])
```

### Why -f Works for JSON

The `-f` flag passes strings, but `gh` automatically parses JSON syntax when the GraphQL variable type expects it. The key is that `json.dumps()` produces valid JSON that `gh` can parse.

| Variable Type  | Python Value            | Command                               |
| -------------- | ----------------------- | ------------------------------------- |
| `[String!]!`   | `["a", "b"]`            | `-f 'labels=["a", "b"]'`              |
| `[ID!]!`       | `["id1", "id2"]`        | `-f 'nodeIds=["id1", "id2"]'`         |
| `IssueFilters` | `{"createdBy": "user"}` | `-f 'filterBy={"createdBy": "user"}'` |

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

## Query Organization Best Practices

**Strong preference: All GraphQL queries should be stored as string constants in `graphql_queries.py`.**

### Why Standalone Constants

1. **Readability**: Multi-line GraphQL strings are easier to read without f-string interpolation
2. **Maintainability**: All queries in one place for easy auditing
3. **Reusability**: Constants can be imported and reused across methods
4. **Testing**: Query structure can be tested independently

### Naming Conventions

- Queries: `GET_<RESOURCE>_QUERY` (e.g., `GET_PR_REVIEW_THREADS_QUERY`)
- Mutations: `<ACTION>_<RESOURCE>_MUTATION` (e.g., `RESOLVE_REVIEW_THREAD_MUTATION`)
- Fragments: `<RESOURCE>_FRAGMENT` (e.g., `ISSUE_PR_LINKAGE_FRAGMENT`)

### When Dynamic Query Building is Acceptable

Only use dynamic query construction when GraphQL limitations require it:

- **Aliased field names**: `issue_123: issue(number: 123)` cannot use variables for aliases
- In these cases, extract reusable fragments to constants and compose them dynamically

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

## Fragment Patterns

Use fragments for reusable field selections across queries.

### Defining Fragments

Store fragments as constants alongside queries:

```python
ISSUE_PR_LINKAGE_FRAGMENT = """fragment IssuePRLinkageFields on CrossReferencedEvent {
  willCloseTarget
  source {
    ... on PullRequest {
      number
      state
      url
    }
  }
}"""
```

### Using Fragments in Queries

Include fragment definition before the query and use spread syntax:

```python
query = f"""{ISSUE_PR_LINKAGE_FRAGMENT}

query {{
  repository(owner: "owner", name: "repo") {{
    issue(number: 123) {{
      timelineItems(first: 20) {{
        nodes {{
          ... on CrossReferencedEvent {{
            ...IssuePRLinkageFields
          }}
        }}
      }}
    }}
  }}
}}"""
```

### Inline Fragments for Type Narrowing

Use `... on TypeName` to access type-specific fields:

```graphql
nodes {
  ... on WorkflowRun {
    id
    databaseId
    checkSuite { status conclusion }
  }
}
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

## Related Topics

- [GitHub Interface Patterns](github-interface-patterns.md) - REST API patterns
- [Subprocess Wrappers](subprocess-wrappers.md) - Running `gh` commands safely

## Additional Resources

The `gh` skill (`.claude/skills/gh/`) provides comprehensive GraphQL resources:

- **`references/graphql.md`** - Complete GraphQL guide (~1000 lines) with use cases, patterns, and examples
- **`references/graphql-schema-core.md`** - Core schema types (~500 lines) with detailed field definitions
- **`references/gh.md`** - Full gh CLI reference including API access patterns

Load the `gh` skill when working with complex GraphQL queries or when you need schema details.
