---
columns:
  - ADMIN_COUNT (NUMBER(18,0))
  - BASE_PLAN_TYPE (VARCHAR(16777216))
  - CUSTOM_ROLE_COUNT (NUMBER(18,0))
  - DAYS_ORG_CREATION_TO_LAST_PLAN_CHANGE (NUMBER(9,0))
  - DAYS_TO_CONVERT (NUMBER(9,0))
  - DEPLOYMENTS_ARRAY (ARRAY)
  - EDITOR_COUNT (NUMBER(18,0))
  - EVER_SELF_SERVE (BOOLEAN)
  - FIRST_ACTIVE_DATE (DATE)
  - FIRST_ENGAGED_DATE (DATE)
  - FIRST_INVOICE_DATE (DATE)
  - FIRST_RUN_AT (FLOAT)
  - FIRST_SELF_SERVE_INVOICE_DATE (DATE)
  - HAS_CONVERTED (BOOLEAN)
  - HAS_SAML_SSO (BOOLEAN)
  - HYBRID_DEPLOYMENT_COUNT (NUMBER(18,0))
  - IS_ACTIVE (BOOLEAN)
  - IS_INTERNAL (BOOLEAN)
  - LAST_ACTIVE_DATE (DATE)
  - LAST_ENGAGED_DATE (DATE)
  - LAST_INVOICE_AMOUNT (NUMBER(38,6))
  - LAST_INVOICE_DATE (DATE)
  - LAST_RUN_AT (FLOAT)
  - LAST_SELF_SERVE_INVOICE_DATE (DATE)
  - LAST_USER_LOGIN (TIMESTAMP_NTZ(9))
  - LAUNCHER_COUNT (NUMBER(18,0))
  - ORGANIZATION_ID (NUMBER(38,0))
  - ORGANIZATION_METADATA (VARIANT)
  - ORGANIZATION_NAME (VARCHAR(16777216))
  - ORGANIZATION_SETTINGS (VARIANT)
  - ORG_CREATED_AT (TIMESTAMP_NTZ(9))
  - ORG_UPDATED_AT (TIMESTAMP_NTZ(9))
  - PLAN_TYPE (VARCHAR(16777216))
  - PREVIOUS_PLAN_LAST_INVOICE_CREATED_AT (TIMESTAMP_NTZ(9))
  - PREVIOUS_PLAN_TYPE (VARCHAR(16777216))
  - SALESFORCE_ACCOUNT_ID (VARCHAR(16777216))
  - SALESFORCE_ACCOUNT_STATUS (VARCHAR(765))
  - SALESFORCE_ACCOUNT_TYPE (VARCHAR(765))
  - SELF_SERVE_INVOICE_COUNT (NUMBER(18,0))
  - SELF_SERVE_OR_ENTERPRISE (VARCHAR(10))
  - SERVERLESS_DEPLOYMENT_COUNT (NUMBER(18,0))
  - STATUS (VARCHAR(16777216))
  - STRIPE_CUSTOMER_ID (VARCHAR(16777216))
  - TIME_TO_FIRST_ACTIVE (NUMBER(9,0))
  - TIME_TO_FIRST_ENGAGED (NUMBER(9,0))
  - TOTAL_INVOICES (NUMBER(18,0))
  - TOTAL_INVOICE_AMOUNT (NUMBER(38,6))
  - TOTAL_SEATS_COUNT (NUMBER(18,0))
  - TOTAL_SELF_SERVE_INVOICE_AMOUNT (NUMBER(38,6))
  - TRIAL_END (TIMESTAMP_NTZ(9))
  - TRIAL_START (TIMESTAMP_NTZ(9))
  - USERS_OBJECT (OBJECT)
  - VIEWER_COUNT (NUMBER(18,0))
schema_hash: 1b69fd225e943b98523f5ba850918067b72b3b154c5252df2b3e732c37c1be26
---

# DWH_REPORTING.PRODUCT.ORGANIZATIONS Table Summary

## Overall Dataset Characteristics

- **Total Rows**: 14,265 organizations
- **Data Quality**: High quality with most core fields having 0% null values
- **Distribution Patterns**:
  - Majority of organizations (91%+) are on trial/non-paying status
  - Heavy concentration in TEAM_V2 plan type
  - Most organizations (95%+) have never reached weekly engagement
  - Strong recency bias with many organizations created in 2024-2025
- **Business Context**: Comprehensive customer lifecycle tracking from trial through conversion and engagement

## Column Details

### Primary Identifiers

- **ORGANIZATION_ID**: NUMBER(38,0) - Unique primary key (2-17,213), no nulls
- **ORGANIZATION_NAME**: VARCHAR - Human-readable names, 99.95% unique, no nulls

### Status & Classification

- **STATUS**: VARCHAR - 4 values (ACTIVE, PENDING_DELETION, READ_ONLY, SUSPENDED), no nulls
- **IS_INTERNAL**: BOOLEAN - Internal Elementl organizations flag, no nulls
- **IS_ACTIVE**: BOOLEAN - Derived active status, no nulls
- **PLAN_TYPE**: VARCHAR - 7 plan types (ENTERPRISE, TEAM_V2, SOLO, etc.), no nulls
- **BASE_PLAN_TYPE**: VARCHAR - Simplified plan grouping, no nulls
- **SELF_SERVE_OR_ENTERPRISE**: VARCHAR - Binary classification, no nulls

