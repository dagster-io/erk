---
columns:
  - ACCOUNT_ID (VARCHAR(16777216))
  - ACCOUNT_NAME (VARCHAR(765))
  - ANONYMOUS_ID (VARCHAR(16777216))
  - CAMPAIGN_CONTENT (VARCHAR(16777216))
  - CAMPAIGN_MEDIUM (VARCHAR(16777216))
  - CAMPAIGN_NAME (VARCHAR(16777216))
  - CAMPAIGN_SOURCE (VARCHAR(16777216))
  - CONTACT_NAME (VARCHAR(361))
  - EMAIL (VARCHAR(16777216))
  - ENABLED_FEATURE_FLAGS (VARCHAR(16777216))
  - EVENT_ID (VARCHAR(16777216))
  - GCLID (VARIANT)
  - HUBSPOT_COMPANY_ID (VARCHAR(16777216))
  - IS_INTERNAL_USER (BOOLEAN)
  - PATH (VARCHAR(16777216))
  - REDDIT_CID (VARIANT)
  - REFERRER (VARCHAR(16777216))
  - REFERRER_HOST (VARCHAR(16777216))
  - REFERRER_HOST_UNPARSED (VARCHAR(16777216))
  - SEARCH (VARCHAR(16777216))
  - SEARCH_PARAMS (VARIANT)
  - TIMESTAMP (TIMESTAMP_NTZ(9))
  - TITLE (VARCHAR(16777216))
  - URL (VARCHAR(16777216))
  - USER_ID (VARCHAR(16777216))
  - UTM_TERM (VARCHAR(16777216))
schema_hash: 9941323e8c092b956164a1fc14cc0715d326de7cdb0157e4a2f5d576a9dafb03
---

# WEBSITE_VISITS_CLOUD Table Summary

## Overall Dataset Characteristics

- **Total Rows**: 26,244,835 records
- **Data Quality**: Generally high data quality with most core fields populated
- **Notable Patterns**:
  - Heavy concentration of internal web application usage (Dagster Cloud platform)
  - Strong correlation between authenticated users (EMAIL/USER_ID populated) and CRM data matching
  - Significant presence of SQL injection and XSS attack attempts in various fields
  - Campaign/marketing data is sparsely populated (100% null for most UTM fields)
- **Table Purpose**: Tracks web page visits on Dagster Cloud platform with overlay of Salesforce Contact and Account data

## Column Details

### Core Event Fields

- **EVENT_ID**: Unique visit identifier, 100% populated with UUID-like format
- **ANONYMOUS_ID**: Session identifier (168,561 unique values), contains malicious injection attempts
- **TIMESTAMP**: Visit timestamp, nearly unique per event, spans multiple years
- **URL**: Full page URL, highly diverse (4M+ unique values), shows Dagster Cloud subdomain pattern

### User Identity Fields

- **EMAIL**: User email when available (98.81% populated), 23,278 unique users
- **USER_ID**: Numeric user ID when logged in (98.74% populated), 21,843 unique users
- **IS_INTERNAL_USER**: Boolean flag distinguishing employees vs external users (98.81% populated)

### Page/Navigation Fields

- **PATH**: URL path template (205 unique patterns), shows application structure
- **TITLE**: Page titles (2.5M+ unique), often contains run IDs and job names
- **REFERRER/REFERRER_HOST**: Traffic source data (64.39% populated), mix of internal navigation and external referrers
- **SEARCH/SEARCH_PARAMS**: Search functionality data (15.51% and 100% populated respectively)

### Marketing/Campaign Fields

- **CAMPAIGN_SOURCE/MEDIUM/NAME/CONTENT**: UTM tracking parameters (all 100% null except sparse values)
- **UTM_TERM**: Search terms for paid campaigns (100% null except 11 values)
- **GCLID**: Google Ads click tracking (100% null except 12 values)
- **REDDIT_CID**: Reddit campaign tracking (completely empty)

### Technical Fields

