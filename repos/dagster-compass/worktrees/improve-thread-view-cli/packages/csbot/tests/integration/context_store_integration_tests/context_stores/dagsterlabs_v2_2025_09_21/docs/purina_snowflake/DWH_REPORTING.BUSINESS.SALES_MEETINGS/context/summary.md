---
columns:
  - ATTENDEES (ARRAY)
  - CALL_CONVERSATION_KEY (VARCHAR(16777216))
  - CONVERSATION_ID (VARCHAR(16777216))
  - CONVERSATION_KEY (VARCHAR(16777216))
  - CREATED_AT (TIMESTAMP_TZ(0))
  - CUSTOMER_INVITE_COUNT (NUMBER(18,0))
  - END_AT (TIMESTAMP_TZ(0))
  - INTERNAL_INVITE_COUNT (NUMBER(18,0))
  - IS_ALL_DAY (BOOLEAN)
  - IS_CANCELED (BOOLEAN)
  - IS_FIRST_ACCOUNT_MEETING (BOOLEAN)
  - IS_FIRST_OPPORTUNITY_MEETING (BOOLEAN)
  - IS_INTERNAL (BOOLEAN)
  - IS_ORGANIZER_CURRENTLY_ACTIVE (BOOLEAN)
  - IS_RECURRING (BOOLEAN)
  - MEETING_EVENT_TYPE (VARCHAR(16777216))
  - MEETING_TITLE (VARCHAR(16777216))
  - MODIFIED_AT (TIMESTAMP_TZ(0))
  - OPPORTUNITY_ID (VARCHAR(16777216))
  - ORGANIZER_NAME (VARCHAR(16777216))
  - ORGANIZER_USER_ID (NUMBER(38,0))
  - PRIMARY_ACCOUNT_ID (VARCHAR(16777216))
  - PRIMARY_ACCOUNT_NAME (VARCHAR(765))
  - START_AT (TIMESTAMP_TZ(0))
schema_hash: 4406b145bea59409d3209276958157c9fac813805ead364738b7783fe03c7d1e
---

# Table Analysis Summary: DWH_REPORTING.BUSINESS.SALES_MEETINGS

## Overall Dataset Characteristics

- **Total Rows**: 9,243 meetings
- **Data Quality**: High quality with minimal null values (most columns have 0% nulls)
- **Time Range**: Contains meetings from 2023 through 2025, with timestamps in UTC
- **Primary Focus**: External sales meetings (no internal-only meetings in dataset)
- **Notable Patterns**:
  - All meetings have external attendees (IS_INTERNAL is always False)
  - No all-day events (IS_ALL_DAY is always False)
  - High uniqueness in conversation keys and IDs indicating comprehensive meeting tracking

## Table and Column Documentation

**Table Comment**: One line per meeting from Gong with aggregated attendee information and enriched business context

### Column Details

#### Identifiers and Keys

- **CONVERSATION_KEY** (VARCHAR): Unique identifier for each meeting (100% unique, no nulls)
- **CALL_CONVERSATION_KEY** (VARCHAR): Associated call conversation key (100% unique)
- **CONVERSATION_ID** (VARCHAR): Gong conversation identifier (100% unique)
- **ORGANIZER_USER_ID** (NUMBER): Internal user ID of meeting organizer (53 unique values, 3.71% nulls)

#### Meeting Basic Information

- **MEETING_TITLE** (VARCHAR): Meeting titles with high variety (6,685 unique titles)
- **START_AT** (TIMESTAMP_TZ): Meeting start times (6,470 unique values, no nulls)
- **END_AT** (TIMESTAMP_TZ): Meeting end times (7,138 unique values, no nulls)
- **ORGANIZER_NAME** (VARCHAR): 53 unique organizers (3.71% nulls matching organizer user ID nulls)

#### Meeting Metadata

