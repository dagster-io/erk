---
columns:
  - CAMPAIGN_ID (VARCHAR(16777216))
  - CAMPAIGN_NAME (VARCHAR(240))
  - CAMPAIGN_SOURCE (VARCHAR(765))
  - CAMPAIGN_STATUS (VARCHAR(765))
  - CAMPAIGN_TYPE (VARCHAR(765))
  - END_DATE (DATE)
  - IS_ABM_CAMPAIGN (BOOLEAN)
  - IS_ACTIVE (BOOLEAN)
  - NEW_ARR_ATTRIBUTED_EXISTING_BUSINESS (FLOAT)
  - NEW_ARR_ATTRIBUTED_NEW_BUSINESS (FLOAT)
  - NEW_ARR_ATTRIBUTED_TOTAL (FLOAT)
  - NUMBER_OF_ACCOUNTS (NUMBER(18,0))
  - NUMBER_OF_CONTACTS (NUMBER(38,0))
  - NUMBER_OF_RESPONSES (NUMBER(38,0))
  - OPPS_ATTRIBUTED_EXISTING_BUSINESS (NUMBER(20,2))
  - OPPS_ATTRIBUTED_NEW_BUSINESS (NUMBER(20,2))
  - OPPS_ATTRIBUTED_TOTAL (NUMBER(20,2))
  - PARENT_CAMPAIGN_NAME (VARCHAR(240))
  - PARENT_ID (VARCHAR(16777216))
  - SALS_INFLUENCED (NUMBER(20,2))
  - START_DATE (DATE)
schema_hash: 5a08b89b3ecdae3a17f5aa367e4e48fce3862ba5e879b76ae624fd9edbe83b90
---

# Table Analysis Summary: DWH_REPORTING.BUSINESS.CAMPAIGNS

## Keywords

campaigns, salesforce, marketing, attribution, ARR, opportunities, SAL, revenue, events, webinars, ABM, account-based marketing

## Overall Dataset Characteristics

- **Total Rows**: 112 campaigns
- **Data Quality**: Generally good with complete primary identifiers (CAMPAIGN_ID) and core metrics
- **Notable Patterns**:
  - High attribution metrics precision (decimal values for fractional attribution)
  - Many campaigns are part of hierarchical parent-child relationships (81.25% have parent campaigns)
  - Mix of completed (majority), in-progress, and planned campaigns
  - Revenue attribution ranges from $0 to $7.7M, indicating significant campaign impact variation
- **Table Purpose**: Campaign performance tracking with sophisticated attribution modeling for SALs and revenue

## Column Analysis

### Primary Identifiers

- **CAMPAIGN_ID**: Unique Salesforce identifier (VARCHAR), no nulls, 112 unique values
- **CAMPAIGN_NAME**: Descriptive campaign names following naming conventions (VARCHAR), no nulls

### Campaign Classification

- **CAMPAIGN_TYPE**: 12 distinct types including ABM, Conference/Tradeshow, Webinars, etc. (3.57% nulls)
- **CAMPAIGN_STATUS**: Three states - Completed, In Progress, Planned (no nulls)
- **IS_ACTIVE**: Boolean flag for current activity status (no nulls)
- **IS_ABM_CAMPAIGN**: Boolean flag for Account-Based Marketing campaigns (no nulls)
- **CAMPAIGN_SOURCE**: 10 distinct sources like Marketing Event, Website Signup (35.71% nulls)

### Hierarchical Structure

- **PARENT_ID**: Links to parent campaigns (18.75% nulls, indicating top-level campaigns)
- **PARENT_CAMPAIGN_NAME**: Standardized parent names like "24-CONF", "25-WBNR" (18.75% nulls)

### Temporal Data

- **START_DATE**: Campaign start dates (16.07% nulls)
- **END_DATE**: Campaign end dates (48.21% nulls, likely for ongoing campaigns)

### Engagement Metrics

- **NUMBER_OF_RESPONSES**: Response count (0-9,813 range, no nulls)
- **NUMBER_OF_CONTACTS**: Contact count (0-9,812 range, no nulls)
- **NUMBER_OF_ACCOUNTS**: Account count (0-6,562 range, no nulls)

### Attribution Metrics (Key Performance Indicators)

