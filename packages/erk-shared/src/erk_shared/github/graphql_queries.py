"""GraphQL queries and mutations for GitHub API.

These are stored in a separate file to keep the implementation code clean
and make the queries easier to read and maintain.
"""

# Query to fetch PR review threads with comments
GET_PR_REVIEW_THREADS_QUERY = """query($owner: String!, $repo: String!, $number: Int!) {
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

# Fragment for PR linkage data on CrossReferencedEvent
# Used by _build_issue_pr_linkage_query for batch issue queries
ISSUE_PR_LINKAGE_FRAGMENT = """fragment IssuePRLinkageFields on CrossReferencedEvent {
  willCloseTarget
  source {
    ... on PullRequest {
      number
      state
      url
      isDraft
      createdAt
      statusCheckRollup {
        state
        contexts(last: 1) {
          totalCount
          checkRunCountsByState { state count }
          statusContextCountsByState { state count }
        }
      }
      mergeable
    }
  }
}"""

# Parameterized query for workflow runs by node IDs
# Uses the nodes(ids: [...]) interface for efficient batch fetching
GET_WORKFLOW_RUNS_BY_NODE_IDS_QUERY = """query($nodeIds: [ID!]!) {
  nodes(ids: $nodeIds) {
    ... on WorkflowRun {
      id
      databaseId
      url
      createdAt
      checkSuite {
        status
        conclusion
        commit { oid }
      }
    }
  }
}"""

# Parameterized query for issues with PR linkages
# Note: filterBy is optional - pass null if not filtering by creator
GET_ISSUES_WITH_PR_LINKAGES_QUERY = """query(
  $owner: String!
  $repo: String!
  $labels: [String!]!
  $states: [IssueState!]!
  $first: Int!
  $filterBy: IssueFilters
) {
  repository(owner: $owner, name: $repo) {
    issues(
      labels: $labels
      states: $states
      filterBy: $filterBy
      first: $first
      orderBy: {field: UPDATED_AT, direction: DESC}
    ) {
      nodes {
        number
        title
        body
        state
        url
        author { login }
        labels(first: 100) { nodes { name } }
        assignees(first: 100) { nodes { login } }
        createdAt
        updatedAt
        timelineItems(itemTypes: [CROSS_REFERENCED_EVENT], first: 20) {
          nodes {
            ... on CrossReferencedEvent {
              willCloseTarget
              source {
                ... on PullRequest {
                  number
                  state
                  url
                  isDraft
                  createdAt
                  statusCheckRollup {
                    state
                    contexts(last: 1) {
                      totalCount
                      checkRunCountsByState { state count }
                      statusContextCountsByState { state count }
                    }
                  }
                  mergeable
                }
              }
            }
          }
        }
      }
    }
  }
}"""
