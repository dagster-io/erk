---
columns:
  - ABM_STATUS (VARCHAR(36))
  - ACCOUNT_CITY (VARCHAR(120))
  - ACCOUNT_COUNTRY (VARCHAR(240))
  - ACCOUNT_ID (VARCHAR(16777216))
  - ACCOUNT_NAME (VARCHAR(765))
  - ACCOUNT_OWNED_SINCE (DATE)
  - ACCOUNT_OWNER_ID (VARCHAR(16777216))
  - ACCOUNT_OWNER_NAME (VARCHAR(363))
  - ACCOUNT_POSTAL_CODE (VARCHAR(60))
  - ACCOUNT_SOURCE (VARCHAR(765))
  - ACCOUNT_SOURCE_CUSTOM (VARCHAR(765))
  - ACCOUNT_STATE (VARCHAR(240))
  - ACCOUNT_STATUS (VARCHAR(765))
  - ACCOUNT_STREET_ADDRESS (VARCHAR(765))
  - ACCOUNT_TECHNOLOGIES (ARRAY)
  - ACCOUNT_TYPE (VARCHAR(765))
  - ACTIVE_CONTRACT_COUNT (NUMBER(18,0))
  - ALL_TIME_CONTRACT_COUNT (NUMBER(18,0))
  - ANNUAL_REVENUE (NUMBER(35,17))
  - ARR_ACTIVE_CONTRACTS (NUMBER(38,17))
  - ARR_ALL_TIME_CONTRACTS (NUMBER(38,17))
  - ASSIGNED_BUSINESS_UNIT_IDS_ARRAY (ARRAY)
  - BUSINESS_UNIT_NAMES_COMPANY (VARCHAR(16777216))
  - CLOUD_CREDITS (FLOAT)
  - CONTRACTED_SEATS (FLOAT)
  - CREATED_AT (TIMESTAMP_TZ(9))
  - DESCRIPTION (VARCHAR(96000))
  - EVER_HAD_SAL (BOOLEAN)
  - EXPANSION_CLASSIFICATION_INPUT (VARCHAR(16777216))
  - EXPANSION_OPPORTUNITY_SIZE (VARCHAR(16777216))
  - FIRST_ABM_CAMPAIGN (VARCHAR(240))
  - FIRST_CONTRACT_START_DATE (DATE)
  - FIRST_DAY_AS_TARGET_ACCOUNT (DATE)
  - FIRST_DAY_ENGAGED (DATE)
  - FIRST_DAY_ENGAGED_AS_TARGET (DATE)
  - FIRST_DAY_WITH_INTENT_SCORE (DATE)
  - FIRST_DAY_WITH_INTENT_SCORE_AS_TARGET (DATE)
  - FIRST_MQL_DATE (TIMESTAMP_TZ(9))
  - FIRST_OPP_WON_DATE (DATE)
  - FIRST_SAL_DATE (DATE)
  - FIRST_SELF_SERVE_INVOICE_DATE (DATE)
  - GONG_CALL_COUNT_L60D (NUMBER(18,0))
  - HAS_ACTIVE_CONTRACT (BOOLEAN)
  - HAS_CURRENT_INTENT_SCORE (BOOLEAN)
  - HUBSPOT_COMPANY_ID (VARCHAR(16777216))
  - INDUSTRY (VARCHAR(765))
  - INTENT_SCORE (FLOAT)
  - IS_ABM_AIRFLOW_ACCOUNT (BOOLEAN)
  - IS_ABM_AI_ACCOUNT (BOOLEAN)
  - IS_ABM_DBT_ACCOUNT (BOOLEAN)
  - IS_ABM_DIGITAL_NATIVE_ACCOUNT (BOOLEAN)
  - IS_COMPASS_COMPANY (BOOLEAN)
  - IS_DAGSTER_COMPANY (BOOLEAN)
  - IS_ENGAGED (BOOLEAN)
  - IS_INTENT_SCORE_GREATER_THAN_ZERO (BOOLEAN)
  - IS_PUBLIC (BOOLEAN)
  - IS_SALES_WORKING_ACCOUNT (BOOLEAN)
  - IS_SELF_SERVE_UPGRADE_ACCOUNT (BOOLEAN)
  - IS_TARGET_ACCOUNT (BOOLEAN)
  - LAST_CONTRACT_END_DATE (DATE)
  - LAST_CREDIT_UTILIZATION_WEEK (DATE)
  - LAST_DAY_ENGAGED (DATE)
  - LAST_DAY_ENGAGED_AS_TARGET (DATE)
  - LAST_DAY_WITH_INTENT_SCORE (DATE)
  - LAST_DAY_WITH_INTENT_SCORE_AS_TARGET (DATE)
  - LAST_FUNDING_ROUND_DATE (DATE)
  - LAST_GONG_CALL_DATE (DATE)
  - LAST_SALES_ACTIVITY_AT (TIMESTAMP_TZ(9))
  - LAST_SAL_DATE (DATE)
  - LAST_SELF_SERVE_INVOICE_DATE (DATE)
  - LAST_WEEK_UTILIZATION_PCT (FLOAT)
  - LATEST_FUNDING_STAGE (VARCHAR(96))
  - NUMBER_OF_EMPLOYEES (NUMBER(38,0))
  - OPEN_OPPORTUNITY_COUNT (NUMBER(13,0))
  - OPEN_OPPORTUNITY_NEW_ARR (FLOAT)
  - ORGANIZATION_ID (VARCHAR(16777216))
  - RECENT_SOURCE (VARCHAR(765))
  - REGION (VARCHAR(150))
  - REVENUE_SEGMENT (VARCHAR(16))
  - SENTIMENT_GONG_CALL_L60D (VARCHAR(16777216))
  - SENTIMENT_GONG_CALL_LAST_3_CALLS (VARCHAR(16777216))
  - SENTIMENT_SCORE_GONG_CALL_L60D (FLOAT)
  - SENTIMENT_SCORE_GONG_CALL_LAST_3_CALLS (FLOAT)
  - STRIPE_CUSTOMER_ID (VARCHAR(16777216))
  - TARGET_ACCOUNT_TYPE (VARCHAR(765))
  - TOTAL_FUNDING (NUMBER(35,17))
  - TOTAL_SALES_ACTIVITY_COUNT (FLOAT)
  - TOTAL_SALES_ENGAGED_CONTACT_COUNT (FLOAT)
  - WEBSITE (VARCHAR(765))
