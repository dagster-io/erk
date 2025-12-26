---
columns:
  - ACCOUNT_CALL_NUMBER (NUMBER(18,0))
  - AE_ID (VARCHAR(16777216))
  - AMOUNT (VARIANT)
  - ATTENDEES (ARRAY)
  - CALL_CONVERSATION_KEY (VARCHAR(16777216))
  - CALL_DIRECTION (VARCHAR(16777216))
  - CALL_DURATION (FLOAT)
  - CALL_END_DATETIME (TIMESTAMP_TZ(9))
  - CALL_SPOTLIGHT_BRIEF (VARCHAR(16777216))
  - CALL_SPOTLIGHT_KEY_POINTS (ARRAY)
  - CALL_SPOTLIGHT_NEXT_STEPS (VARCHAR(16777216))
  - CALL_SPOTLIGHT_TYPE (VARCHAR(16777216))
  - CALL_START_DATETIME (TIMESTAMP_TZ(9))
  - CALL_STATUS (VARCHAR(16777216))
  - CALL_TITLE (VARCHAR(16777216))
  - CALL_TRANSCRIPT_ROW_ID (VARCHAR(32))
  - CALL_URL (VARCHAR(16777216))
  - CONVERSATION_ID (VARCHAR(16777216))
  - CUSTOMER_INVITE_COUNT (NUMBER(18,0))
  - FORECAST_CATEGORY (VARCHAR(16777216))
  - INTERNAL_INVITE_COUNT (NUMBER(18,0))
  - IS_CANCELED (BOOLEAN)
  - IS_FIRST_ACCOUNT_MEETING (BOOLEAN)
  - IS_FIRST_OPPORTUNITY_MEETING (BOOLEAN)
  - OPPORTUNITY_ID (VARCHAR(16777216))
  - ORGANIZER_NAME (VARCHAR(16777216))
  - PRESENTATION_DURATION_SEC (FLOAT)
  - PRIMARY_ACCOUNT_ID (VARCHAR(16777216))
  - PRIMARY_ACCOUNT_NAME (VARCHAR(765))
  - PROVIDER_UNIQUE_ID (VARCHAR(16777216))
  - QUESTION_COMPANY_COUNT (NUMBER(38,0))
  - QUESTION_NON_COMPANY_COUNT (NUMBER(38,0))
  - SENTIMENT_SCORE (FLOAT)
  - SOURCE_SYSTEM (VARCHAR(16777216))
  - STAGE_NAME (VARCHAR(16777216))
  - TRANSCRIPT_SENTENCES (ARRAY)
  - WEBCAM_NON_COMPANY_DURATION_SEC (FLOAT)
  - WEBCAM_OWNER_DURATION_SEC (FLOAT)
  - YEAR1_AMOUNT (VARIANT)
schema_hash: c989c83a8fe5a4b3529ce614bca4486f345c86e808e1462720d27acd49c16897
---

# Sales Meeting Transcripts Data Summary

## Overall Dataset Characteristics

- **Total Rows**: 7,851 sales call transcripts
- **Data Source**: Gong conversation analysis system optimized for LLM training
- **Data Quality**: High quality with minimal null values in core fields
- **Primary Focus**: B2B sales calls for Dagster Labs (data orchestration platform)
- **Time Range**: Calls span from 2023 to 2025 with detailed conversation analysis

**Table Comment**: One line per call transcript from Gong with structured conversation content optimized for LLM training and analysis

## Column Details

### Primary Identifiers

- **CALL_CONVERSATION_KEY** (VARCHAR): Unique conversation identifier, no nulls, 7,851 unique values
- **CALL_TRANSCRIPT_ROW_ID** (VARCHAR): Unique transcript row identifier, no nulls
- **CONVERSATION_ID** (VARCHAR): Gong system identifier, no nulls

### Call Metadata

- **CALL_TITLE** (VARCHAR): Call titles, 5,983 unique values, no nulls
- **CALL_STATUS** (VARCHAR): All calls are "COMPLETED" status
- **CALL_START_DATETIME** (TIMESTAMP): Call start times, 0.17% nulls
- **CALL_END_DATETIME** (TIMESTAMP): Call end times, 4.76% nulls
- **CALL_DIRECTION** (VARCHAR): 4 types - conference, inbound, outbound, unknown
- **CALL_DURATION** (FLOAT): Duration in seconds, 4.64% nulls, range 0-9,099 seconds

