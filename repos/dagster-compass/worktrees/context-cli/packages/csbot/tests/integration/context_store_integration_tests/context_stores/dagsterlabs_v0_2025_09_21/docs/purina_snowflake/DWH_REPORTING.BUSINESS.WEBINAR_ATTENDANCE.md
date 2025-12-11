---
columns:
  - ACCOUNT_ID (VARCHAR(16777216))
  - ACCOUNT_NAME (VARCHAR(765))
  - ATTENDANCE_REGISTRATION_DIFF (NUMBER(19,0))
  - ATTENDANCE_STATUS (VARCHAR(27))
  - ATTENDED_LIVE (BOOLEAN)
  - CIRCLES_NUMBER (NUMBER(38,0))
  - COMMENTS_NUMBER (NUMBER(38,0))
  - CUMULATIVE_WEBINARS_ATTENDED (NUMBER(13,0))
  - CUMULATIVE_WEBINARS_REGISTERED (NUMBER(18,0))
  - EMAIL (VARCHAR(16777216))
  - ENGAGEMENT_SCORE (FLOAT)
  - HUBSPOT_COMPANY_ID (VARCHAR(16777216))
  - HUBSPOT_CONTACT_ID (VARCHAR(16777216))
  - INITIAL_JOIN_AT (TIMESTAMP_TZ(9))
  - IS_FIRST_WEBINAR_ATTENDED (BOOLEAN)
  - IS_FIRST_WEBINAR_REGISTRATION (BOOLEAN)
  - IS_INTERNAL_USER (BOOLEAN)
  - IS_PARENT_EVENT (BOOLEAN)
  - LEAD_SCORE (NUMBER(38,0))
  - LEAD_SCORE_DETAILS (VARIANT)
  - LIVE_TIME_HOURS (NUMBER(38,12))
  - MESSAGES_REACTIONS_COUNT (NUMBER(38,0))
  - NAME (VARCHAR(16777216))
  - ON_DEMAND_TIME_HOURS (NUMBER(38,6))
  - POLLS_NUMBER (NUMBER(38,0))
  - QUESTIONS (VARIANT)
  - QUESTIONS_NUMBER (NUMBER(38,0))
  - RAW_LEAD_SCORE (NUMBER(38,0))
  - REGISTRANT_ID (VARCHAR(16777216))
  - SALESFORCE_CONTACT_ID (VARCHAR(16777216))
  - SIGNED_UP_AT (TIMESTAMP_TZ(9))
  - TEST_STATUS (VARCHAR(11))
  - TITLE (VARCHAR(384))
  - TOTAL_ATTENDANCE_TIME_HOURS (NUMBER(38,12))
  - VIEWED_ON_DEMAND (BOOLEAN)
  - WEBINAR_ID (VARCHAR(16777216))
  - WEBINAR_NAME (VARCHAR(16777216))
  - WEBINAR_PLATFORM (VARCHAR(6))
  - WEBINAR_START_AT (TIMESTAMP_TZ(9))
schema_hash: 894ecef58965c35649b5fdef7d53567c12ea4477a5ec2f221f369709f5f5eb03
---

# Table Summary: DWH_REPORTING.BUSINESS.WEBINAR_ATTENDANCE

## Overall Dataset Characteristics

- **Total rows**: 8,365 records
- **Data quality**: High completeness for core fields with some platform-specific nulls
- **Coverage**: Spans webinars from August 2024 through January 2025
- **Platform distribution**: Covers both Zoom (majority) and Sequel platforms
- **Attendance patterns**: Mix of registration types with varying engagement levels

## Table and Column Documentation

**Table Comment**: Unified view of webinar attendance across Zoom and Sequel platforms, combining registration and attendance data

## Column Details

### Core Identifiers

- **REGISTRANT_ID** (VARCHAR): Platform-specific unique identifier for each registrant (0% null, 8,365 unique values)
- **WEBINAR_ID** (VARCHAR): Platform-specific webinar identifier (0% null, 24 unique webinars)
- **EMAIL** (VARCHAR): Registrant email address (0% null, 4,826 unique emails indicating repeat attendees)

### Webinar Information

- **WEBINAR_NAME** (VARCHAR): Webinar title (0% null, 24 unique webinars covering topics like Dagster, data platforms, MLOps)
- **WEBINAR_START_AT** (TIMESTAMP_TZ): Webinar start time (0% null, 24 unique times, mostly 16:00 or 17:00 UTC)
- **WEBINAR_PLATFORM** (VARCHAR): Hosting platform - "Zoom" or "Sequel" (0% null)

### Registration & Attendance

