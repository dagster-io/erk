---
columns:
  - CREATED_AT (TIMESTAMP_NTZ(9))
  - EMAIL_HASH (VARCHAR(128))
  - FIRST_NAME (VARCHAR(16777216))
  - LAST_LOGIN (TIMESTAMP_NTZ(9))
  - LAST_NAME (VARCHAR(16777216))
  - OAUTH_PROVIDER (VARCHAR(16777216))
  - ORGANIZATIONS_ARRAY (ARRAY)
  - ORGANIZATION_COUNT (NUMBER(18,0))
  - UPDATED_AT (TIMESTAMP_NTZ(9))
  - USER_ID (NUMBER(38,0))
  - USER_TITLE (VARCHAR(16777216))
schema_hash: d4e962b079eb5b14fc47e9c54442107cd58dd5eec8e5ac7e215ec96d24278739
---

# DWH_REPORTING.PRODUCT.USERS Table Summary

## Overall Dataset Characteristics

- **Total Rows**: 99,031 users
- **Data Quality**: Generally good with complete core identifiers (USER_ID, EMAIL_HASH) but significant null values in optional fields
- **Key Pattern**: One row per user with comprehensive organization relationship data stored as structured JSON arrays
- **Distribution**: Most users (likely ~89%) appear to be inactive based on null LAST_LOGIN values; most belong to a single organization

## Column Details

### Core Identifiers

- **USER_ID**: Primary key, NUMBER(38,0), no nulls, unique values (1 to 269018 range)
- **EMAIL_HASH**: Unique hashed email identifier, VARCHAR(128), virtually no duplicates (99,030 unique out of 99,031)

### Personal Information

- **FIRST_NAME**: VARCHAR(16777216), 3.5% nulls, 27,374 unique values - good for personalization queries
- **LAST_NAME**: VARCHAR(16777216), 4.3% nulls, 48,717 unique values - good for personalization queries
- **USER_TITLE**: VARCHAR(16777216), 94% nulls, only 440 unique values - limited utility due to high null rate

### Temporal Data

- **CREATED_AT**: TIMESTAMP_NTZ(9), no nulls, unique per user - excellent for cohort analysis and user registration trends
- **UPDATED_AT**: TIMESTAMP_NTZ(9), 70.98% nulls - indicates most users haven't been updated since creation
- **LAST_LOGIN**: TIMESTAMP_NTZ(9), 89.41% nulls - high percentage of inactive users

### Authentication

- **OAUTH_PROVIDER**: VARCHAR(16777216), 91.92% nulls, only 3 providers (EMAIL, GITHUB, GOOGLE) - most users use standard email authentication

### Organization Relationships (Key Feature)

- **ORGANIZATIONS_ARRAY**: ARRAY containing structured JSON objects with organization details including:
  - organization_id, organization_name, user_role
  - relationship_created_at, organization_created_at
  - organization_user_rank, user_organization_rank
- **ORGANIZATION_COUNT**: NUMBER(18,0), ranges 0-17, most users belong to 1 organization

## Query Considerations

### Good for Filtering

- **USER_ID**: Primary key filtering
- **CREATED_AT**: Date range filtering for user registration analysis
- **ORGANIZATION_COUNT**: Filter by number of org memberships
- **OAUTH_PROVIDER**: Authentication method filtering (though high null rate)

### Good for Grouping/Aggregation

- **CREATED_AT**: Time-based cohort analysis (by day/month/year)
- **ORGANIZATION_COUNT**: Distribution of multi-org users
- **OAUTH_PROVIDER**: Authentication method distribution
- **LAST_LOGIN**: Active vs inactive user segmentation

### Potential Join Keys

- **USER_ID**: Primary key for joining with other user-related tables
- Organization data within **ORGANIZATIONS_ARRAY** can be extracted for joins with organization tables

### Data Quality Considerations

- High null rates in USER_TITLE (94%), UPDATED_AT (71%), OAUTH_PROVIDER (92%), and LAST_LOGIN (89%)
- When querying optional fields, account for significant null values
- ORGANIZATIONS_ARRAY requires JSON parsing functions for analysis
- Consider filtering out inactive users (null LAST_LOGIN) for engagement analysis

## Keywords

users, customers, accounts, authentication, organizations, relationships, user management, oauth, login activity, user engagement, cohort analysis, multi-tenant, json arrays, structured data, user roles, timestamps, hashed emails, privacy, GDPR

## Table and Column Documentation

**Table Comment**: "Comprehensive users table with all organization relationships as structured objects for product reporting and analytics. One row per user."

**Column Comments**:

- USER_ID: "Unique identifier for the user"
- USER_TITLE: "User's job title"
- FIRST_NAME: "User's first name"
- LAST_NAME: "User's last name"
- CREATED_AT: "When the user account was created"
- UPDATED_AT: "When the user account was last updated"
- OAUTH_PROVIDER: "OAuth provider used for authentication (google, github, microsoft, etc.)"
- LAST_LOGIN: "Most recent login timestamp"
- ORGANIZATIONS_ARRAY: "Array of structured objects containing all organization relationships. Each object includes organization_id, organization_name, user_role, relationship_created_at, organization_created_at, organization_user_rank, and user_organization_rank."
- ORGANIZATION_COUNT: "Total number of organizations the user belongs to"