- **ENABLED_FEATURE_FLAGS**: Application feature flags (29.71% populated), JSON array format
- **SEARCH_PARAMS**: Query parameters (100% populated), mostly empty objects

### CRM Integration Fields

- **CONTACT_NAME**: Salesforce contact name (89.17% populated when user identified)
- **ACCOUNT_NAME**: Salesforce account name (89.18% populated)
- **ACCOUNT_ID**: Salesforce account ID (89.18% populated)
- **HUBSPOT_COMPANY_ID**: HubSpot company identifier (89.18% populated)

## Security Concerns

Multiple fields contain SQL injection and XSS attack attempts, particularly in:

- ANONYMOUS_ID
- PATH
- REFERRER fields
- SEARCH fields

## Query Considerations

### Good for Filtering

- **TIMESTAMP**: Date/time range filtering
- **IS_INTERNAL_USER**: Segment internal vs external traffic
- **EMAIL/USER_ID**: User-specific analysis
- **PATH**: Page/feature usage analysis
- **ACCOUNT_NAME/CONTACT_NAME**: Customer segmentation

### Good for Grouping/Aggregation

- **PATH**: Page popularity analysis
- **IS_INTERNAL_USER**: User type analysis
- **ACCOUNT_NAME**: Customer usage patterns
- **REFERRER_HOST**: Traffic source analysis
- **DATE(TIMESTAMP)**: Time-based trending

### Potential Join Keys

- **EMAIL**: Link to other user tables
- **USER_ID**: Primary user identifier
- **ACCOUNT_ID**: Salesforce account linkage
- **HUBSPOT_COMPANY_ID**: HubSpot integration

### Data Quality Considerations

- High null percentages in marketing fields may limit campaign analysis
- Malicious input attempts should be filtered for clean analytics
- CRM data availability correlates strongly with authenticated sessions
- SEARCH_PARAMS stored as VARIANT type requires JSON parsing

## Keywords

website analytics, web traffic, user behavior, Dagster Cloud, Salesforce integration, HubSpot, page visits, user sessions, marketing attribution, UTM tracking, referral analysis, feature flags, SQL injection attempts, XSS attacks, customer analytics

## Table and Column Documentation

### Table Comment

"Segment web page visit data from the webapp overlaid with basic Salesforce Contact and Account Info where possible."

### Column Comments

- **EVENT_ID**: "Unique identifier for the website visit event"
- **ANONYMOUS_ID**: "Anonymous identifier for the visitor"
- **TIMESTAMP**: "Date and time when the visit occurred"
- **EMAIL**: "Email of the visitor if available"
- **USER_ID**: "User identifier if the visitor is logged in"
- **PATH**: "Path of the visited page"
- **IS_INTERNAL_USER**: "Boolean flag indicating whether the visitor is an internal user (employee) or external user"
- **TITLE**: "Title of the visited page"
- **REFERRER_HOST**: "Host domain that referred the visit"
- **URL**: "Full URL of the visited page"
- **REFERRER_HOST_UNPARSED**: "Unparsed referrer host information"
- **REFERRER**: "Full referrer URL"
- **CAMPAIGN_SOURCE**: "Source of the marketing campaign"
- **SEARCH**: "Search query used to find the page"
- **CAMPAIGN_MEDIUM**: "Medium of the marketing campaign"
- **SEARCH_PARAMS**: "Parameters used in the search"
- **CAMPAIGN_NAME**: "Name of the marketing campaign"
- **CAMPAIGN_CONTENT**: "Content identifier of the marketing campaign"
- **REDDIT_CID**: "Reddit campaign identifier"
- **UTM_TERM**: "UTM term parameter from the URL"
- **GCLID**: "Google click identifier"
- **CONTACT_NAME**: "Name of the contact if matched with Salesforce"
- **ACCOUNT_NAME**: "Name of the Salesforce account if matched"
- **HUBSPOT_COMPANY_ID**: "Hubspot company identifier if matched"
- **ACCOUNT_ID**: "Salesforce account identifier if matched"
