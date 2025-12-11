---
columns:
  - ACCOUNT_ID (VARCHAR(16777216))
  - ACCOUNT_NAME (VARCHAR(765))
  - CAMPAIGN_END_DATE (DATE)
  - CAMPAIGN_ID (VARCHAR(16777216))
  - CAMPAIGN_MEMBER_ID (VARCHAR(16777216))
  - CAMPAIGN_NAME (VARCHAR(240))
  - CAMPAIGN_SOURCE (VARCHAR(765))
  - CAMPAIGN_START_DATE (DATE)
  - CAMPAIGN_STATUS (VARCHAR(765))
  - CAMPAIGN_TYPE (VARCHAR(765))
  - CONTACT_ID (VARCHAR(16777216))
  - CREATED_DATE (TIMESTAMP_TZ(9))
  - EMAIL (VARCHAR(240))
  - FIRST_NAME (VARCHAR(120))
  - FIRST_RESPONDED_DATE (DATE)
  - HAS_RESPONDED (BOOLEAN)
  - IS_ABM_CAMPAIGN (BOOLEAN)
  - IS_ACTIVE_CAMPAIGN (BOOLEAN)
  - IS_PARENT_CAMPAIGN (BOOLEAN)
  - LAST_NAME (VARCHAR(240))
  - MEMBER_STATUS (VARCHAR(120))
  - PARENT_CAMPAIGN_ID (VARCHAR(16777216))
  - PARENT_CAMPAIGN_NAME (VARCHAR(240))
  - SALESFORCE_OBJECT_ASSOCIATION (VARCHAR(120))
  - TITLE (VARCHAR(384))
schema_hash: f2f4a31b2fc263043f65220265788632ea5ac273186ebc1433755dc4984fc1c6
---

# Campaign Members Table Analysis Summary

## Overall Dataset Characteristics

The `DWH_REPORTING.BUSINESS.CAMPAIGN_MEMBERS` table contains **63,676 rows** representing individual campaign members from Salesforce. This is a comprehensive dataset tracking marketing campaign participation with good data quality overall. The table shows a mix of contact-based and account-based campaign members, with 97 unique campaigns represented.

**Key Patterns:**

- Most records (86.72%) have complete contact information
- 25.48% of members have responded to campaigns
- Campaign activity spans from 2023 to 2025
- Account-based marketing (ABM) campaigns represent a smaller subset
- Strong hierarchical structure with parent-child campaign relationships

## Column Details

### Identifiers and Keys

- **CAMPAIGN_ID**: VARCHAR, 97 unique campaigns, no nulls - Primary identifier for campaigns
- **CAMPAIGN_MEMBER_ID**: VARCHAR, fully unique (63,676 values), no nulls - Primary key for table
- **CONTACT_ID**: VARCHAR, 46,746 unique values, 13.28% nulls - Links to Salesforce contacts
- **ACCOUNT_ID**: VARCHAR, 24,205 unique accounts, minimal nulls (0.01%) - Company associations

### Personal Information

- **FIRST_NAME**: VARCHAR, 14,507 unique values, 14.06% nulls - Individual's first name
- **LAST_NAME**: VARCHAR, 26,941 unique values, 13.28% nulls - Individual's last name
- **EMAIL**: VARCHAR, 46,497 unique values, 13.67% nulls - Contact email addresses
- **TITLE**: VARCHAR, 14,854 unique job titles, 35.64% nulls - Professional roles

### Campaign Details

- **CAMPAIGN_NAME**: VARCHAR, 97 unique campaign names, no nulls - Descriptive campaign titles
- **MEMBER_STATUS**: VARCHAR, 9 possible statuses (Attended, Enrolled, On Demand, Registered, Requested, Responded, Scanned, Scheduled, Sent), no nulls
- **CAMPAIGN_TYPE**: VARCHAR, 11 types including Conference/Tradeshow, Webinar, ABM, etc., 7.29% nulls
- **CAMPAIGN_SOURCE**: VARCHAR, 10 sources like Website Signup, Marketing Event, 31.08% nulls
- **CAMPAIGN_STATUS**: VARCHAR, 3 statuses (Completed, In Progress, Planned), no nulls

### Response Tracking

- **HAS_RESPONDED**: BOOLEAN, no nulls - Response indicator
- **FIRST_RESPONDED_DATE**: DATE, 868 unique dates, 25.48% nulls - Initial response timing

### Campaign Hierarchy

- **PARENT_CAMPAIGN_ID**: VARCHAR, 11 unique parent campaigns, 11.29% nulls
- **PARENT_CAMPAIGN_NAME**: VARCHAR, 11 parent names (24-CONF, 25-ABM, etc.), 11.29% nulls
- **IS_PARENT_CAMPAIGN**: BOOLEAN, no nulls - Hierarchy indicator

