# Analytics Logging

The Slackbot includes comprehensive analytics logging to track bot usage and performance. The analytics functionality has been split into two separate components:

> **📋 Documentation Status**: This documentation has been updated to accurately reflect the current implementation. See the [Implementation Status](#implementation-status) section for details on what's currently available vs. planned features.

- **SlackbotKvStore**: Bot-specific key-value storage for conversation state and metadata
- **SlackbotAnalyticsStore**: Cross-bot analytics storage for tracking usage events

## Overview

Analytics events are automatically logged to a SQLite database and include:

- **New conversations**: When users start new threads with the bot
- **New replies**: When users send messages in existing threads
- **User joins**: When new users join channels where the bot is active
- **Token usage**: Total tokens consumed by the AI model
- **Thumbs up/down**: User feedback on bot responses

All analytics events now include enriched user information when available:

- **User real name**: Full name from Slack profile
- **Timezone**: User's timezone setting
- **Email**: User's email address (when available)

The system also includes automatic cleanup of old analytics data (older than 180 days) with probabilistic execution.

## Architecture

### SlackbotKvStore

Handles bot-specific data storage:

- Conversation state and metadata
- Thread tracking
- Bot-specific configuration

### SlackbotAnalyticsStore

Handles cross-bot analytics:

- Event logging for all bot interactions
- Token consumption tracking
- Automatic cleanup of old data (180+ days)
- Raw analytics data export

## Database Schema

The analytics data is stored in a SQLite table with the following structure:

```sql
CREATE TABLE analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    channel_id TEXT,
    user_id TEXT,
    thread_ts TEXT,
    message_ts TEXT,
    metadata TEXT,
    tokens_used INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Event Types

### NEW_CONVERSATION

Logged when a user starts a new conversation with the bot (mentions the bot in a new thread).

**Fields:**

- `channel_id`: The Slack channel ID
- `user_id`: The user who started the conversation
- `thread_ts`: The thread timestamp
- `message_ts`: The message timestamp
- `metadata`: JSON string with metadata including:
  - `message_length`: Length of the user message
  - `user_info`: Enriched user information (real name, timezone, email)
  - `user_metadata`: User attributes (admin status, bot status, deleted status, etc.)
  - `conversation_context`: Thread context (bot-initiated, cron job, continuation status, etc.)
  - `bot_metadata`: Bot configuration details (bot type, organization info, etc.)

### NEW_REPLY

Logged when a user sends a message in an existing thread where the bot has already responded.

**Fields:**

- `channel_id`: The Slack channel ID
- `user_id`: The user who sent the reply
- `thread_ts`: The thread timestamp
- `message_ts`: The message timestamp
- `metadata`: JSON string with metadata including:
  - `message_length`: Length of the user message
  - `user_info`: Enriched user information (real name, timezone, email)
  - `user_metadata`: User attributes (admin status, bot status, deleted status, etc.)
  - `conversation_context`: Thread context (continuation, bot-initiated, cron job, etc.)
  - `bot_metadata`: Bot configuration details (bot type, organization info, etc.)

### USER_JOINED_CHANNEL

Logged when a new user joins a channel where the bot is active.

**Fields:**

- `channel_id`: The Slack channel ID
- `user_id`: The user who joined the channel
- `metadata`: JSON string with enriched user information (when available)
  - `user_info`: User details
    - `real_name`: User's full name from Slack
    - `timezone`: User's timezone setting
    - `email`: User's email address

### TOKEN_USAGE

Logged after each AI model interaction with comprehensive token usage including cache tokens.

**Fields:**

- `channel_id`: The Slack channel ID
- `user_id`: The user who initiated the interaction
- `thread_ts`: The thread timestamp
- `message_ts`: The message timestamp
- `tokens_used`: Total tokens consumed (including all token types)
- `metadata`: JSON string with comprehensive token usage details:
  - `input_tokens`: Regular input tokens consumed
  - `output_tokens`: Generated output tokens
  - `cache_creation_input_tokens`: Tokens used to create cache entries
  - `cache_read_input_tokens`: Tokens read from existing cache
  - `total_tokens`: Total tokens (input + output + cache creation + cache read)
  - `cache_creation` (optional): Cache creation breakdown by TTL:
    - `ephemeral_5m_input_tokens`: 5-minute cache entries
    - `ephemeral_1h_input_tokens`: 1-hour cache entries
  - `service_tier` (optional): Service tier used (standard, priority, batch)
  - `server_tool_use` (optional): Server-side tool usage:
    - `web_search_requests`: Number of web search requests made

### THUMBS_UP / THUMBS_DOWN

Logged when users react to bot responses with thumbs up or thumbs down feedback.

**Fields:**

- `channel_id`: The Slack channel ID
- `user_id`: The user who provided feedback
- `thread_ts`: The thread timestamp
- `message_ts`: The message timestamp that received feedback
- `metadata`: JSON string with enriched user information (when available)
  - `user_info`: User details
    - `real_name`: User's full name from Slack
    - `timezone`: User's timezone setting
    - `email`: User's email address

## Onboarding Events

### ORGANIZATION_CREATED

Logged when a new organization is created during the onboarding process.

**Fields:**

- `metadata`: JSON string with organization details
  - `organization_id`: The database ID of the created organization
  - `organization_name`: Name of the organization
  - `organization_industry`: Industry classification
  - `referral_token`: The referral token used for signup

### GOVERNANCE_CHANNEL_CREATED

Logged when a governance channel is successfully created during onboarding.

**Fields:**

- `channel_id`: The Slack channel ID of the governance channel
- `metadata`: JSON string with setup details
  - `organization_id`: The organization ID
  - `channel_name`: Name of the governance channel
  - `team_id`: Slack team/workspace ID
  - `contextstore_repo`: Associated GitHub repository name

### FIRST_DATASET_SYNC

Logged when the first dataset synchronization completes successfully.

**Fields:**

- `channel_id`: The governance channel ID
- `metadata`: JSON string with sync details
  - `connection_name`: Name of the connection used
  - `table_count`: Number of tables/datasets processed
  - `sync_duration_seconds`: Time taken for the sync
  - `pr_url`: GitHub pull request URL for the dataset updates
  - `is_first_sync`: Boolean flag (always true for this event)

### ADDITIONAL_CHANNEL_CREATED

Logged when additional channels are created after the initial setup.

**Fields:**

- `channel_id`: The new channel ID
- `user_id`: The user who created the channel
- `metadata`: JSON string with channel details
  - `channel_name`: Name of the new channel
  - `organization_id`: The organization ID
  - `governance_channel`: Associated governance channel
  - `channel_order`: Sequential number of this channel for the organization

## Admin and Setup Events

### ADMIN_COMMAND_USED

Logged when admin commands are executed (e.g., !admin).

**Fields:**

- `channel_id`: The channel where the command was used
- `user_id`: The user who executed the command
- `metadata`: JSON string with command details
  - `command_type`: Type of admin command used
  - `action_taken`: Specific action performed
  - `is_first_use`: Whether this is the user's first admin command

### CONNECTION_MANAGEMENT_ACCESSED

Logged when users access the connection management interface.

**Fields:**

- `channel_id`: The governance channel ID
- `user_id`: The user accessing the interface
- `metadata`: JSON string with access details
  - `access_method`: How the interface was accessed (button, URL, etc.)
  - `organization_id`: The organization ID

### CONTEXTSTORE_REPO_CREATED

Logged when a GitHub context store repository is created.

**Fields:**

- `metadata`: JSON string with repository details
  - `repo_name`: Name of the created repository
  - `repo_url`: GitHub URL of the repository
  - `organization_id`: The organization ID
  - `user_email`: Email of the user added as collaborator

### SLACK_CONNECT_INVITE_SENT

Logged when Slack Connect invites are sent to users.

**Fields:**

- `channel_id`: The channel for which the invite was sent
- `user_id`: The user who received the invite (if known)
- `metadata`: JSON string with invite details
  - `invite_type`: Type of invite (governance, main_channel, etc.)
  - `organization_id`: The organization ID
  - `is_first_invite`: Whether this is the first invite for this user

## User Engagement Events

### FIRST_SUCCESSFUL_QUERY

Logged when a user successfully gets their first AI response from the bot.

**Fields:**

- `channel_id`: The channel where the query occurred
- `user_id`: The user who made the query
- `thread_ts`: The thread timestamp
- `message_ts`: The message timestamp
- `tokens_used`: Tokens consumed for the response
- `metadata`: JSON string with query details
  - `query_length`: Length of the user's query
  - `response_time_ms`: Time taken to generate response
  - `connection_used`: Data connection used (if any)
  - `is_first_query`: Boolean flag (always true for this event)

### WELCOME_MESSAGE_SENT

Logged when welcome messages are sent to users joining channels.

**Fields:**

- `channel_id`: The channel where the welcome was sent
- `user_id`: The user who received the welcome
- `metadata`: JSON string with welcome details
  - `welcome_type`: Type of welcome (new_member, governance, etc.)
  - `message_length`: Length of the welcome message
  - `has_setup_buttons`: Whether setup buttons were included

### GOVERNANCE_WELCOME_SENT

Logged when governance-specific welcome messages are sent.

**Fields:**

- `channel_id`: The governance channel ID
- `user_id`: The user who received the welcome
- `metadata`: JSON string with governance welcome details
  - `has_connections`: Whether warehouse connections exist
  - `connection_count`: Number of existing connections
  - `setup_buttons_shown`: List of setup buttons displayed

### CONNECTION_SETUP_SUCCEEDED

Logged when a data warehouse connection is successfully established and datasets are synced. Use `is_first_sync: true` to identify the first connection for an organization.

**Fields:**

- `channel_id`: The governance channel ID
- `metadata`: JSON string with connection success details
  - `connection_name`: Name of the connection
  - `connection_type`: Type of warehouse (e.g., "snowflake", "bigquery", "redshift")
  - `table_count`: Number of tables/datasets successfully synced
  - `organization_id`: The organization ID
  - `sync_duration_seconds`: Time taken for the dataset sync process
  - `is_first_sync`: Whether this was the organization's first connection setup
  - `pr_url`: GitHub pull request URL for the dataset updates

### COWORKER_INVITED

Logged when coworkers are invited to join channels via Slack Connect or other invitation methods.

**Fields:**

- `channel_id`: The channel for which the invite was sent
- `user_id`: The user who received the invite (if known)
- `metadata`: JSON string with invite details
  - `invite_type`: Type of invite (slack_connect_governance_channel, slack_connect_main_channel, etc.)
  - `organization_id`: The organization ID
  - `invited_email`: Email of the invited user (when available)
  - `invite_method`: Method of invitation (email, user_id, etc.)
  - `is_onboarding`: Whether this was part of the onboarding process
  - `is_first_dataset_sync`: Whether this was triggered by the first dataset sync

### SLACK_MODAL_INTERACTION

Logged when users interact with Slack modals (replaces the more specific MODAL_SUBMITTED event).

**Fields:**

- `channel_id`: The channel where the modal interaction occurred
- `user_id`: The user who interacted with the modal
- `thread_ts`: The thread timestamp (if applicable)
- `message_ts`: The message timestamp (if applicable)
- `metadata`: JSON string with interaction details
  - `modal_type`: Type of modal (connection_management, dataset_addition, etc.)
  - `action_taken`: Specific action performed in the modal
  - `organization_id`: The organization ID
  - `interaction_type`: Type of interaction (submit, cancel, etc.)

## Usage

### Getting Raw Analytics Data

The primary method for accessing analytics data:

```python
from csbot.slackbot.storage.sqlite import create_sqlite_connection_factory
from csbot.slackbot.slackbot_analytics import SlackbotAnalyticsStore

# Connect to the database
sql_conn_factory = create_sqlite_connection_factory("path/to/slackbot.db")
analytics_store = SlackbotAnalyticsStore(sql_conn_factory)

# Get all analytics data for the last 30 days
data = await analytics_store.get_analytics_data(days=30)

for record in data:
    event_type = record['event_type']
    user_id = record['user_id']
    tokens_used = record['tokens_used']

    # Access enriched user information if available
    user_info = record.get('user_info')
    if user_info:
        real_name = user_info.get('real_name', 'Unknown')
        timezone = user_info.get('timezone', 'Unknown')
        print(f"Event: {event_type}, User: {real_name} ({timezone}), Tokens: {tokens_used}")
    else:
        print(f"Event: {event_type}, User ID: {user_id}, Tokens: {tokens_used}")
```

### Logging Analytics Events

Analytics events are automatically logged by the bot, but you can also log custom events:

```python
# Log a custom analytics event (basic)
await analytics_store.log_analytics_event(
    bot_id="your_bot_id",
    event_type=AnalyticsEventType.NEW_CONVERSATION,
    channel_id="C1234567890",
    user_id="U1234567890",
    thread_ts="1234567890.123456",
    message_ts="1234567890.123456",
    metadata={"message_length": 42},
    tokens_used=150
)

# Log analytics event with enriched user information (recommended)
await analytics_store.log_analytics_event_with_enriched_user(
    bot_id="your_bot_id",
    event_type=AnalyticsEventType.NEW_CONVERSATION,
    channel_id="C1234567890",
    user_id="U1234567890",
    thread_ts="1234567890.123456",
    message_ts="1234567890.123456",
    metadata={"message_length": 42},
    tokens_used=150,
    enriched_person=enriched_person,  # EnrichedPerson object
    user_email="user@example.com"
)
```

### Accessing Enriched User Information

The enhanced analytics system automatically enriches user data and stores it in the `metadata` field. When retrieving analytics data, user information is extracted and made available in the `user_info` field:

```python
# Get analytics data with enriched user information
data = await analytics_store.get_analytics_data(days=30)

for record in data:
    user_info = record.get('user_info')
    if user_info:
        print(f"User: {user_info.get('real_name')}")
        print(f"Timezone: {user_info.get('timezone')}")
        print(f"Email: {user_info.get('email')}")
```

## Implementation Status

### ✅ Currently Implemented

- **Basic event logging**: NEW_CONVERSATION, NEW_REPLY, TOKEN_USAGE, USER_JOINED_CHANNEL, etc.
- **User information**: Real name, timezone, email from Slack profiles
- **User metadata**: Admin status, owner status, bot status, account deletion status
- **Conversation context**: Bot-initiated threads, cron job detection, thread continuation
- **Bot metadata**: Bot type, organization info, team/channel info
- **Token tracking**: Input/output token counts for cost monitoring
- **Automatic cleanup**: Data older than 180 days is automatically removed
- **CLI export**: Export analytics data to CSV format

### ⚠️ Documented but Not Yet Implemented

- **Channel metadata**: Channel name, privacy settings, member count, topic, purpose
- **Message analysis**: Word count, mentions detection, link analysis, code blocks
- **Performance metrics**: Response time tracking and categorization
- **Timestamp metadata**: Business hours detection, weekend analysis
- **Enhanced TOKEN_USAGE**: User context and performance metrics in token events

## Comprehensive Metadata Reference

The analytics system captures the following metadata for each event:

### User Information (`user_info`)

- `real_name`: User's full name from Slack profile
- `timezone`: User's timezone setting
- `email`: User's email address

### User Metadata (`user_metadata`)

- `is_admin`: Whether user is workspace admin
- `is_owner`: Whether user is workspace owner
- `is_bot`: Whether user is a bot account
- `deleted`: Whether user account is deleted
- `is_restricted`: Whether user is restricted (optional)
- `is_ultra_restricted`: Whether user is ultra restricted (optional)

### Channel Metadata (`channel_metadata`) - NOT YET IMPLEMENTED

_This feature is documented but not yet implemented. Channel metadata would include channel name, privacy settings, member count, etc._

### Message Analysis (`message_analysis`) - NOT YET IMPLEMENTED

_This feature is documented but not yet implemented. Message analysis would include word count, mentions detection, link analysis, etc._

### Performance Metrics (`performance`) - NOT YET IMPLEMENTED

_This feature is documented but not yet implemented. Performance metrics would include response times and categorization._

### Conversation Context (`conversation_context`)

- `is_thread_continuation`: Whether this continues an existing thread
- `is_bot_initiated`: Whether thread was started by the bot
- `is_cron_job`: Whether this is an automated cron job thread
- `cron_job_name`: Name of the cron job (if applicable)

### Bot Metadata (`bot_metadata`)

- `bot_type`: Type of bot instance (BotTypeQA, BotTypeGovernance, etc.)
- `channel_name`: Bot's primary channel name
- `team_id`: Slack team/workspace ID
- `governance_alerts_channel`: Governance alerts channel name (optional)
- `has_github_monitor`: Whether GitHub monitoring is enabled
- `organization_name`: Organization name (optional)
- `organization_id`: Organization ID as string (optional)

### Token Usage Specific (`TOKEN_USAGE` events only)

- `input_tokens`: Tokens consumed for input
- `output_tokens`: Tokens generated for output
- `total_tokens`: Total tokens (input + output)

### Data Cleanup

The system automatically cleans up old analytics data:

```python
# Manually trigger cleanup of data older than 180 days
await analytics_store.cleanup_old_analytics()
```

### Example Queries

```sql
-- Get total tokens used in the last 7 days
SELECT SUM(tokens_used)
FROM analytics
WHERE bot_id = 'your_bot_id'
  AND created_at >= datetime('now', '-7 days')
  AND tokens_used IS NOT NULL;

-- Get unique users in the last 30 days
SELECT COUNT(DISTINCT user_id)
FROM analytics
WHERE bot_id = 'your_bot_id'
  AND created_at >= datetime('now', '-30 days')
  AND user_id IS NOT NULL;

-- Get event counts by type
SELECT event_type, COUNT(*)
FROM analytics
WHERE bot_id = 'your_bot_id'
  AND created_at >= datetime('now', '-30 days')
GROUP BY event_type;

-- Get analytics across all bots
SELECT bot_id, COUNT(*) as events, SUM(tokens_used) as total_tokens
FROM analytics
WHERE created_at >= datetime('now', '-30 days')
GROUP BY bot_id;

-- Get user activity with enriched information (requires JSON extraction)
SELECT
    user_id,
    json_extract(metadata, '$.user_info.real_name') as real_name,
    COUNT(*) as interactions,
    SUM(tokens_used) as total_tokens
FROM analytics
WHERE bot_id = 'your_bot_id'
  AND created_at >= datetime('now', '-30 days')
  AND user_id IS NOT NULL
  AND json_extract(metadata, '$.user_info') IS NOT NULL
GROUP BY user_id, real_name
ORDER BY interactions DESC;

-- Get user engagement by timezone
SELECT
    json_extract(metadata, '$.user_info.timezone') as timezone,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(*) as total_interactions,
    AVG(tokens_used) as avg_tokens_per_interaction
FROM analytics
WHERE bot_id = 'your_bot_id'
  AND created_at >= datetime('now', '-30 days')
  AND event_type IN ('new_conversation', 'new_reply')
  AND json_extract(metadata, '$.user_info.timezone') IS NOT NULL
GROUP BY timezone
ORDER BY unique_users DESC;

-- Token usage analysis
SELECT
    AVG(json_extract(metadata, '$.input_tokens')) as avg_input_tokens,
    AVG(json_extract(metadata, '$.output_tokens')) as avg_output_tokens,
    AVG(tokens_used) as avg_total_tokens
FROM analytics
WHERE bot_id = 'your_bot_id'
  AND event_type = 'token_usage'
  AND created_at >= datetime('now', '-7 days')
  AND tokens_used IS NOT NULL;

-- Bot type activity analysis
SELECT
    json_extract(metadata, '$.bot_metadata.bot_type') as bot_type,
    json_extract(metadata, '$.bot_metadata.organization_name') as organization_name,
    COUNT(*) as total_messages,
    COUNT(DISTINCT user_id) as unique_users,
    AVG(json_extract(metadata, '$.message_length')) as avg_message_length
FROM analytics
WHERE bot_id = 'your_bot_id'
  AND event_type IN ('new_conversation', 'new_reply')
  AND created_at >= datetime('now', '-30 days')
  AND json_extract(metadata, '$.bot_metadata.bot_type') IS NOT NULL
GROUP BY bot_type, organization_name
ORDER BY total_messages DESC;

-- Conversation context analysis
SELECT
    json_extract(metadata, '$.conversation_context.is_bot_initiated') as is_bot_initiated,
    json_extract(metadata, '$.conversation_context.is_cron_job') as is_cron_job,
    COUNT(*) as message_count,
    AVG(json_extract(metadata, '$.message_length')) as avg_message_length,
    COUNT(DISTINCT user_id) as unique_users
FROM analytics
WHERE bot_id = 'your_bot_id'
  AND event_type IN ('new_conversation', 'new_reply')
  AND created_at >= datetime('now', '-30 days')
  AND json_extract(metadata, '$.conversation_context') IS NOT NULL
GROUP BY is_bot_initiated, is_cron_job
ORDER BY message_count DESC;

-- Message length analysis
SELECT
    CASE
        WHEN json_extract(metadata, '$.message_length') < 50 THEN 'Short'
        WHEN json_extract(metadata, '$.message_length') < 200 THEN 'Medium'
        ELSE 'Long'
    END as message_length_category,
    COUNT(*) as message_count,
    AVG(tokens_used) as avg_tokens_used,
    AVG(json_extract(metadata, '$.message_length')) as avg_char_length
FROM analytics
WHERE bot_id = 'your_bot_id'
  AND event_type IN ('new_conversation', 'new_reply')
  AND created_at >= datetime('now', '-30 days')
  AND json_extract(metadata, '$.message_length') IS NOT NULL
GROUP BY message_length_category
ORDER BY message_count DESC;

-- User admin/owner activity patterns
SELECT
    json_extract(metadata, '$.user_metadata.is_admin') as is_admin,
    json_extract(metadata, '$.user_metadata.is_owner') as is_owner,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(*) as total_interactions,
    AVG(tokens_used) as avg_tokens,
    AVG(json_extract(metadata, '$.message_length')) as avg_message_length
FROM analytics
WHERE bot_id = 'your_bot_id'
  AND event_type IN ('new_conversation', 'new_reply')
  AND created_at >= datetime('now', '-30 days')
  AND json_extract(metadata, '$.user_metadata') IS NOT NULL
GROUP BY is_admin, is_owner
ORDER BY total_interactions DESC;
```

## CLI Export

Use the CLI to export analytics data to CSV:

```bash
# Export analytics data to CSV
slackbot export-analytics \
  --config path/to/config.yaml \
  --output analytics.csv \
  --days 30

# Export last 7 days
slackbot export-analytics \
  --config path/to/config.yaml \
  --output analytics.csv \
  --days 7
```

This will create:

- `analytics.csv`: Raw analytics data with all fields (id, bot_id, event_type, channel_id, user_id, thread_ts, message_ts, metadata, tokens_used, created_at)

## Configuration

The analytics database is automatically created when the bot starts. The database is configured in your bot configuration:

```yaml
database_uri: "sqlite://./slackbot.db" # SQLite file path
# Or for PostgreSQL:
# database_uri: "postgresql://user:password@host:port/database"
```

## Privacy Considerations

- User IDs are stored as provided by Slack
- Channel IDs are stored for analytics purposes
- Message content is not stored, only metadata about message length
- Token usage is tracked for cost monitoring
- **Enhanced user information** is collected and stored including:
  - Real names from Slack profiles
  - Email addresses from Slack profiles
  - Timezone information
- User enrichment data is cached for 30 days to minimize API calls
- All data is stored locally in SQLite or PostgreSQL
- Data older than 180 days is automatically cleaned up

## Performance

- Analytics logging is asynchronous and non-blocking
- Database operations are optimized with appropriate indexes
- Token usage tracking is integrated into the streaming response pipeline
- Minimal overhead on bot performance
- Automatic cleanup runs probabilistically (1% chance per analytics log) to maintain database size
- Data older than 180 days is automatically removed during cleanup
