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
  - action: "passing array or object variables to gh api graphql with -F and json.dumps()"
    warning: "Arrays and objects require special gh syntax: arrays use -f key[]=value1 -f key[]=value2, objects use -f key[subkey]=value. Using -F key=[...] or -F key={...} passes them as literal strings, not typed values."
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

| Flag | Type            | Example                          |
| ---- | --------------- | -------------------------------- |
| `-f` | String          | `-f owner=dagster-io`            |
| `-F` | Integer/Boolean | `-F number=123`, `-F draft=true` |

The `-F` flag performs type conversion:

- `true`/`false` → boolean
- Integer strings → integers

### Array and Object Variables (CRITICAL)

**Arrays and objects require special syntax.** The `-F` flag does NOT work for arrays/objects passed with `json.dumps()` - it treats them as literal strings!

**Array syntax:** Use `key[]=value1 -f key[]=value2`:

```bash
# ✅ CORRECT: Array with gh's array syntax
gh api graphql -f query='...' -f 'labels[]=erk-plan' -f 'labels[]=bug' -f 'states[]=OPEN'

# ❌ WRONG: -F with JSON array (passes as literal string "[\"erk-plan\"]")
gh api graphql -f query='...' -F 'labels=["erk-plan", "bug"]'
```

**Object syntax:** Use `key[subkey]=value`:

```bash
# ✅ CORRECT: Object with gh's object syntax
gh api graphql -f query='...' -f 'filterBy[createdBy]=schrockn'

# ❌ WRONG: -F with JSON object (passes as literal string "{\"createdBy\": ...}")
gh api graphql -f query='...' -F 'filterBy={"createdBy": "schrockn"}'
```

**In Python:**

```python
# ✅ CORRECT: Build array/object args properly
cmd = ["gh", "api", "graphql", "-f", f"query={query}"]

# Add array elements individually
for label in labels:
    cmd.extend(["-f", f"labels[]={label}"])

# Add object properties with key[subkey] syntax
if creator is not None:
    cmd.extend(["-f", f"filterBy[createdBy]={creator}"])

# Use -F only for integers/booleans (not arrays/objects)
cmd.extend(["-F", f"first={limit}"])
```

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

## Related Topics

- [GitHub Interface Patterns](github-interface-patterns.md) - REST API patterns
- [Subprocess Wrappers](subprocess-wrappers.md) - Running `gh` commands safely

## Additional Resources

The `gh` skill (`.claude/skills/gh/`) provides comprehensive GraphQL resources:

- **`references/graphql.md`** - Complete GraphQL guide (~1000 lines) with use cases, patterns, and examples
- **`references/graphql-schema-core.md`** - Core schema types (~500 lines) with detailed field definitions
- **`references/gh.md`** - Full gh CLI reference including API access patterns

Load the `gh` skill when working with complex GraphQL queries or when you need schema details.
