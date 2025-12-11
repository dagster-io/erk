---
columns:
  - ACCOUNT_ID (VARCHAR(16777216))
  - ACCOUNT_NAME (VARCHAR(765))
  - ADDITIONAL_EMAILS (ARRAY)
  - ASSIGNED_BUSINESS_UNIT_IDS_ARRAY (ARRAY)
  - BUSINESS_UNIT_NAMES_CONTACT (VARCHAR(16777216))
  - CONTACT_SOURCE (VARCHAR(120))
  - CREATED_DATE (TIMESTAMP_TZ(9))
  - CUSTOMER_DATE (TIMESTAMP_TZ(9))
  - EMAIL_DOMAIN_CONTACT (VARCHAR(16777216))
  - EMAIL_HASH (VARCHAR(128))
  - ENGAGEMENT_SCORE (FLOAT)
  - ENRICHMENT_DETAILS (VARCHAR(765))
  - EVER_COMPLETED_DAGSTER_U_COURSE (BOOLEAN)
  - EVER_ENROLLED_IN_DAGSTER_U (BOOLEAN)
  - FIRST_NAME (VARCHAR(120))
  - FIRST_TOUCH_ADGROUP_ID (VARCHAR(16777216))
  - FIRST_TOUCH_ADGROUP_NAME (VARCHAR(256))
  - FIRST_TOUCH_ATTRIBUTION_CATEGORY (VARCHAR(16777216))
  - FIRST_TOUCH_CAMPAIGN_CONTENT (VARCHAR(16777216))
  - FIRST_TOUCH_CAMPAIGN_ID (VARCHAR(16777216))
  - FIRST_TOUCH_CAMPAIGN_MEDIUM (VARCHAR(16777216))
  - FIRST_TOUCH_CAMPAIGN_NAME (VARCHAR(16777216))
  - FIRST_TOUCH_CAMPAIGN_SOURCE (VARCHAR(16777216))
  - FIRST_TOUCH_PATH (VARCHAR(16777216))
  - FIRST_TOUCH_REFERRER_HOST (VARCHAR(16777216))
  - FIRST_TOUCH_REFERRER_MEDIUM (VARCHAR(16777216))
  - FIRST_TOUCH_SESSION_STARTED_AT (TIMESTAMP_NTZ(9))
  - FIRST_TOUCH_UTM_TERM (VARCHAR(16777216))
  - FIT_SCORE (FLOAT)
  - GTM_LEAD_SOURCE (VARCHAR(256))
  - GTM_LEAD_SOURCE_ACTION (VARCHAR(256))
  - HUBSPOT_COMPANY_ID (VARCHAR(16777216))
  - HUBSPOT_CONTACT_ID (VARCHAR(16777216))
  - IMPORT_SOURCE (VARCHAR(256))
  - IS_COMPASS_CONTACT (BOOLEAN)
  - IS_DAGSTER_CONTACT (BOOLEAN)
  - IS_INTERNAL_USER (BOOLEAN)
  - IS_PERSONAL_EMAIL (BOOLEAN)
  - LAST_BDR_ACTIVITY_DATE (TIMESTAMP_TZ(9))
  - LAST_MODIFIED_TIME (TIMESTAMP_TZ(9))
  - LAST_NAME (VARCHAR(240))
  - LAST_SELLER_ACTIVITY_DATE (TIMESTAMP_TZ(9))
  - LATEST_SOURCE (VARCHAR(256))
  - LATEST_SOURCE_DATE (TIMESTAMP_TZ(9))
  - LATEST_SOURCE_DRILL_LEVEL_1 (VARCHAR(256))
  - LATEST_SOURCE_DRILL_LEVEL_2 (VARCHAR(16777216))
  - LEAD_DATE (TIMESTAMP_TZ(9))
  - LEAD_SOURCE (VARCHAR(765))
  - LEAD_SOURCE_ACTION (VARCHAR(256))
  - LIFECYCLE_STAGE (VARCHAR(256))
  - LIFECYCLE_STAGE_DATE (TIMESTAMP_TZ(9))
  - LINKEDIN_URL (VARCHAR(765))
  - MARKETING_LEAD_SOURCE (VARCHAR(256))
  - MQL_DATE (TIMESTAMP_TZ(9))
  - NAME (VARCHAR(361))
  - NUM_DAGSTER_U_COURSES_STARTED (NUMBER(18,0))
  - ORIGINAL_SOURCE (VARCHAR(256))
  - ORIGINAL_SOURCE_DRILL_LEVEL_1 (VARCHAR(256))
  - ORIGINAL_SOURCE_DRILL_LEVEL_2 (VARCHAR(16777216))
  - ORIGINAL_SOURCE_DRILL_LEVEL_2_CATEGORY (VARCHAR(16777216))
  - OWNER_ID (VARCHAR(16777216))
  - PHONE (VARCHAR(120))
  - SALESFORCE_CONTACT_ID (VARCHAR(16777216))
  - SQL_DATE (TIMESTAMP_TZ(9))
  - STATUS (VARCHAR(765))
  - TITLE (VARCHAR(384))
  - TITLE_CATEGORY (VARCHAR(16777216))
  - TRAFFIC_SOURCE (VARCHAR(765))
  - TRIAL_SOURCE (VARCHAR(256))
  - WAS_EVER_CUSTOMER (BOOLEAN)
  - WAS_EVER_LEAD (BOOLEAN)
  - WAS_EVER_MQL (BOOLEAN)
  - WAS_EVER_SQL (BOOLEAN)
  - WAS_MQL_FROM_CUSTOMER_DATE (BOOLEAN)
