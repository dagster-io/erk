# GitHub GraphQL Schema - Core Types

This document provides a focused reference for the most commonly used GraphQL types and fields in GitHub's API. For the complete schema, visit: https://docs.github.com/en/graphql/reference

**Load this document only when you need detailed field information for specific types.** Most use cases are covered in `graphql.md`.

---

## Repository

Represents a Git repository.

```graphql
type Repository {
  # Identifiers
  id: ID!
  databaseId: Int!
  name: String!
  nameWithOwner: String!

  # Basic info
  description: String
  url: URI!
  homepageUrl: URI
  isPrivate: Boolean!
  isFork: Boolean!
  isArchived: Boolean!

  # Ownership
  owner: RepositoryOwner!

  # Dates
  createdAt: DateTime!
  updatedAt: DateTime!
  pushedAt: DateTime

  # Stats
  stargazerCount: Int!
  forkCount: Int!

  # Language
  primaryLanguage: Language

  # Connections
  issues(
    first: Int
    after: String
    states: [IssueState!]
    labels: [String!]
    orderBy: IssueOrder
  ): IssueConnection!

  pullRequests(
    first: Int
    after: String
    states: [PullRequestState!]
    baseRefName: String
    headRefName: String
  ): PullRequestConnection!

  discussions(first: Int, after: String, categoryId: ID): DiscussionConnection!

  discussionCategories(first: Int, after: String): DiscussionCategoryConnection!

  projectsV2(first: Int, after: String): ProjectV2Connection!

  refs(
    first: Int
    after: String
    refPrefix: String! # "refs/heads/" or "refs/tags/"
  ): RefConnection!

  defaultBranchRef: Ref

  # Access
  viewerCanAdminister: Boolean!
  viewerCanUpdateTopics: Boolean!
  viewerHasStarred: Boolean!
}
```

**Common Queries:**

```graphql
# Basic repo info
query {
  repository(owner: "facebook", name: "react") {
    id
    name
    stargazerCount
    forkCount
  }
}

# Repo with open issues
query {
  repository(owner: "myorg", name: "myrepo") {
    issues(first: 10, states: OPEN) {
      nodes {
        number
        title
      }
    }
  }
}
```

---

## Issue

A trackable work item.

```graphql
type Issue {
  # Identifiers
  id: ID!
  databaseId: Int!
  number: Int!

  # Content
  title: String!
  body: String
  bodyHTML: HTML!
  bodyText: String!

  # Status
  state: IssueState! # OPEN or CLOSED
  stateReason: IssueStateReason # COMPLETED, NOT_PLANNED, REOPENED
  closed: Boolean!
  locked: Boolean!

  # Metadata
  author: Actor
  createdAt: DateTime!
  updatedAt: DateTime!
  closedAt: DateTime

  # Repository
  repository: Repository!
  url: URI!

  # Connections
  assignees(first: Int, after: String): UserConnection!

  labels(first: Int, after: String): LabelConnection!

  comments(first: Int, after: String): IssueCommentConnection!

  projectItems(
    first: Int
    after: String
    includeArchived: Boolean = true
  ): ProjectV2ItemConnection!

  milestone: Milestone

  timelineItems(
    first: Int
    after: String
    itemTypes: [IssueTimelineItemsItemType!]
  ): IssueTimelineItemsConnection!

  # Reactions
  reactions(first: Int, content: ReactionContent): ReactionConnection!

  # Access
  viewerCanUpdate: Boolean!
  viewerCanReact: Boolean!
  viewerDidAuthor: Boolean!
}
```

**Common Queries:**

```graphql
# Issue with assignees and labels
query {
  repository(owner: "myorg", name: "myrepo") {
    issue(number: 123) {
      title
      state
      assignees(first: 5) {
        nodes {
          login
        }
      }
      labels(first: 10) {
        nodes {
          name
          color
        }
      }
    }
  }
}

# Issue with comments
query {
  repository(owner: "myorg", name: "myrepo") {
    issue(number: 123) {
      title
      comments(first: 50) {
        nodes {
          author {
            login
          }
          body
          createdAt
        }
      }
    }
  }
}
```