- **SALS_INFLUENCED**: Sales Accepted Leads with fractional attribution (0.00-176.88, 2 decimal precision)
- **NEW_ARR_ATTRIBUTED_TOTAL**: Total new ARR attribution (0.0-7.7M range)
- **NEW_ARR_ATTRIBUTED_NEW_BUSINESS**: New business ARR (0.0-7.2M range)
- **NEW_ARR_ATTRIBUTED_EXISTING_BUSINESS**: Expansion ARR (-14.9K to 494K, can be negative)
- **OPPS_ATTRIBUTED_TOTAL**: Total opportunity attribution (0.00-401.26, fractional values)
- **OPPS_ATTRIBUTED_NEW_BUSINESS**: New business opportunities (0.00-337.02)
- **OPPS_ATTRIBUTED_EXISTING_BUSINESS**: Existing business opportunities (0.00-64.24)

## Table and Column Documentation

### Table Comment

"One line per campaign in Salesforce, with attribution metrics for SALs and opportunities"

### Column Comments

- **CAMPAIGN_ID**: "Unique identifier for the campaign from Salesforce"
- **CAMPAIGN_TYPE**: "Type of campaign (e.g., Event, Webinar, Email)"
- **CAMPAIGN_NAME**: "Name of the campaign"
- **CAMPAIGN_STATUS**: "Current status of the campaign"
- **IS_ACTIVE**: "Boolean indicating if the campaign is currently active"
- **PARENT_ID**: "Identifier for the parent campaign if this is a sub-campaign"
- **PARENT_CAMPAIGN_NAME**: "Name of the parent campaign if this is a sub-campaign"
- **END_DATE**: "Date when the campaign ended or is expected to end"
- **START_DATE**: "Date when the campaign started"
- **NUMBER_OF_RESPONSES**: "Number of responses received for this campaign"
- **NUMBER_OF_CONTACTS**: "Number of contacts associated with this campaign"
- **CAMPAIGN_SOURCE**: "Source of the campaign (e.g., Marketing Event, Webinar)"
- **NUMBER_OF_ACCOUNTS**: "Number of accounts associated with this campaign"
- **IS_ABM_CAMPAIGN**: "Boolean indicating if this is an Account-Based Marketing campaign"
- **SALS_INFLUENCED**: "Number of Sales Accepted Leads (SALs) influenced by this campaign, rounded to 2 decimal places"
- **NEW_ARR_ATTRIBUTED_TOTAL**: "Total New Annual Recurring Revenue (ARR) attributed to this campaign, rounded to 2 decimal places"
- **NEW_ARR_ATTRIBUTED_NEW_BUSINESS**: "New Business ARR attributed to this campaign, rounded to 2 decimal places"
- **NEW_ARR_ATTRIBUTED_EXISTING_BUSINESS**: "Existing Business ARR attributed to this campaign, rounded to 2 decimal places"
- **OPPS_ATTRIBUTED_TOTAL**: "Total number of opportunities attributed to this campaign, rounded to 2 decimal places"
- **OPPS_ATTRIBUTED_NEW_BUSINESS**: "Number of new business opportunities attributed to this campaign, rounded to 2 decimal places"
- **OPPS_ATTRIBUTED_EXISTING_BUSINESS**: "Number of existing business opportunities attributed to this campaign, rounded to 2 decimal places"

## Query Considerations

### Good for Filtering

- **CAMPAIGN_STATUS**: Filter by active/completed campaigns
- **CAMPAIGN_TYPE**: Segment by campaign categories
- **IS_ACTIVE**: Current vs historical campaigns
- **IS_ABM_CAMPAIGN**: ABM vs non-ABM analysis
- **PARENT_CAMPAIGN_NAME**: Filter by campaign families
- **Date fields**: Time-based filtering (note high null percentage in END_DATE)

### Good for Grouping/Aggregation

- **CAMPAIGN_TYPE**: Performance by campaign type
- **PARENT_CAMPAIGN_NAME**: Roll-up reporting by campaign families
- **CAMPAIGN_STATUS**: Status-based analysis
- **CAMPAIGN_SOURCE**: Source effectiveness analysis
- **Date fields**: Time-series analysis (monthly/quarterly trends)

### Key Metrics for Analysis

- All ARR attribution fields for revenue impact analysis
- SALS_INFLUENCED for lead generation effectiveness
- OPPS_ATTRIBUTED fields for pipeline analysis
- Engagement metrics (responses, contacts, accounts) for reach analysis

### Data Quality Considerations

- Handle nulls in END_DATE (48% null rate) and START_DATE (16% null rate)
- CAMPAIGN_SOURCE has 35% nulls - consider in analysis
- Negative values possible in NEW_ARR_ATTRIBUTED_EXISTING_BUSINESS (contraction scenarios)
- Fractional attribution values indicate sophisticated multi-touch attribution modeling

### Potential Relationships

- Parent-child campaign hierarchy via PARENT_ID
- Could join with Salesforce opportunity/lead tables via CAMPAIGN_ID
- Time-based relationships possible with date fields
