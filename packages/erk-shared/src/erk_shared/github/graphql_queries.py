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