**Common Mutations:**

```graphql
# Create issue
mutation ($repoId: ID!, $title: String!, $body: String) {
  createIssue(input: { repositoryId: $repoId, title: $title, body: $body }) {
    issue {
      id
      number
      url
    }
  }
}

# Add labels
mutation ($issueId: ID!, $labelIds: [ID!]!) {
  addLabelsToLabelable(input: { labelableId: $issueId, labelIds: $labelIds }) {
    labelable {
      ... on Issue {
        labels(first: 10) {
          nodes {
            name
          }
        }
      }
    }
  }
}

# Close issue
mutation ($issueId: ID!) {
  closeIssue(input: { issueId: $issueId, stateReason: COMPLETED }) {
    issue {
      state
      closedAt
    }
  }
}
```

---

## PullRequest

A code review request.

```graphql
type PullRequest {
  # Identifiers
  id: ID!
  databaseId: Int!
  number: Int!

  # Content
  title: String!
  body: String
  bodyHTML: HTML!

  # Status
  state: PullRequestState! # OPEN, CLOSED, MERGED
  isDraft: Boolean!
  merged: Boolean!
  mergeable: MergeableState! # MERGEABLE, CONFLICTING, UNKNOWN
  closed: Boolean!
  locked: Boolean!

  # Dates
  createdAt: DateTime!
  updatedAt: DateTime!
  closedAt: DateTime
  mergedAt: DateTime

  # Authors
  author: Actor
  mergedBy: Actor

  # Repository
  repository: Repository!
  url: URI!

  # Branches
  baseRefName: String!
  headRefName: String!
  baseRefOid: GitObjectID!
  headRefOid: GitObjectID!

  # Changes
  additions: Int!
  deletions: Int!
  changedFiles: Int!

  # Connections
  assignees(first: Int, after: String): UserConnection!

  labels(first: Int, after: String): LabelConnection!

  reviewRequests(first: Int, after: String): ReviewRequestConnection!

  reviews(
    first: Int
    after: String
    states: [PullRequestReviewState!]
    author: String
  ): PullRequestReviewConnection!

  comments(first: Int, after: String): IssueCommentConnection!

  reviewThreads(first: Int, after: String): PullRequestReviewThreadConnection!

  commits(first: Int, after: String): PullRequestCommitConnection!

  files(first: Int, after: String): PullRequestChangedFileConnection!

  projectItems(
    first: Int
    after: String
    includeArchived: Boolean = true
  ): ProjectV2ItemConnection!

  milestone: Milestone

  # Access
  viewerCanUpdate: Boolean!
  viewerCanReact: Boolean!
  viewerDidAuthor: Boolean!
  viewerCanApplySuggestion: Boolean!
}
```

**Nested Type: PullRequestReview**

```graphql
type PullRequestReview {
  id: ID!
  author: Actor
  body: String!
  state: PullRequestReviewState! # PENDING, COMMENTED, APPROVED, CHANGES_REQUESTED, DISMISSED
  submittedAt: DateTime
  createdAt: DateTime!

  comments(first: Int): PullRequestReviewCommentConnection!
}
```

**Nested Type: PullRequestChangedFile**

```graphql
type PullRequestChangedFile {
  path: String!
  additions: Int!
  deletions: Int!
  changeType: PatchStatus! # ADDED, DELETED, MODIFIED, RENAMED, COPIED, CHANGED
}
```

**Common Queries:**

```graphql
# PR with reviews and status
query {
  repository(owner: "myorg", name: "myrepo") {
    pullRequest(number: 456) {
      title
      state
      isDraft
      mergeable

      reviews(first: 10) {
        nodes {
          author {
            login
          }
          state
          body
        }
      }

      commits(last: 1) {
        nodes {
          commit {
            statusCheckRollup {
              state
            }
          }
        }
      }
    }
  }
}

# PR with files changed
query {
  repository(owner: "myorg", name: "myrepo") {
    pullRequest(number: 456) {
      files(first: 100) {
        nodes {
          path
          additions
          deletions
          changeType
        }
      }
    }
  }
}
```

