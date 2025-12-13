---
columns:
  - ACTIVE_DAYS_7D (NUMBER(18,0))
  - ALERTS_SENT (NUMBER(13,0))
  - ASSETS_WITH_AUTOMATION_CONDITION_COUNT (NUMBER(18,0))
  - ASSETS_WITH_FRESHNESS_POLICY_COUNT (NUMBER(18,0))
  - ASSETS_WITH_KINDS_COUNT (NUMBER(18,0))
  - ASSETS_WITH_NEW_FRESHNESS_POLICY_COUNT (NUMBER(18,0))
  - ASSETS_WITH_TAGS_COUNT (NUMBER(18,0))
  - ASSET_CHECK_EVALUATIONS (NUMBER(13,0))
  - ASSET_COUNT (NUMBER(18,0))
  - ASSET_GROUP_COUNT (NUMBER(18,0))
  - ASSET_HEALTH_PAGE_VIEWS (NUMBER(18,0))
  - ASSET_MATERIALIZATIONS (NUMBER(13,0))
  - ASSET_OBSERVATIONS (NUMBER(13,0))
  - BASE_PLAN_TYPE (VARCHAR(16777216))
  - BILLABLE_STEPS (NUMBER(18,0))
  - CATALOG_HOME_PAGE_VIEWS (NUMBER(18,0))
  - CUSTOM_ROLE_USERS_COUNT (NUMBER(18,0))
  - DATE_DAY (DATE)
  - DAYS_SINCE_CREATION (NUMBER(9,0))
  - DISTINCT_ASSETS_MATERIALIZED (NUMBER(18,0))
  - ENV_VARS_COUNT (NUMBER(21,0))
  - HAS_SAML_SSO (BOOLEAN)
  - INSIGHTS_PAGE_VIEWS (NUMBER(18,0))
  - IS_ACTIVE (BOOLEAN)
  - IS_INTERNAL (BOOLEAN)
  - IS_IN_TRIAL (BOOLEAN)
  - IS_LAST_DAY_OF_MONTH (BOOLEAN)
  - IS_LAST_DAY_OF_WEEK (BOOLEAN)
  - IS_WEEKLY_ACTIVE_ORGANIZATION (BOOLEAN)
  - IS_WEEKLY_ENGAGED_ORGANIZATION (BOOLEAN)
  - LAST_RUN_AT (FLOAT)
  - LAST_USER_LOGIN (TIMESTAMP_NTZ(9))
  - ORGANIZATION_ID (NUMBER(38,0))
  - ORGANIZATION_NAME (VARCHAR(16777216))
  - ORG_CREATED_AT (TIMESTAMP_NTZ(9))
  - PIPELINE_CANCELLATIONS (NUMBER(13,0))
  - PIPELINE_FAILURES (NUMBER(13,0))
  - PIPELINE_STARTS (NUMBER(13,0))
  - PIPELINE_SUCCESSES (NUMBER(13,0))
  - PIPELINE_SUCCESSES_7D (NUMBER(25,0))
  - PLAN_TYPE (VARCHAR(16777216))
  - RUNS_COMPLETED (NUMBER(18,0))
  - SALESFORCE_ACCOUNT_ID (VARCHAR(16777216))
  - SALESFORCE_ACCOUNT_STATUS (VARCHAR(765))
  - SALESFORCE_ACCOUNT_TYPE (VARCHAR(765))
  - STATUS (VARCHAR(16777216))
  - STRIPE_CUSTOMER_ID (VARCHAR(16777216))
  - TOTAL_SYSTEM_EVENTS (NUMBER(18,0))
  - UNIQUE_ASSET_HEALTH_VIEWERS (NUMBER(18,0))
  - UNIQUE_CATALOG_HOME_PAGE_VIEWERS (NUMBER(18,0))
  - UNIQUE_INSIGHTS_VIEWERS (NUMBER(18,0))
schema_hash: 9b75e253e98dba1d90aa5a3ead2fbf419cb6cf818a971505d81c38cb1cdde338
---

# Organizations by Day Table Summary

## Overall Dataset Characteristics

