---
columns:
  - AMOUNT_DUE (NUMBER(38,6))
  - AMOUNT_PAID (NUMBER(38,6))
  - CUSTOMER_ID (VARCHAR(16777216))
  - CUSTOMER_NAME (VARCHAR(16777216))
  - DAGSTER_CLOUD_ORGANIZATION_ID (VARCHAR(16777216))
  - INVOICE_CREATED_AT (TIMESTAMP_NTZ(9))
  - INVOICE_ID (VARCHAR(16777216))
  - INVOICE_NUMBER (VARCHAR(16777216))
  - INVOICE_STATUS (VARCHAR(16777216))
  - INVOICE_TOTAL (NUMBER(38,6))
  - IS_FIRST_SELF_SERVE_INVOICE (BOOLEAN)
  - IS_PAID (BOOLEAN)
  - IS_SELF_SERVE (BOOLEAN)
  - MONTHS_WITH_SELF_SERVE_INVOICE (NUMBER(18,0))
  - PERIOD_END (TIMESTAMP_NTZ(9))
  - PERIOD_START (TIMESTAMP_NTZ(9))
  - SUBSCRIPTION_ENDED_AT (TIMESTAMP_NTZ(9))
  - SUBSCRIPTION_ID (VARCHAR(16777216))
  - SUBSCRIPTION_PLAN (VARCHAR(16777216))
  - SUBSCRIPTION_PLAN_TYPE (VARCHAR(10))
  - SUBSCRIPTION_STARTED_AT (TIMESTAMP_NTZ(9))
  - SUBSCRIPTION_STATUS (VARCHAR(16777216))
  - USAGE_PERIOD (DATE)
schema_hash: 31193c7544953afa34520cb2532690b623921641152410887c027c4c7be99e9e
---

# DWH_REPORTING.BUSINESS.SELF_SERVE_INVOICES - Data Summary

## Overall Dataset Characteristics

- **Total Rows**: 11,310 invoices
- **Data Quality**: Excellent - no null values in most critical columns, with only two columns having any null values
- **Time Period**: Covers invoices from August 2022 through future dates (up to 2025), indicating both historical data and projected invoices
- **Customer Base**: 1,031 unique customers with 1,133 unique subscriptions
- **Invoice Pattern**: Monthly billing cycle with invoices created in the month following usage

## Table and Column Documentation

**Table Comment**: One line per self-serve invoice from Stripe, with enriched customer and subscription information for customers on self-serve plans

### Column Details

#### Identifiers and Keys

- **INVOICE_ID** (VARCHAR): Unique invoice identifier from Stripe - perfect primary key with 100% uniqueness
- **INVOICE_NUMBER** (VARCHAR): Sequential invoice numbers from Stripe - also 100% unique
- **CUSTOMER_ID** (VARCHAR): Stripe customer identifiers - 1,031 unique customers across 11,310 invoices (avg ~11 invoices per customer)
- **SUBSCRIPTION_ID** (VARCHAR): Stripe subscription identifiers - 1,133 unique subscriptions
- **DAGSTER_CLOUD_ORGANIZATION_ID** (VARCHAR): Dagster Cloud organization IDs - only 0.88% null values, making it reliable for joins

#### Customer Information

- **CUSTOMER_NAME** (VARCHAR): Customer names from Stripe - matches customer_id uniqueness (1,031 unique names)

#### Financial Data

- **INVOICE_TOTAL** (NUMBER): Total invoice amounts ranging from -$570.34 to $21,144.09 (negative values likely indicate credits/refunds)
- **AMOUNT_DUE** (NUMBER): Outstanding amounts from $0 to $21,144.09
- **AMOUNT_PAID** (NUMBER): Paid amounts from $0 to $21,144.09
- **IS_PAID** (BOOLEAN): Payment status indicator
- **INVOICE_STATUS** (VARCHAR): Only 2 values - "paid" and "open"

#### Subscription Plans

- **SUBSCRIPTION_PLAN** (VARCHAR): 4 plan types - SOLO, STANDARD, TEAM, TEAM_V2
- **SUBSCRIPTION_PLAN_TYPE** (VARCHAR): Always "SELF_SERVE" (constant value)
- **IS_SELF_SERVE** (BOOLEAN): Always True (constant value)

#### Temporal Data

- **INVOICE_CREATED_AT** (TIMESTAMP): Invoice creation timestamps with high granularity (9,975 unique values)
- **USAGE_PERIOD** (DATE): 38 distinct monthly periods from 2022-08 to future dates
- **PERIOD_START/PERIOD_END** (TIMESTAMP): Billing period boundaries
- **SUBSCRIPTION_STARTED_AT** (TIMESTAMP): Subscription start dates (1,133 unique - matches subscription count)
- **SUBSCRIPTION_ENDED_AT** (TIMESTAMP): Subscription end dates - 67.78% null (indicating active subscriptions)

#### Subscription Status

- **SUBSCRIPTION_STATUS** (VARCHAR): 3 values - "active", "canceled", "unpaid"

#### Analytics Fields

- **IS_FIRST_SELF_SERVE_INVOICE** (BOOLEAN): Flags first invoice for each customer
- **MONTHS_WITH_SELF_SERVE_INVOICE** (NUMBER): Running count of months with invoices (1-37 range)

## Query Considerations

### Excellent Filtering Columns

- **USAGE_PERIOD**: Perfect for time-based analysis (38 distinct monthly values)
- **SUBSCRIPTION_PLAN**: Good for plan-based segmentation (4 distinct values)
- **INVOICE_STATUS**: Simple paid/open filtering (2 values)
- **SUBSCRIPTION_STATUS**: Customer lifecycle analysis (3 values)
- **IS_FIRST_SELF_SERVE_INVOICE**: Customer acquisition analysis

### Strong Grouping/Aggregation Candidates

- **CUSTOMER_ID/CUSTOMER_NAME**: Customer-level analysis
- **SUBSCRIPTION_PLAN**: Plan performance comparison
- **USAGE_PERIOD**: Time series analysis
- **SUBSCRIPTION_STATUS**: Cohort analysis
- **MONTHS_WITH_SELF_SERVE_INVOICE**: Customer tenure analysis

### Join Key Potential

- **CUSTOMER_ID**: Primary customer identifier for external customer tables
- **SUBSCRIPTION_ID**: For detailed subscription information
- **DAGSTER_CLOUD_ORGANIZATION_ID**: Links to Dagster Cloud organization data (only 0.88% null)

### Data Quality Considerations

- **Negative Invoice Amounts**: Some invoices have negative totals (likely credits) - should be considered in revenue calculations
- **Future Dates**: Some invoices/periods extend into 2025 - may be projected or scheduled invoices
- **Subscription End Dates**: 67.78% null values indicate active subscriptions - important for churn analysis
- **Constant Fields**: SUBSCRIPTION_PLAN_TYPE and IS_SELF_SERVE are always the same value - useful for validation but not filtering

### Keywords

self-serve invoices, stripe billing, subscription revenue, dagster cloud, customer invoicing, saas billing, monthly recurring revenue, subscription plans, invoice status, customer lifecycle, billing periods, payment tracking, subscription analytics, revenue analysis, customer segmentation