**Common Mutations:**

```graphql
# Create PR
mutation (
  $repoId: ID!
  $baseRefName: String!
  $headRefName: String!
  $title: String!
  $body: String
) {
  createPullRequest(
    input: {
      repositoryId: $repoId
      baseRefName: $baseRefName
      headRefName: $headRefName
      title: $title
      body: $body
    }
  ) {
    pullRequest {
      id
      number
      url
    }
  }
}

# Merge PR
mutation ($prId: ID!, $commitHeadline: String) {
  mergePullRequest(
    input: {
      pullRequestId: $prId
      commitHeadline: $commitHeadline
      mergeMethod: SQUASH
    }
  ) {
    pullRequest {
      merged
      mergedAt
    }
  }
}
```

---

## ProjectV2

GitHub Projects (current version).

```graphql
type ProjectV2 {
  # Identifiers
  id: ID!
  databaseId: Int!
  number: Int!

  # Content
  title: String!
  shortDescription: String
  readme: String

  # Status
  public: Boolean!
  closed: Boolean!

  # Dates
  createdAt: DateTime!
  updatedAt: DateTime!
  closedAt: DateTime

  # Ownership
  owner: ProjectV2Owner!
  url: URI!

  # Connections
  items(
    first: Int
    after: String
    orderBy: ProjectV2ItemOrder
  ): ProjectV2ItemConnection!

  fields(
    first: Int
    after: String
    orderBy: ProjectV2FieldOrder
  ): ProjectV2FieldConnection!

  views(
    first: Int
    after: String
    orderBy: ProjectV2ViewOrder
  ): ProjectV2ViewConnection!

  # Access
  viewerCanUpdate: Boolean!
  viewerCanClose: Boolean!
}
```

**Field Types (Union):**

```graphql
# Base field type
type ProjectV2Field {
  id: ID!
  name: String!
  dataType: ProjectV2FieldType! # TEXT, NUMBER, DATE, SINGLE_SELECT, ITERATION
  createdAt: DateTime!
  updatedAt: DateTime!
}

# Single select dropdown
type ProjectV2SingleSelectField {
  id: ID!
  name: String!
  dataType: ProjectV2FieldType!

  options: [ProjectV2SingleSelectFieldOption!]!
}

type ProjectV2SingleSelectFieldOption {
  id: String!
  name: String!
  color: ProjectV2SingleSelectFieldOptionColor!
  description: String
}

# Iteration/Sprint field
type ProjectV2IterationField {
  id: ID!
  name: String!
  dataType: ProjectV2FieldType!

  configuration: ProjectV2IterationFieldConfiguration!
}

type ProjectV2IterationFieldConfiguration {
  iterations: [ProjectV2IterationFieldIteration!]!
  completedIterations: [ProjectV2IterationFieldIteration!]!
  duration: Int!
  startDay: Int!
}

type ProjectV2IterationFieldIteration {
  id: String!
  title: String!
  startDate: Date!
  duration: Int!
}
```

**ProjectV2Item:**

```graphql
type ProjectV2Item {
  id: ID!
  databaseId: Int!

  # Dates
  createdAt: DateTime!
  updatedAt: DateTime!

  # Content (union type)
  content: ProjectV2ItemContent # Issue, PullRequest, or DraftIssue
  # Project
  project: ProjectV2!

  # Field values
  fieldValues(first: Int, after: String): ProjectV2ItemFieldValueConnection!

  fieldValueByName(name: String!): ProjectV2ItemFieldValue
}
```

**Common Queries:**

```graphql
# Get project with fields
query {
  organization(login: "myorg") {
    projectV2(number: 1) {
      id
      title
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
                id
                title
                startDate
              }
            }
          }
        }
      }
    }
  }
}

# Get project items with content
query {
  node(id: "PROJECT_ID") {
    ... on ProjectV2 {
      items(first: 50) {
        nodes {
          id
          content {
            ... on Issue {
              number
              title
              repository {
                nameWithOwner
              }
            }
            ... on PullRequest {
              number
              title
              repository {
                nameWithOwner
              }
            }
          }
        }
      }
    }
  }
}
```

