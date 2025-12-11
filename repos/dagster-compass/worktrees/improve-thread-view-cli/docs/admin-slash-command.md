# Compass Admin Slash Command

The `/compass-admin` (production) and `/staging-compass-admin` (staging) slash commands provide administrative functionality for the Compass bot system through Slack's modal interface.

## Overview

The Compass admin slash command is a Slack-integrated administrative interface that allows authorized users to:

- Add and manage warehouse connections
- Add or update datasets
- Access billing management
- Trigger governance workflows with automated PR creation

## Command Variants

- **Production**: `/compass-admin`
- **Staging**: `/staging-compass-admin`
- **Local Development**: `/staging-compass-admin` (uses staging configuration)

## Critical Requirements

### ⚠️ Governance Channel Restriction

The slash command **ONLY works in registered governance channels**. It will **NOT work** in:

- Direct messages (DMs)
- Random Slack channels
- Personal conversations
- Any channel not configured as a governance channel

### Channel Configuration

The governance channel is specified in the bot configuration file:

```yaml
# Example from local.csbot.config.yaml
bots:
  - channel_name: "#dagster-compass-dev"
    governance_alerts_channel: "#dagster-compass-dev" # This is the governance channel
```

## How It Works

### 1. Command Routing

- User types `/compass-admin` in a Slack channel
- Bot server receives the slash command via webhook
- System looks up the channel in `bots_by_governance_channel` registry
- If channel is not a registered governance channel, returns error

### 2. Permission Validation

```python
# From bot_server.py:200
bot = self.bots_by_governance_channel.get(bot_key)
if not bot:
    await send_ephemeral_message(
        payload["response_url"],
        "❌ This command can only be run from a Compass governance channel."
    )
```

### 3. Modal Interface

If validation passes, opens a modal with admin options:

- 🔗 Add warehouse connection
- 📊 Add or update dataset
- 💳 Manage billing

## Setup Instructions

### For Local Development

1. **Ensure bot is running**:

   ```bash
   slackbot start --config local.csbot.config.yaml
   ```

2. **Identify your governance channel**:

   ```bash
   grep governance_alerts_channel local.csbot.config.yaml
   ```

3. **Go to the governance channel** (typically `#dagster-compass-dev`)

4. **Invite the bot** to the channel if not already present

5. **Run the command** in that channel:
   ```
   /staging-compass-admin
   ```

### For Production

1. **Navigate to your production governance channel**
2. **Run**: `/compass-admin`

## Troubleshooting

### Common Issues

| Issue                                                            | Cause                                  | Solution                                                |
| ---------------------------------------------------------------- | -------------------------------------- | ------------------------------------------------------- |
| "This command can only be run from a Compass governance channel" | Running in wrong channel               | Use the governance channel specified in config          |
| Command not found                                                | Bot not installed or wrong environment | Verify bot installation and use correct command variant |
| No response                                                      | Bot not running                        | Start the slackbot service                              |
| Modal doesn't open                                               | Permissions or configuration issue     | Check bot permissions and configuration                 |

### Debugging Steps

1. **Verify channel configuration**:

   ```bash
   # Check which channel is configured as governance
   grep -A 5 -B 5 governance_alerts_channel *.csbot.config.yaml
   ```

2. **Check bot status**:

   ```bash
   # Ensure slackbot is running
   ps aux | grep slackbot
   ```

3. **Verify bot is in channel**:
   - Look for the bot in the channel member list
   - Try mentioning the bot: `@compass`

4. **Check logs** for specific error messages when running the command

### Configuration Examples

#### Local Development

```yaml
# local.csbot.config.yaml
bots:
  - channel_name: "#dagster-compass-dev"
    governance_alerts_channel: "#dagster-compass-dev"
```

#### Production

```yaml
# prod.csbot.config.yaml
bots:
  - channel_name: "#compass-main"
    governance_alerts_channel: "#compass-governance"
```

## Architecture Notes

### Code Locations

- **Slash command handler**: `src/csbot/slackbot/bot_server/bot_server.py:191`
- **Admin command logic**: `src/csbot/slackbot/admin_commands.py`
- **Channel bot integration**: `src/csbot/slackbot/channel_bot/bot.py:1884`

### Security Design

- **Channel-based permissions**: Only works in configured governance channels
- **JWT token validation**: Connection management URLs use secure tokens
- **Audit trail**: All actions logged to governance channels
- **Team visibility**: Admin actions visible to team members in governance channels

### Bot Registration

The bot maintains two registries:

- `bots`: Regular bot channels
- `bots_by_governance_channel`: Governance channels (used for admin commands)

## Feature Details

### Connection Management

- Opens JWT-secured web interface
- Allows adding warehouse connections (Snowflake, BigQuery, etc.)
- Redirects to connection setup flows

### Dataset Management

- Modal form for adding/updating datasets
- Validates connection selection and dataset names
- Creates GitHub PRs for dataset changes
- Posts progress to governance channel threads

### Billing Management

- Provides access to billing portal
- Secure URL generation with JWT tokens

## Error Messages

| Message                                                              | Meaning             | Action                 |
| -------------------------------------------------------------------- | ------------------- | ---------------------- |
| "❌ This command can only be run from a Compass governance channel." | Wrong channel       | Use governance channel |
| "Missing token parameter"                                            | Configuration issue | Check bot setup        |
| "No bot server found"                                                | Service not running | Start slackbot service |

---

**Key Takeaway**: The admin slash command is designed for controlled governance workflows and will only function in specifically configured governance channels, never in DMs or arbitrary channels.