schema_hash: 1a5ab8366ce45085cd42092abf6d51e6e7bd6fc7f4dba557bc2a01a7c6303d7b
---

# Table Documentation: DWH_REPORTING.BUSINESS.ACCOUNTS

## Overall Dataset Characteristics

**Total Rows:** 45,147 accounts

This table represents a comprehensive customer relationship management (CRM) dataset containing account-level information from Salesforce with enriched data from Hubspot and other business systems. The data shows high data completeness for core account attributes but significant sparsity in contract-related and advanced analytics fields, suggesting this includes a mix of prospects, customers, and churned accounts across different stages of the sales funnel.

**Data Quality Observations:**

- Core account fields (ID, name, type, owner) have 100% completeness
- Contract-related fields show ~99% null values, indicating most accounts don't have active contracts
- Geographic data has moderate completeness (12-24% null rates)
- Advanced analytics fields (intent scores, engagement metrics) show high null rates
- Financial data varies significantly in completeness

## Column Details

### Core Account Identifiers

- **ACCOUNT_ID** (VARCHAR): Primary key, unique Salesforce identifier (100% complete)
- **ACCOUNT_NAME** (VARCHAR): Account name with high uniqueness (44,931 unique values)
- **HUBSPOT_COMPANY_ID** (VARCHAR): Hubspot identifier, nearly unique (45,146 values)
- **ORGANIZATION_ID** (VARCHAR): Dagster+ org ID (88.90% null - only for active users)
- **STRIPE_CUSTOMER_ID** (VARCHAR): Stripe customer ID (88.99% null - only for paying customers)

### Account Classification

- **ACCOUNT_TYPE** (VARCHAR): 10 distinct types including Customer, Prospect, Partner, Churned
- **IS_TARGET_ACCOUNT** (BOOLEAN): Target account flag (mostly False)
- **TARGET_ACCOUNT_TYPE** (VARCHAR): Single value "Non-Target Account" for all records
- **ACCOUNT_STATUS** (VARCHAR): 11 statuses tracking sales funnel position (MQL, Lead, Customer, etc.)
- **REVENUE_SEGMENT** (VARCHAR): Binary classification - Corporate Sales vs Enterprise Sales

### Marketing & Sales Intelligence

