---
columns:
  - COMMENTS_ARRAY (ARRAY)
  - COMMENTS_TOTAL_COUNT (NUMBER(18,0))
  - DAYS_OPEN (NUMBER(9,0))
  - DAYS_TO_FIRST_COMMENT (NUMBER(9,0))
  - FIRST_COMMENT_AT (TIMESTAMP_TZ(9))
  - FULL_NAME (VARCHAR(256))
  - ISSUE_AUTHOR_LOGIN (VARCHAR(256))
  - ISSUE_AUTHOR_NAME (VARCHAR(256))
  - ISSUE_AUTHOR_USER_ID (NUMBER(38,0))
  - ISSUE_BODY (VARCHAR(16777216))
  - ISSUE_CLOSED_AT (TIMESTAMP_TZ(9))
  - ISSUE_CREATED_AT (TIMESTAMP_TZ(9))
  - ISSUE_ID (NUMBER(38,0))
  - ISSUE_LAST_UPDATED_AT (TIMESTAMP_TZ(9))
  - ISSUE_NUMBER (VARCHAR(16777216))
  - ISSUE_TITLE (VARCHAR(1024))
  - ISSUE_URL (VARCHAR(16777216))
  - IS_CLOSED (BOOLEAN)
  - IS_DAGSTER_REPO (BOOLEAN)
  - LAST_COMMENT_AT (TIMESTAMP_TZ(9))
  - REPOSITORY_NAME (VARCHAR(256))
  - STATE (VARCHAR(256))
schema_hash: 5ce45b0cf1cd6379bdffaa04525128876604e5d4dedc65995a2854a083315741
---

# GitHub Issues Dataset Summary

## Overall Dataset Characteristics

- **Total rows**: 46,971 GitHub issues
- **Data quality**: High - minimal null values across most columns (0-5% for key fields)
- **Temporal scope**: Issues span from 2018 to 2025, providing comprehensive historical coverage
- **Repository coverage**: 84 unique Dagster-related repositories
- **Activity patterns**: Mix of open (7.12%) and closed (92.88%) issues with varying engagement levels

**Table Comment**: GitHub issues and their associated comments, filtered to Dagster-related repositories only. This table provides a comprehensive view of issue activity across Dagster projects.

## Column Details

### Identifiers and URLs

- **ISSUE_ID**: Primary key, unique numeric identifier (46,971 unique values, no nulls)
- **ISSUE_NUMBER**: Repository-specific issue number (30,628 unique values across repos)
- **ISSUE_URL**: Direct GitHub URLs for each issue (all unique)

### Repository Information

- **FULL_NAME**: Complete repo identifier format "owner/repo" (84 repositories)
- **REPOSITORY_NAME**: Just the repo name portion (84 unique values)
- **IS_DAGSTER_REPO**: Boolean flag (always true, but includes some false values for filtering)

### Issue Content

- **ISSUE_TITLE**: Issue titles (45,962 unique out of 46,971 - very high uniqueness)
- **ISSUE_BODY**: Full issue descriptions (5.65% null, 39,797 unique values)

### Author Information

- **ISSUE_AUTHOR_USER_ID**: GitHub user IDs (2,159 unique authors)
- **ISSUE_AUTHOR_LOGIN**: GitHub usernames (2,064 unique, 0.23% null)
- **ISSUE_AUTHOR_NAME**: Full names (21.45% null, 1,566 unique)

### Status and Lifecycle

- **IS_CLOSED/STATE**: Issue status (closed/open states align with boolean flag)
- **ISSUE_CREATED_AT**: Creation timestamps (46,916 unique values)
- **ISSUE_CLOSED_AT**: Close timestamps (7.12% null for open issues)
- **ISSUE_LAST_UPDATED_AT**: Last activity timestamps (45,877 unique)

### Engagement Metrics