**Common Mutations:**

```graphql
# Create project
mutation ($ownerId: ID!, $title: String!) {
  createProjectV2(input: { ownerId: $ownerId, title: $title }) {
    projectV2 {
      id
      number
      url
    }
  }
}

# Add item to project
mutation ($projectId: ID!, $contentId: ID!) {
  addProjectV2ItemById(
    input: { projectId: $projectId, contentId: $contentId }
  ) {
    item {
      id
    }
  }
}

# Update field value (text/number/date)
mutation ($projectId: ID!, $itemId: ID!, $fieldId: ID!, $value: String!) {
  updateProjectV2ItemFieldValue(
    input: {
      projectId: $projectId
      itemId: $itemId
      fieldId: $fieldId
      value: { text: $value }
    }
  ) {
    projectV2Item {
      id
    }
  }
}

# Update single select field
mutation ($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
  updateProjectV2ItemFieldValue(
    input: {
      projectId: $projectId
      itemId: $itemId
      fieldId: $fieldId
      value: { singleSelectOptionId: $optionId }
    }
  ) {
    projectV2Item {
      id
    }
  }
}

# Update iteration field
mutation ($projectId: ID!, $itemId: ID!, $fieldId: ID!, $iterationId: String!) {
  updateProjectV2ItemFieldValue(
    input: {
      projectId: $projectId
      itemId: $itemId
      fieldId: $fieldId
      value: { iterationId: $iterationId }
    }
  ) {
    projectV2Item {
      id
    }
  }
}
```

---

## Discussion

A discussion thread.

```graphql
type Discussion {
  # Identifiers
  id: ID!
  databaseId: Int!
  number: Int!

  # Content
  title: String!
  body: String!
  bodyHTML: HTML!

  # Status
  locked: Boolean!
  closed: Boolean!

  # Metadata
  author: Actor
  createdAt: DateTime!
  updatedAt: DateTime!
  closedAt: DateTime

  # Category
  category: DiscussionCategory!

  # Repository
  repository: Repository!
  url: URI!

  # Answer
  answer: DiscussionComment
  answerChosenAt: DateTime
  answerChosenBy: Actor

  # Connections
  comments(first: Int, after: String): DiscussionCommentConnection!

  labels(first: Int, after: String): LabelConnection!

  reactions(first: Int, content: ReactionContent): ReactionConnection!

  # Poll (if discussion is a poll)
  poll: DiscussionPoll

  # Access
  viewerCanUpdate: Boolean!
  viewerCanReact: Boolean!
  viewerDidAuthor: Boolean!
}
```

**DiscussionCategory:**

```graphql
type DiscussionCategory {
  id: ID!
  name: String!
  description: String
  emoji: String!
  emojiHTML: HTML!

  # If true, only maintainers can create discussions in this category
  isAnswerable: Boolean!

  repository: Repository!
}
```

**DiscussionComment:**

```graphql
type DiscussionComment {
  id: ID!
  databaseId: Int!

  body: String!
  bodyHTML: HTML!

  author: Actor
  createdAt: DateTime!
  updatedAt: DateTime!

  discussion: Discussion!
  url: URI!

  # If comment is a reply
  replyTo: DiscussionComment

  # Nested replies
  replies(first: Int, after: String): DiscussionCommentConnection!

  reactions(first: Int, content: ReactionContent): ReactionConnection!

  viewerCanUpdate: Boolean!
  viewerCanReact: Boolean!
  viewerDidAuthor: Boolean!
}
```

**Common Queries:**