- **ABM_STATUS** (VARCHAR): 6-stage account-based marketing funnel status
- **INTENT_SCORE** (FLOAT): Buying intent score (0-69,999 range, mostly 0)
- **IS_INTENT_SCORE_GREATER_THAN_ZERO** (BOOLEAN): Intent score flag
- **IS_ENGAGED** (BOOLEAN): Marketing engagement flag
- **IS_SALES_WORKING_ACCOUNT** (BOOLEAN): Active sales engagement flag

### Contract & Revenue Data

- **HAS_ACTIVE_CONTRACT** (BOOLEAN): 99.31% null - active contract status
- **FIRST_CONTRACT_START_DATE** (DATE): Contract start dates (99.31% null)
- **LAST_CONTRACT_END_DATE** (DATE): Contract end dates (99.31% null)
- **ARR_ACTIVE_CONTRACTS** (NUMBER): Active ARR ($9,850-$420,000 range when present)
- **ARR_ALL_TIME_CONTRACTS** (NUMBER): Total historical ARR
- **ACTIVE_CONTRACT_COUNT** (NUMBER): Count of active contracts (0-1 when present)
- **CLOUD_CREDITS** (FLOAT): Cloud credit balances (99.34% null)
- **CONTRACTED_SEATS** (FLOAT): Licensed seats (99.36% null)

### Company Demographics

- **WEBSITE** (VARCHAR): Company websites (3.40% null)
- **INDUSTRY** (VARCHAR): 243 industry classifications (12.60% null)
- **IS_PUBLIC** (BOOLEAN): Public company status (27.25% null)
- **NUMBER_OF_EMPLOYEES** (NUMBER): Employee count (0-3.1M range, 11.44% null)
- **ANNUAL_REVENUE** (NUMBER): Company revenue (wide range, 14.67% null)
- **DESCRIPTION** (VARCHAR): Business descriptions (15.50% null)

### Geographic Information

- **ACCOUNT_STREET_ADDRESS** (VARCHAR): Street addresses (24.21% null)
- **ACCOUNT_CITY** (VARCHAR): 6,252 unique cities (17.88% null)
- **ACCOUNT_STATE** (VARCHAR): States/provinces (14.53% null)
- **ACCOUNT_COUNTRY** (VARCHAR): 212 countries (12.78% null)
- **ACCOUNT_POSTAL_CODE** (VARCHAR): Postal codes (23.23% null)
- **REGION** (VARCHAR): 6 business regions - EAST, WEST, INTERNATIONAL

### Sales Team & Ownership

- **ACCOUNT_OWNER_ID** (VARCHAR): 30 unique account owners
- **ACCOUNT_OWNER_NAME** (VARCHAR): Account owner names
- **ACCOUNT_OWNED_SINCE** (DATE): Ownership start dates (8.14% null)

### Opportunity Management

- **OPEN_OPPORTUNITY_COUNT** (NUMBER): Count of open opportunities (0-8 range)
- **OPEN_OPPORTUNITY_NEW_ARR** (FLOAT): Potential ARR from opportunities

### Marketing Attribution

- **ACCOUNT_SOURCE** (VARCHAR): 9 lead sources (50.42% null)
- **ACCOUNT_SOURCE_CUSTOM** (VARCHAR): 15 custom source values (1.14% null)
- **RECENT_SOURCE** (VARCHAR): Most recent marketing touchpoint (3.01% null)

### Technology & Enrichment

- **ACCOUNT_TECHNOLOGIES** (ARRAY): Technology stack arrays (27.31% null)
- **TOTAL_FUNDING** (NUMBER): Funding amounts (71.65% null)
- **LATEST_FUNDING_STAGE** (VARCHAR): 17 funding stages (83.72% null)
- **LAST_FUNDING_ROUND_DATE** (DATE): Recent funding dates (69.99% null)

### Advanced Analytics & Engagement

- **FIRST_MQL_DATE** (TIMESTAMP_TZ): Marketing qualified lead dates (84.94% null)
- **FIRST_SAL_DATE/LAST_SAL_DATE** (DATE): Sales accepted lead tracking (96.95% null)
- **EVER_HAD_SAL** (BOOLEAN): SAL history flag
- **FIRST_OPP_WON_DATE** (DATE): First won opportunity dates (99.27% null)

### ABM Campaign Tracking

- **IS_ABM_AI_ACCOUNT/IS_ABM_DIGITAL_NATIVE_ACCOUNT/IS_ABM_DBT_ACCOUNT/IS_ABM_AIRFLOW_ACCOUNT** (BOOLEAN): Technology-specific ABM flags
- **FIRST_ABM_CAMPAIGN** (VARCHAR): Initial ABM campaign names (94.15% null)

