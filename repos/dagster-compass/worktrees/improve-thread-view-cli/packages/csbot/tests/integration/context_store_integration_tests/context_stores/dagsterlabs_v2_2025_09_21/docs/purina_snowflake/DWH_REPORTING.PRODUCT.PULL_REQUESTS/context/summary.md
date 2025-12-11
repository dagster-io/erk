---
columns:
  - ACTIVE_LOCK_REASON (VARCHAR(256))
  - APPROVED_REVIEWS_COUNT (NUMBER(18,0))
  - BASE_LABEL (VARCHAR(256))
  - BASE_REF (VARCHAR(256))
  - BASE_REPO_ID (NUMBER(38,0))
  - BASE_REPO_NAME (VARCHAR(256))
  - BASE_SHA (VARCHAR(256))
  - BASE_USER_COMPANY (VARCHAR(256))
  - BASE_USER_FULL_NAME (VARCHAR(256))
  - BASE_USER_ID (NUMBER(38,0))
  - BASE_USER_USERNAME (VARCHAR(256))
  - CHANGES_REQUESTED_COUNT (NUMBER(18,0))
  - CLOSED_AT (TIMESTAMP_TZ(9))
  - COMMENTED_REVIEWS_COUNT (NUMBER(18,0))
  - COMMITS_ARRAY (ARRAY)
  - CREATED_AT (TIMESTAMP_TZ(9))
  - DAYS_OPEN (NUMBER(9,0))
  - DAYS_TO_FIRST_COMMENT (NUMBER(9,0))
  - DAYS_TO_FIRST_REVIEW (NUMBER(9,0))
  - FIRST_COMMIT_DATE (TIMESTAMP_TZ(9))
  - FIRST_REVIEW_AT (TIMESTAMP_TZ(9))
  - HEAD_LABEL (VARCHAR(256))
  - HEAD_REF (VARCHAR(256))
  - HEAD_REPO_ID (NUMBER(38,0))
  - HEAD_REPO_NAME (VARCHAR(256))
  - HEAD_SHA (VARCHAR(256))
  - HEAD_USER_COMPANY (VARCHAR(256))
  - HEAD_USER_FULL_NAME (VARCHAR(256))
  - HEAD_USER_ID (NUMBER(38,0))
  - HEAD_USER_USERNAME (VARCHAR(256))
  - ISSUE_AUTHOR_LOGIN (VARCHAR(256))
  - ISSUE_AUTHOR_NAME (VARCHAR(256))
  - ISSUE_AUTHOR_USER_ID (NUMBER(38,0))
  - ISSUE_BODY (VARCHAR(16777216))
  - ISSUE_CLOSED_AT (TIMESTAMP_TZ(9))
  - ISSUE_COMMENTS_COUNT (NUMBER(18,0))
  - ISSUE_CREATED_AT (TIMESTAMP_TZ(9))
  - ISSUE_DAYS_OPEN (NUMBER(9,0))
  - ISSUE_ID (NUMBER(38,0))
  - ISSUE_LAST_UPDATED_AT (TIMESTAMP_TZ(9))
  - ISSUE_NUMBER (VARCHAR(16777216))
  - ISSUE_REPO_NAME (VARCHAR(256))
  - ISSUE_TITLE (VARCHAR(1024))
  - IS_DRAFT (BOOLEAN)
  - LAST_COMMIT_DATE (TIMESTAMP_TZ(9))
  - LAST_REVIEW_AT (TIMESTAMP_TZ(9))
  - MERGE_COMMIT_SHA (VARCHAR(256))
  - PR_STATUS (VARCHAR(19))
  - PULL_REQUEST_ID (NUMBER(38,0))
  - REPOSITORIES_TOUCHED (ARRAY)
  - REPOSITORIES_TOUCHED_COUNT (NUMBER(18,0))
  - REVIEWS_ARRAY (ARRAY)
  - TOTAL_COMMITS_COUNT (NUMBER(18,0))
  - TOTAL_REVIEWS_COUNT (NUMBER(18,0))
  - UPDATED_AT (TIMESTAMP_TZ(9))
schema_hash: 03a554fa05910c75e4566dbc4e709c7d59cb58a69df814cd42e1d64c2bd18567
---

# Table Summary: DWH_REPORTING.PRODUCT.PULL_REQUESTS

## Overall Dataset Characteristics

- **Total Rows**: 38,677 pull requests
- **Data Quality**: High quality dataset with minimal null values in critical fields
- **Coverage**: Comprehensive GitHub pull request data spanning multiple repositories (83 unique repos)
- **Time Range**: Data spans from early GitHub activity through 2025, with recent updates
- **Notable Patterns**:
  - Most PRs are from the main "dagster" repository
  - High merge rate (97.87% have close dates, suggesting most are merged rather than abandoned)
  - Active review culture with detailed review tracking
  - Rich commit and collaboration metadata

