---
columns:
  - ASSIGNEE_ID (VARCHAR(16777216))
  - ASSIGNEE_NAME (VARCHAR(16777216))
  - BUSINESS_HOURS_TIME_TO_FIRST_RESPONSE (NUMBER(38,0))
  - BUSINESS_HOURS_TIME_TO_RESOLUTION (NUMBER(38,0))
  - CREATED_AT (TIMESTAMP_NTZ(9))
  - CUSTOM_FIELDS (VARIANT)
  - DAYS_OPEN (NUMBER(9,0))
  - EXTERNAL_ISSUE_LINK (VARIANT)
  - FIRST_RESPONSE_TIME (TIMESTAMP_NTZ(9))
  - HAS_ACTIVE_CONTRACT (BOOLEAN)
  - HAS_TAG_FIRST_RESPONSE_SLA_BREACH (BOOLEAN)
  - HAS_TAG_VIP_ACCOUNT (BOOLEAN)
  - HAS_TAG_WAS_ESCALATED (BOOLEAN)
  - ISSUE_BODY (VARCHAR(16777216))
  - ISSUE_ID (VARCHAR(16777216))
  - ISSUE_LINK (VARCHAR(16777216))
  - ISSUE_NUMBER (NUMBER(38,0))
  - ISSUE_SOURCE (VARCHAR(16777216))
  - ISSUE_STATE (VARCHAR(16777216))
  - ISSUE_TITLE (VARCHAR(16777216))
  - ISSUE_TYPE (VARCHAR(16777216))
  - IS_OPEN_ISSUE (BOOLEAN)
  - LATEST_MESSAGE_TIME (TIMESTAMP_NTZ(9))
  - NUMBER_OF_TOUCHES (NUMBER(38,0))
  - OPEN_OPPORTUNITY_ARR (FLOAT)
  - OPEN_OPPORTUNITY_COUNT (NUMBER(13,0))
  - PYLON_ACCOUNT_ID (VARCHAR(16777216))
  - PYLON_ACCOUNT_NAME (VARCHAR(16777216))
  - REQUESTER_EMAIL (VARCHAR(16777216))
  - REQUESTER_ID (VARCHAR(16777216))
  - REQUESTER_NAME (VARCHAR(16777216))
  - RESOLUTION_TIME (TIMESTAMP_NTZ(9))
  - SALESFORCE_ACCOUNT_ID (VARCHAR(16777216))
  - SALESFORCE_ACCOUNT_NAME (VARCHAR(765))
  - SALESFORCE_ACCOUNT_STATUS (VARCHAR(765))
  - SLACK_CHANNEL_ID (VARCHAR(16777216))
  - SUPPORT_TIER (VARIANT)
  - SUPPORT_TIER_LEVEL (VARCHAR(8))
  - TAGS (VARCHAR(16777216))
  - TEAM_ID (VARCHAR(16777216))
  - TEAM_NAME (VARCHAR(16777216))
  - TIME_TO_FIRST_RESPONSE (NUMBER(38,0))
  - TIME_TO_RESOLUTION (NUMBER(38,0))
  - TIME_TO_RESOLUTION_HOURS (NUMBER(9,0))
schema_hash: 42a1bae13debe6aaa8249f28ded21c958100b43e37406e8d10b38df51656df86
---

# Support Issues Table Analysis Summary

## Keywords

support tickets, customer issues, Pylon integration, Salesforce CRM, support metrics, SLA tracking, customer success, issue resolution, VIP accounts, enterprise support

## Overall Dataset Characteristics

- **Total Rows**: 12,120 support issues
- **Data Quality**: High quality with minimal null values in key fields
- **Time Range**: Issues span from creation to resolution with comprehensive timestamp tracking
- **Integration**: Rich dataset combining Pylon support system data with Salesforce CRM context
- **Support Channels**: Multi-channel support including Slack, email, forms, and Microsoft Teams

## Table and Column Documentation

**Table Comment**: Support issues from Pylon with enriched business context from Salesforce accounts, including customer status and sales pipeline information

**Column Comments**:

