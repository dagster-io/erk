---
columns:
  - ACCOUNT_EXECUTIVE_NAME (VARCHAR(363))
  - ACCOUNT_FIRST_DAY_AS_TARGET_ACCOUNT (DATE)
  - ACCOUNT_ID (VARCHAR(16777216))
  - ACCOUNT_NAME (VARCHAR(765))
  - ACCOUNT_SOURCE (VARCHAR(3900))
  - AMOUNT (NUMBER(35,17))
  - AMOUNT_YEAR1 (NUMBER(35,17))
  - AMOUNT_YEAR2 (NUMBER(35,17))
  - AMOUNT_YEAR3 (NUMBER(35,17))
  - AMOUNT_YEAR4 (NUMBER(35,17))
  - AMOUNT_YEAR5 (NUMBER(35,17))
  - ARR_HISTORICAL_AVG (NUMBER(35,17))
  - ARR_VELOCITY (NUMBER(35,17))
  - BUDGET (NUMBER(35,17))
  - CAMPAIGNS_INFLUENCED_OPP_STRUCTURED (ARRAY)
  - CAMPAIGNS_INFLUENCED_SAL_STRUCTURED (ARRAY)
  - CLOSED_DATE_HISTORICAL_AVG (DATE)
  - CLOSE_DATE (DATE)
  - COMPETITOR (VARCHAR(4099))
  - CONTACT_ID (VARCHAR(16777216))
  - CONTACT_NAME (VARCHAR(361))
  - CREATED_AT (TIMESTAMP_TZ(9))
  - CREATED_BY_NAME (VARCHAR(363))
  - CURRENT_DATA_STACK (VARCHAR(4099))
  - CURRENT_ORCHESTRATOR (VARCHAR(765))
  - DESCRIPTION (VARCHAR(96000))
  - DISCOVERY_DATE (DATE)
  - EVALUATION_DATE (DATE)
  - FEATURE_REQUIREMENTS (VARCHAR(4099))
  - FORECAST_CATEGORY (VARCHAR(120))
  - FORECAST_CATEGORY_NAME (VARCHAR(765))
  - INTRO_MEETING_DATE (DATE)
  - IS_ABM_INFLUENCED_OPP (BOOLEAN)
  - IS_ABM_INFLUENCED_SAL (BOOLEAN)
  - IS_ACCOUNT_FIRST_OPP (BOOLEAN)
  - IS_CLOSED (BOOLEAN)
  - IS_EXISTING_BUSINESS (BOOLEAN)
  - IS_PRIMARY_EVALUATOR_IDENTIFIED (BOOLEAN)
  - IS_TARGET_ACCOUNT (BOOLEAN)
  - IS_WON (BOOLEAN)
  - LEAD_SOURCE (VARCHAR(765))
  - LOSS_DETAILS (VARCHAR(98304))
  - LOSS_REASON (VARCHAR(4099))
  - MANUAL_FORECAST_CATEGORY (VARCHAR(765))
  - MEETING_HELD_DATE (DATE)
  - MISSING_FUNCTIONALITY (VARCHAR(4099))
  - NEGOTIATION_REVIEW_DATE (DATE)
  - NEW_ARR (FLOAT)
  - NEXT_STEP (VARCHAR(765))
  - OPEN_TO_SAL_DAYS (NUMBER(9,0))
  - OPPORTUNITY_ID (VARCHAR(16777216))
  - OPPORTUNITY_NAME (VARCHAR(360))
  - OPPORTUNITY_PROBABILITY_PREDICTION (FLOAT)
  - OPPORTUNITY_TYPE (VARCHAR(765))
  - OPP_FIRST_TOUCH_CAMPAIGN_NAME (VARCHAR(240))
  - OPP_LAST_TOUCH_CAMPAIGN_NAME (VARCHAR(240))
  - OWNER_ID (VARCHAR(16777216))
  - OWNER_MANAGER_NAME (VARCHAR(363))
  - OWNER_NAME (VARCHAR(363))
  - OWNER_TITLE (VARCHAR(240))
  - PARTNER_ACCOUNT_ID (VARCHAR(16777216))
  - PARTNER_ACCOUNT_NAME (VARCHAR(765))
  - PRE_OPPORTUNITY_DATE (DATE)
  - PRIOR_TERM_ARR (NUMBER(35,17))
  - PROBABILITY (FLOAT)
  - PROPOSAL_DATE (DATE)
  - RECENT_SOURCE (VARCHAR(105))
  - REVENUE_SEGMENT (VARCHAR(16))
  - RISKS (VARCHAR(4099))
  - SALES_ENGINEER_NAME (VARCHAR(363))
  - SAL_CREATED_BY_NAME (VARCHAR(363))
  - SAL_DATE (TIMESTAMP_TZ(9))
  - SAL_FIRST_TOUCH_CAMPAIGN_NAME (VARCHAR(240))
  - SAL_LAST_TOUCH_CAMPAIGN_NAME (VARCHAR(240))
  - SAL_TO_CLOSED_DAYS (NUMBER(9,0))
  - STAGE_BEFORE_CLOSED_LOST (VARCHAR(16777216))
  - STAGE_NAME (VARCHAR(16777216))
  - STAGE_ORDER_NUMBER (NUMBER(38,0))
  - TARGET_ACCOUNT_TYPE (VARCHAR(765))
  - TERM_MONTHS (FLOAT)
  - UPDATED_AT (TIMESTAMP_TZ(9))
  - WIN_LOSS_COMPETITOR (VARCHAR(765))
  - WITHIN_BUDGET (BOOLEAN)