## Table Comment

Comprehensive GitHub pull requests table with one row per pull request, enriched with commit information, review data, user details, and calculated workflow metrics. This table provides a complete view of PR lifecycle and collaboration patterns for development analytics and team insights.

## Column Details

### Primary Keys & Identifiers

- **PULL_REQUEST_ID**: Unique numeric identifier for each PR (38,677 unique values, no nulls)
- **ISSUE_ID**: Associated GitHub issue ID (38,677 unique values, no nulls)
- **ISSUE_NUMBER**: Human-readable issue number (27,796 unique values, varchar format)

### Repository & Branch Information

- **ISSUE_REPO_NAME**: Repository name (83 unique repos, "dagster" being primary)
- **HEAD_REF/BASE_REF**: Branch names for source and target branches
- **HEAD_SHA/BASE_SHA**: Commit SHAs for branch heads
- **HEAD_REPO_ID/BASE_REPO_ID**: Numeric repository identifiers

### User Information

- **HEAD_USER_USERNAME/BASE_USER_USERNAME**: GitHub usernames (728 head users, base is always "dagster-io")
- **HEAD_USER_FULL_NAME**: Display names with some nulls (0.74%)
- **HEAD_USER_COMPANY**: Mostly null (98.57%), limited company data available

### Timestamps & Lifecycle

- **CREATED_AT**: PR creation timestamp (no nulls, 38,628 unique values)
- **CLOSED_AT**: PR closure timestamp (2.13% nulls for open PRs)
- **UPDATED_AT**: Last update timestamp
- **FIRST_REVIEW_AT/LAST_REVIEW_AT**: Review timing (14.07% nulls for PRs without reviews)

### Status & Metadata

- **PR_STATUS**: Current state - "Merged", "Open", "Closed (Not Merged)" (3 values)
- **IS_DRAFT**: Boolean draft status
- **MERGE_COMMIT_SHA**: SHA of merge commit (2.29% nulls for unmerged PRs)

### Review Analytics

- **REVIEWS_ARRAY**: Structured JSON array with detailed review data
- **TOTAL_REVIEWS_COUNT**: Count of all reviews (0-84 range)
- **APPROVED_REVIEWS_COUNT**: Approved reviews count (0-4 range)
- **CHANGES_REQUESTED_COUNT**: Reviews requesting changes (0-7 range)
- **COMMENTED_REVIEWS_COUNT**: Comment-only reviews (0-83 range)

### Commit Information

- **COMMITS_ARRAY**: Structured JSON array with commit details, author info, and status data
- **TOTAL_COMMITS_COUNT**: Number of commits per PR (0-201 range)
- **FIRST_COMMIT_DATE/LAST_COMMIT_DATE**: Commit timing (13.98% nulls)
- **REPOSITORIES_TOUCHED**: Array of repos affected by commits
- **REPOSITORIES_TOUCHED_COUNT**: Count of affected repositories (0-2 range)

### Calculated Metrics

- **DAYS_TO_FIRST_REVIEW**: Time to first review (14.07% nulls, 0-894 days)
- **DAYS_OPEN**: Total days PR was open (0-1531 days)
- **DAYS_TO_FIRST_COMMENT**: Time to first issue comment (15.27% nulls)

### Issue Details

- **ISSUE_TITLE**: Title of associated issue (37,817 unique values)
- **ISSUE_BODY**: Issue description with rich content (5.43% nulls)
- **ISSUE_AUTHOR_LOGIN**: Issue creator username (826 unique users)
- **ISSUE_COMMENTS_COUNT**: Number of issue comments (0-232 range)
- **ISSUE_DAYS_OPEN**: Days issue was open

## Potential Query Considerations

### Good for Filtering

- **PR_STATUS**: Filter by merged, open, or closed PRs
- **ISSUE_REPO_NAME**: Filter by specific repositories
- **IS_DRAFT**: Exclude draft PRs from analysis
- **CREATED_AT/CLOSED_AT**: Time-based filtering
- **HEAD_USER_USERNAME**: Filter by contributor
- **BASE_REF**: Filter by target branch (master/main)

### Good for Grouping/Aggregation

- **ISSUE_REPO_NAME**: Repository-level analytics
- **HEAD_USER_USERNAME**: Contributor activity analysis
- **PR_STATUS**: Status distribution analysis
- **BASE_REF**: Branch-based analysis
- **CREATED_AT** (date parts): Time-series analysis
- **TOTAL_REVIEWS_COUNT/APPROVED_REVIEWS_COUNT**: Review pattern analysis

### Potential Join Keys