### Sales Team Information

- **AE_ID** (VARCHAR): Account executive identifier, 42 unique AEs, no nulls
- **ORGANIZER_NAME** (VARCHAR): Meeting organizer, 46 unique names, 11.34% nulls

### Meeting Analytics

- **WEBCAM_OWNER_DURATION_SEC** (FLOAT): Company webcam usage, no nulls
- **WEBCAM_NON_COMPANY_DURATION_SEC** (FLOAT): Customer webcam usage, no nulls
- **PRESENTATION_DURATION_SEC** (FLOAT): Screen sharing duration, 4.64% nulls
- **QUESTION_COMPANY_COUNT** (NUMBER): Questions from company (0-113 range)
- **QUESTION_NON_COMPANY_COUNT** (NUMBER): Questions from customers (0-159 range)

### AI-Generated Call Intelligence

- **CALL_SPOTLIGHT_BRIEF** (VARCHAR): AI-generated call summaries, 9.77% nulls
- **CALL_SPOTLIGHT_TYPE** (VARCHAR): Call categorization - "sales_call" or "long_sales_call", 9.62% nulls
- **CALL_SPOTLIGHT_NEXT_STEPS** (VARCHAR): Extracted action items, 10.80% nulls
- **CALL_SPOTLIGHT_KEY_POINTS** (ARRAY): Key conversation points, 16.88% nulls
- **SENTIMENT_SCORE** (FLOAT): Call sentiment analysis (-0.85 to +0.73 range), 0.38% nulls

### Salesforce Integration

- **OPPORTUNITY_ID** (VARCHAR): Salesforce opportunity link, 2,109 unique, 14.93% nulls
- **STAGE_NAME** (VARCHAR): 14 sales stages including Discovery, Proposal, Closed Won, etc.
- **FORECAST_CATEGORY** (VARCHAR): 6 categories - Best Case, Closed, Commit, etc.
- **AMOUNT** (VARIANT): Deal values, 530 unique amounts, 14.93% nulls
- **PRIMARY_ACCOUNT_ID/NAME** (VARCHAR): Customer account info, 1,798 unique accounts

### Attendee Information

- **ATTENDEES** (ARRAY): Detailed participant data with names, emails, titles, affiliations
- **CUSTOMER_INVITE_COUNT** (NUMBER): Customer attendee count (1-42 range)
- **INTERNAL_INVITE_COUNT** (NUMBER): Internal attendee count (1-16 range)
- **IS_FIRST_OPPORTUNITY_MEETING** (BOOLEAN): First meeting flag
- **IS_FIRST_ACCOUNT_MEETING** (BOOLEAN): Account relationship flag

### Conversation Content

- **TRANSCRIPT_SENTENCES** (ARRAY): Structured conversation data with speaker info, timing, topics
  - Each sentence includes: speaker_id, speaker_name, speaker_title, speaker_affiliation, topic, start_ms, end_ms, duration_ms, text, sentence_order
  - Optimized for LLM analysis with 0.38% nulls

### Technical Fields

- **SOURCE_SYSTEM** (VARCHAR): 5 platforms - Zoom (dominant), Google Meet, Microsoft Teams, etc.
- **CALL_URL** (VARCHAR): Meeting links, 6,874 unique URLs
- **PROVIDER_UNIQUE_ID** (VARCHAR): 100% null - unused field
- **YEAR1_AMOUNT** (VARIANT): 100% null - unused field
- **ACCOUNT_CALL_NUMBER** (NUMBER): Sequential call number per account (1-1,184 range)

## Query Considerations

### Excellent for Filtering

- **AE_ID**: Filter by sales rep (42 options)
- **CALL_START_DATETIME**: Time-based analysis
- **STAGE_NAME**: Sales pipeline filtering
- **SOURCE_SYSTEM**: Platform analysis
- **CALL_DIRECTION**: Call type filtering
- **PRIMARY_ACCOUNT_NAME**: Customer-specific queries

### Good for Grouping/Aggregation