schema_hash: d48d6c8cbf486fc75e5e7d1ee2b23bf0c7955b0c5f5ba204cb986e6fee858c3b
---

# Table Summary: DWH_REPORTING.BUSINESS.CONTACTS

## Keywords

Salesforce, HubSpot, contacts, CRM, lead management, marketing attribution, customer lifecycle, business development, email marketing, contact tracking, account management, lead scoring, sales funnel

## Table and Column Documentation

**Table Comment:** One line per contacts in Salesforce, with additional information from other Salesforce and Hubspot tables

**Column Comments:**

- SALESFORCE_CONTACT_ID: Unique identifier for the contact from Salesforce
- ACCOUNT_ID: Identifier of the associated account
- NAME: Full name of the contact
- HUBSPOT_CONTACT_ID: Identifier for the contact in Hubspot
- ACCOUNT_NAME: Name of the associated account
- HUBSPOT_COMPANY_ID: Identifier for the company in Hubspot
- LAST_NAME: Last name of the contact
- FIRST_NAME: First name of the contact
- IS_PERSONAL_EMAIL: Boolean indicating if the contact's email is from a personal email domain
- EMAIL_DOMAIN_CONTACT: The domain part of the contact's email address
- PHONE: Phone number of the contact
- IS_INTERNAL_USER: Boolean indicating if the contact is an internal user based on email domain
- TITLE: Job title of the contact
- ENRICHMENT_DETAILS: Additional enrichment details about the contact
- TITLE_CATEGORY: Categorized classification of the contact's job title based on standardized mappings
- LEAD_SOURCE: Original source of the lead
- CONTACT_SOURCE: Source of the contact in Salesforce
- TRAFFIC_SOURCE: Traffic source for the contact
- OWNER_ID: Identifier for the contact owner
- STATUS: Current status of the contact
- LINKEDIN_URL: URL to the contact's LinkedIn profile
- CREATED_DATE: Date when the contact was created in Salesforce
- [Additional detailed comments for lifecycle, attribution, and scoring fields...]

## Overall Dataset Characteristics

**Total Rows:** 201,410 contacts

**General Data Quality:** The dataset shows good overall completeness for core fields like contact IDs and names, but has significant null percentages in optional fields like enrichment details (97.77%), LinkedIn URLs (62.95%), and various attribution tracking fields (95-99% null). This suggests a mix of highly tracked contacts and basic contact records.

**Notable Patterns:**

