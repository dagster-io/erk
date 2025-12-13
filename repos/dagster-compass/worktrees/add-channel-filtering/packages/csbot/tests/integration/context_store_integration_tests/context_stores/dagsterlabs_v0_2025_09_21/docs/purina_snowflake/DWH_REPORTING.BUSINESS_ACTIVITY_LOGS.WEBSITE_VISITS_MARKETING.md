---
columns:
  - ACCOUNT_ID (VARCHAR(16777216))
  - ACCOUNT_NAME (VARCHAR(765))
  - ANONYMOUS_ID (VARCHAR(16777216))
  - CAMPAIGN_CONTENT (VARCHAR(16777216))
  - CAMPAIGN_IDENTIFIER (VARCHAR(16777216))
  - CAMPAIGN_MEDIUM (VARCHAR(16777216))
  - CAMPAIGN_NAME (VARCHAR(16777216))
  - CAMPAIGN_SOURCE (VARCHAR(16777216))
  - CONTACT_NAME (VARCHAR(361))
  - EMAIL (VARCHAR(16777216))
  - EVENT_ID (VARCHAR(16777216))
  - GCLID (VARIANT)
  - HUBSPOT_COMPANY_ID (VARCHAR(16777216))
  - IS_INTERNAL_USER (BOOLEAN)
  - IS_PAID_CATEGORY (BOOLEAN)
  - PAGE_ATTRIBUTION_CATEGORY (VARCHAR(16777216))
  - PAGE_VIEW_NUMBER (NUMBER(18,0))
  - PAID_CAMPAIGN_PLATFORM (VARCHAR(16777216))
  - PATH (VARCHAR(16777216))
  - REDDIT_CID (VARIANT)
  - REFERRER (VARCHAR(16777216))
  - REFERRER_HOST (VARCHAR(16777216))
  - REFERRER_HOST_UNPARSED (VARCHAR(16777216))
  - REFERRER_MEDIUM (VARCHAR(16777216))
  - SEARCH (VARCHAR(16777216))
  - SEARCH_PARAMS (VARIANT)
  - SESSION_ATTRIBUTION_CATEGORY (VARCHAR(16777216))
  - SESSION_ID (VARCHAR(32))
  - SESSION_NUMBER (NUMBER(13,0))
  - TIMESTAMP (TIMESTAMP_NTZ(9))
  - TITLE (VARCHAR(16777216))
  - URL (VARCHAR(16777216))
  - USER_ID (VARCHAR(16777216))
  - UTM_TERM (VARCHAR(16777216))
schema_hash: f7561a4d729544731c46a3c2825b9be2dc45bb5b88791d6f3415ad36dae4c784
---

# Table Analysis Summary: DWH_REPORTING.BUSINESS_ACTIVITY_LOGS.WEBSITE_VISITS_MARKETING

## Table and Column Docs

**Table Comment:** Segment web page visit data from the marketing site overlaid with basic Salesforce Contact and Account Info where possible.

**Column Comments:**

- EVENT_ID: Unique identifier for the website visit event
- TIMESTAMP: Date and time when the visit occurred
- EMAIL: Email of the visitor if available
- ANONYMOUS_ID: Anonymous identifier for the visitor
- USER_ID: User identifier if the visitor is logged in
- IS_INTERNAL_USER: Boolean flag indicating whether the visitor is an internal user (employee) or external user
- PATH: Path of the visited page
- TITLE: Title of the visited page
- URL: Full URL of the visited page
- REFERRER_HOST_UNPARSED: Unparsed referrer host information
- REFERRER_HOST: Host domain that referred the visit
- REFERRER: Full referrer URL
- SEARCH: Search query used to find the page
- SEARCH_PARAMS: Parameters used in the search
- CAMPAIGN_MEDIUM: Medium of the marketing campaign
- CAMPAIGN_SOURCE: Source of the marketing campaign
- CAMPAIGN_NAME: Name of the marketing campaign
- CAMPAIGN_CONTENT: Content identifier of the marketing campaign
- UTM_TERM: UTM term parameter from the URL
- REDDIT_CID: Reddit campaign identifier
- GCLID: Google click identifier
- REFERRER_MEDIUM: Medium of the referrer that led the visitor to the page (e.g., direct, search, social, cpc, etc.)
- PAGE_ATTRIBUTION_CATEGORY: Categorization of the page view based on referrer, campaign, and path (e.g., cpc, search, docs, blog, other-campaign, etc.)
- PAGE_VIEW_NUMBER: Sequential number of the page view for a given anonymous visitor, ordered by timestamp
- IS_PAID_CATEGORY: Boolean indicating if the page view attribution category represents paid traffic (e.g., true for cpc, false for organic search or direct traffic)
- SESSION_ATTRIBUTION_CATEGORY: Attribution category for the session, based on the first page view in the session
- SESSION_ID: Unique identifier for the session, generated as a hash of anonymous_id and session_number
- SESSION_NUMBER: Sequential number of the session for a given anonymous visitor, incremented when a new session is detected based on inactivity threshold
- CONTACT_NAME: Name of the contact if matched with Salesforce
- ACCOUNT_NAME: Name of the Salesforce account if matched
- ACCOUNT_ID: Salesforce account identifier if matched
- HUBSPOT_COMPANY_ID: Hubspot company identifier if matched