### Sales Activity Metrics

- **TOTAL_SALES_ENGAGED_CONTACT_COUNT** (FLOAT): Sales engagement metrics
- **TOTAL_SALES_ACTIVITY_COUNT** (FLOAT): Activity count tracking
- **LAST_SALES_ACTIVITY_AT** (TIMESTAMP_TZ): Most recent sales activity (80.26% null)

### Call Intelligence (Gong)

- **LAST_GONG_CALL_DATE** (DATE): Recent call dates (96.02% null)
- **SENTIMENT_SCORE_GONG_CALL_L60D** (FLOAT): 60-day sentiment scores
- **SENTIMENT_GONG_CALL_L60D** (VARCHAR): Sentiment categories (Positive/Negative)
- **GONG_CALL_COUNT_L60D** (NUMBER): Recent call counts

### Usage Analytics

- **LAST_WEEK_UTILIZATION_PCT** (FLOAT): Credit utilization percentages (99.35% null)
- **LAST_CREDIT_UTILIZATION_WEEK** (DATE): Usage tracking dates
- **EXPANSION_OPPORTUNITY_SIZE** (VARCHAR): 4 expansion categories (99.36% null)

### Self-Serve Tracking

- **FIRST_SELF_SERVE_INVOICE_DATE/LAST_SELF_SERVE_INVOICE_DATE** (DATE): Self-service usage dates (98.19% null)
- **IS_SELF_SERVE_UPGRADE_ACCOUNT** (BOOLEAN): Upgrade tracking flag

## Potential Query Considerations

### Good for Filtering:

- **ACCOUNT_TYPE**: Customer segmentation
- **REVENUE_SEGMENT**: Sales team routing
- **ACCOUNT_STATUS**: Funnel analysis
- **REGION**: Geographic analysis
- **IS_TARGET_ACCOUNT**: Target account focus
- **INDUSTRY**: Vertical analysis
- **HAS_ACTIVE_CONTRACT**: Customer vs. prospect analysis

### Good for Grouping/Aggregation:

- **ACCOUNT_OWNER_NAME**: Sales rep performance
- **INDUSTRY**: Market segment analysis
- **REGION**: Geographic rollups
- **ACCOUNT_TYPE**: Customer lifecycle stages
- **ABM_STATUS**: Marketing funnel analysis
- **REVENUE_SEGMENT**: Sales segment analysis

### Potential Join Keys:

- **ACCOUNT_ID**: Primary key for account-related joins
- **HUBSPOT_COMPANY_ID**: Hubspot data integration
- **ORGANIZATION_ID**: Product usage data joins
- **STRIPE_CUSTOMER_ID**: Financial/billing data
- **ACCOUNT_OWNER_ID**: Sales rep/user data

### Data Quality Considerations:

- Contract fields are largely null - filter for non-null values when analyzing customers
- Geographic data has varying completeness - consider null handling
- Intent scores and engagement metrics are sparse - suitable for subset analysis
- Financial data (ARR, revenue) may need null value treatment
- Date fields span multiple years - consider time-based filtering
- Technology arrays may need special JSON/array handling

## Keywords

CRM, Salesforce, accounts, customers, prospects, ABM, account-based marketing, sales funnel, revenue, contracts, ARR, intent scores, opportunity management, lead generation, customer segmentation, sales analytics, marketing attribution, geographic analysis, industry verticals, technology stack, funding data, engagement metrics, call intelligence, usage analytics

## Table and Column Documentation

### Table Comment

"One line per account in Salesforce, with additional information from other Salesforce and Hubspot tables"

### Key Column Comments

- **ACCOUNT_ID**: "Unique identifier for the account from Salesforce"
- **ACCOUNT_TYPE**: "Type of the account (e.g., Customer, Prospect, Partner)"
- **ABM_STATUS**: "Account-based marketing status indicating where the account is in the marketing and sales funnel"
- **INTENT_SCORE**: "Score indicating the account's buying intent"
- **ARR_ACTIVE_CONTRACTS**: "Annual recurring revenue from active contracts"
- **EXPANSION_OPPORTUNITY_SIZE**: "Size classification of expansion opportunity for the account"
- **REVENUE_SEGMENT**: "Defines whether the account is a corporate or enterprise account"