- Strong relationship between Salesforce and HubSpot systems with dual ID tracking
- Rich attribution and lifecycle tracking for engaged contacts
- Concentration of activity around specific lead sources and campaigns
- Clear segmentation between personal and business email addresses

## Column Analysis

### Core Identifiers

- **SALESFORCE_CONTACT_ID**: Perfect uniqueness (201,410 unique values, 0% null) - primary key
- **HUBSPOT_CONTACT_ID**: High uniqueness with some nulls (183,141 unique, 9.07% null)
- **ACCOUNT_ID**: Links to 32,119 unique accounts (0.02% null)

### Contact Information

- **NAME/FIRST_NAME/LAST_NAME**: High uniqueness in names (180,272 unique full names)
- **EMAIL_HASH**: Hashed email addresses (184,110 unique, 8.58% null)
- **EMAIL_DOMAIN_CONTACT**: 33,931 unique domains, indicating diverse company representation
- **PHONE**: Available for ~58% of contacts (41.92% null)

### Classification Fields

- **TITLE_CATEGORY**: 5 standardized categories (Executive, Individual Contributor, Manager, Other)
- **IS_PERSONAL_EMAIL**: Clear boolean split between personal/business emails
- **IS_INTERNAL_USER**: Flags internal company contacts

### Lead Attribution & Sources

- **LEAD_SOURCE**: 20 different sources with 20.44% null rate
- **GTM_LEAD_SOURCE**: 17 go-to-market sources (9.08% null)
- **TRAFFIC_SOURCE**: 10 traffic channels with high null rate (52.01%)

### Lifecycle Management

- **STATUS**: 9 status categories (Prospect, Client, Qualified, etc.)
- **LIFECYCLE_STAGE**: 7 stages tracking progression through sales funnel
- **WAS*EVER*[LEAD/MQL/SQL/CUSTOMER]**: Boolean flags for lifecycle history

### Scoring & Engagement

- **ENGAGEMENT_SCORE**: Numeric score 0-238 (17.12% null)
- **FIT_SCORE**: Numeric score 0-195 (12.78% null)
- **NUM_DAGSTER_U_COURSES_STARTED**: 0-4 courses (specific to business context)

### Temporal Tracking

- **CREATED_DATE**: Full timestamp coverage for all contacts
- **LAST_MODIFIED_TIME**: Recent activity tracking (9.07% null)
- **Various \_DATE fields**: Track progression through lifecycle stages

## Query Considerations

### Ideal for Filtering

- **STATUS**: Well-distributed categorical values
- **TITLE_CATEGORY**: Standardized job role categories
- **LEAD_SOURCE/GTM_LEAD_SOURCE**: Source attribution analysis
- **IS_PERSONAL_EMAIL/IS_INTERNAL_USER**: Boolean segmentation
- **LIFECYCLE_STAGE**: Sales funnel analysis
- **Date fields**: Temporal filtering and cohort analysis

### Good for Grouping/Aggregation

- **ACCOUNT_NAME**: Company-level analysis (31,979 unique companies)
- **EMAIL_DOMAIN_CONTACT**: Domain-based segmentation
- **OWNER_ID**: Sales rep performance (36 unique owners)
- **TITLE_CATEGORY**: Role-based analysis
- **Various source fields**: Attribution reporting

### Potential Join Keys

- **SALESFORCE_CONTACT_ID**: Primary key for contact-related tables
- **ACCOUNT_ID**: Links to account/company tables
- **HUBSPOT_CONTACT_ID/HUBSPOT_COMPANY_ID**: HubSpot system integration
- **OWNER_ID**: Links to sales rep/user tables

### Data Quality Considerations

- High null rates in attribution fields may require careful handling in analysis
- EMAIL_HASH field suggests privacy compliance but limits direct email analysis
- CONTACT_SOURCE is completely null (100%) - may be deprecated
- First-touch attribution fields are sparse (95-99% null) but valuable when present
- Some fields have data quality issues (trailing spaces in TITLE_CATEGORY values)