schema_hash: 517747f52ae03da095727b6e4dfb31b760935c4e050df3a6410e3b7eb9207a99
---

# DWH_REPORTING.BUSINESS.OPPORTUNITIES Table Summary

## Keywords

Sales opportunities, Salesforce CRM, Hubspot data, sales pipeline, opportunity tracking, revenue analysis, sales performance, customer acquisition, deal management, ARR analysis

## Overall Dataset Characteristics

- **Total Rows**: 2,888 opportunities
- **Data Quality**: Generally high quality with low null percentages on key fields
- **Time Range**: Opportunities from 2021 to 2025 based on dates
- **Business Context**: Sales opportunity tracking table combining Salesforce and Hubspot data for comprehensive opportunity management
- **Coverage**: Mix of new business (majority), renewals, and upsells across Corporate Sales and Enterprise Sales segments

## Table and Column Documentation

### Table Comment

"One line per opportunity in Salesforce, with additional information from other Salesforce and Hubspot tables"

### Column Documentation

- **OPPORTUNITY_ID**: "Unique identifier for the opportunity from Salesforce"
- **ACCOUNT_ID**: "Related account identifier"
- **OPPORTUNITY_NAME**: "Name of the opportunity"
- **ACCOUNT_NAME**: "Name of the related account"
- **OWNER_NAME**: "Name of the opportunity owner"
- **OWNER_TITLE**: "Title of the opportunity owner"
- **CLOSE_DATE**: "Expected or actual date of closing the opportunity"
- **CREATED_BY_NAME**: "Name of the user who created the opportunity"
- **STAGE_NAME**: "Current stage of the opportunity in the sales pipeline"
- **STAGE_ORDER_NUMBER**: "Numerical order of the stage in the pipeline"
- **DESCRIPTION**: "Detailed description of the opportunity"
- **AMOUNT**: "Total amount of the opportunity"
- **IS_CLOSED**: "Boolean indicating if the opportunity is closed"
- **IS_WON**: "Boolean indicating if the opportunity was won"
- **SAL_CREATED_BY_NAME**: "Name of the user who created the SAL"
- **SAL_DATE**: "Date when this opportunity became a Sales Accepted Lead"
- **SALES_ENGINEER_NAME**: "Name of the sales engineer assigned to the opportunity"
- **CONTACT_NAME**: "Name of the primary contact for this opportunity"
- **AMOUNT_YEAR1-5**: "Amount for the [first/second/third/fourth/fifth] year of the opportunity"
- **IS_TARGET_ACCOUNT**: "Boolean indicating if the related account is a target account"
- **TARGET_ACCOUNT_TYPE**: "Classification of target account type for the related account"
- **TERM_MONTHS**: "Number of months in the term of the opportunity (i.e. contract length)"
- **OPPORTUNITY_TYPE**: "Type of opportunity (e.g., new business, expansion)"
- **PROBABILITY**: "Probability of closing the opportunity (percentage)"
- **NEXT_STEP**: "Next step in the sales process"
- **LEAD_SOURCE**: "Source of the lead that generated the opportunity"
- **CREATED_AT**: "Date when the opportunity was created"
- **UPDATED_AT**: "Date when the opportunity was last updated"
- **IS_ACCOUNT_FIRST_OPP**: "Boolean indicating if this is the first opportunity for the account"
- **LOSS_REASON**: "Reason for closing the opportunity as lost"
- **LOSS_DETAILS**: "Detailed explanation for closing the opportunity as lost"
- **STAGE_BEFORE_CLOSED_LOST**: "The stage of the opportunity immediately before it was marked as closed lost"
- **WIN_LOSS_COMPETITOR**: "Competitor that won/lost the deal"
- **COMPETITOR**: "Information about competing solutions"
- **MANUAL_FORECAST_CATEGORY**: "Manually set forecast category"
- **FORECAST_CATEGORY_NAME**: "Name of the forecast category"
- **FORECAST_CATEGORY**: "System-calculated forecast category"
- **NEW_ARR**: "New annual recurring revenue from the opportunity"
- **PRIOR_TERM_ARR**: "ARR from the previous term"
- **RECENT_SOURCE**: "Most recent marketing source for the opportunity"
- **ACCOUNT_SOURCE**: "Source of the related account in Salesforce"
- **CURRENT_ORCHESTRATOR**: "Current workflow orchestrator used by the customer"
- **RISKS**: "Identified risks associated with the opportunity"
- **BUDGET**: "Budget information for the opportunity"
- **WITHIN_BUDGET**: "Boolean indicating if the opportunity is within the customer's budget"
- **MISSING_FUNCTIONALITY**: "Functionality that is missing and requested by the prospect"
- **FEATURE_REQUIREMENTS**: "Specific feature requirements for the opportunity"
- **IS_PRIMARY_EVALUATOR_IDENTIFIED**: "Boolean indicating if the primary evaluator has been identified"
- **CURRENT_DATA_STACK**: "Description of the customer's current data stack"
- Various date fields for pipeline stage tracking
- **CONTACT_ID**: "Identifier for the primary contact"
- **OWNER_ID**: "Identifier for the opportunity owner"
- **CLOSED_DATE_HISTORICAL_AVG**: "Historical average number of days taken to close opportunities at the point the opportunity was created"
- **OPPORTUNITY_PROBABILITY_PREDICTION**: "Model-predicted probability of winning the opportunity"
- **ARR_HISTORICAL_AVG**: "Historical average annual recurring revenue (ARR) for opportunities"
- **ACCOUNT_FIRST_DAY_AS_TARGET_ACCOUNT**: "First date the related account was marked as a target account"
- **IS_ABM_INFLUENCED_SAL/OPP**: "Boolean indicating if this SAL/opportunity was influenced by account-based marketing"
- **SAL_TO_CLOSED_DAYS**: "Number of days between SAL date and close date"
- **OPEN_TO_SAL_DAYS**: "Number of days between when the opportunity was created and when it became a SAL"
- **ARR_VELOCITY**: "ARR velocity calculated as amount_year1 divided by sal_to_closed_days for won opportunities"
- **PARTNER_ACCOUNT_ID/NAME**: "Identifier/Name for the partner account"
- Campaign tracking fields with first/last touch attribution
- **CAMPAIGNS_INFLUENCED_SAL/OPP_STRUCTURED**: JSON arrays containing detailed campaign influence data