- **Total Rows**: 7,098,151
- **Date Range**: 1,530 unique dates spanning from July 2021 to July 2025
- **Organizations**: 14,257 unique organizations tracked over time
- **Data Quality**: Generally high quality with minimal null values in core fields, though some metrics have ~10% null rates for newer features
- **Table Purpose**: Daily snapshots of Dagster+ organizations with comprehensive operational and business metrics

## Column Details

### Core Identification & Temporal Fields

- **DATE_DAY** (DATE): Daily snapshot date, no nulls, spans ~4 years
- **ORGANIZATION_ID** (NUMBER): Unique org identifier, sequential from 2 to 17,212
- **ORGANIZATION_NAME** (VARCHAR): Human-readable org names, no nulls
- **ORG_CREATED_AT** (TIMESTAMP): Organization creation timestamp, no nulls
- **DAYS_SINCE_CREATION** (NUMBER): Calculated field showing org age, 0-1,529 days

### Organization Status & Business Context

- **STATUS** (VARCHAR): 4 values - ACTIVE, PENDING_DELETION, READ_ONLY, SUSPENDED
- **PLAN_TYPE** (VARCHAR): 7 subscription plans including ENTERPRISE, TEAM_V2, STANDARD
- **BASE_PLAN_TYPE** (VARCHAR): 6 base plan types (simplified version of PLAN_TYPE)
- **IS_ACTIVE** (BOOLEAN): Active status flag, no nulls
- **IS_INTERNAL** (BOOLEAN): Internal organization flag, no nulls
- **IS_IN_TRIAL** (BOOLEAN): Trial status indicator, no nulls

### External System Integration

- **SALESFORCE_ACCOUNT_ID** (VARCHAR): 54% null, 5,028 unique values when present
- **SALESFORCE_ACCOUNT_TYPE** (VARCHAR): 9 types including Customer, Prospect, Partner
- **SALESFORCE_ACCOUNT_STATUS** (VARCHAR): 12 statuses like MQL, Lead, Client
- **STRIPE_CUSTOMER_ID** (VARCHAR): 8.5% null, payment system integration
- **HAS_SAML_SSO** (BOOLEAN): 64% null, SSO capability flag

### User Activity & Engagement

- **LAST_USER_LOGIN** (TIMESTAMP): 35.5% null, tracks user engagement
- **LAST_RUN_AT** (FLOAT): 70% null, Unix timestamp of last pipeline run
- **IS_WEEKLY_ACTIVE_ORGANIZATION** (BOOLEAN): 10% null, activity classification
- **IS_WEEKLY_ENGAGED_ORGANIZATION** (BOOLEAN): 10% null, engagement classification
- **ACTIVE_DAYS_7D** (NUMBER): 10% null, rolling 7-day activity count

### Daily Event Metrics (All with 0% nulls)

- **TOTAL_SYSTEM_EVENTS** (NUMBER): 0 to 42M+ events, wide distribution
- **PIPELINE_STARTS/SUCCESSES/FAILURES/CANCELLATIONS** (NUMBER): Pipeline execution metrics
- **ASSET_MATERIALIZATIONS/OBSERVATIONS** (NUMBER): Asset-related events
- **ASSET_CHECK_EVALUATIONS** (NUMBER): Data quality check events
- **ALERTS_SENT** (NUMBER): Alert notification count
- **BILLABLE_STEPS** (NUMBER): Usage-based billing metric

### Asset & Configuration Metrics (10% null for newer features)

- **ASSET_COUNT** (NUMBER): Total assets in organization
- **DISTINCT_ASSETS_MATERIALIZED** (NUMBER): Unique assets with activity
- **ASSET_GROUP_COUNT** (NUMBER): Asset grouping organization
- **ASSETS*WITH*\*\_COUNT** fields: Various asset capability counters
- **ENV_VARS_COUNT** (NUMBER): Environment variables configured

### UI Analytics (10% null)

- **INSIGHTS_PAGE_VIEWS/UNIQUE_INSIGHTS_VIEWERS**: Analytics page usage
- **CATALOG_HOME_PAGE_VIEWS/UNIQUE_CATALOG_HOME_PAGE_VIEWERS**: Catalog usage
- **ASSET_HEALTH_PAGE_VIEWS/UNIQUE_ASSET_HEALTH_VIEWERS**: Health monitoring usage

