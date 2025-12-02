# Erk Slackbot

A Slack bot for managing Erk implementation plans directly from Slack.

## Features

- `/erk-plan` - Create plans from Slack messages
- `/erk-submit` - Submit plans to the Erk queue for automated implementation
- `/erk-plans` - List open plans

## Slack App Setup

### 1. Create a Slack App

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps)
2. Click **Create New App**
3. Choose **From scratch**
4. Enter app name (e.g., "Erk Bot") and select your workspace
5. Click **Create App**

### 2. Enable Socket Mode

Socket Mode allows the bot to receive events without exposing a public URL.

1. In the left sidebar, go to **Settings > Socket Mode**
2. Toggle **Enable Socket Mode** to ON
3. When prompted, create an App-Level Token:
   - Token Name: `erk-socket-token`
   - Scope: `connections:write`
   - Click **Generate**
4. **Copy and save this token** - this is your `SLACK_APP_TOKEN` (starts with `xapp-`)

### 3. Configure Bot Token Scopes

1. Go to **Features > OAuth & Permissions**
2. Scroll to **Scopes > Bot Token Scopes**
3. Add these scopes:
   - `chat:write` - Send messages
   - `commands` - Handle slash commands
   - `im:history` - Read DM history (for DM interactions)
   - `im:read` - View DMs
   - `im:write` - Send DMs
   - `channels:history` - Read channel messages (optional, for channel mentions)
   - `app_mentions:read` - Respond to @mentions

### 4. Create Slash Commands

1. Go to **Features > Slash Commands**
2. Click **Create New Command** for each:

| Command       | Request URL                   | Description                        |
| ------------- | ----------------------------- | ---------------------------------- |
| `/erk-plan`   | (leave blank for Socket Mode) | Create a plan from message content |
| `/erk-submit` | (leave blank for Socket Mode) | Submit a plan to the Erk queue     |
| `/erk-plans`  | (leave blank for Socket Mode) | List open plans                    |

For each command:

- Enter the command name
- Add a short description
- Leave Request URL blank (Socket Mode handles this)
- Click **Save**

### 5. Enable Events (for DM and Channel Interactions)

To respond to DMs and @mentions (not just slash commands):

1. Go to **Features > Event Subscriptions**
2. Toggle **Enable Events** to ON
3. Expand **Subscribe to bot events**
4. Add these events:
   - `message.im` - Messages in DMs with the bot
   - `app_mention` - When someone @mentions the bot in a channel

### 6. Install the App

1. Go to **Settings > Install App**
2. Click **Install to Workspace**
3. Review permissions and click **Allow**
4. **Copy the Bot User OAuth Token** - this is your `SLACK_BOT_TOKEN` (starts with `xoxb-`)

## Environment Variables

Set these environment variables before running the bot:

```bash
# Required: Bot User OAuth Token (from OAuth & Permissions page)
export SLACK_BOT_TOKEN="xoxb-your-bot-token"

# Required: App-Level Token (from Socket Mode page)
export SLACK_APP_TOKEN="xapp-your-app-token"

# Optional: Path to your git repository (defaults to current directory)
export ERK_REPO_PATH="/path/to/your/repo"
```

## Running the Bot

### Install Dependencies

```bash
# From the erk repository root
uv sync --extra slackbot
```

### Start the Bot

```bash
# From the erk repository root
uv run uvicorn slackbot.app:web_app --port 3000
```

Or with auto-reload for development:

```bash
uv run uvicorn slackbot.app:web_app --reload --port 3000
```

### Verify It's Running

- Visit http://localhost:3000/health - should return `{"status": "ok"}`
- The bot should show as online in Slack

## Usage

### Slash Commands

**Create a plan:**

```
/erk-plan # My Feature

## Goal
Implement a new feature that does X

## Steps
1. Create the data model
2. Add API endpoints
3. Build the UI
```

**Submit a plan to the queue:**

```
/erk-submit 123
```

**List open plans:**

```
/erk-plans
```

### DM Interactions

You can DM the bot directly. Send a message starting with a plan command:

- `plan: <content>` - Create a plan
- `submit: <issue_number>` - Submit a plan
- `list` or `plans` - List open plans

### Channel @Mentions

Mention the bot in any channel it's been added to:

```
@Erk Bot plan: # My Feature

## Goal
...
```

## Adding the Bot to Channels

1. Go to the channel where you want the bot
2. Click the channel name to open settings
3. Go to **Integrations > Apps**
4. Click **Add apps** and search for your bot
5. Click **Add**

Or use the Slack command:

```
/invite @Erk Bot
```

## Troubleshooting

### Bot not responding to slash commands

1. Check that Socket Mode is enabled
2. Verify both tokens are set correctly
3. Check the terminal for error messages
4. Ensure the bot is running (`/health` endpoint responds)

### Bot not responding to DMs or @mentions

1. Verify Event Subscriptions are enabled
2. Check that `message.im` and `app_mention` events are subscribed
3. Ensure the bot has required scopes (`im:history`, `app_mentions:read`)

### "not_authed" or "invalid_auth" errors

1. Regenerate your tokens in the Slack app settings
2. Make sure you're using the correct token types:
   - `SLACK_BOT_TOKEN` starts with `xoxb-`
   - `SLACK_APP_TOKEN` starts with `xapp-`

### GitHub API errors

1. Ensure `gh` CLI is installed and authenticated: `gh auth status`
2. Check that `ERK_REPO_PATH` points to a valid git repository
3. Verify you have permissions to create issues in the repository
