---
columns:
  - ASSIGNEE_EMAIL (VARCHAR(256))
  - ASSIGNEE_ID (VARCHAR(256))
  - ASSIGNEE_NAME (VARCHAR(256))
  - CANCELED_AT (TIMESTAMP_TZ(9))
  - COMMENTS_ARRAY (ARRAY)
  - COMMENT_COUNT (NUMBER(18,0))
  - COMPLETED_AT (TIMESTAMP_TZ(9))
  - COMPLEXITY_LEVEL (VARCHAR(7))
  - CREATED_AT (TIMESTAMP_TZ(9))
  - CREATOR_EMAIL (VARCHAR(256))
  - CREATOR_ID (VARCHAR(256))
  - CREATOR_NAME (VARCHAR(256))
  - DAYS_TO_COMPLETION (NUMBER(9,0))
  - DAYS_UNTIL_DUE (NUMBER(9,0))
  - DUE_DATE (DATE)
  - ENGAGEMENT_LEVEL (VARCHAR(7))
  - ESTIMATE (NUMBER(38,0))
  - FIRST_COMMENT_AT (TIMESTAMP_TZ(9))
  - ISSUE_DESCRIPTION (VARCHAR(32768))
  - ISSUE_ID (VARCHAR(256))
  - ISSUE_NUMBER (NUMBER(38,0))
  - ISSUE_STATUS (VARCHAR(9))
  - ISSUE_TITLE (VARCHAR(512))
  - ISSUE_URL (VARCHAR(256))
  - LABEL_NAMES (ARRAY)
  - LATEST_COMMENT_AT (TIMESTAMP_TZ(9))
  - PRIORITY (NUMBER(38,0))
  - PRIORITY_ORDER (NUMBER(1,0))
  - PROJECT_DESCRIPTION (VARCHAR(256))
  - PROJECT_ID (VARCHAR(256))
  - PROJECT_NAME (VARCHAR(256))
  - REPORT_DATE (DATE)
  - STATE_CHANGES_ARRAY (ARRAY)
  - STATE_ID (VARCHAR(256))
  - TEAM_ID (VARCHAR(256))
  - UNIQUE_COMMENTERS (NUMBER(18,0))
  - UPDATED_AT (TIMESTAMP_TZ(9))
  - WORKFLOW_STATE_NAME (VARCHAR(256))
  - WORKFLOW_STATE_TYPE (VARCHAR(256))
  - _FIVETRAN_SYNCED (TIMESTAMP_TZ(9))
schema_hash: 109401086bbe36fcaffb35e52522860a7a882d7c65359dc57e72e47afcd78409
---

# LINEAR_ISSUES Table Summary

## Overall Dataset Characteristics

**Total Rows:** 11,980

This table contains a comprehensive view of Linear project management issues from Dagster Labs with extensive enrichment for analytics and reporting. The data spans from early 2024 to September 2025, with good data quality overall. Issues are distributed across 23 teams and 317 projects, with varying levels of engagement and completion status.

**Data Quality Observations:**

- High completeness for core fields (issue ID, title, team, timestamps)
- Moderate null rates for assignee information (31-34%)
- High null rates for optional fields like due dates (93%) and estimates (74%)
- Rich enrichment data including comment activity, state changes, and calculated metrics

**Notable Patterns:**

- 46% of issues are completed, 78% have never been canceled
- Most issues (74%) have no story point estimates
- Comment activity varies significantly (0-159 comments per issue)
- Priority distribution shows many issues with no priority assigned

## Column Details

### Primary Identifiers

- **ISSUE_ID**: Unique varchar identifier (no nulls, 11,980 unique values)
- **ISSUE_NUMBER**: Team-scoped numeric identifier (range 1-2,424)
- **ISSUE_URL**: Direct Linear app links for each issue

### Core Issue Information