### Temporal Convenience Fields

- **IS_LAST_DAY_OF_WEEK/MONTH** (BOOLEAN): Date classification helpers
- **PIPELINE_SUCCESSES_7D** (NUMBER): Rolling 7-day success count

## Query Considerations

### Filtering Columns

- **DATE_DAY**: Primary temporal filter for time-based analysis
- **STATUS**: Filter active vs inactive organizations
- **PLAN_TYPE/BASE_PLAN_TYPE**: Segment by subscription tier
- **IS_ACTIVE, IS_INTERNAL**: Basic org classification
- **ORGANIZATION_NAME/ID**: Specific org analysis

### Grouping/Aggregation Opportunities

- **DATE_DAY**: Time series analysis (daily, weekly, monthly trends)
- **PLAN_TYPE**: Revenue/usage analysis by subscription tier
- **STATUS**: Organization lifecycle analysis
- **IS_INTERNAL**: Internal vs external org comparisons
- **SALESFORCE_ACCOUNT_TYPE**: Customer segmentation

### Potential Join Keys

- **ORGANIZATION_ID**: Primary key for joining with other org-related tables
- **SALESFORCE_ACCOUNT_ID**: CRM system integration
- **STRIPE_CUSTOMER_ID**: Billing system integration

### Data Quality Considerations

- Many newer metrics (asset-related, UI analytics) have ~10% null values
- **HAS_SAML_SSO** has 64% nulls (feature not applicable to all orgs)
- **SALESFORCE_ACCOUNT_ID** 54% null (not all orgs in CRM)
- **LAST_USER_LOGIN** 35% null (some orgs never had logins)
- **LAST_RUN_AT** 70% null (many orgs don't run pipelines)

## Keywords

Dagster, organizations, daily metrics, pipeline events, asset materializations, subscription plans, user activity, business intelligence, time series, SaaS analytics, customer data, event tracking, usage metrics

## Table and Column Documentation

**Table Comment**: One line per day per organization in Dagster+, with organization details and daily event metrics

**Column Comments**:

- DATE_DAY: Date for which this organization data snapshot applies
- ORGANIZATION_NAME: Name of the organization
- ORG_CREATED_AT: Date when the organization was created
- ORGANIZATION_ID: Unique identifier for the organization in Dagster+
- STATUS: Current status of the organization
- PLAN_TYPE: Subscription plan type of the organization
- BASE_PLAN_TYPE: Base subscription plan type of the organization
- IS_INTERNAL: Boolean indicating if this is an internal organization
- HAS_SAML_SSO: Boolean indicating if the organization has SAML SSO enabled
- IS_ACTIVE: Boolean indicating if the organization is currently active
- SALESFORCE_ACCOUNT_ID: Related account identifier in Salesforce
- SALESFORCE_ACCOUNT_TYPE: Type of the related account in Salesforce
- SALESFORCE_ACCOUNT_STATUS: Status of the related account in Salesforce
- STRIPE_CUSTOMER_ID: Identifier for the customer in Stripe
- LAST_USER_LOGIN: Date of the last user login for this organization
- DAYS_SINCE_CREATION: Number of days between organization creation and the snapshot date
- LAST_RUN_AT: Date of the last pipeline/asset run for this organization
- TOTAL_SYSTEM_EVENTS: Total number of system events recorded for the organization on this date
- PIPELINE_STARTS: Number of pipeline start events recorded for the organization on this date
- PIPELINE_FAILURES: Number of pipeline failure events recorded for the organization on this date
- PIPELINE_SUCCESSES: Number of pipeline success events recorded for the organization on this date
- PIPELINE_CANCELLATIONS: Number of pipeline cancellation events recorded for the organization on this date
- ASSET_MATERIALIZATIONS: Number of asset materialization events recorded for the organization on this date
- ASSET_OBSERVATIONS: Number of asset observation events recorded for the organization on this date
- ASSET_CHECK_EVALUATIONS: Number of asset check evaluation events recorded for the organization on this date
- ALERTS_SENT: Number of alert success events recorded for the organization on this date
- ASSETS_WITH_NEW_FRESHNESS_POLICY_COUNT: Number of assets with new freshness policy events recorded for the organization on this date