## Column Analysis by Data Type and Usage

### Primary Keys & Identifiers

- **OPPORTUNITY_ID**: Unique identifier (2,888 unique values), perfect for filtering and joins
- **ACCOUNT_ID**: Account reference (1,982 unique values), good for account-level analysis
- **OWNER_ID**: Owner reference (42 unique values), useful for sales rep performance analysis

### Financial Metrics

- **AMOUNT**: Total opportunity value (16.52% nulls), ranges from $0 to $2.1M
- **NEW_ARR**: Annual recurring revenue (16.48% nulls), ranges from -$111K to $700K
- **AMOUNT_YEAR1-5**: Multi-year contract breakdowns, Year1 most complete (16.41% nulls)
- **PRIOR_TERM_ARR**: Previous contract value (12.53% nulls)

### Sales Pipeline & Status

- **STAGE_NAME**: 14 distinct pipeline stages from "Pre-Opportunity" to "Closed Won/Lost"
- **STAGE_ORDER_NUMBER**: Numeric pipeline ordering (1-10)
- **IS_CLOSED/IS_WON**: Boolean status indicators (complete data)
- **PROBABILITY**: Win probability (0-100%, 6 distinct values)

### Temporal Tracking

- **CLOSE_DATE**: Expected/actual close dates (complete data, 911 unique values)
- **CREATED_AT**: Opportunity creation timestamps (nearly unique per row)
- **SAL_DATE**: Sales Accepted Lead date (47.85% nulls)
- Stage-specific dates (intro, discovery, evaluation, proposal, negotiation)