### Temporal Data

- **ORG_CREATED_AT**: TIMESTAMP - Organization creation time, no nulls
- **ORG_UPDATED_AT**: TIMESTAMP - Last update time, no nulls
- **TRIAL_START/TRIAL_END**: TIMESTAMP - Trial period boundaries, 8.79% nulls
- **LAST_USER_LOGIN**: TIMESTAMP - Most recent login, 21.61% nulls

### Engagement & Activity Metrics

- **LAST_RUN_AT/FIRST_RUN_AT**: FLOAT - Dagster run timestamps, 73.92% nulls
- **FIRST_ACTIVE_DATE/LAST_ACTIVE_DATE**: DATE - Weekly activity periods, 81% nulls
- **FIRST_ENGAGED_DATE/LAST_ENGAGED_DATE**: DATE - Weekly engagement periods, 95.09% nulls
- **TIME_TO_FIRST_ACTIVE/TIME_TO_FIRST_ENGAGED**: NUMBER - Days to reach milestones

### Financial Data

- **HAS_CONVERTED**: BOOLEAN - Trial to paid conversion flag, no nulls
- **DAYS_TO_CONVERT**: NUMBER - Conversion timeline, 91.17% nulls
- **TOTAL_INVOICE_AMOUNT**: NUMBER - Lifetime revenue (0-464K), no nulls
- **LAST_INVOICE_AMOUNT**: NUMBER - Most recent billing (0-350K), no nulls
- **STRIPE_CUSTOMER_ID**: VARCHAR - Payment system ID, 8.38% nulls
- **FIRST_INVOICE_DATE/LAST_INVOICE_DATE**: DATE - Billing timeline, 91.17% nulls

### User & Deployment Counts

- **TOTAL_SEATS_COUNT**: NUMBER - Total activated users (0-12,624), no nulls
- **ADMIN_COUNT/EDITOR_COUNT/VIEWER_COUNT/LAUNCHER_COUNT**: NUMBER - Role-based counts, no nulls
- **HYBRID_DEPLOYMENT_COUNT/SERVERLESS_DEPLOYMENT_COUNT**: NUMBER - Infrastructure counts, no nulls

### Complex Data Structures

- **DEPLOYMENTS_ARRAY**: ARRAY - Detailed deployment information, no nulls
- **USERS_OBJECT**: OBJECT - User details by ID, 1.03% nulls
- **ORGANIZATION_METADATA**: VARIANT - GitHub/Slack integrations, 65.85% nulls
- **ORGANIZATION_SETTINGS**: VARIANT - Configuration data, 0.56% nulls

### External System Integration

- **SALESFORCE_ACCOUNT_ID**: VARCHAR - CRM integration, 50.52% nulls
- **SALESFORCE_ACCOUNT_TYPE/STATUS**: VARCHAR - Sales pipeline data, no nulls
- **HAS_SAML_SSO**: BOOLEAN - Enterprise authentication, 65.85% nulls

## Potential Query Considerations

### Good for Filtering

- **STATUS** - Organization lifecycle filtering
- **PLAN_TYPE/BASE_PLAN_TYPE** - Subscription tier analysis
- **IS_ACTIVE/HAS_CONVERTED** - Business metrics segmentation
- **ORG_CREATED_AT** - Cohort analysis by signup period
- **SELF_SERVE_OR_ENTERPRISE** - Go-to-market segmentation

### Good for Grouping/Aggregation

- **PLAN_TYPE** - Revenue analysis by subscription tier
- **STATUS** - Pipeline analysis
- **SALESFORCE_ACCOUNT_TYPE** - Sales funnel metrics
- **BASE_PLAN_TYPE** - Simplified plan analytics
- Date fields for time-series analysis (created_at, trial dates)

### Potential Join Keys

- **ORGANIZATION_ID** - Primary key for joins with other org-related tables
- **STRIPE_CUSTOMER_ID** - Payment system integration
- **SALESFORCE_ACCOUNT_ID** - CRM system joins

### Data Quality Considerations

- High null percentage in engagement metrics (95%+ for engaged dates)
- Revenue data sparse (91%+ nulls for conversion metrics)
- Complex JSON fields may require parsing for detailed analysis
- Timestamp fields use different formats (TIMESTAMP_NTZ vs FLOAT)
- Large range in user counts suggests potential data quality issues for outliers

## Keywords

organizations, customers, subscriptions, trials, conversions, revenue, billing, deployments, users, engagement, activity, Dagster, Salesforce, Stripe, SAML, plans, enterprise, self-serve, lifecycle, analytics, business intelligence

## Table and Column Docs

### Table Comment

Comprehensive organizations dimension table with one row per organization, enriched with deployment information, user data, billing details, and business metrics. This table provides a complete view of organization lifecycle, usage patterns, and business intelligence for analytics and reporting.

### Column Comments

