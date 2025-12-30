# GitHub GraphQL API Reference

This document provides comprehensive guidance for using GitHub's GraphQL API via `gh api graphql` when the standard `gh` porcelain commands (`gh pr`, `gh issue`, `gh repo`) are insufficient.

## Table of Contents

- [When to Use GraphQL](#when-to-use-graphql)
- [Use Cases Requiring GraphQL](#use-cases-requiring-graphql)
- [Getting Started](#getting-started)
- [Common GraphQL Patterns](#common-graphql-patterns)
- [Complete Examples](#complete-examples)
- [Schema Reference](#schema-reference)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## When to Use GraphQL

### Decision Tree

```
Can the task be done with gh porcelain commands?
├─ Yes → Use gh pr/issue/repo/release commands
└─ No → Consider these questions:
    ├─ Need Projects V2 operations? → GraphQL (no REST API exists)
    ├─ Need to query multiple repos in one call? → GraphQL (batch queries)
    ├─ Need complex nested data? → GraphQL (single request)
    ├─ Need Discussion API access? → GraphQL (no porcelain commands)
    ├─ Need advanced issue search? → GraphQL (complex filters)
    └─ Need custom field queries? → GraphQL (flexible schema)
```

### Quick Reference: CLI vs GraphQL

| Capability                  | gh CLI Command    | GraphQL Required?       |
| --------------------------- | ----------------- | ----------------------- |
| Create PR                   | `gh pr create`    | ❌ No                   |
| List PRs with basic filters | `gh pr list`      | ❌ No                   |
| View PR with reviews        | `gh pr view`      | ❌ No                   |
| Create issue                | `gh issue create` | ❌ No                   |
| Manage Projects V2          | N/A               | ✅ Yes                  |
| Query Discussions           | N/A               | ✅ Yes                  |
| Batch query repos           | N/A               | ✅ Yes                  |
| Advanced issue search       | N/A               | ✅ Yes                  |
| Complex nested queries      | Limited           | ✅ Yes (more efficient) |
| Custom field queries        | Limited           | ✅ Yes (more flexible)  |

---

## Use Cases Requiring GraphQL

### 1. Projects V2 Management

**Why GraphQL?** Projects V2 has **no REST API**. All operations must use GraphQL.

**Common Operations:**

- Create, update, delete projects
- Add issues/PRs to projects
- Update custom field values (status, priority, sprint, etc.)
- Query project items with custom fields
- Manage project views and workflows

**Example Scenario:** Automating project board updates when PRs merge.

```bash
# Get project ID and field IDs
gh api graphql -f query='
  query($org: String!, $number: Int!) {
    organization(login: $org) {
      projectV2(number: $number) {
        id
        fields(first: 20) {
          nodes {
            ... on ProjectV2Field {
              id
              name
            }
            ... on ProjectV2SingleSelectField {
              id
              name
              options {
                id
                name
              }
            }
          }
        }
      }
    }
  }
' -f org=myorg -F number=1
```

### 2. Discussion API

**Why GraphQL?** Discussions API has no porcelain commands in `gh`.

**Common Operations:**

- Create, update, close discussions
- Add comments and replies
- Mark answers
- Query discussion categories
- Vote on polls

**Example Scenario:** Automated discussion creation for release announcements.

```bash
# Create discussion with category
gh api graphql -H 'GraphQL-Features: discussions_api' -f query='
  mutation($repoId: ID!, $categoryId: ID!, $title: String!, $body: String!) {
    createDiscussion(input: {
      repositoryId: $repoId
      categoryId: $categoryId
      title: $title
      body: $body
    }) {
      discussion {
        id
        url
        number
      }
    }
  }
' -F repoId=$REPO_ID -F categoryId=$CATEGORY_ID \
  -f title="Release v2.0" -f body="What's new in v2.0..."
```

### 3. Batch Operations

**Why GraphQL?** Query multiple repositories, issues, or PRs in a **single API call** using aliases.

**Common Operations:**

- Fetch data from multiple repos simultaneously
- Compare stats across repositories
- Aggregate metrics from multiple sources
- Reduce API rate limit consumption

**Example Scenario:** Compare stargazer counts across multiple repos in one call.

```bash
# Batch query using aliases
gh api graphql -f query='
  {
    repo1: repository(owner: "facebook", name: "react") {
      name
      stargazerCount
      forkCount
    }
    repo2: repository(owner: "vuejs", name: "vue") {
      name
      stargazerCount
      forkCount
    }
    repo3: repository(owner: "angular", name: "angular") {
      name
      stargazerCount
      forkCount
    }
  }
'
```

**Result:** One API call instead of three, saving rate limit quota.

### 4. Complex Nested Queries

**Why GraphQL?** Fetch deeply nested relationships in a single request vs. multiple REST calls.

**Common Operations:**

- PR with reviews, comments, and status checks in one call
- Issue with timeline, reactions, and linked PRs
- Repository with open issues, recent PRs, and contributors
- User with repositories, contributions, and activity

**Example Scenario:** Get PR details with all reviews and status checks.

```bash
gh api graphql -f query='
  query($owner: String!, $repo: String!, $number: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $number) {
        title
        state
        author { login }
        reviews(first: 10) {
          nodes {
            author { login }
            state
            body
          }
        }
        commits(last: 1) {
          nodes {
            commit {
              statusCheckRollup {
                state
                contexts(last: 1) {
                  totalCount
                  checkRunCountsByState { state count }
                  statusContextCountsByState { state count }
                }
              }
            }
          }
        }
      }
    }
  }
' -f owner=myorg -f repo=myrepo -F number=123
```

**Alternative with REST:** Would require 3-4 separate API calls.

### 4a. Efficient CI Check Status Queries

**Why GraphQL?** The `statusCheckRollup` connection provides pre-aggregated count fields that avoid O(n) iteration over check nodes.

**Anti-pattern (inefficient):**

```graphql
# DON'T: Fetches up to 100 individual nodes (~5-10KB per PR)
statusCheckRollup {
  state
  contexts(last: 100) {
    nodes {
      ... on StatusContext { state }
      ... on CheckRun { status, conclusion }
    }
  }
}
```

**Optimal pattern:**

```graphql
# DO: Uses pre-aggregated counts (~300 bytes per PR, ~15-30x smaller)
statusCheckRollup {
  state
  contexts(last: 1) {
    totalCount
    checkRunCountsByState { state count }
    statusContextCountsByState { state count }
  }
}
```

**Available fields on `StatusCheckRollupContextConnection`:**

- `totalCount` - Total number of checks
- `checkRunCount` - Number of CheckRun checks
- `statusContextCount` - Number of StatusContext checks
- `checkRunCountsByState` - Array of `{state, count}` for CheckRuns
- `statusContextCountsByState` - Array of `{state, count}` for StatusContexts

**Passing criteria:**

- CheckRun states: `SUCCESS`, `SKIPPED`, `NEUTRAL`
- StatusContext states: `SUCCESS`

**Example: Calculate passing checks**

```python
def calculate_passing(contexts: dict) -> tuple[int, int]:
    """Returns (passing, total) from aggregated counts."""
    passing = 0
    for item in contexts.get("checkRunCountsByState", []):
        if item["state"] in {"SUCCESS", "SKIPPED", "NEUTRAL"}:
            passing += item["count"]
    for item in contexts.get("statusContextCountsByState", []):
        if item["state"] == "SUCCESS":
            passing += item["count"]
    return (passing, contexts["totalCount"])
```

**Performance comparison:**

| Approach           | Data per PR | 10 PRs    |
| ------------------ | ----------- | --------- |
| Fetching 100 nodes | ~5-10KB     | ~50-100KB |
| Aggregated counts  | ~300 bytes  | ~3KB      |

### 5. Advanced Issue Search

**Why GraphQL?** More powerful search syntax with complex filters and advanced operators.

**Common Operations:**

- Multi-criteria searches across repos
- Complex boolean logic (AND/OR/NOT)
- Date range filtering
- Reaction and comment count filtering
- Advanced sorting options

**Example Scenario:** Find high-priority bugs with specific labels across multiple repos.

```bash
gh api graphql -f query='
  query {
    search(
      query: "org:myorg label:bug label:priority-high state:open"
      type: ISSUE
      first: 50
    ) {
      issueCount
      nodes {
        ... on Issue {
          number
          title
          repository { nameWithOwner }
          labels(first: 5) {
            nodes { name }
          }
          createdAt
        }
      }
    }
  }
'
```

### 6. Custom Field Queries

**Why GraphQL?** Precise field selection reduces response size and improves performance.

**Common Operations:**

- Request only fields you need (no over-fetching)
- Avoid large payloads from REST endpoints
- Optimize for mobile or bandwidth-constrained environments
- Build custom data aggregations

**Example Scenario:** Get minimal PR data for dashboard display.

```bash
gh api graphql -f query='
  query($owner: String!, $repo: String!) {
    repository(owner: $owner, name: $repo) {
      pullRequests(first: 10, states: OPEN) {
        nodes {
          number
          title
          isDraft
          author { login }
          createdAt
        }
      }
    }
  }
' -f owner=myorg -f repo=myrepo
```

---

## Getting Started

### Authentication

Before using GraphQL API, ensure proper authentication and scopes:

```bash
# Check current auth status
gh auth status

# Login with specific scopes
gh auth login --scopes "project,read:discussion,repo"

# For Projects V2, ensure you have project scope
gh auth refresh --scopes "project"
```

**Required Scopes by Feature:**

- Projects V2: `project` (read/write) or `read:project` (read-only)
- Discussions: No special scope needed (included in `repo`)
- Repository data: `repo` (private repos) or public access
- User profile: No authentication needed (public data)

### Basic GraphQL Query Structure

```bash
gh api graphql -f query='
  query {
    viewer {
      login
      name
    }
  }
'
```

**Components:**

- `gh api graphql` - Command to invoke GraphQL endpoint
- `-f query='...'` - Flag to pass query string
- `query { ... }` - GraphQL query operation

### Basic GraphQL Mutation Structure

```bash
gh api graphql -f query='
  mutation($input: CreateIssueInput!) {
    createIssue(input: $input) {
      issue {
        id
        url
      }
    }
  }
' -f input='{"repositoryId":"...","title":"Bug report"}'
```

**Components:**

- `mutation { ... }` - GraphQL mutation operation
- `$input` - Variable declaration
- `input: $input` - Variable usage
- Return fields specified in nested object

---

## Common GraphQL Patterns

### Pattern 1: Using Variables

Variables make queries reusable and avoid string concatenation issues.

**Variable Types:**

- `-f variable=value` - String variable
- `-F variable=value` - Number, Boolean, or null variable

**Example:**

```bash
gh api graphql -f query='
  query($owner: String!, $repo: String!, $prNumber: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $prNumber) {
        title
        state
      }
    }
  }
' -f owner=facebook -f repo=react -F prNumber=12345
```

**Type Annotations:**

- `String!` - Required string
- `String` - Optional string
- `Int!` - Required integer
- `Boolean` - Optional boolean
- `ID!` - Required ID (special string type)

### Pattern 2: Pagination with Cursors

GitHub GraphQL uses cursor-based pagination for large datasets.

**Manual Pagination:**

```bash
gh api graphql -f query='
  query($owner: String!, $repo: String!, $cursor: String) {
    repository(owner: $owner, name: $repo) {
      issues(first: 100, after: $cursor, states: OPEN) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          number
          title
        }
      }
    }
  }
' -f owner=myorg -f repo=myrepo -f cursor=null
```

**Automatic Pagination:**

```bash
gh api graphql --paginate -f query='
  query($owner: String!, $repo: String!, $endCursor: String) {
    repository(owner: $owner, name: $repo) {
      issues(first: 100, after: $endCursor, states: OPEN) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          number
          title
        }
      }
    }
  }
' -f owner=myorg -f repo=myrepo
```

**Key Points:**

- `pageInfo` with `hasNextPage` and `endCursor` required for `--paginate`
- Variable must be named `$endCursor` for automatic pagination
- Default page size: 100 items (adjust with `first: N`)

### Pattern 3: ID Resolution (Query Before Mutation)

Most mutations require GraphQL node IDs, which must be queried first.

**Step 1: Query for IDs**

```bash
# Get repository ID
REPO_ID=$(gh api graphql -f query='
  query($owner: String!, $repo: String!) {
    repository(owner: $owner, name: $repo) {
      id
    }
  }
' -f owner=myorg -f repo=myrepo --jq '.data.repository.id')

# Get issue ID
ISSUE_ID=$(gh api graphql -f query='
  query($owner: String!, $repo: String!, $number: Int!) {
    repository(owner: $owner, name: $repo) {
      issue(number: $number) {
        id
      }
    }
  }
' -f owner=myorg -f repo=myrepo -F number=123 --jq '.data.repository.issue.id')
```

**Step 2: Use IDs in Mutation**

```bash
# Add issue to project using IDs
gh api graphql -f query='
  mutation($projectId: ID!, $contentId: ID!) {
    addProjectV2ItemById(input: {
      projectId: $projectId
      contentId: $contentId
    }) {
      item {
        id
      }
    }
  }
' -F projectId=$PROJECT_ID -F contentId=$ISSUE_ID
```

**Why This Pattern?**

- GraphQL uses opaque node IDs (e.g., `MDEwOlJlcG9zaXRvcnkxMjk2MjY5`)
- These differ from REST API IDs (e.g., issue number `123`)
- IDs ensure precise targeting across GitHub's distributed system

### Pattern 4: Batch Queries with Aliases

Use aliases to query multiple resources in parallel within one API call.

**Without Aliases (Error):**

```graphql
{
  repository(owner: "facebook", name: "react") {
    stargazerCount
  }
  repository(owner: "vuejs", name: "vue") {
    stargazerCount
  }
}
# ❌ Error: Duplicate field 'repository'
```

**With Aliases (Success):**

```bash
gh api graphql -f query='
  {
    react: repository(owner: "facebook", name: "react") {
      name
      stargazerCount
    }
    vue: repository(owner: "vuejs", name: "vue") {
      name
      stargazerCount
    }
    angular: repository(owner: "angular", name: "angular") {
      name
      stargazerCount
    }
  }
' --jq '.data | to_entries[] | "\(.key): \(.value.stargazerCount) stars"'
```

**Benefits:**

- One API call vs. three separate calls
- Lower rate limit consumption
- Faster response time
- Easier to aggregate results

### Pattern 5: Inline Fragments for Union/Interface Types

Use inline fragments when querying fields that return union or interface types.

**Example: Project Fields (Union Type)**

```bash
gh api graphql -f query='
  query($projectId: ID!) {
    node(id: $projectId) {
      ... on ProjectV2 {
        fields(first: 20) {
          nodes {
            ... on ProjectV2Field {
              id
              name
            }
            ... on ProjectV2SingleSelectField {
              id
              name
              options {
                id
                name
              }
            }
            ... on ProjectV2IterationField {
              id
              name
              configuration {
                iterations {
                  startDate
                  id
                }
              }
            }
          }
        }
      }
    }
  }
' -F projectId=$PROJECT_ID
```

**Why Inline Fragments?**

- Project fields can be different types (text, select, iteration, etc.)
- Each type has unique fields (e.g., `options` for select fields)
- Inline fragments (`... on TypeName`) specify per-type fields

### Pattern 6: Error Handling

GraphQL returns partial data with errors, unlike REST's all-or-nothing approach.

**Example Response with Errors:**

```json
{
  "data": {
    "repository": {
      "issue": null
    }
  },
  "errors": [
    {
      "type": "NOT_FOUND",
      "path": ["repository", "issue"],
      "message": "Could not resolve to an Issue with the number of 9999."
    }
  ]
}
```

**Handling in Scripts:**

```bash
response=$(gh api graphql -f query='...')

# Check for errors
if echo "$response" | jq -e '.errors' > /dev/null; then
  echo "GraphQL errors occurred:"
  echo "$response" | jq '.errors'
  exit 1
fi

# Process successful data
echo "$response" | jq '.data'
```

**Common Error Types:**

- `NOT_FOUND` - Resource doesn't exist
- `FORBIDDEN` - Insufficient permissions
- `VALIDATION_ERROR` - Invalid input
- `RATE_LIMITED` - API rate limit exceeded

### Pattern 7: Rate Limit Management

Check rate limits and optimize queries to stay within bounds.

**Check Current Rate Limit:**

```bash
gh api graphql -f query='
  query {
    rateLimit {
      limit
      cost
      remaining
      resetAt
    }
  }
'
```

**Query Cost Calculation:**

- Simple queries: 1 point
- Queries with connections: 1 + (first/100)
- Complex nested queries: Additive based on connections

**Optimization Strategies:**

- Use cursor pagination to fetch large datasets incrementally
- Batch queries with aliases instead of multiple calls
- Request only needed fields to reduce query complexity
- Use conditional requests with `If-None-Match` headers

**Example: Check Cost Before Running:**

```bash
# Add cost to any query
gh api graphql -f query='
  query {
    rateLimit { cost remaining }
    repository(owner: "facebook", name: "react") {
      issues(first: 100) {
        nodes { title }
      }
    }
  }
' --jq '.data.rateLimit'
```

---

## Complete Examples

### Example 1: Projects V2 - Full Workflow

**Scenario:** Create project, add issues, set status field.

**Step 1: Get Organization ID**

```bash
ORG_ID=$(gh api graphql -f query='
  query($login: String!) {
    organization(login: $login) {
      id
    }
  }
' -f login=myorg --jq '.data.organization.id')
```

**Step 2: Create Project**

```bash
PROJECT_ID=$(gh api graphql -f query='
  mutation($ownerId: ID!, $title: String!) {
    createProjectV2(input: {
      ownerId: $ownerId
      title: $title
    }) {
      projectV2 {
        id
        number
      }
    }
  }
' -F ownerId=$ORG_ID -f title="Q1 Roadmap" \
  --jq '.data.createProjectV2.projectV2.id')
```

**Step 3: Get Project Fields**

```bash
gh api graphql -f query='
  query($projectId: ID!) {
    node(id: $projectId) {
      ... on ProjectV2 {
        fields(first: 20) {
          nodes {
            ... on ProjectV2SingleSelectField {
              id
              name
              options {
                id
                name
              }
            }
          }
        }
      }
    }
  }
' -F projectId=$PROJECT_ID > project_fields.json

# Extract Status field ID and "In Progress" option ID
STATUS_FIELD_ID=$(jq -r '.data.node.fields.nodes[] | select(.name == "Status") | .id' project_fields.json)
IN_PROGRESS_ID=$(jq -r '.data.node.fields.nodes[] | select(.name == "Status") | .options[] | select(.name == "In Progress") | .id' project_fields.json)
```

**Step 4: Add Issue to Project**

```bash
# Get issue ID
ISSUE_ID=$(gh api graphql -f query='
  query($owner: String!, $repo: String!, $number: Int!) {
    repository(owner: $owner, name: $repo) {
      issue(number: $number) {
        id
      }
    }
  }
' -f owner=myorg -f repo=myrepo -F number=123 \
  --jq '.data.repository.issue.id')

# Add to project
ITEM_ID=$(gh api graphql -f query='
  mutation($projectId: ID!, $contentId: ID!) {
    addProjectV2ItemById(input: {
      projectId: $projectId
      contentId: $contentId
    }) {
      item {
        id
      }
    }
  }
' -F projectId=$PROJECT_ID -F contentId=$ISSUE_ID \
  --jq '.data.addProjectV2ItemById.item.id')
```

**Step 5: Update Status Field**

```bash
gh api graphql -f query='
  mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
    updateProjectV2ItemFieldValue(input: {
      projectId: $projectId
      itemId: $itemId
      fieldId: $fieldId
      value: { singleSelectOptionId: $optionId }
    }) {
      projectV2Item {
        id
      }
    }
  }
' -F projectId=$PROJECT_ID -F itemId=$ITEM_ID \
  -F fieldId=$STATUS_FIELD_ID -f optionId=$IN_PROGRESS_ID
```

### Example 2: Discussions - Create and Manage

**Step 1: Get Discussion Categories**

```bash
gh api graphql -H 'GraphQL-Features: discussions_api' -f query='
  query($owner: String!, $repo: String!) {
    repository(owner: $owner, name: $repo) {
      discussionCategories(first: 10) {
        nodes {
          id
          name
          description
        }
      }
    }
  }
' -f owner=myorg -f repo=myrepo > categories.json

# Find "Announcements" category
CATEGORY_ID=$(jq -r '.data.repository.discussionCategories.nodes[] | select(.name == "Announcements") | .id' categories.json)
```

**Step 2: Get Repository ID**

```bash
REPO_ID=$(gh api graphql -f query='
  query($owner: String!, $repo: String!) {
    repository(owner: $owner, name: $repo) {
      id
    }
  }
' -f owner=myorg -f repo=myrepo --jq '.data.repository.id')
```

**Step 3: Create Discussion**

```bash
DISCUSSION_ID=$(gh api graphql -H 'GraphQL-Features: discussions_api' -f query='
  mutation($repoId: ID!, $categoryId: ID!, $title: String!, $body: String!) {
    createDiscussion(input: {
      repositoryId: $repoId
      categoryId: $categoryId
      title: $title
      body: $body
    }) {
      discussion {
        id
        url
        number
      }
    }
  }
' -F repoId=$REPO_ID -F categoryId=$CATEGORY_ID \
  -f title="Release v2.0.0" \
  -f body="Excited to announce v2.0 with new features..." \
  --jq '.data.createDiscussion.discussion.id')
```

**Step 4: Add Comment**

```bash
gh api graphql -H 'GraphQL-Features: discussions_api' -f query='
  mutation($discussionId: ID!, $body: String!) {
    addDiscussionComment(input: {
      discussionId: $discussionId
      body: $body
    }) {
      comment {
        id
        url
      }
    }
  }
' -F discussionId=$DISCUSSION_ID \
  -f body="Read the full changelog: https://..."
```

### Example 3: Batch Repository Analysis

**Scenario:** Compare multiple repositories in one call.

```bash
gh api graphql -f query='
  {
    react: repository(owner: "facebook", name: "react") {
      name
      description
      stargazerCount
      forkCount
      openIssues: issues(states: OPEN) { totalCount }
      openPRs: pullRequests(states: OPEN) { totalCount }
      primaryLanguage { name }
    }
    vue: repository(owner: "vuejs", name: "vue") {
      name
      description
      stargazerCount
      forkCount
      openIssues: issues(states: OPEN) { totalCount }
      openPRs: pullRequests(states: OPEN) { totalCount }
      primaryLanguage { name }
    }
    angular: repository(owner: "angular", name: "angular") {
      name
      description
      stargazerCount
      forkCount
      openIssues: issues(states: OPEN) { totalCount }
      openPRs: pullRequests(states: OPEN) { totalCount }
      primaryLanguage { name }
    }
  }
' --jq '
  .data | to_entries[] |
  "\(.key):\n  Stars: \(.value.stargazerCount)\n  Forks: \(.value.forkCount)\n  Open Issues: \(.value.openIssues.totalCount)\n  Open PRs: \(.value.openPRs.totalCount)\n  Language: \(.value.primaryLanguage.name)\n"
'
```

**Output:**

```
react:
  Stars: 225000
  Forks: 45000
  Open Issues: 850
  Open PRs: 120
  Language: JavaScript

vue:
  Stars: 207000
  Forks: 35000
  Open Issues: 520
  Open PRs: 85
  Language: TypeScript

angular:
  Stars: 94000
  Forks: 25000
  Open Issues: 1850
  Open PRs: 220
  Language: TypeScript
```

### Example 4: Complex Nested Query - PR Analysis

**Scenario:** Get complete PR context in one call.

```bash
gh api graphql -f query='
  query($owner: String!, $repo: String!, $number: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $number) {
        title
        body
        state
        isDraft
        author { login }
        createdAt
        updatedAt

        # Reviews
        reviews(first: 10) {
          nodes {
            author { login }
            state
            body
            submittedAt
          }
        }

        # Comments
        comments(first: 20) {
          nodes {
            author { login }
            body
            createdAt
          }
        }

        # Status checks (using efficient aggregated counts)
        commits(last: 1) {
          nodes {
            commit {
              statusCheckRollup {
                state
                contexts(last: 1) {
                  totalCount
                  checkRunCountsByState { state count }
                  statusContextCountsByState { state count }
                }
              }
            }
          }
        }

        # Files changed
        files(first: 100) {
          nodes {
            path
            additions
            deletions
          }
        }
      }
    }
  }
' -f owner=myorg -f repo=myrepo -F number=456
```

**Alternative with REST:** Would require 5+ separate API calls:

1. `GET /repos/:owner/:repo/pulls/:number`
2. `GET /repos/:owner/:repo/pulls/:number/reviews`
3. `GET /repos/:owner/:repo/issues/:number/comments`
4. `GET /repos/:owner/:repo/commits/:sha/status`
5. `GET /repos/:owner/:repo/pulls/:number/files`

### Example 5: Advanced Issue Search

**Scenario:** Find issues matching complex criteria.

```bash
gh api graphql -f query='
  query {
    search(
      query: "org:myorg is:issue is:open label:bug label:priority-high created:>2025-01-01 comments:>5"
      type: ISSUE
      first: 50
    ) {
      issueCount
      nodes {
        ... on Issue {
          number
          title
          repository { nameWithOwner }
          author { login }
          createdAt
          labels(first: 10) {
            nodes { name color }
          }
          comments { totalCount }
          reactions { totalCount }
        }
      }
    }
  }
' --jq '
  "Total matching issues: \(.data.search.issueCount)\n\n" +
  (.data.search.nodes[] |
    "[\(.repository.nameWithOwner)#\(.number)] \(.title)\n  Author: \(.author.login) | Created: \(.createdAt) | Comments: \(.comments.totalCount)\n  Labels: \(.labels.nodes | map(.name) | join(", "))\n"
  )
'
```

**Search Query Syntax:**

- `org:myorg` - Organization filter
- `is:issue` - Type filter
- `is:open` - State filter
- `label:bug` - Label filter (can specify multiple)
- `created:>2025-01-01` - Date range
- `comments:>5` - Comment count filter

---

## Schema Reference

### Core Object Types

#### Repository

Represents a Git repository.

**Key Fields:**

- `id: ID!` - Node ID
- `name: String!` - Repository name
- `nameWithOwner: String!` - Full name (owner/repo)
- `description: String` - Repository description
- `url: URI!` - GitHub URL
- `issues(...)` - Issues connection
- `pullRequests(...)` - PRs connection
- `projects(...)` - Projects connection (legacy)
- `projectsV2(...)` - Projects V2 connection
- `discussions(...)` - Discussions connection

#### Issue

A trackable work item.

**Key Fields:**

- `id: ID!` - Node ID
- `number: Int!` - Issue number
- `title: String!` - Issue title
- `body: String` - Issue description
- `state: IssueState!` - OPEN or CLOSED
- `author: Actor` - Issue creator
- `assignees(...)` - Assigned users
- `labels(...)` - Labels
- `comments(...)` - Comments
- `projectItems(...)` - Associated project items

#### PullRequest

A code review request.

**Key Fields:**

- `id: ID!` - Node ID
- `number: Int!` - PR number
- `title: String!` - PR title
- `body: String` - PR description
- `state: PullRequestState!` - OPEN, CLOSED, or MERGED
- `isDraft: Boolean!` - Draft status
- `mergeable: MergeableState!` - Merge status
- `reviews(...)` - Code reviews
- `commits(...)` - Commits
- `files(...)` - Changed files

#### ProjectV2

The current GitHub Projects.

**Key Fields:**

- `id: ID!` - Node ID
- `number: Int!` - Project number
- `title: String!` - Project title
- `shortDescription: String` - Description
- `items(...)` - Project items
- `fields(...)` - Project fields (returns union type)
- `views(...)` - Project views

**Field Types (Union):**

- `ProjectV2Field` - Text, number, date
- `ProjectV2SingleSelectField` - Dropdown with options
- `ProjectV2IterationField` - Sprint/iteration field

#### Discussion

A discussion thread.

**Key Fields:**

- `id: ID!` - Node ID
- `number: Int!` - Discussion number
- `title: String!` - Discussion title
- `body: String` - Discussion content
- `category: DiscussionCategory!` - Category
- `author: Actor` - Discussion creator
- `comments(...)` - Comments
- `answer: DiscussionComment` - Marked answer

#### User

A GitHub user account.

**Key Fields:**

- `id: ID!` - Node ID
- `login: String!` - Username
- `name: String` - Display name
- `email: String` - Public email
- `avatarUrl: URI!` - Avatar image
- `repositories(...)` - User repositories
- `issues(...)` - Created issues
- `pullRequests(...)` - Created PRs

#### Organization

An organization account.

**Key Fields:**

- `id: ID!` - Node ID
- `login: String!` - Organization name
- `name: String` - Display name
- `description: String` - Description
- `repositories(...)` - Org repositories
- `teams(...)` - Org teams
- `projectsV2(...)` - Org projects

### Common Mutations

#### Issue Mutations

- `createIssue(input: CreateIssueInput!)` - Create issue
- `updateIssue(input: UpdateIssueInput!)` - Update issue
- `closeIssue(input: CloseIssueInput!)` - Close issue
- `reopenIssue(input: ReopenIssueInput!)` - Reopen issue
- `addLabelsToLabelable(input: AddLabelsToLabelableInput!)` - Add labels
- `addAssigneesToAssignable(input: AddAssigneesToAssignableInput!)` - Add assignees

#### Pull Request Mutations

- `createPullRequest(input: CreatePullRequestInput!)` - Create PR
- `updatePullRequest(input: UpdatePullRequestInput!)` - Update PR
- `closePullRequest(input: ClosePullRequestInput!)` - Close PR
- `mergePullRequest(input: MergePullRequestInput!)` - Merge PR
- `addPullRequestReview(input: AddPullRequestReviewInput!)` - Add review

#### Projects V2 Mutations

- `createProjectV2(input: CreateProjectV2Input!)` - Create project
- `updateProjectV2(input: UpdateProjectV2Input!)` - Update project
- `deleteProjectV2(input: DeleteProjectV2Input!)` - Delete project
- `addProjectV2ItemById(input: AddProjectV2ItemByIdInput!)` - Add item
- `updateProjectV2ItemFieldValue(input: UpdateProjectV2ItemFieldValueInput!)` - Update field
- `deleteProjectV2Item(input: DeleteProjectV2ItemInput!)` - Delete item

#### Discussion Mutations

- `createDiscussion(input: CreateDiscussionInput!)` - Create discussion
- `updateDiscussion(input: UpdateDiscussionInput!)` - Update discussion
- `closeDiscussion(input: CloseDiscussionInput!)` - Close discussion
- `addDiscussionComment(input: AddDiscussionCommentInput!)` - Add comment
- `markDiscussionCommentAsAnswer(input: MarkDiscussionCommentAsAnswerInput!)` - Mark answer

### Schema Introspection

**Query Schema via gh CLI:**

```bash
# Get all type names
gh api graphql -f query='
  query {
    __schema {
      types {
        name
        kind
      }
    }
  }
'

# Get fields for specific type
gh api graphql -f query='
  query {
    __type(name: "Repository") {
      fields {
        name
        type {
          name
          kind
        }
      }
    }
  }
'
```

**Official Schema Documentation:**

- Full schema: https://docs.github.com/en/graphql/reference
- Object types: https://docs.github.com/en/graphql/reference/objects
- Mutations: https://docs.github.com/en/graphql/reference/mutations
- Enums: https://docs.github.com/en/graphql/reference/enums

---

## Best Practices

### 1. Request Only What You Need

**❌ Over-fetching:**

```graphql
query {
  repository(owner: "facebook", name: "react") {
    # Fetches ALL fields (expensive)
  }
}
```

**✅ Selective fields:**

```graphql
query {
  repository(owner: "facebook", name: "react") {
    name
    stargazerCount
  }
}
```

### 2. Use Pagination for Large Datasets

**❌ Fetching too many items:**

```graphql
query {
  repository(owner: "facebook", name: "react") {
    issues(first: 10000) {
      # Max is 100
      nodes {
        title
      }
    }
  }
}
```

**✅ Paginated approach:**

```graphql
query ($cursor: String) {
  repository(owner: "facebook", name: "react") {
    issues(first: 100, after: $cursor) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        title
      }
    }
  }
}
```

### 3. Batch Related Queries

**❌ Multiple API calls:**

```bash
gh api graphql -f query='{ repo1: repository(...) { stargazerCount } }'
gh api graphql -f query='{ repo2: repository(...) { stargazerCount } }'
gh api graphql -f query='{ repo3: repository(...) { stargazerCount } }'
```

**✅ Single batched call:**

```bash
gh api graphql -f query='
  {
    repo1: repository(...) { stargazerCount }
    repo2: repository(...) { stargazerCount }
    repo3: repository(...) { stargazerCount }
  }
'
```

### 4. Handle Errors Gracefully

**✅ Check for errors in responses:**

```bash
response=$(gh api graphql -f query='...')

if echo "$response" | jq -e '.errors' > /dev/null; then
  echo "Errors occurred:"
  echo "$response" | jq '.errors[] | "\(.type): \(.message)"'
  exit 1
fi
```

### 5. Monitor Rate Limits

**✅ Track rate limit usage:**

```bash
gh api graphql -f query='
  {
    rateLimit {
      cost
      remaining
      resetAt
    }
    # ... your actual query
  }
'
```

### 6. Use Modern Node IDs

**✅ Use X-Github-Next-Global-ID header:**

```bash
gh api graphql -H 'X-Github-Next-Global-ID: 1' -f query='...'
```

This ensures you get modern node IDs that work across GitHub's infrastructure.

---

## Troubleshooting

### Common Issues

#### 1. "Could not resolve to a X with the id of Y"

**Cause:** Using wrong ID type (REST ID vs. GraphQL node ID).

**Solution:** Query for the GraphQL node ID first:

```bash
# Get node ID from issue number
gh api graphql -f query='
  query($owner: String!, $repo: String!, $number: Int!) {
    repository(owner: $owner, name: $repo) {
      issue(number: $number) {
        id  # This is the GraphQL node ID
      }
    }
  }
' -f owner=myorg -f repo=myrepo -F number=123
```

#### 2. "Field 'X' doesn't exist on type 'Y'"

**Cause:** Incorrect field name or missing inline fragment for union types.

**Solution:** Check schema documentation or use introspection:

```bash
gh api graphql -f query='
  query {
    __type(name: "ProjectV2") {
      fields {
        name
      }
    }
  }
'
```

#### 3. "Variable $X of type Y! was provided invalid value"

**Cause:** Wrong variable flag (`-f` vs `-F`) or incorrect type.

**Solution:**

- Use `-f` for strings: `-f title="My issue"`
- Use `-F` for numbers/booleans: `-F number=123`

#### 4. "Was provided invalid value for Y (Expected value to not be null)"

**Cause:** Required field missing or null.

**Solution:** Check mutation input requirements:

```bash
# Required fields have ! in schema
mutation($input: CreateIssueInput!) {
  # CreateIssueInput requires: repositoryId, title
}
```

#### 5. Rate Limit Exceeded

**Error:** `"message": "API rate limit exceeded"`

**Solution:**

- Check reset time: `gh api rate_limit`
- Use pagination to reduce query cost
- Batch queries with aliases
- Wait until rate limit resets

#### 6. Pagination Not Working with --paginate

**Cause:** Missing `pageInfo` or wrong variable name.

**Solution:** Ensure your query includes:

```graphql
query($endCursor: String) {  # Must be named $endCursor
  repository(...) {
    issues(after: $endCursor) {
      pageInfo {
        hasNextPage  # Required
        endCursor    # Required
      }
      nodes { ... }
    }
  }
}
```

#### 7. "GraphQL-Features header required"

**Error:** `"message": "This API requires GraphQL-Features header"`

**Solution:** Add header for Discussions API:

```bash
gh api graphql -H 'GraphQL-Features: discussions_api' -f query='...'
```

### Debugging Tips

**1. Pretty-print JSON response:**

```bash
gh api graphql -f query='...' | jq '.'
```

**2. Save response to file for inspection:**

```bash
gh api graphql -f query='...' > response.json
```

**3. Test queries in GitHub GraphQL Explorer:**
https://docs.github.com/en/graphql/overview/explorer

**4. Enable debug mode:**

```bash
GH_DEBUG=api gh api graphql -f query='...'
```

**5. Validate query syntax:**
Use online GraphQL validator or GitHub's schema explorer.

---

## Additional Resources

### Official Documentation

- GitHub GraphQL API: https://docs.github.com/en/graphql
- Schema reference: https://docs.github.com/en/graphql/reference
- Guides: https://docs.github.com/en/graphql/guides
- Explorer (interactive): https://docs.github.com/en/graphql/overview/explorer

### GitHub CLI

- `gh api` documentation: https://cli.github.com/manual/gh_api
- GitHub CLI manual: https://cli.github.com/manual/

### GraphQL Learning

- GraphQL.org: https://graphql.org/learn/
- GraphQL queries: https://graphql.org/learn/queries/
- GraphQL best practices: https://graphql.org/learn/best-practices/

### Related Skills

- `gh` skill: General GitHub CLI guidance (`references/gh.md`)
- `graphite` skill: Stacked PR workflows (uses gh under the hood)