- **IS_CANCELED** (BOOLEAN): Meeting cancellation status (mostly False)
- **IS_RECURRING** (BOOLEAN): Recurring meeting indicator (mostly False)
- **IS_ALL_DAY** (BOOLEAN): All-day event flag (always False)
- **IS_INTERNAL** (BOOLEAN): Internal meeting flag (always False - all meetings have external participants)
- **MEETING_EVENT_TYPE** (VARCHAR): Event type with 3 values (MeetingCancelledEvent, MeetingUpdatedEvent, MeetingsSnowflakeBackfiller$1)

#### Attendee Information

- **ATTENDEES** (ARRAY): Complex JSON array containing detailed attendee information including:
  - attendee_name, title, email, invitee_status
  - account_name, salesforce_contact_id, affiliation (company/non_company)
- **CUSTOMER_INVITE_COUNT** (NUMBER): External attendees (range 1-42)
- **INTERNAL_INVITE_COUNT** (NUMBER): Internal attendees (range 0-43)
- **IS_ORGANIZER_CURRENTLY_ACTIVE** (BOOLEAN): Current organizer status (3.71% nulls)

#### Business Context

- **PRIMARY_ACCOUNT_NAME** (VARCHAR): Associated account name (2,146 unique accounts, 8.42% nulls)
- **PRIMARY_ACCOUNT_ID** (VARCHAR): Salesforce account ID (2,147 unique, 8.42% nulls)
- **OPPORTUNITY_ID** (VARCHAR): Associated opportunity (2,241 unique, 14.44% nulls)
- **IS_FIRST_OPPORTUNITY_MEETING** (BOOLEAN): First meeting flag for opportunity
- **IS_FIRST_ACCOUNT_MEETING** (BOOLEAN): First meeting flag for account

#### Audit Fields

- **CREATED_AT** (TIMESTAMP_TZ): Meeting creation timestamp (8,221 unique values)
- **MODIFIED_AT** (TIMESTAMP_TZ): Last modification timestamp (8,944 unique values)

## Potential Query Considerations

### Filtering Columns

- **START_AT/END_AT**: Excellent for date range filtering
- **ORGANIZER_NAME**: Good for sales rep performance analysis
- **PRIMARY_ACCOUNT_NAME**: Filter by specific accounts
- **IS_CANCELED**: Exclude cancelled meetings
- **MEETING_EVENT_TYPE**: Filter by event types
- **IS_FIRST_OPPORTUNITY_MEETING/IS_FIRST_ACCOUNT_MEETING**: Identify new business activities

### Grouping/Aggregation Columns

- **ORGANIZER_NAME**: Sales rep performance metrics
- **PRIMARY_ACCOUNT_NAME**: Account-level meeting analysis
- **Date functions on START_AT**: Time-based trending (daily/weekly/monthly)
- **CUSTOMER_INVITE_COUNT/INTERNAL_INVITE_COUNT**: Meeting size analysis

### Potential Join Keys

- **PRIMARY_ACCOUNT_ID**: Links to Salesforce Account records
- **OPPORTUNITY_ID**: Links to Salesforce Opportunity records
- **ORGANIZER_USER_ID**: Links to user/employee tables
- **ATTENDEES array contacts**: Salesforce Contact IDs for attendee analysis

### Data Quality Considerations

- **Null Handling**: 8.42% of meetings lack primary account information; 14.44% lack opportunity association
- **Array Processing**: ATTENDEES column requires JSON parsing functions for detailed analysis
- **Time Zones**: All timestamps are in UTC
- **Historical Data**: Contains future dates (2025) indicating scheduled meetings
- **Organizer Status**: Some organizers may be inactive (IS_ORGANIZER_CURRENTLY_ACTIVE = False)

## Keywords

sales meetings, gong, conversation tracking, customer meetings, sales performance, meeting analytics, attendee management, salesforce integration, opportunity tracking, account management, sales rep activity, meeting metadata, customer engagement, business development, sales operations