### Temporal Data

- **CREATED_DATE**: TIMESTAMP_TZ, 34,357 unique timestamps, no nulls - Record creation
- **CAMPAIGN_START_DATE**: DATE, 56 unique dates, 46.27% nulls - Campaign launch
- **CAMPAIGN_END_DATE**: DATE, 32 unique dates, 72.21% nulls - Campaign completion

### Business Logic Flags

- **SALESFORCE_OBJECT_ASSOCIATION**: VARCHAR, 3 types (Account, Contact, Lead), no nulls
- **IS_ACTIVE_CAMPAIGN**: BOOLEAN, no nulls - Campaign status indicator
- **IS_ABM_CAMPAIGN**: BOOLEAN, no nulls - ABM classification

### Company Information

- **ACCOUNT_NAME**: VARCHAR, 24,448 unique company names, 0.69% nulls

## Potential Query Considerations

### Excellent for Filtering

- **CAMPAIGN_TYPE**: Well-defined categories for campaign analysis
- **MEMBER_STATUS**: Clear engagement levels for conversion analysis
- **HAS_RESPONDED**: Binary flag for response analysis
- **CAMPAIGN_STATUS**: Campaign lifecycle filtering
- **IS_ACTIVE_CAMPAIGN**: Current vs. historical campaigns
- **SALESFORCE_OBJECT_ASSOCIATION**: Contact vs. Lead vs. Account analysis

### Good for Grouping/Aggregation

- **CAMPAIGN_NAME/CAMPAIGN_ID**: Campaign performance analysis
- **ACCOUNT_NAME/ACCOUNT_ID**: Account-level engagement metrics
- **CAMPAIGN_TYPE**: Channel effectiveness analysis
- **PARENT_CAMPAIGN_NAME**: Program-level reporting
- **FIRST_RESPONDED_DATE**: Time-based response analysis

### Potential Join Keys

- **CONTACT_ID**: Link to contact/lead tables
- **ACCOUNT_ID**: Link to account/company tables
- **CAMPAIGN_ID**: Link to campaign detail tables
- **PARENT_CAMPAIGN_ID**: Self-join for hierarchy analysis

### Data Quality Considerations

- 13-14% of records missing contact information (likely account-based campaigns)
- 35.64% missing job titles - consider in professional demographic analysis
- 46-72% missing campaign date ranges - impacts temporal analysis
- 31% missing campaign source data - limits attribution analysis
- Date ranges span 2023-2025, suggesting both historical and future-dated records

## Keywords

campaign members, salesforce, marketing campaigns, lead generation, contact management, campaign tracking, member status, response tracking, ABM, account-based marketing, conference, webinar, demand generation, campaign hierarchy, marketing analytics, lead qualification, campaign performance, engagement tracking, salesforce CRM, marketing automation

## Table and Column Documentation

**Table Comment:** One line per campaign member in Salesforce, with campaign and contact information

**Column Comments:**

- CAMPAIGN_ID: Identifier for the campaign
- CONTACT_ID: Identifier for the contact associated with the campaign member
- CAMPAIGN_MEMBER_ID: Unique identifier for the campaign member from Salesforce
- CAMPAIGN_NAME: Name of the campaign
- ACCOUNT_ID: Account identifier associated with the campaign member
- LAST_NAME: Last name of the campaign member
- FIRST_NAME: First name of the campaign member
- EMAIL: Email address of the campaign member
- ACCOUNT_NAME: Company or account name of the campaign member
- SALESFORCE_OBJECT_ASSOCIATION: Type of Salesforce object association (Contact or Lead)
- MEMBER_STATUS: Status of the campaign member (e.g., Responded, Sent)
- TITLE: Job title of the campaign member
- HAS_RESPONDED: Boolean indicating if the campaign member has responded
- FIRST_RESPONDED_DATE: Date when the campaign member first responded
- PARENT_CAMPAIGN_ID: Identifier for the parent campaign if this is a sub-campaign
- CREATED_DATE: Date when the campaign member record was created
- PARENT_CAMPAIGN_NAME: Name of the parent campaign if this is a sub-campaign
- IS_PARENT_CAMPAIGN: Boolean indicating if this is a parent campaign
- CAMPAIGN_TYPE: Type of campaign (e.g., Event, Webinar, Email)
- CAMPAIGN_SOURCE: Source of the campaign
- CAMPAIGN_STATUS: Current status of the campaign
- CAMPAIGN_START_DATE: Campaign start date
- IS_ACTIVE_CAMPAIGN: Boolean indicating if the campaign is currently active
- CAMPAIGN_END_DATE: Campaign end date
- IS_ABM_CAMPAIGN: Boolean indicating if this is an Account-Based Marketing campaign
