# Refactor GraphQL Query to Use Fragments

## Summary

Refactor `_build_issue_pr_linkage_query()` to use a named GraphQL fragment for the repeated PR fields, following the existing pattern in `_build_batch_pr_query()`.

## File to Modify

`src/erk/core/github/real.py` - lines 859-912

## Implementation

### 1. Define the fragment (before the query)

```graphql
fragment IssuePRLinkageFields on CrossReferencedEvent {
  willCloseTarget
  source {
    ... on PullRequest {
      number
      state
      url
      isDraft
      title
      createdAt
      statusCheckRollup {
        state
      }
      mergeable
      labels(first: 10) {
        nodes {
          name
        }
      }
    }
  }
}
```

### 2. Simplify each issue query to use fragment spread

```python
issue_query = f"""    issue_{issue_num}: issue(number: {issue_num}) {{
  timelineItems(itemTypes: [CROSS_REFERENCED_EVENT], first: 20) {{
    nodes {{
      ... on CrossReferencedEvent {{
        ...IssuePRLinkageFields
      }}
    }}
  }}
}}"""
```

### 3. Combine fragment with query (following `_build_batch_pr_query` pattern)

```python
query = f"""{fragment_definition}

query {{
  repository(owner: "{owner}", name: "{repo}") {{
{chr(10).join(issue_queries)}
  }}
}}"""
```

## Tests

Existing tests in `tests/core/operations/test_github.py` (lines 498-902) should continue to pass as this is a pure refactoring with no behavioral changes.
