# Slack App Setup

1. Create a new app

- Go to `https://api.slack.com/apps`
- Click `Create New App` -> `From scratch`
- Pick your dev workspace

2. Configure bot token scopes

- Open `OAuth & Permissions`
- Add these **Bot Token Scopes**:
  - `app_mentions:read`
  - `chat:write`
  - `channels:history`
  - `groups:history`
  - `im:history`
  - `mpim:history`
  - `reactions:write`

3. Enable Socket Mode

- Open `Socket Mode`
- Enable `Socket Mode`
- Create an app-level token with scope `connections:write`
- Save the app token (`xapp-...`)

4. Enable Event Subscriptions

- Open `Event Subscriptions`
- Enable `Enable Events`
- Under `Subscribe to bot events`, add `app_mention`
- Save changes

5. Install app to workspace

- Open `Install App`
- Click `Install to Workspace`
- Copy the bot token (`xoxb-...`)
- If you add/change scopes later, reinstall the app

6. Invite bot to a channel

- In Slack, open a test channel and run `/invite @your-bot-name`
