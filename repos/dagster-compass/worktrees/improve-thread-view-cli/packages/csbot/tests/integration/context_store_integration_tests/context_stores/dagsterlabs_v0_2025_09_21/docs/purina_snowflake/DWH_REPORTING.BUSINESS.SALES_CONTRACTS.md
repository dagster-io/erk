---
columns:
  - ACCOUNT_ID (VARCHAR(16777216))
  - ACCOUNT_NAME (VARCHAR(765))
  - ACTIVATED_DATE (TIMESTAMP_TZ(9))
  - ARR (NUMBER(35,17))
  - BILLED_THRU (VARCHAR(765))
  - CLOUD_CREDITS_CONTRACTED (FLOAT)
  - CONCURRENCY_SLOTS (FLOAT)
  - CONTRACTED_PER_CONCURRENCY_SLOT_PRICE (NUMBER(35,17))
  - CONTRACTED_PER_CREDIT_PRICE (NUMBER(35,17))
  - CONTRACTED_PER_SEAT_PRICE (NUMBER(35,17))
  - CONTRACT_DESCRIPTION (VARCHAR(96000))
  - CONTRACT_END_DATE (DATE)
  - CONTRACT_ID (VARCHAR(16777216))
  - CONTRACT_NUMBER (VARCHAR(90))
  - CONTRACT_START_DATE (DATE)
  - CONTRACT_STATUS (VARCHAR(300))
  - CONTRACT_TERM (NUMBER(38,0))
  - CREATED_DATE (TIMESTAMP_TZ(9))
  - IS_ACTIVE_CONTRACT (BOOLEAN)
  - IS_SERVERLESS (BOOLEAN)
  - LAUNCHER_SEATS (FLOAT)
  - OPPORTUNITY_ID (VARCHAR(16777216))
  - OPPORTUNITY_NAME (VARCHAR(360))
  - OPPORTUNITY_TYPE (VARCHAR(765))
  - OWNER_EXPIRATION_NOTICE (VARCHAR(120))
  - PRICING_MODEL (VARCHAR(765))
  - ROLL_OVER_CREDITS (FLOAT)
  - SPECIAL_TERMS (VARCHAR(4000))
schema_hash: 07227d0aa483a00f95e5ab87603eec16b638e25012929bcee2ad7bd99800a26e
---

# Sales Contracts Dataset Summary

## Overall Dataset Characteristics

- **Total Rows**: 557 contracts
- **Data Quality**: High quality with minimal nulls in core fields. All contracts have status "Activated" and unique identifiers are properly maintained.
- **Notable Patterns**:
  - Contract terms are predominantly 12 months (most common value)
  - ARR ranges widely from ~$5,832 to $420,000, indicating diverse customer sizes
  - Most contracts use "Cloud Credits & Seats" pricing model
  - Cloud credits range from 10K to 110M, showing significant usage variation
- **Business Context**: Salesforce-sourced contract data with comprehensive account and opportunity linkage

## Column Details

### Primary Identifiers

- **CONTRACT_ID**: VARCHAR, 0% nulls, 557 unique values - Primary key for contracts
- **CONTRACT_NUMBER**: VARCHAR, 0% nulls, 557 unique values - Business-readable contract identifier
- **ACCOUNT_ID**: VARCHAR, 0% nulls, 310 unique values - Foreign key to accounts (multiple contracts per account possible)
- **OPPORTUNITY_ID**: VARCHAR, 0.90% nulls, 436 unique values - Links to sales opportunities

### Account & Opportunity Information

- **ACCOUNT_NAME**: VARCHAR, 0% nulls, 310 unique values - Company names like "HDI AG", "AgentSync"
- **OPPORTUNITY_NAME**: VARCHAR, 0.90% nulls, 436 unique values - Deal names, often include renewal/expansion indicators
- **OPPORTUNITY_TYPE**: VARCHAR, 0.90% nulls, 3 values - "New Business", "Renewal", "Upsell"

### Financial Metrics

- **ARR**: NUMBER, 0% nulls, 339 unique values - Annual Recurring Revenue ($5,832 to $420,000)
- **CLOUD_CREDITS_CONTRACTED**: FLOAT, 5.03% nulls, 109 unique values - Credit allocation (10K to 110M)
- **CONTRACTED_PER_CREDIT_PRICE**: NUMBER, 29.62% nulls - Price per credit ($0.00015 to $0.06)
- **CONTRACTED_PER_SEAT_PRICE**: NUMBER, 30.88% nulls - Price per seat ($100 to $1,200)
- **CONTRACTED_PER_CONCURRENCY_SLOT_PRICE**: NUMBER, 97.85% nulls - Rarely used pricing metric

### Contract Terms

