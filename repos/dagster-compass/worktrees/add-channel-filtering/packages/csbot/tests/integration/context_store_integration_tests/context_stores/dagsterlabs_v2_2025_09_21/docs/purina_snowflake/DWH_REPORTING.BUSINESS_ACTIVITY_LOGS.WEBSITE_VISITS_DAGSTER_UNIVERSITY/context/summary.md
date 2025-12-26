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
schema_hash: 6e3f4325b86fc13e4dbbd981ab53a9dd41d4b121ba051511dd7038f7f1dcd763
---

# Dataset Summary: Dagster University Website Visits

## Overall Dataset Characteristics

- **Total Rows**: 191,257
- **Data Quality**: High quality with minimal null values in core tracking fields
- **Time Range**: Data spans multiple years (2024-2025 based on timestamps)
- **Purpose**: Web analytics data for Dagster University with integrated CRM data from Salesforce and HubSpot
- **Table Comment**: Segment web page visit data from Dagster University overlaid with basic Salesforce Contact and Account Info where possible.

## Column Details

### Core Event Data

- **EVENT_ID**: Unique visit identifier (VARCHAR, 0% null) - Primary key with 191,257 unique values
- **TIMESTAMP**: Visit timestamp (TIMESTAMP_NTZ, 0% null) - Nearly all unique values (191,218)
- **ANONYMOUS_ID**: Anonymous visitor tracking (VARCHAR, 0% null) - 34,609 unique values indicating repeat visitors

### User Identification

- **EMAIL**: Visitor email (VARCHAR, 21.09% null) - 9,355 unique emails when available
- **USER_ID**: Logged-in user ID (VARCHAR, 92.47% null) - Only 1,233 unique values, indicating most visits are anonymous
- **IS_INTERNAL_USER**: Employee flag (BOOLEAN, 21.09% null) - Distinguishes internal vs external users

### Page Data

- **TITLE**: Page title (VARCHAR, 14.54% null) - 100 unique page titles
- **PATH**: URL path (VARCHAR, 0% null) - 1,830 unique paths including course-specific URLs
- **URL**: Complete URL (VARCHAR, 0% null) - 9,842 unique URLs

### Traffic Source Data

- **REFERRER_HOST**: Referring domain (VARCHAR, 20.97% null) - 450 unique referring hosts
- **REFERRER**: Full referrer URL (VARCHAR, 20.97% null) - 14,285 unique referrers
- **REFERRER_HOST_UNPARSED**: Raw referrer data (VARCHAR, 20.97% null)

### Marketing Attribution

- **CAMPAIGN_SOURCE**: Marketing source (VARCHAR, 99.59% null) - Limited data with 14 sources
- **CAMPAIGN_MEDIUM**: Marketing medium (VARCHAR, 99.74% null) - 6 mediums when available
- **CAMPAIGN_NAME**: Campaign name (VARCHAR, 99.75% null) - 14 campaign names
- **CAMPAIGN_CONTENT**: Campaign content ID (VARCHAR, 99.89% null) - Very sparse data
- **UTM_TERM**: UTM term parameter (VARCHAR, 100.00% null) - Minimal usage
- **SEARCH**: Search parameters (VARCHAR, 93.77% null) - 7,933 unique search strings
- **SEARCH_PARAMS**: Structured search data (VARIANT, 0% null but mostly null values)

### External Platform IDs

- **REDDIT_CID**: Reddit campaign ID (VARIANT, 100.00% null) - No Reddit data
- **GCLID**: Google click ID (VARIANT, 100.00% null) - Minimal Google Ads data

### CRM Integration (Salesforce)

- **CONTACT_NAME**: Salesforce contact name (VARCHAR, 23.25% null) - 8,624 unique contacts
- **ACCOUNT_ID**: Salesforce account ID (VARCHAR, 23.13% null) - 2,672 unique accounts
- **ACCOUNT_NAME**: Salesforce account name (VARCHAR, 23.13% null) - 2,669 unique account names
- **HUBSPOT_COMPANY_ID**: HubSpot company ID (VARCHAR, 23.13% null) - 2,672 unique companies

## Query Considerations

### Good for Filtering

- **TIMESTAMP**: Date/time range filtering
- **PATH**: Specific page analysis
- **EMAIL**: Known user analysis
- **IS_INTERNAL_USER**: Internal vs external segmentation
- **REFERRER_HOST**: Traffic source analysis
- **ACCOUNT_NAME**: Company-specific analysis

### Good for Grouping/Aggregation

- **ANONYMOUS_ID**: Visitor session analysis
- **PATH**: Page popularity metrics
- **TITLE**: Content performance
- **REFERRER_HOST**: Traffic source attribution
- **CAMPAIGN_SOURCE**: Marketing channel effectiveness
- **ACCOUNT_NAME**: Company engagement analysis

### Join Keys

- **EMAIL**: Links to CRM systems
- **ACCOUNT_ID**: Salesforce integration
- **HUBSPOT_COMPANY_ID**: HubSpot integration
- **ANONYMOUS_ID**: Visitor journey tracking

### Data Quality Considerations

- High null percentage in marketing attribution fields (99%+ for most UTM parameters)
- 92% of visits are anonymous (no USER_ID)
- CRM data available for ~77% of visits with emails
- Some local file paths in URL/PATH fields indicating offline content access
- Search parameters mostly empty but when present, often contain security tokens

## Keywords

web analytics, website visits, dagster university, salesforce integration, hubspot, user tracking, marketing attribution, utm parameters, referrer analysis, course engagement, anonymous visitors, logged-in users, page views, traffic sources, campaign tracking, crm overlay

## Table and Column Documentation

**Table Comment**: Segment web page visit data from Dagster University overlaid with basic Salesforce Contact and Account Info where possible.

**Column Comments**:

- EVENT_ID: Unique identifier for the website visit event
- TIMESTAMP: Date and time when the visit occurred
- EMAIL: Email of the visitor if available
- ANONYMOUS_ID: Anonymous identifier for the visitor
- USER_ID: User identifier if the visitor is logged in
- IS_INTERNAL_USER: Boolean flag indicating whether the visitor is an internal user (employee) or external user
- TITLE: Title of the visited page
- PATH: Path of the visited page
- URL: Full URL of the visited page
- REFERRER_HOST: Host domain that referred the visit
- REFERRER: Full referrer URL
- REFERRER_HOST_UNPARSED: Unparsed referrer host information
- SEARCH: Search query used to find the page
- SEARCH_PARAMS: Parameters used in the search
- CAMPAIGN_SOURCE: Source of the marketing campaign
- CAMPAIGN_MEDIUM: Medium of the marketing campaign
- CAMPAIGN_NAME: Name of the marketing campaign
- CAMPAIGN_CONTENT: Content identifier of the marketing campaign
- UTM_TERM: UTM term parameter from the URL
- REDDIT_CID: Reddit campaign identifier
- GCLID: Google click identifier
- CONTACT_NAME: Name of the contact if matched with Salesforce
- ACCOUNT_ID: Salesforce account identifier if matched
- ACCOUNT_NAME: Name of the Salesforce account if matched
- HUBSPOT_COMPANY_ID: Hubspot company identifier if matched