### People & Ownership

- **OWNER_NAME**: 42 different owners (complete data)
- **OWNER_TITLE**: 12 different titles (0.69% nulls)
- **ACCOUNT_EXECUTIVE_NAME**: 36 different AEs (14.85% nulls)
- **SALES_ENGINEER_NAME**: 6 different SEs (40.03% nulls)

### Business Classification

- **OPPORTUNITY_TYPE**: New Business (majority), Renewal, Upsell
- **REVENUE_SEGMENT**: Corporate Sales vs Enterprise Sales
- **IS_EXISTING_BUSINESS**: Boolean flag for existing customers

### Competitive Intelligence

- **COMPETITOR**: Detailed competitor information (53.57% nulls)
- **WIN_LOSS_COMPETITOR**: Primary competitor (39.02% nulls)
- **CURRENT_ORCHESTRATOR**: Customer's current solution (61.70% nulls)

### Marketing Attribution

- **LEAD_SOURCE**: Original lead source (2.77% nulls, 17 distinct values)
- **RECENT_SOURCE**: Most recent marketing touchpoint (25.52% nulls)
- Campaign tracking with structured JSON arrays for multi-touch attribution

## Query Considerations

### Excellent for Filtering

- **IS_CLOSED/IS_WON**: Boolean filters for pipeline vs closed deals
- **STAGE_NAME/STAGE_ORDER_NUMBER**: Pipeline stage analysis
- **OPPORTUNITY_TYPE**: New business vs renewal/upsell analysis
- **REVENUE_SEGMENT**: Corporate vs Enterprise segmentation
- **CLOSE_DATE/CREATED_AT**: Time-based filtering

### Ideal for Grouping/Aggregation

- **OWNER_NAME**: Sales rep performance analysis
- **ACCOUNT_NAME**: Account-level opportunity tracking
- **STAGE_NAME**: Pipeline distribution analysis
- **OPPORTUNITY_TYPE**: Business type performance
- **LEAD_SOURCE/RECENT_SOURCE**: Marketing source effectiveness

### Potential Join Keys

- **ACCOUNT_ID**: Link to account tables
- **OWNER_ID**: Link to user/employee tables
- **CONTACT_ID**: Link to contact tables
- **PARTNER_ACCOUNT_ID**: Link to partner information

### Data Quality Considerations

- High null percentages in descriptive fields (DESCRIPTION 92.76%, LOSS_DETAILS 100%)
- SAL_DATE missing for ~48% of records (likely non-sales-qualified opportunities)
- Contact information sparse (88.50% nulls)
- Budget information largely incomplete (89.34% nulls)
- Campaign structured arrays contain detailed attribution data for analysis

### Business Metrics Calculations

- Win rate analysis using IS_WON
- Pipeline velocity using SAL_TO_CLOSED_DAYS and OPEN_TO_SAL_DAYS
- ARR analysis using NEW_ARR and multi-year amounts
- Sales cycle analysis using various date fields
- Conversion funnel analysis using STAGE_ORDER_NUMBER