- **AE_ID**: Sales performance by rep
- **STAGE_NAME**: Pipeline analysis
- **CALL_SPOTLIGHT_TYPE**: Call categorization
- **SOURCE_SYSTEM**: Platform usage patterns
- **FORECAST_CATEGORY**: Revenue forecasting
- **PRIMARY_ACCOUNT_ID**: Account-level metrics

### Key Relationships

- **Primary Keys**: CALL_CONVERSATION_KEY, CALL_TRANSCRIPT_ROW_ID
- **Salesforce Links**: OPPORTUNITY_ID → STAGE_NAME, AMOUNT, FORECAST_CATEGORY
- **Account Relationships**: PRIMARY_ACCOUNT_ID ↔ PRIMARY_ACCOUNT_NAME
- **Time Series**: CALL_START_DATETIME enables temporal analysis

### Data Quality Considerations

- **PROVIDER_UNIQUE_ID** and **YEAR1_AMOUNT**: 100% null, avoid in queries
- **Call Spotlight fields**: ~10-17% nulls for AI-generated content
- **Salesforce fields**: ~15% nulls where calls aren't linked to opportunities
- **TRANSCRIPT_SENTENCES**: Core conversation data with minimal nulls (0.38%)

### LLM Training Optimization

- **TRANSCRIPT_SENTENCES**: Structured for conversation analysis with speaker attribution and timing
- Rich metadata for context including participant roles, company affiliations, and meeting outcomes
- Sentiment scoring and AI-generated summaries for training data classification

## Keywords

Sales calls, conversation transcripts, Gong, CRM integration, Salesforce, B2B sales, call analytics, sentiment analysis, LLM training data, meeting intelligence, sales pipeline, account management, conversation AI, deal tracking, customer interactions

## Table and Column Documentation

**Table Comment**: One line per call transcript from Gong with structured conversation content optimized for LLM training and analysis

**Column Comments**:

- **CALL_CONVERSATION_KEY**: Unique identifier for the conversation/call
- **CALL_TRANSCRIPT_ROW_ID**: Unique identifier for the transcript row
- **CALL_TITLE**: Title of the call
- **CALL_STATUS**: Current status of the call (e.g., completed, in progress)
- **CONVERSATION_ID**: Identifier for the conversation in Gong
- **CALL_DIRECTION**: Direction of the call (inbound, outbound)
- **CALL_END_DATETIME**: Planned end date and time for the call
- **AE_ID**: Identifier for the account executive/call owner
- **CALL_URL**: URL to access the call recording in Gong
- **CALL_DURATION**: Duration of the call in seconds (browser duration)
- **PRESENTATION_DURATION_SEC**: Duration of presentation/screen sharing in seconds
- **WEBCAM_OWNER_DURATION_SEC**: Duration of webcam usage by call owner in seconds
- **CALL_SPOTLIGHT_BRIEF**: Brief summary of the call spotlight from Gong
- **WEBCAM_NON_COMPANY_DURATION_SEC**: Duration of webcam usage by non-company participants in seconds
- **CALL_SPOTLIGHT_TYPE**: Type of call spotlight categorization from Gong
- **CALL_SPOTLIGHT_NEXT_STEPS**: Next steps identified from the call spotlight analysis
- **CALL_SPOTLIGHT_KEY_POINTS**: Key points extracted from the call spotlight analysis
- **QUESTION_COMPANY_COUNT**: Number of questions asked by company representatives during the call
- **QUESTION_NON_COMPANY_COUNT**: Number of questions asked by non-company participants during the call
- **SOURCE_SYSTEM**: Source system where the call originated
- **PROVIDER_UNIQUE_ID**: Unique identifier from the call provider system
- **OPPORTUNITY_ID**: Identifier for the associated opportunity from Salesforce
- **STAGE_NAME**: Current stage of the associated opportunity (e.g., Qualified, Proposal, Closed Won)
- **FORECAST_CATEGORY**: Forecast category classification of the opportunity
- **AMOUNT**: Total amount/value of the associated opportunity
- **YEAR1_AMOUNT**: Year 1 amount value of the associated opportunity
- **TRANSCRIPT_SENTENCES**: Array of JSON objects containing individual sentences with speaker information, timing, and metadata. Each sentence includes speaker_id, speaker_name, speaker_title, speaker_affiliation, topic, start_ms, end_ms, duration_ms, text, and sentence_order. Optimized for LLM training and conversation analysis.