```graphql
# Discussion with comments
query {
  repository(owner: "myorg", name: "myrepo") {
    discussion(number: 10) {
      title
      body
      category {
        name
        emoji
      }
      answer {
        body
        author {
          login
        }
      }
      comments(first: 50) {
        nodes {
          author {
            login
          }
          body
          createdAt
          replies(first: 10) {
            nodes {
              author {
                login
              }
              body
            }
          }
        }
      }
    }
  }
}

# Discussion categories
query {
  repository(owner: "myorg", name: "myrepo") {
    discussionCategories(first: 20) {
      nodes {
        id
        name
        description
        emoji
        isAnswerable
      }
    }
  }
}
```

**Common Mutations:**

**Note:** Discussions API requires special header: `-H 'GraphQL-Features: discussions_api'`

```graphql
# Create discussion
mutation ($repoId: ID!, $categoryId: ID!, $title: String!, $body: String!) {
  createDiscussion(
    input: {
      repositoryId: $repoId
      categoryId: $categoryId
      title: $title
      body: $body
    }
  ) {
    discussion {
      id
      number
      url
    }
  }
}

# Add comment
mutation ($discussionId: ID!, $body: String!) {
  addDiscussionComment(input: { discussionId: $discussionId, body: $body }) {
    comment {
      id
      url
    }
  }
}

# Reply to comment
mutation ($discussionId: ID!, $replyToId: ID!, $body: String!) {
  addDiscussionComment(
    input: { discussionId: $discussionId, replyToId: $replyToId, body: $body }
  ) {
    comment {
      id
      url
    }
  }
}

# Mark comment as answer
mutation ($id: ID!) {
  markDiscussionCommentAsAnswer(input: { id: $id }) {
    discussion {
      answer {
        id
        body
      }
    }
  }
}
```

---

## User

A GitHub user account.

```graphql
type User {
  # Identifiers
  id: ID!
  databaseId: Int!
  login: String!

  # Profile
  name: String
  email: String!
  bio: String
  bioHTML: HTML!
  avatarUrl(size: Int): URI!
  websiteUrl: URI
  location: String
  company: String

  # Status
  isHireable: Boolean!
  isCampusExpert: Boolean!
  isDeveloperProgramMember: Boolean!

  # Dates
  createdAt: DateTime!
  updatedAt: DateTime!

  # Connections
  repositories(
    first: Int
    after: String
    privacy: RepositoryPrivacy
    orderBy: RepositoryOrder
  ): RepositoryConnection!

  issues(first: Int, after: String, states: [IssueState!]): IssueConnection!

  pullRequests(
    first: Int
    after: String
    states: [PullRequestState!]
  ): PullRequestConnection!

  followers(first: Int, after: String): FollowerConnection!
  following(first: Int, after: String): FollowingConnection!

  # Stats
  repositoriesContributedTo(
    first: Int
    contributionTypes: [RepositoryContributionType!]
  ): RepositoryConnection!
}
```

**Common Queries:**

```graphql
# User profile
query {
  user(login: "octocat") {
    name
    login
    bio
    avatarUrl
    company
    location
    websiteUrl

    repositories(first: 10, orderBy: { field: STARGAZERS, direction: DESC }) {
      nodes {
        name
        stargazerCount
      }
    }
  }
}

# Current authenticated user
query {
  viewer {
    login
    name
    email
  }
}
```

---

## Organization

An organization account.

```graphql
type Organization {
  # Identifiers
  id: ID!
  databaseId: Int!
  login: String!

  # Profile
  name: String
  description: String
  email: String
  websiteUrl: URI
  location: String
  avatarUrl(size: Int): URI!

  # Dates
  createdAt: DateTime!
  updatedAt: DateTime!

  # Connections
  repositories(
    first: Int
    after: String
    privacy: RepositoryPrivacy
    orderBy: RepositoryOrder
  ): RepositoryConnection!

  members(first: Int, after: String): UserConnection!

  teams(first: Int, after: String, privacy: TeamPrivacy): TeamConnection!

  projectsV2(
    first: Int
    after: String
    orderBy: ProjectV2Order
  ): ProjectV2Connection!

  # Access
  viewerCanAdminister: Boolean!
  viewerCanCreateProjects: Boolean!
  viewerCanCreateRepositories: Boolean!
  viewerIsAMember: Boolean!
}
```

