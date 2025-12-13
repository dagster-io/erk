# Plan: Enhance GitHub GraphQL Documentation

## Objective

Update `docs/agent/architecture/github-graphql.md` to document:

1. Strong preference for queries as string constants in standalone files
2. Patterns for passing JSON arrays/objects via `-f` flag
3. Fragment patterns for reusability

## Files to Modify

- `docs/agent/architecture/github-graphql.md` - Add new sections

## Implementation

### 1. Add "Query Organization Best Practices" Section

Add after the existing "Query Organization" section to strengthen the guidance:

```markdown
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
```

### 2. Add "Passing Complex Variables" Section

Add after the "Variable Passing Syntax" section:

````markdown
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
````

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

````

### 3. Add "Fragment Patterns" Section

Add new section:

```markdown
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
````

### Using Fragments in Queries

Include fragment definition before the query and use spread syntax:

```python
query = f\"""{ISSUE_PR_LINKAGE_FRAGMENT}

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
}}\"""
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

```

## Success Criteria

- Documentation covers query organization as strong preference (not just suggestion)
- Array/object variable passing patterns are clearly documented with examples
- Fragment patterns are documented for reusability
- All examples are derived from actual working code in the codebase
```