- ISSUE_ID: Unique identifier for the support issue from Pylon
- ISSUE_TITLE: Title or subject of the support issue
- ISSUE_NUMBER: Sequential number assigned to the support issue
- IS_OPEN_ISSUE: Boolean indicating if the issue is currently open (not closed)
- SUPPORT_TIER_LEVEL: Standardized support tier classification (highest, high, medium, low, urgent, critical, other, n_a, unknown)
- PYLON_ACCOUNT_ID: Internal Pylon account identifier
- ISSUE_BODY: Detailed description or body content of the support issue
- PYLON_ACCOUNT_NAME: Account name as stored in Pylon
- ASSIGNEE_ID: Identifier of the person assigned to handle the issue
- REQUESTER_NAME: Name of the person who submitted the support request
- REQUESTER_ID: Identifier of the person who submitted the support request
- ASSIGNEE_NAME: Name of the person assigned to handle the issue
- REQUESTER_EMAIL: Email address of the person who submitted the support request
- TEAM_ID: Identifier of the support team handling the issue
- ISSUE_STATE: Current state of the issue (e.g., open, closed, in progress)
- TEAM_NAME: Name of the support team handling the issue
- ISSUE_TYPE: Type or category of the support issue
- NUMBER_OF_TOUCHES: Number of times the issue has been touched or updated
- FIRST_RESPONSE_TIME: Timestamp of the first response to the support issue
- RESOLUTION_TIME: Timestamp when the issue was resolved
- BUSINESS_HOURS_TIME_TO_FIRST_RESPONSE: Time to first response calculated during business hours only
- TIME_TO_FIRST_RESPONSE: Total time from issue creation to first response
- BUSINESS_HOURS_TIME_TO_RESOLUTION: Time to resolution calculated during business hours only
- TIME_TO_RESOLUTION: Total time from issue creation to resolution
- ISSUE_LINK: URL link to view the issue in Pylon
- CUSTOM_FIELDS: JSON object containing custom field data from Pylon
- TAGS: Tags or labels associated with the issue for categorization
- SUPPORT_TIER: Raw support tier value from custom fields
- ISSUE_SOURCE: Source or channel through which the issue was submitted
- CREATED_AT: Timestamp when the support issue was created
- LATEST_MESSAGE_TIME: Timestamp of the most recent message or update on the issue
- EXTERNAL_ISSUE_LINK: Link to external issue tracking system if applicable
- SLACK_CHANNEL_ID: Identifier for the Slack channel associated with the support issue
- HAS_TAG_VIP_ACCOUNT: Boolean indicating if the issue is tagged as a VIP account issue
- HAS_TAG_FIRST_RESPONSE_SLA_BREACH: Boolean indicating if the issue is tagged as having a first response SLA breach
- DAYS_OPEN: For open issues, days since creation; for closed issues, days from creation to resolution
- TIME_TO_RESOLUTION_HOURS: Time in hours from issue creation to resolution (null for open issues)
- HAS_TAG_WAS_ESCALATED: Boolean indicating if the issue was escalated
- SALESFORCE_ACCOUNT_NAME: Account name from Salesforce for the associated account
- SALESFORCE_ACCOUNT_ID: Salesforce account ID linked to this support issue
- SALESFORCE_ACCOUNT_STATUS: Current status of the associated Salesforce account
- HAS_ACTIVE_CONTRACT: Boolean indicating if the associated account has an active contract
- OPEN_OPPORTUNITY_ARR: Total potential Annual Recurring Revenue from open opportunities for the associated account
- OPEN_OPPORTUNITY_COUNT: Number of open sales opportunities for the associated account

## Column Details

### Key Identifiers

- **ISSUE_ID**: VARCHAR, 100% populated, unique values (12,120), perfect for joins
- **ISSUE_NUMBER**: NUMBER, 100% populated, sequential from 6 to 14,007
- **PYLON_ACCOUNT_ID**: VARCHAR, 99.88% populated, 1,887 unique accounts

### Issue Content & Classification

- **ISSUE_TITLE**: VARCHAR, 91.45% populated, 10,835 unique titles
- **ISSUE_BODY**: VARCHAR, 99.78% populated, detailed descriptions
- **ISSUE_TYPE**: VARCHAR, 100% populated, only 2 values: "Conversation" or "Ticket"
- **SUPPORT_TIER_LEVEL**: VARCHAR, 100% populated, 6 standardized tiers (high, highest, medium, n_a, other, unknown)
- **ISSUE_STATE**: VARCHAR, 100% populated, 5 states (Closed, New, On Hold, Waiting on Customer, Waiting on You)

### Support Team & Assignment

- **ASSIGNEE_ID/NAME**: VARCHAR, 69.22% populated, 64 unique assignees
- **TEAM_ID/NAME**: VARCHAR, 83.11% populated, 25 teams including Adopt, Build, Triage
- **REQUESTER_ID/NAME/EMAIL**: VARCHAR, 97.23% populated, 3,000+ unique requesters