- **ISSUE_TITLE**: Issue titles (512 char max, highly unique - 10,978 distinct values)
- **ISSUE_DESCRIPTION**: Long-form descriptions (32KB max, ~20% null rate)
- **PRIORITY**: Numeric scale 0-4 (0=No priority is most common)
- **ESTIMATE**: Story points 0-16 (75% null, when present mostly 1-3 points)

### Workflow & State Management

- **STATE_ID**: References to workflow states (171 unique states)
- **WORKFLOW_STATE_NAME**: Human-readable state names (28 types: Backlog, Done, In Progress, etc.)
- **WORKFLOW_STATE_TYPE**: Categorized as backlog/unstarted/started/completed/canceled
- **STATE_CHANGES_ARRAY**: Complete state transition history with timestamps and actors

### User Assignment & Ownership

- **ASSIGNEE_ID/NAME/EMAIL**: Current assignee (31-34% null rate, 78 unique assignees)
- **CREATOR_ID/NAME/EMAIL**: Issue creator (6-12% null rate, 80 unique creators)

### Project & Team Context

- **TEAM_ID**: Owning team (23 teams, no nulls)
- **PROJECT_ID/NAME/DESCRIPTION**: Associated project (37-39% null rate, 317 projects)
- **LABEL_NAMES**: Array of issue labels (72% null)

### Temporal Data

- **CREATED_AT/UPDATED_AT**: Issue lifecycle timestamps (no nulls)
- **COMPLETED_AT**: Completion timestamp (46% null - matches incomplete issues)
- **CANCELED_AT**: Cancellation timestamp (78% null)
- **DUE_DATE**: Optional due dates (94% null, when set range from 2024-2025)

### Engagement & Activity Metrics

- **COMMENT_COUNT**: Total comments per issue (0-159 range)
- **UNIQUE_COMMENTERS**: Distinct users who commented (0-9 range)
- **LATEST_COMMENT_AT/FIRST_COMMENT_AT**: Comment timing (58% null)
- **COMMENTS_ARRAY**: Structured comment data with full details

### Calculated Analytics Fields

- **DAYS_TO_COMPLETION**: Time to complete (0-598 days, null for incomplete)
- **DAYS_UNTIL_DUE**: Days until due date (negative if overdue)
- **PRIORITY_ORDER**: Sortable priority (1=High to 5=Unknown)
- **ISSUE_STATUS**: Categorized status (Open/Completed/Canceled/Overdue)
- **ENGAGEMENT_LEVEL**: Based on comment activity (High/Unknown)
- **COMPLEXITY_LEVEL**: Based on estimates (High/Medium/Low/Unknown)

### System Fields

- **REPORT_DATE**: Static date (2025-09-21) for this dataset snapshot
- **\_FIVETRAN_SYNCED**: ETL sync timestamps

## Query Considerations

### Good for Filtering

- **WORKFLOW_STATE_TYPE**: Filter by workflow stage (backlog/started/completed)
- **TEAM_ID**: Filter by owning team
- **ASSIGNEE_ID**: Filter by assigned person
- **ISSUE_STATUS**: Filter by calculated status
- **PRIORITY_ORDER**: Filter by priority level
- **CREATED_AT/COMPLETED_AT**: Date range filtering

### Good for Grouping/Aggregation

- **TEAM_ID**: Team-level metrics
- **WORKFLOW_STATE_NAME**: Status distribution analysis
- **ASSIGNEE_NAME**: Workload analysis
- **PROJECT_NAME**: Project progress tracking
- **PRIORITY_ORDER**: Priority distribution
- **ENGAGEMENT_LEVEL/COMPLEXITY_LEVEL**: Issue categorization

### Potential Join Keys

- **TEAM_ID**: Link to team information tables
- **ASSIGNEE_ID/CREATOR_ID**: Link to user/employee tables
- **PROJECT_ID**: Link to project details tables
- **STATE_ID**: Link to workflow configuration tables

### Data Quality Considerations