- **CONTRACT_TERM**: NUMBER, 0% nulls, 9 unique values - Contract length in months (3-18, mostly 12)
- **CONTRACT_START_DATE**: DATE, 0% nulls, 375 unique values - Contract effective dates
- **CONTRACT_END_DATE**: DATE, 0% nulls, 372 unique values - Contract expiration dates
- **PRICING_MODEL**: VARCHAR, 1.62% nulls, 5 values - "Cloud Credits & Seats", "Platform Fee Based", etc.

### Capacity & Features

- **LAUNCHER_SEATS**: FLOAT, 7.18% nulls - Seat allocation (0-200, commonly 3-50)
- **CONCURRENCY_SLOTS**: FLOAT, 97.85% nulls - Rarely used capacity metric (3-40)
- **IS_SERVERLESS**: BOOLEAN, 0% nulls - Service type indicator
- **ROLL_OVER_CREDITS**: FLOAT, 95.69% nulls - Credit carryover amounts

### Status & Metadata

- **CONTRACT_STATUS**: VARCHAR, 0% nulls, 1 value - All contracts are "Activated"
- **IS_ACTIVE_CONTRACT**: BOOLEAN, 0% nulls - Current activity status
- **CREATED_DATE**: TIMESTAMP, 0% nulls - Contract creation timestamp
- **ACTIVATED_DATE**: TIMESTAMP, 0% nulls - Contract activation timestamp
- **BILLED_THRU**: VARCHAR, 2.33% nulls - Payment processor ("STRIPE", "AWS", "AZURE", "GCP")

### Administrative Fields

- **OWNER_EXPIRATION_NOTICE**: VARCHAR, 3.95% nulls - Notice period (60 or 90 days)
- **SPECIAL_TERMS**: VARCHAR, 99.46% nulls - Rarely used contract modifications
- **CONTRACT_DESCRIPTION**: VARCHAR, 99.64% nulls - Additional contract notes

## Query Considerations

### Excellent for Filtering

- **IS_ACTIVE_CONTRACT**: Boolean filter for current contracts
- **OPPORTUNITY_TYPE**: Filter by business type (New/Renewal/Upsell)
- **PRICING_MODEL**: Filter by pricing structure
- **CONTRACT_TERM**: Filter by contract length
- **IS_SERVERLESS**: Filter by service type
- **Date fields**: Filter by time ranges

### Good for Grouping/Aggregation

- **ACCOUNT_NAME**: Group by customer
- **OPPORTUNITY_TYPE**: Segment by business type
- **PRICING_MODEL**: Analyze by pricing approach
- **CONTRACT_TERM**: Group by contract length
- **BILLED_THRU**: Analyze by payment method
- **Date fields**: Time-based analysis (monthly/yearly trends)

### Potential Join Keys

- **ACCOUNT_ID**: Link to account master data
- **OPPORTUNITY_ID**: Link to opportunity details
- **CONTRACT_ID**: Primary key for contract-related tables

### Data Quality Considerations

- Some pricing fields have high null percentages (29-98%) - check for nulls when analyzing pricing
- **SPECIAL_TERMS** and **CONTRACT_DESCRIPTION** are mostly empty - limited analytical value
- **ROLL_OVER_CREDITS** has 95.69% nulls - only relevant for specific contract types
- **OPPORTUNITY_ID** has 0.90% nulls - may indicate some contracts without linked opportunities

## Keywords

sales contracts, salesforce, ARR, annual recurring revenue, cloud credits, contract terms, pricing models, account management, opportunity tracking, contract status, renewal tracking, subscription revenue, SaaS contracts, business intelligence

## Table and Column Documentation

**Table Comment**: One line per contract from Salesforce with contract details and related account information

**Column Comments**:

- CONTRACT_ID: Unique identifier for the contract
- ACCOUNT_NAME: Name of the related account
- ACCOUNT_ID: Related account identifier
- OPPORTUNITY_ID: Related opportunity identifier
- OPPORTUNITY_NAME: Name of the related opportunity
- OPPORTUNITY_TYPE: Type of opportunity (e.g., new business, expansion)
- CONTRACT_NUMBER: Unique contract number in Salesforce
- ARR: Annual recurring revenue for the contract
- CLOUD_CREDITS_CONTRACTED: Number of cloud credits contracted
- CREATED_DATE: Date when the contract was created
- CONTRACT_TERM: Term length of the contract
- CONTRACT_END_DATE: End date of the contract
- CONTRACT_START_DATE: Start date of the contract
- PRICING_MODEL: Pricing model used for the contract
- IS_SERVERLESS: Boolean indicating if this is a serverless contract
- CONTRACT_STATUS: Current status of the contract
- LAUNCHER_SEATS: Number of launcher seats included in the contract
- ACTIVATED_DATE: Date when the contract was activated
- BILLED_THRU: Date through which the contract is billed
- ROLL_OVER_CREDITS: Credits that roll over from previous periods
- IS_ACTIVE_CONTRACT: Boolean indicating if the contract is currently active