- **ATTENDANCE_STATUS** (VARCHAR): 5 statuses including "Attended Live", "Registered, Did Not Attend", "Attended On Demand" (0% null)
- **SIGNED_UP_AT** (TIMESTAMP_TZ): Registration timestamp (0.1% null, 8,336 unique values)
- **INITIAL_JOIN_AT** (TIMESTAMP_TZ): First join time for Zoom webinars (71.7% null - Zoom only field)
- **ATTENDED_LIVE** (BOOLEAN): Live attendance flag (0% null)
- **VIEWED_ON_DEMAND** (BOOLEAN): On-demand viewing flag (82.5% null - Sequel only)

### User Classification

- **IS_INTERNAL_USER** (BOOLEAN): Internal user flag based on email domain (0% null)
- **IS_FIRST_WEBINAR_REGISTRATION** (BOOLEAN): First-time registration indicator (0% null)
- **IS_FIRST_WEBINAR_ATTENDED** (BOOLEAN): First-time attendance indicator (0% null)

### Engagement Metrics

- **TOTAL_ATTENDANCE_TIME_HOURS** (NUMBER): Total attendance duration in hours (54.2% null, range 0-20.2 hours)
- **LIVE_TIME_HOURS** (NUMBER): Live session time (54.2% null, Sequel only)
- **ON_DEMAND_TIME_HOURS** (NUMBER): On-demand viewing time (82.5% null, Sequel only)
- **ENGAGEMENT_SCORE** (FLOAT): Sequel engagement score 0-76 (82.5% null)
- **LEAD_SCORE** (NUMBER): Sequel lead score 1-10 (82.5% null)

### Cumulative Tracking

- **CUMULATIVE_WEBINARS_REGISTERED** (NUMBER): Total registrations per email (0% null, range 1-17)
- **CUMULATIVE_WEBINARS_ATTENDED** (NUMBER): Total attendances per email (0% null, range 0-13)
- **ATTENDANCE_REGISTRATION_DIFF** (NUMBER): Difference metric (0% null, range -10 to 0)

### Interactive Features (Sequel Only - 82.5% null)

- **POLLS_NUMBER** (NUMBER): Poll participations (0-4 range)
- **QUESTIONS_NUMBER** (NUMBER): Questions asked (0-7 range)
- **QUESTIONS** (VARIANT): JSON array of question details
- **COMMENTS_NUMBER** (NUMBER): Comments made (0-11 range)
- **MESSAGES_REACTIONS_COUNT** (NUMBER): Reaction count (0-4 range)

### CRM Integration

- **SALESFORCE_CONTACT_ID** (VARCHAR): Salesforce contact ID (3% null, 4,690 unique)
- **HUBSPOT_CONTACT_ID** (VARCHAR): HubSpot contact ID (4.2% null, 4,628 unique)
- **ACCOUNT_ID** (VARCHAR): Salesforce account ID (3% null, 2,281 unique)
- **ACCOUNT_NAME** (VARCHAR): Company name (3% null, 2,278 unique)
- **TITLE** (VARCHAR): Job title (39.3% null, 1,230 unique)

### Contact Details

- **NAME** (VARCHAR): Registrant name (54.2% null, 2,596 unique)

## Query Considerations

### Good for Filtering

- **WEBINAR_PLATFORM**: Filter by Zoom vs Sequel
- **ATTENDANCE_STATUS**: Filter by attendance type
- **IS_INTERNAL_USER**: Exclude internal users
- **WEBINAR_START_AT**: Date range filtering
- **EMAIL**: Individual user analysis

### Good for Grouping/Aggregation

- **WEBINAR_NAME**: Webinar performance analysis
- **ACCOUNT_NAME**: Company-level analysis
- **ATTENDANCE_STATUS**: Attendance pattern analysis
- **WEBINAR_PLATFORM**: Platform comparison
- **TITLE**: Role-based analysis

### Potential Join Keys

- **EMAIL**: Primary key for user journey analysis
- **SALESFORCE_CONTACT_ID**: Link to Salesforce data
- **HUBSPOT_CONTACT_ID**: Link to HubSpot data
- **ACCOUNT_ID**: Link to account/company data

### Data Quality Considerations

- Platform-specific nulls (82.5% for Sequel-only fields)
- Name field has 54% nulls - use with caution
- Title field has 39% nulls
- Some engagement metrics only available for attended sessions
- Time fields may need timezone considerations

## Keywords

webinar, attendance, registration, engagement, zoom, sequel, dagster, data platform, mlops, live attendance, on-demand viewing, lead scoring, crm integration, salesforce, hubspot, user journey, cumulative metrics, platform comparison, attendance analytics