- **ORGANIZATION_ID**: Primary key - unique identifier for the organization
- **STATUS**: Current status of the organization (ACTIVE, INACTIVE, etc.)
- **ORGANIZATION_NAME**: Human-readable name of the organization
- **IS_INTERNAL**: Boolean flag indicating if this is an internal Elementl organization
- **IS_ACTIVE**: Boolean indicating whether the organization is active (status = ACTIVE and not internal)
- **ORG_CREATED_AT**: Timestamp when the organization was created
- **TRIAL_END**: End date of the organization's trial period
- **TRIAL_START**: Start date of the organization's trial period
- **HAS_CONVERTED**: Boolean indicating whether the organization has converted from trial to paid
- **LAST_USER_LOGIN**: Timestamp of the most recent user login across all users in the organization
- **LAST_RUN_AT**: Timestamp of the most recent Dagster run in the organization
- **DAYS_TO_CONVERT**: Number of days from organization creation to first invoice (conversion time)
- **PLAN_TYPE**: Current plan type of the organization
- **FIRST_RUN_AT**: Timestamp of the first Dagster run in the organization
- **BASE_PLAN_TYPE**: Base plan type extracted from plan_type (before any suffixes)
- **SELF_SERVE_OR_ENTERPRISE**: Categorized plan type (SELF_SERVE or ENTERPRISE)
- **HAS_SAML_SSO**: Boolean indicating whether the organization has SAML SSO enabled
- **SALESFORCE_ACCOUNT_ID**: Salesforce account ID associated with this organization
- **SALESFORCE_ACCOUNT_TYPE**: Type of the Salesforce account (unset if not available)
- **SALESFORCE_ACCOUNT_STATUS**: Status of the Salesforce account (unset if not available)
- **STRIPE_CUSTOMER_ID**: Stripe customer ID associated with this organization
- **FIRST_INVOICE_DATE**: Date of the first invoice for this organization
- **LAST_INVOICE_DATE**: Date of the most recent invoice for this organization
- **LAST_INVOICE_AMOUNT**: Amount of the most recent invoice
- **TOTAL_INVOICES**: Total number of invoices for this organization
- **TOTAL_INVOICE_AMOUNT**: Total amount of all invoices for this organization
- **TOTAL_SELF_SERVE_INVOICE_AMOUNT**: Total amount from self-serve invoices only
- **SELF_SERVE_INVOICE_COUNT**: Number of self-serve invoices
- **EVER_SELF_SERVE**: Boolean indicating whether the organization has ever had self-serve billing
- **FIRST_SELF_SERVE_INVOICE_DATE**: Date of the first self-serve invoice
- **LAST_SELF_SERVE_INVOICE_DATE**: Date of the most recent self-serve invoice
- **HYBRID_DEPLOYMENT_COUNT**: Number of active hybrid deployments for this organization
- **SERVERLESS_DEPLOYMENT_COUNT**: Number of active serverless deployments for this organization
- **ADMIN_COUNT**: Number of users with ADMIN role in this organization
- **DEPLOYMENTS_ARRAY**: Array of deployment objects containing detailed information about all deployments for this organization
- **EDITOR_COUNT**: Number of users with EDITOR role in this organization
- **VIEWER_COUNT**: Number of users with VIEWER role in this organization
- **LAUNCHER_COUNT**: Number of users with LAUNCHER role in this organization
- **ORGANIZATION_METADATA**: JSON object containing additional organization metadata
- **CUSTOM_ROLE_COUNT**: Number of users with CUSTOM role in this organization
- **TOTAL_SEATS_COUNT**: Total number of activated user seats in this organization
- **ORGANIZATION_SETTINGS**: JSON object containing organization-specific settings
- **USERS_OBJECT**: Object containing detailed information about all users in this organization, keyed by user_id
- **ORG_UPDATED_AT**: Timestamp when the organization was last updated
- **PREVIOUS_PLAN_TYPE**: The organization's previous plan type before the most recent plan change (null if no plan changes)
- **PREVIOUS_PLAN_LAST_INVOICE_CREATED_AT**: Date of the last invoice for the previous plan type (null if no plan changes)
- **FIRST_ENGAGED_DATE**: Date when the organization first became weekly engaged (minimum date from dim_organizations_by_day where is_weekly_engaged_organization = true)
- **LAST_ENGAGED_DATE**: Date when the organization was last weekly engaged (maximum date from dim_organizations_by_day where is_weekly_engaged_organization = true)
- **DAYS_ORG_CREATION_TO_LAST_PLAN_CHANGE**: Number of days from organization creation to the most recent plan change (null if no plan changes)
- **FIRST_ACTIVE_DATE**: Date when the organization first became weekly active (minimum date from dim_organizations_by_day where is_weekly_active_organization = true)
- **LAST_ACTIVE_DATE**: Date when the organization was last weekly active (maximum date from dim_organizations_by_day where is_weekly_active_organization = true)
- **TIME_TO_FIRST_ENGAGED**: Number of days from organization creation to first weekly engagement
- **TIME_TO_FIRST_ACTIVE**: Number of days from organization creation to first weekly activity