- **COMMENTS_TOTAL_COUNT**: Comment counts (0-232 range, many issues have 0-5 comments)
- **FIRST_COMMENT_AT/LAST_COMMENT_AT**: Comment timing (17.80% null for uncommented issues)
- **COMMENTS_ARRAY**: Structured JSON containing full comment details and metadata

### Derived Analytics

- **DAYS_OPEN**: Issue lifecycle duration (0-2,431 days range)
- **DAYS_TO_FIRST_COMMENT**: Response time metric (17.80% null, 0-1,494 days range)

## Potential Query Considerations

### Good for Filtering

- **REPOSITORY_NAME/FULL_NAME**: Filter by specific repos or repo groups
- **STATE/IS_CLOSED**: Filter by issue status
- **ISSUE_CREATED_AT**: Time-based filtering for trends analysis
- **ISSUE_AUTHOR_LOGIN**: Filter by specific contributors
- **COMMENTS_TOTAL_COUNT**: Filter by engagement level

### Good for Grouping/Aggregation

- **REPOSITORY_NAME**: Aggregate metrics by repository
- **ISSUE_AUTHOR_LOGIN**: Analyze contributor activity
- **STATE**: Group by open/closed status
- **Date fields**: Time-based aggregations (monthly, yearly trends)

### Potential Join Keys

- **ISSUE_AUTHOR_USER_ID**: Link to user/contributor tables
- **REPOSITORY_NAME/FULL_NAME**: Link to repository metadata
- **ISSUE_ID**: Primary key for joining with related issue data

### Data Quality Considerations

- **Null handling**: 17.80% of issues have no comments (affects comment-related fields)
- **Author names**: 21.45% null rate requires careful handling in queries
- **JSON parsing**: COMMENTS_ARRAY requires JSON functions for detailed comment analysis
- **Date ranges**: Some future dates present (2025) may indicate ongoing or scheduled items

## Keywords

GitHub, issues, Dagster, repository management, software development, issue tracking, comments, pull requests, open source, project management, developer activity, bug tracking, feature requests, software analytics

## Table and Column Docs

**Table Comment**: GitHub issues and their associated comments, filtered to Dagster-related repositories only. This table provides a comprehensive view of issue activity across Dagster projects.

**Column Comments**:

- ISSUE_ID: Unique GitHub issue ID from Fivetran
- FULL_NAME: Full name of the GitHub repository (e.g., 'dagster-io/dagster')
- ISSUE_NUMBER: Issue number within the repository
- REPOSITORY_NAME: Name of the GitHub repository (e.g., 'dagster', 'community-integrations')
- ISSUE_URL: Direct URL to the GitHub issue
- ISSUE_TITLE: Title/subject of the GitHub issue
- ISSUE_AUTHOR_USER_ID: GitHub user ID of the person who created the issue
- ISSUE_BODY: Full text content of the issue description
- ISSUE_AUTHOR_LOGIN: GitHub username of the person who created the issue
- ISSUE_AUTHOR_NAME: Full name of the person who created the issue
- IS_DAGSTER_REPO: Boolean flag indicating if this is from a Dagster-related repository (always true in this table)
- IS_CLOSED: Boolean indicating whether the issue is closed
- STATE: Current state of the issue (open, closed)
- ISSUE_CREATED_AT: Timestamp when the issue was originally created
- ISSUE_CLOSED_AT: Timestamp when the issue was closed (null if still open)
- ISSUE_LAST_UPDATED_AT: Timestamp when the issue was last updated
- COMMENTS_TOTAL_COUNT: Total number of comments on the issue
- FIRST_COMMENT_AT: Timestamp of the earliest comment on the issue
- LAST_COMMENT_AT: Timestamp of the most recent comment on the issue
- COMMENTS_ARRAY: Array of structured comment objects containing all comment details and metadata
- DAYS_OPEN: Number of days the issue has been open (or was open before closing)
- DAYS_TO_FIRST_COMMENT: Number of days between issue creation and the first comment (null if no comments)
