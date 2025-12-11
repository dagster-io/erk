---
columns:
  - BOT_ID (VARCHAR(16777216))
  - CHANNEL_ID (VARCHAR(16777216))
  - CREATED_AT (TIMESTAMP_NTZ(9))
  - CUSTOMER_ID (VARCHAR(16777216))
  - EVENT_ID (NUMBER(38,0))
  - EVENT_TIMESTAMP (TIMESTAMP_LTZ(9))
  - EVENT_TYPE (VARCHAR(16777216))
  - IS_BOT_USAGE (BOOLEAN)
  - IS_INTERNAL_WORKSPACE (BOOLEAN)
  - MESSAGE_LENGTH (NUMBER(38,0))
  - MESSAGE_TIMESTAMP (TIMESTAMP_LTZ(0))
  - METADATA (VARCHAR(16777216))
  - THREAD_TIMESTAMP (TIMESTAMP_LTZ(0))
  - TOKENS_USED (NUMBER(38,0))
  - USER_ID (VARCHAR(16777216))
schema_hash: 876961e441b8b513f7774a97fcd1f556c79953fdd660cca7b8c73b158f3b8529
---

# Table Analysis Summary: DWH_REPORTING.BUSINESS.COMPASS_EVENTS

## Overall Dataset Characteristics

**Total Rows:** 6,100

**General Data Quality:** The dataset shows good overall data quality with minimal null values in key identifier columns. The data represents events from a Compass analytics platform spanning from August to September 2025.

**Notable Patterns:**

- Events are distributed across 68 different customers and 87 channels
- High concentration of events around specific timestamps (2,119 unique event timestamps for 6,100 rows)
- Mixed internal/external workspace usage (both True and False values present)
- Token usage and message length data is available for approximately half of the records

## Column Details

### Primary Identifiers

- **EVENT_ID:** Sequential integer (1-6100), serves as primary key with 100% uniqueness
- **CUSTOMER_ID:** String identifier with 68 unique customers, follows naming pattern "\*-compass"
- **BOT_ID:** String identifier (70 unique values) following pattern "T[ID]-[customer]-compass"
- **CHANNEL_ID:** Slack-style channel IDs (87 unique values) starting with "C"
- **USER_ID:** Slack-style user IDs (140 unique values) starting with "U", 8.16% null

### Temporal Data

- **EVENT_TIMESTAMP:** Primary event time with timezone, 2,119 unique values (multiple events per timestamp)
- **CREATED_AT:** System creation timestamp, 100% unique (no timezone)
- **THREAD_TIMESTAMP:** Thread-level timestamp, 12.13% null, 1,341 unique values
- **MESSAGE_TIMESTAMP:** Message-level timestamp, 12.13% null, 2,625 unique values

### Event Classification

- **EVENT_TYPE:** 6 distinct types - new_conversation, new_reply, thumbs_down, thumbs_up, token_usage, user_joined_channel
- **IS_BOT_USAGE:** Boolean flag indicating bot interaction
- **IS_INTERNAL_WORKSPACE:** Boolean flag distinguishing internal vs external usage

### Metrics and Content

- **TOKENS_USED:** AI token consumption (0-7,040 range), 49.51% null - only populated for token_usage events
- **MESSAGE_LENGTH:** Character count (2-11,391 range), 55.21% null - extracted from metadata
- **METADATA:** JSON string with additional context, 55.21% null, 378 unique values

## Potential Query Considerations

### Good for Filtering:

- **CUSTOMER_ID:** Excellent for customer-specific analysis
- **EVENT_TYPE:** Essential for filtering by interaction types
- **IS_INTERNAL_WORKSPACE:** Clear internal/external segmentation
- **IS_BOT_USAGE:** Bot vs human interaction analysis
- **EVENT_TIMESTAMP:** Time-based filtering and analysis

### Good for Grouping/Aggregation:

- **CUSTOMER_ID:** Customer usage patterns
- **EVENT_TYPE:** Event type distribution analysis
- **CHANNEL_ID:** Channel activity analysis
- **BOT_ID:** Bot performance metrics
- **DATE functions on timestamps:** Time-series analysis

### Potential Join Keys:

- **EVENT_ID:** Primary key for joins with other event tables
- **CUSTOMER_ID:** Customer dimension joins
- **USER_ID:** User behavior analysis (note null values)
- **BOT_ID:** Bot configuration/metadata joins

### Data Quality Considerations:

- **USER_ID nulls (8.16%):** May indicate system events or anonymous interactions
- **METADATA/MESSAGE_LENGTH nulls (~55%):** Primarily for non-message events
- **TOKENS_USED nulls (~50%):** Only relevant for token_usage event types
- **Timestamp nulls (12.13%):** Thread and message timestamps missing for some event types

## Keywords

compass analytics, events, bot interactions, customer usage, token consumption, slack channels, conversation tracking, AI metrics, workspace analytics, message analysis

## Table and Column Documentation

### Table Comment

Business layer model for Compass analytics events that provides clean, transformed data from the compass_event_analytics staging model

### Column Comments

- **EVENT_ID:** Unique identifier for the compass event
- **EVENT_TYPE:** Type of event (e.g., message, interaction, response)
- **CHANNEL_ID:** Identifier for the communication channel where the event occurred
- **USER_ID:** Identifier for the user who interacted with the bot
- **BOT_ID:** Identifier for the AI bot that generated the event
- **METADATA:** JSON object containing additional event metadata and context
- **TOKENS_USED:** Number of AI tokens consumed for this event
- **MESSAGE_LENGTH:** Length of the message in characters, extracted from metadata
- **CREATED_AT:** Timestamp when the event record was created in the system
- **THREAD_TIMESTAMP:** Timestamp for the thread where the event occurred
- **MESSAGE_TIMESTAMP:** Timestamp when the message or event was created