## Overall Dataset Characteristics

- **Total Rows:** 3,340,001 website visit events
- **Data Quality:** High data completeness for core tracking fields (EVENT_ID, TIMESTAMP, ANONYMOUS_ID, PATH, URL) with 0% nulls
- **Time Range:** Data spans from 2023 to 2025, indicating active tracking over multiple years
- **Unique Visitors:** 1,210,173 unique anonymous IDs, suggesting substantial visitor volume
- **Sessions:** 2,048,882 unique sessions across visitors

## Column Analysis

### Core Identifiers

- **EVENT_ID:** Unique for every row (3.34M unique values), perfect primary key
- **ANONYMOUS_ID:** 1.21M unique values across 3.34M rows, indicating multiple page views per visitor
- **SESSION_ID:** 2.05M unique values, derived from anonymous_id and session_number

### Temporal Data

- **TIMESTAMP:** Nearly unique values (3.34M vs 3.34M rows), high precision timestamp data
- **PAGE_VIEW_NUMBER:** Ranges 1-4,769, indicating some very active users
- **SESSION_NUMBER:** Ranges 0-1,746, showing long-term visitor engagement

### User Information

- **EMAIL:** 88.65% null, only 15,923 unique emails when present (identified visitors)
- **USER_ID:** 93.33% null, 8,154 unique when present (logged-in users)
- **IS_INTERNAL_USER:** 88.65% null, boolean when present (employee identification)

### Page/Content Data

- **PATH:** 1,552 unique paths with common values like "/", "/blog/\*", "/platform"
- **TITLE:** 2,539 unique page titles with good descriptive content
- **URL:** 304,868 unique URLs (includes query parameters)

### Traffic Attribution

- **REFERRER_HOST:** 23.81% null, 7,386 unique domains including Google, social platforms
- **REFERRER_MEDIUM:** 57.34% null, 6 categories: ai, email, referral, search, social, unknown
- **PAGE_ATTRIBUTION_CATEGORY:** Complete data, 55 categories for traffic classification
- **SESSION_ATTRIBUTION_CATEGORY:** Complete data, 53 categories based on session start

### Marketing Campaign Data

- **Campaign fields** (SOURCE, MEDIUM, NAME, CONTENT): 91-93% null, present for paid/tracked campaigns
- **UTM_TERM:** 93.84% null, 478 unique terms when present
- **GCLID:** 95.33% null, Google Ads click IDs when present (130K unique)
- **REDDIT_CID:** 98.46% null, Reddit campaign tracking

### CRM Integration

- **CONTACT_NAME:** 90.52% null, 14,559 unique contacts when matched
- **ACCOUNT_NAME:** 90.49% null, 7,283 unique accounts when matched
- **ACCOUNT_ID/HUBSPOT_COMPANY_ID:** 90.49% null, Salesforce/HubSpot integration fields

## Query Considerations

### Excellent for Filtering

- **TIMESTAMP:** Time-based analysis and trending
- **PATH/URL:** Page-specific analysis
- **REFERRER_MEDIUM, PAGE_ATTRIBUTION_CATEGORY:** Traffic source analysis
- **IS_PAID_CATEGORY:** Paid vs organic traffic segmentation
- **EMAIL/USER_ID presence:** Known vs anonymous visitor analysis

### Good for Grouping/Aggregation

- **ANONYMOUS_ID:** Visitor-level metrics
- **SESSION_ID:** Session-level analysis
- **PAGE_ATTRIBUTION_CATEGORY:** Traffic source reporting
- **PATH:** Page performance analysis
- **REFERRER_HOST:** Referral source analysis

### Potential Join Keys

- **EMAIL:** Could join to user/contact tables
- **ACCOUNT_ID:** Salesforce Account lookups
- **HUBSPOT_COMPANY_ID:** HubSpot company data
- **USER_ID:** Internal user system integration

### Data Quality Considerations

- High null rates in marketing attribution fields (90%+) - expect sparse campaign data
- Email/user identification available for only ~11% of visits
- CRM matching (Salesforce/HubSpot) available for ~9.5% of visits
- Some fields like SEARCH_PARAMS and REDDIT_CID stored as VARIANT type
- REFERRER fields have moderate null rates (~24-57%)

## Keywords

website analytics, web tracking, marketing attribution, visitor behavior, session analysis, traffic sources, campaign tracking, page views, referrals, conversion tracking, dagster, salesforce integration, hubspot integration, utm tracking, google ads, reddit ads, organic traffic, paid traffic, user journey, web analytics