### Timing & SLA Metrics

- **CREATED_AT**: TIMESTAMP, 100% populated, spans full dataset timeline
- **FIRST_RESPONSE_TIME**: TIMESTAMP, 75.57% populated
- **RESOLUTION_TIME**: TIMESTAMP, 93.41% populated
- **TIME_TO_FIRST_RESPONSE**: NUMBER, 74.88% populated, 0 to 9.4M seconds
- **TIME_TO_RESOLUTION**: NUMBER, 93.39% populated, some negative values (-1.1M to 10.1M)
- **DAYS_OPEN**: NUMBER, 100% populated, -37 to 538 days (negative indicates closed before creation date)

### Channel & Source Information

- **ISSUE_SOURCE**: VARCHAR, 100% populated, 5 channels (email, form, manual, microsoftTeams, slack)
- **SLACK_CHANNEL_ID**: VARCHAR, 84.38% populated, 393 unique channels
- **ISSUE_LINK**: VARCHAR, 100% populated, unique Pylon URLs

### Tagging & Categorization

- **TAGS**: VARCHAR, 60.70% populated, 67 unique tag combinations (VIP-account, after-hours, etc.)
- **HAS_TAG_VIP_ACCOUNT**: BOOLEAN, 100% populated
- **HAS_TAG_FIRST_RESPONSE_SLA_BREACH**: BOOLEAN, 100% populated
- **HAS_TAG_WAS_ESCALATED**: BOOLEAN, 100% populated
- **CUSTOM_FIELDS**: VARIANT (JSON), 99.98% populated, 4,806 unique configurations

### Salesforce Integration

- **SALESFORCE_ACCOUNT_ID**: VARCHAR, 81.04% populated, 1,187 unique accounts
- **SALESFORCE_ACCOUNT_NAME**: VARCHAR, 80.37% populated, 1,172 unique names
- **SALESFORCE_ACCOUNT_STATUS**: VARCHAR, 80.37% populated, 10 statuses (Client, MQL, Adoption & Expansion, etc.)
- **HAS_ACTIVE_CONTRACT**: BOOLEAN, 58.78% populated
- **OPEN_OPPORTUNITY_ARR**: FLOAT, 80.37% populated, -$111K to $700K range
- **OPEN_OPPORTUNITY_COUNT**: NUMBER, 80.37% populated, 0-3 opportunities

## Query Considerations

### Excellent for Filtering

- **ISSUE_STATE**: Filter by open/closed status
- **SUPPORT_TIER_LEVEL**: Filter by priority/tier
- **ISSUE_SOURCE**: Filter by channel (Slack, email, etc.)
- **TEAM_NAME**: Filter by support team
- **HAS_TAG_VIP_ACCOUNT**: Filter VIP customer issues
- **SALESFORCE_ACCOUNT_STATUS**: Filter by customer lifecycle stage
- **HAS_ACTIVE_CONTRACT**: Filter paying vs. non-paying customers

### Good for Grouping/Aggregation

- **SUPPORT_TIER_LEVEL**: Analyze by support tier
- **TEAM_NAME**: Performance by team
- **ISSUE_SOURCE**: Volume by channel
- **SALESFORCE_ACCOUNT_STATUS**: Issues by customer type
- **DATE(CREATED_AT)**: Time-based analysis
- **ASSIGNEE_NAME**: Individual performance metrics

### Join Keys & Relationships

- **ISSUE_ID**: Primary key for joining to other issue-related tables
- **PYLON_ACCOUNT_ID**: Join to Pylon account data
- **SALESFORCE_ACCOUNT_ID**: Join to Salesforce CRM data
- **ASSIGNEE_ID/REQUESTER_ID**: Join to user/employee tables
- **TEAM_ID**: Join to team/organization data

### Data Quality Considerations

- **Negative TIME_TO_RESOLUTION values**: May indicate data sync issues or timezone problems
- **Missing ASSIGNEE data**: 30.78% unassigned issues may affect team performance analysis
- **Missing Salesforce data**: 19-20% of issues lack CRM context
- **EXTERNAL_ISSUE_LINK**: Only 4.61% populated, mostly null
- **Tag parsing**: TAGS field contains JSON arrays requiring special handling

### Performance Optimization Tips

- Use DATE functions on timestamp fields for time-based queries
- Consider indexing on frequently filtered columns (ISSUE_STATE, SUPPORT_TIER_LEVEL)
- JSON parsing may be needed for CUSTOM_FIELDS and TAGS analysis
- Time calculations benefit from business hours vs. total time distinction