- Handle high null rates in assignee fields when analyzing workload
- Consider that 74% of estimates are null when doing capacity planning
- Account for timezone handling in timestamp fields
- Array fields (COMMENTS_ARRAY, STATE_CHANGES_ARRAY, LABEL_NAMES) require JSON parsing
- Some state-related fields have ~2% nulls that should be handled in joins

## Keywords

Linear, issues, project management, workflow, tickets, bugs, features, tasks, development, engineering, team collaboration, sprint planning, kanban, agile, issue tracking, assignment, completion, engagement, comments, state transitions, priorities, estimates, projects, teams, analytics, reporting, business intelligence

## Table and Column Documentation

**Table Comment:** Comprehensive Linear issues table with one row per issue, enriched with comment activity, user assignments, project context, and calculated engagement indicators. This table provides a complete view of issue lifecycle and team collaboration for LLM analysis and business intelligence.

**Column Comments:**

- ISSUE_ID: Primary key - unique identifier for the Linear issue
- ISSUE_NUMBER: Issue number within the team
- ISSUE_TITLE: Title of the Linear issue
- ISSUE_DESCRIPTION: Detailed description of the issue
- ISSUE_URL: Direct URL to the Linear issue
- STATE_ID: Foreign key to workflow state
- WORKFLOW_STATE_NAME: Name of the current workflow state (e.g., 'Backlog', 'In Progress', 'Done')
- PRIORITY: Numeric priority level (0=No priority, 1=High, 2=Medium, 3=Low)
- WORKFLOW_STATE_TYPE: Type of workflow state (e.g., 'backlog', 'unstarted', 'started', 'completed', 'canceled')
- ASSIGNEE_ID: User ID of the person assigned to the issue
- ASSIGNEE_NAME: Name of the assigned user
- ASSIGNEE_EMAIL: Email address of the assigned user
- CREATOR_ID: User ID of the person who created the issue
- CREATOR_EMAIL: Email address of the creator
- PROJECT_ID: Foreign key to the associated project
- CREATOR_NAME: Name of the user who created the issue
- PROJECT_DESCRIPTION: Description of the associated project
- TEAM_ID: Team ID that owns the issue
- PROJECT_NAME: Name of the associated project
- LABEL_NAMES: Array of label names applied to the issue
- CREATED_AT: Timestamp when the issue was created
- UPDATED_AT: Timestamp when the issue was last updated
- COMPLETED_AT: Timestamp when the issue was completed (null if not completed)
- CANCELED_AT: Timestamp when the issue was canceled (null if not canceled)
- DUE_DATE: Due date for the issue (null if no due date set)
- ESTIMATE: Story point estimate for the issue
- COMMENT_COUNT: Total number of comments on the issue
- LATEST_COMMENT_AT: Timestamp of the most recent comment
- FIRST_COMMENT_AT: Timestamp of the first comment
- UNIQUE_COMMENTERS: Number of unique users who commented on the issue
- COMMENTS_ARRAY: Array of structured comment objects containing all comment details, commenter names, timestamps, and metadata
- STATE_CHANGES_ARRAY: Array of structured state change objects containing complete workflow state transition history with timestamps, actor information, and state details
- DAYS_TO_COMPLETION: Number of days from creation to completion (null if not completed)
- DAYS_UNTIL_DUE: Number of days until due date (negative if overdue, null if no due date or completed)
- PRIORITY_ORDER: Numeric priority for sorting (1=High, 2=Medium, 3=Low, 4=No priority, 5=Unknown)
- ISSUE_STATUS: Calculated status (Completed, Canceled, Overdue, Open)
- ENGAGEMENT_LEVEL: Engagement level based on comment activity (High, None, Unknown)
- REPORT_DATE: Date when this report was generated
- COMPLEXITY_LEVEL: Complexity level based on estimate (High >5, Medium >2, Low, Unknown)
- \_FIVETRAN_SYNCED: Timestamp of last Fivetran sync