- **PULL_REQUEST_ID**: Primary key for joins
- **ISSUE_ID**: Link to issue-specific tables
- **HEAD_USER_ID/BASE_USER_ID**: Link to user profile tables
- **HEAD_REPO_ID/BASE_REPO_ID**: Link to repository metadata

### Data Quality Considerations

- Array fields (REVIEWS_ARRAY, COMMITS_ARRAY) contain structured JSON requiring special handling
- Some calculated fields have higher null percentages (reviews, commits) indicating PRs without those activities
- Company information is largely missing (98%+ nulls)
- Time zone data is preserved in timestamp fields
- Large varchar fields may contain extensive markdown content

## Keywords

GitHub, pull requests, code review, software development, version control, collaboration, merge analysis, developer productivity, repository analytics, commit tracking, review metrics, workflow analysis, open source, development lifecycle

## Table and Column Docs

**Table Comment**: Comprehensive GitHub pull requests table with one row per pull request, enriched with commit information, review data, user details, and calculated workflow metrics. This table provides a complete view of PR lifecycle and collaboration patterns for development analytics and team insights.

**Column Comments**:

- PULL_REQUEST_ID: Primary key - unique identifier for the GitHub pull request
- ISSUE_ID: Associated GitHub issue ID linked to this pull request
- ACTIVE_LOCK_REASON: Reason why the pull request is locked (if applicable)
- ISSUE_TITLE: Title of the associated GitHub issue
- CREATED_AT: Timestamp when the pull request was created
- CLOSED_AT: Timestamp when the pull request was closed (null if still open)
- IS_DRAFT: Boolean indicating whether the pull request is in draft status
- MERGE_COMMIT_SHA: SHA of the merge commit if the PR was merged
- UPDATED_AT: Timestamp when the pull request was last updated
- HEAD_LABEL: Label/name of the head branch
- HEAD_REF: Reference name of the head branch
- HEAD_SHA: SHA of the head commit
- HEAD_USER_ID: User ID of the head branch owner
- HEAD_REPO_ID: Repository ID of the head branch
- HEAD_USER_USERNAME: GitHub username of the head branch owner
- HEAD_REPO_NAME: Name of the repository containing the head branch
- BASE_LABEL: Label/name of the base branch
- BASE_REF: Reference name of the base branch
- BASE_SHA: SHA of the base commit
- BASE_REPO_ID: Repository ID of the base branch
- BASE_USER_USERNAME: GitHub username of the base branch owner
- BASE_USER_ID: User ID of the base branch owner
- BASE_REPO_NAME: Name of the repository containing the base branch
- REVIEWS_ARRAY: Array of structured review objects containing reviewer details, states, and timestamps
- TOTAL_REVIEWS_COUNT: Total number of reviews on the pull request
- APPROVED_REVIEWS_COUNT: Number of approved reviews
- CHANGES_REQUESTED_COUNT: Number of reviews requesting changes
- FIRST_REVIEW_AT: Timestamp of the first review
- COMMENTED_REVIEWS_COUNT: Number of review comments
- LAST_REVIEW_AT: Timestamp of the most recent review
- HEAD_USER_FULL_NAME: Full name of the head branch owner
- BASE_USER_FULL_NAME: Full name of the base branch owner
- HEAD_USER_COMPANY: Company/organization of the head branch owner
- BASE_USER_COMPANY: Company/organization of the base branch owner
- DAYS_TO_FIRST_REVIEW: Number of days from PR creation to first review (null if no reviews)
- DAYS_OPEN: Number of days the pull request has been open (or was open before closing)
- COMMITS_ARRAY: Array of structured commit objects containing all commit details, author information, and status data
- TOTAL_COMMITS_COUNT: Total number of commits in the pull request
- LAST_COMMIT_DATE: Date of the most recent commit in the pull request
- FIRST_COMMIT_DATE: Date of the earliest commit in the pull request
- REPOSITORIES_TOUCHED_COUNT: Number of different repositories touched by commits in this pull request
- REPOSITORIES_TOUCHED: Array of repository names touched by commits in this pull request
- ISSUE_AUTHOR_USER_ID: GitHub user ID of the person who created the associated issue
- ISSUE_AUTHOR_LOGIN: GitHub username of the person who created the associated issue
- ISSUE_AUTHOR_NAME: Full name of the person who created the associated issue
- ISSUE_BODY: Body content of the associated GitHub issue
- ISSUE_CREATED_AT: Timestamp when the associated issue was created
- ISSUE_CLOSED_AT: Timestamp when the associated issue was closed (null if still open)
- ISSUE_LAST_UPDATED_AT: Timestamp when the associated issue was last updated
- ISSUE_COMMENTS_COUNT: Total number of comments on the associated issue
- ISSUE_DAYS_OPEN: Number of days the associated issue has been open
- DAYS_TO_FIRST_COMMENT: Number of days between issue creation and the first comment (null if no comments)
