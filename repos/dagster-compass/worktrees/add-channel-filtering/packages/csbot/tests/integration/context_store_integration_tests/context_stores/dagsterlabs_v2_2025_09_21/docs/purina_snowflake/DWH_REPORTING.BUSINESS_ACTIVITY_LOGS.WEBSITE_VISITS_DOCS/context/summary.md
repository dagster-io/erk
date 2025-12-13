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

# Dataset Summary: WEBSITE_VISITS_DOCS

## Overall Dataset Characteristics

- **Total Rows**: 921,896 website visit records
- **Data Quality**: Generally high quality with consistent event tracking
- **Time Period**: Appears to span from 2025 (based on timestamp samples)
- **Primary Purpose**: Web analytics tracking for Dagster documentation website with CRM integration
- **Notable Patterns**:
  - High percentage of anonymous visitors (73.77% missing emails)
  - Most visits lack marketing attribution data (>99% null for campaign fields)
  - Strong segmentation between anonymous and identified visitors

## Column Details

### Primary Identifiers

- **EVENT_ID**: Unique visit identifier (VARCHAR, 0% null) - Primary key with 921,896 unique values
- **ANONYMOUS_ID**: Visitor tracking ID (VARCHAR, 0% null) - 147,351 unique visitors indicating repeat visits
- **TIMESTAMP**: Visit timestamp (TIMESTAMP_NTZ, 0% null) - 920,612 unique values showing precise tracking

### User Identity Fields

- **EMAIL**: User email when available (VARCHAR, 73.77% null) - 7,141 unique emails when present
- **USER_ID**: Logged-in user identifier (VARCHAR, 92.11% null) - 2,100 unique users when logged in
- **IS_INTERNAL_USER**: Employee flag (BOOLEAN, 73.77% null) - True/False values for identified users

### Page/Content Information

- **TITLE**: Page title (VARCHAR, 0% null) - 856 unique page titles across documentation
- **PATH**: URL path (VARCHAR, 0% null) - 1,222 unique paths showing site structure
- **URL**: Full page URL (VARCHAR, 0% null) - 29,515 unique URLs with parameters

### Traffic Source Data

- **REFERRER**: Full referring URL (VARCHAR, 28.79% null) - 6,806 unique referrers
- **REFERRER_HOST**: Referring domain (VARCHAR, 28.79% null) - 1,925 unique domains
- **REFERRER_HOST_UNPARSED**: Raw referrer data (VARCHAR, 28.79% null)

### Search & Campaign Attribution

- **SEARCH**: Search query parameters (VARCHAR, 96.40% null) - Mostly empty, 26,941 unique when present
- **SEARCH_PARAMS**: Search parameters as JSON (VARIANT, 0% null) - 26,939 unique parameter sets
- **CAMPAIGN_SOURCE**: Marketing source (VARCHAR, 99.61% null) - 18 sources when present
- **CAMPAIGN_MEDIUM**: Marketing medium (VARCHAR, 99.90% null) - 8 mediums when present
- **CAMPAIGN_NAME**: Campaign identifier (VARCHAR, 99.90% null) - 19 campaigns when present
- **CAMPAIGN_CONTENT**: Campaign content ID (VARCHAR, 99.91% null) - 32 content IDs when present
- **UTM_TERM**: UTM terms (VARCHAR, 99.93% null) - 48 terms including "dagster", "airflow", "AI pipeline tools"
- **GCLID**: Google Ads identifier (VARIANT, 99.94% null) - 471 unique click IDs when present
- **REDDIT_CID**: Reddit campaign ID (VARIANT, 100% null) - No data present

### CRM Integration Fields

- **CONTACT_NAME**: Salesforce contact name (VARCHAR, 75.59% null) - 6,699 unique contacts
- **ACCOUNT_ID**: Salesforce account ID (VARCHAR, 75.52% null) - 2,708 unique accounts
- **ACCOUNT_NAME**: Salesforce account name (VARCHAR, 75.52% null) - 2,706 unique company names
- **HUBSPOT_COMPANY_ID**: HubSpot company identifier (VARCHAR, 75.52% null) - 2,708 unique companies

## Potential Query Considerations

### Good for Filtering

- **TIMESTAMP**: Date range filtering for temporal analysis
- **PATH/TITLE**: Content performance analysis
- **REFERRER_HOST**: Traffic source analysis
- **IS_INTERNAL_USER**: Segmenting internal vs external traffic
- **EMAIL/USER_ID**: Identified vs anonymous user analysis

### Good for Grouping/Aggregation

- **PATH**: Page popularity metrics
- **REFERRER_HOST**: Traffic source analysis
- **ACCOUNT_NAME**: Company-level analytics
- **TITLE**: Content engagement analysis
- **CAMPAIGN_SOURCE/MEDIUM**: Marketing attribution (when present)

### Potential Join Keys

- **EMAIL**: Can link to other user/contact systems
- **ACCOUNT_ID**: Links to Salesforce Account records
- **HUBSPOT_COMPANY_ID**: Links to HubSpot company data
- **USER_ID**: Links to user management systems

### Data Quality Considerations

- High null percentages in marketing attribution fields limit campaign analysis
- 73%+ of visits are anonymous, limiting personalization queries
- Search parameters stored as VARIANT may need JSON parsing
- Some URLs contain local file paths indicating offline documentation usage
- Referrer data missing for ~29% of visits (direct traffic)

## Keywords

website analytics, web tracking, documentation visits, Dagster docs, user behavior, traffic sources, marketing attribution, CRM integration, Salesforce, HubSpot, page views, referrer analysis, campaign tracking, user identification, anonymous visitors, content performance, SEO analysis, conversion tracking

## Table and Column Documentation

**Table Comment**: "Segment web page visit data from the Docs website overlaid with basic Salesforce Contact and Account Info where possible."

**Column Comments**:

- EVENT_ID: "Unique identifier for the website visit event"
- ANONYMOUS_ID: "Anonymous identifier for the visitor"
- TIMESTAMP: "Date and time when the visit occurred"
- EMAIL: "Email of the visitor if available"
- USER_ID: "User identifier if the visitor is logged in"
- TITLE: "Title of the visited page"
- PATH: "Path of the visited page"
- REFERRER_HOST_UNPARSED: "Unparsed referrer host information"
- URL: "Full URL of the visited page"
- REFERRER: "Full referrer URL"
- REFERRER_HOST: "Host domain that referred the visit"
- SEARCH: "Search query used to find the page"
- SEARCH_PARAMS: "Parameters used in the search"
- CAMPAIGN_SOURCE: "Source of the marketing campaign"
- CAMPAIGN_MEDIUM: "Medium of the marketing campaign"
- CAMPAIGN_NAME: "Name of the marketing campaign"
- CAMPAIGN_CONTENT: "Content identifier of the marketing campaign"
- UTM_TERM: "UTM term parameter from the URL"
- REDDIT_CID: "Reddit campaign identifier"
- GCLID: "Google click identifier"
- IS_INTERNAL_USER: "Boolean flag indicating whether the visitor is an internal user (employee) or external user"
- CONTACT_NAME: "Name of the contact if matched with Salesforce"
- ACCOUNT_ID: "Salesforce account identifier if matched"
- ACCOUNT_NAME: "Name of the Salesforce account if matched"
- HUBSPOT_COMPANY_ID: "Hubspot company identifier if matched"