**Common Queries:**

```graphql
# Organization with repositories
query {
  organization(login: "github") {
    name
    description

    repositories(first: 10, orderBy: { field: STARGAZERS, direction: DESC }) {
      nodes {
        name
        stargazerCount
      }
    }
  }
}

# Organization projects
query {
  organization(login: "myorg") {
    projectsV2(first: 20) {
      nodes {
        id
        number
        title
      }
    }
  }
}
```

---

## Common Enums

### IssueState

```graphql
enum IssueState {
  OPEN
  CLOSED
}
```

### PullRequestState

```graphql
enum PullRequestState {
  OPEN
  CLOSED
  MERGED
}
```

### PullRequestReviewState

```graphql
enum PullRequestReviewState {
  PENDING
  COMMENTED
  APPROVED
  CHANGES_REQUESTED
  DISMISSED
}
```

### MergeableState

```graphql
enum MergeableState {
  MERGEABLE
  CONFLICTING
  UNKNOWN
}
```

### ProjectV2FieldType

```graphql
enum ProjectV2FieldType {
  TEXT
  NUMBER
  DATE
  SINGLE_SELECT
  ITERATION
}
```

### ReactionContent

```graphql
enum ReactionContent {
  THUMBS_UP
  THUMBS_DOWN
  LAUGH
  HOORAY
  CONFUSED
  HEART
  ROCKET
  EYES
}
```

---

## Input Types

### CreateIssueInput

```graphql
input CreateIssueInput {
  repositoryId: ID!
  title: String!
  body: String
  assigneeIds: [ID!]
  labelIds: [ID!]
  milestoneId: ID
  projectIds: [ID!]
}
```

### CreatePullRequestInput

```graphql
input CreatePullRequestInput {
  repositoryId: ID!
  baseRefName: String!
  headRefName: String!
  title: String!
  body: String
  draft: Boolean
  maintainerCanModify: Boolean
}
```

### CreateProjectV2Input

```graphql
input CreateProjectV2Input {
  ownerId: ID!
  title: String!
  repositoryId: ID
  teamId: ID
}
```

### AddProjectV2ItemByIdInput

```graphql
input AddProjectV2ItemByIdInput {
  projectId: ID!
  contentId: ID!
}
```

### UpdateProjectV2ItemFieldValueInput

```graphql
input UpdateProjectV2ItemFieldValueInput {
  projectId: ID!
  itemId: ID!
  fieldId: ID!
  value: ProjectV2FieldValue!
}

input ProjectV2FieldValue {
  text: String
  number: Float
  date: Date
  singleSelectOptionId: String
  iterationId: String
}
```

### CreateDiscussionInput

```graphql
input CreateDiscussionInput {
  repositoryId: ID!
  categoryId: ID!
  title: String!
  body: String!
}
```

---

## Connection Types

All connections follow this pattern:

```graphql
type XConnection {
  edges: [XEdge!]
  nodes: [X!]
  pageInfo: PageInfo!
  totalCount: Int!
}

type XEdge {
  node: X!
  cursor: String!
}

type PageInfo {
  hasNextPage: Boolean!
  hasPreviousPage: Boolean!
  startCursor: String
  endCursor: String
}
```

**Usage:**

- Use `nodes` for simple list access
- Use `edges` when you need cursors for each item
- Always include `pageInfo` for pagination

---

## Introspection

### Query All Types

```graphql
query {
  __schema {
    types {
      name
      kind
      description
    }
  }
}
```

### Query Specific Type

```graphql
query {
  __type(name: "Repository") {
    name
    kind
    fields {
      name
      type {
        name
        kind
      }
      description
    }
  }
}
```

### Query Enum Values

```graphql
query {
  __type(name: "IssueState") {
    name
    enumValues {
      name
      description
    }
  }
}
```

---

## Additional Resources

- Full schema: https://docs.github.com/en/graphql/reference
- GraphQL Explorer: https://docs.github.com/en/graphql/overview/explorer
- GraphQL changelog: https://docs.github.com/en/graphql/overview/changelog
