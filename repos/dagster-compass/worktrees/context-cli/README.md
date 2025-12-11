# Compass

Compass is a multi-surface data analysis platform that powers Slack bots, contextual document search, and administrative tooling built on the csbot client and context store.

## Getting Started

### 1. Prerequisites

- **uv** package manager (https://docs.astral.sh/uv/) installed and available on your `PATH`.
- A new Slack app to host the local Compass bot.

Compass runs locally against an ephemeral SQLite database and a fake DuckDB warehouse, so no additional infrastructure is required.

### 2. Install Python Dependencies

Run the editable install once, and only repeat the dev install when you change `pyproject.toml`:

```bash
uv sync
uv sync --group dev
```

Install Temporal:

```bash
brew install temporal
```

### 3. Verify the Toolchain

Before launching the bot, run the quality gates and test suite:

```bash
make pyright
make ruff
make test
```

### 4. Configure Environment Variables

Create a `.env` file at the repository root (or export the variables in your shell) and populate it with sample credentials. Replace placeholder values with the real secrets from 1Password or the Slack/GitHub portals when you have them:

Your `.env` file should look like this:

```env
SLACK_APP_TOKEN=xapp-...
SLACK_BOT_TOKEN=xoxb-...
ANTHROPIC_API_KEY=...
GITHUB_TOKEN=<create one at https://github.com/settings/tokens/new>
SLACK_ADMIN_TOKEN=foo
COMPASS_DEV_TOOLS_BOT_TOKEN=bar
OPENAI_API_KEY=temp
STRIPE_TOKEN=...
STRIPE_PUBLISHABLE_KEY=...
STRIPE_SANDBOX_TEST_TOKEN=...
JWT_SECRET=foo
PROSPECTOR_DATA_BQ_JSON=...
```

How to get credentials from different services:

- Slack app tokens (required for local bot):
  1. Create a new Slack app in your workspace (dagsterlabs): `https://api.slack.com/apps`
  1. Import the Compass manifest from `infra/slack_bot_manifests/<your_name>_local_dev_manifest.json` (or another manifest in that directory) via the Slack App Manifest workflow
  1. After installation, copy issued tokens to your `.env` using the names below
- Quick links to obtain credentials:
  - SLACK_APP_TOKEN: `https://api.slack.com/apps` → your app → Basic Information → App-Level Tokens (create with `connections:write`)
  - SLACK_BOT_TOKEN: `https://api.slack.com/apps` → your app → OAuth & Permissions → Install App (Bot User OAuth Token). May need to add a Slack workspace admin (e.g. yuhan) as a collaborator and ask them to install it for you.
  - SLACK_ADMIN_TOKEN: can be found in 1password in the "Compass shared env vars" secured note
  - COMPASS_DEV_TOOLS_BOT_TOKEN: can be found in 1password in the "Compass shared env vars" secured note
  - ANTHROPIC_API_KEY: `https://console.anthropic.com/account/keys`
  - OPENAI_API_KEY: `https://platform.openai.com/api-keys`
  - GITHUB_TOKEN: `https://github.com/settings/tokens/new`
  - STRIPE_TOKEN / STRIPE_PUBLISHABLE_KEY / STRIPE_SANDBOX_TEST_TOKEN: can be found in 1password in the "Compass shared env vars" secured note
  - JWT_SECRET: generate locally, e.g. `openssl rand -base64 32`
  - PROSPECTOR_DATA_BQ_JSON: can be shared via 1password upon request

Keep these values outside of source control—commit your code without `.env` and use a password manager to store production credentials.

`make test` executes `uv run pytest -n auto packages/csbot/tests/` to validate both unit and integration tests.

#### End-to-End Testing with Video Recording

For debugging E2E test failures, you can enable video recording of Playwright browser interactions:

```bash
# Run E2E tests with video recording enabled
COMPASS_E2E_TESTS=1 COMPASS_RECORD_VIDEO=1 uv run pytest -n auto -v packages/csbot/tests/webapp/onboarding/

# Videos will be saved to test-videos/ directory with descriptive names like:
# test_complete_onboarding_flow_with_form_submission_video-20.webm
```

**Environment Variables for E2E Testing:**

- `COMPASS_E2E_TESTS=1`: Enables E2E tests (required)
- `COMPASS_RECORD_VIDEO=1`: Enables video recording of browser interactions (optional)
- `COMPASS_E2E_CI=1`: Sets longer timeouts for CI environments (optional)

Video recording is automatically enabled in GitHub Actions when E2E tests run on the master branch or when PR/commit titles contain 'RUN_E2E'.

### 5. Run the Slack Bot Locally

Start the bot once your environment is configured:

```bash
uv run slackbot start --config=local.csbot.config.yaml
```

**Tip**: To run everything together in one command:

```bash
uv run compass-dev local-dev --config=local.csbot.config.yaml
```

This will start:

- The Slack bot
- The admin panel on `http://localhost:8080`
- Temporal development server on `localhost:7233`
- Temporal worker with the DummyWorkflow registered

You will need to be added to the [dagster-compass GH context repo](https://github.com/dagster-compass) for the default seed data to work.

For other environments use the corresponding config files (for example, `uv run slackbot start --config=staging.csbot.config.yaml`).

There may be different scenarios to test locally.

#### Scenario 1: Compass App in Dagster Labs Slack

This scenario simulates the Compass bot running in the Dagster Labs workspace with standard bot configuration.

- **Configuration file**: `local.csbot.config.yaml`
- **Seed data**: `seed_data/dagsterlabs_slack`
- **Slack app**: Standard workspace app (not enterprise grid)
  - **Default slack channel**: [#dagster-compass-dev](https://dagsterlabs.slack.com/archives/C098WPHD1BL)
  - **Default governance channel**: [#dagster-compass-dev-governance](https://dagsterlabs.slack.com/archives/C09BJTK72KV)
  - **Default stripe plan**: https://dashboard.stripe.com/acct_1S0rBN4IQUdrBZhC/test/subscriptions/sub_1SDvOF4IQUdrBZhCUO9UfIYO

**Setup**:

1. Create a Slack app and [Configure Environment Variables](#4-configure-environment-variables)
2. Start the services:

   ```bash
   # Option 1: Start everything together (recommended - includes Temporal)
   uv run compass-dev local-dev --config=local.csbot.config.yaml

   # Option 2: Start bot only
   uv run slackbot start --config=local.csbot.config.yaml
   ```

3. Note: you can configure the channels, bot instances, connections, etc, in `seed_data/dagsterlabs_slack` folder.

**What this tests**:

- Standard bot interactions in a workspace
- Database operations with pre-seeded Dagster Labs data
- Basic Slack API functionality
- Bot configuration without onboarding features

#### Scenario 2: New Organization Onboarding in Enterprise Grid Slack

This scenario tests the complete new customer onboarding flow, simulating what happens when a new organization signs up for Compass.

- **Configuration**: Use local configuration patterns from `local-with-onboarding.csbot.config.yaml` as reference
- **Database**: Fresh SQLite database (no seed data. if you want to keep the seed data, you can run `uv run slackbot start --config=local-with-onboarding.csbot.config.yaml --no-reset-db`)
- **Purpose**: Test end-to-end onboarding

**Setup**:

1. Create a Slack app and [Configure Environment Variables](#4-configure-environment-variables)
1. Fill in the `client_id` field in [infra/slack_bot_manifests/app_config.yaml](infra/slack_bot_manifests/app_config.yaml) for your manifest (must be quoted as a string)
1. Get the Slack configuration token from https://api.slack.com/apps (at the bottom of the page, click "Generate Your App Configuration Token" and select "dagsterlabs" workspace) and set it as `SLACK_CONFIG_TOKEN` environment variable
1. Ensure that organization-wide installation is enabled in your Slack app config. You may need to manually mark it as ready for public distribution at `https://app.slack.com/app-settings/TCC8P0589/<your_app_id>/distribute` (replace `<your_app_id>` with your actual app ID)
1. Run the automated OAuth flow:
   ```bash
   compass-dev reinstall-to-enterprise-grid --manifest infra/slack_bot_manifests/prod_manifest.json
   ```
   (The command will prompt for client secret if not provided)
   This command will:
   - Automatically start ngrok tunnel
   - Fetch and update the Slack manifest with the ngrok redirect URL
   - Open the OAuth URL in your browser for the dagsterio enterprise workspace
   - Run the callback server to capture the token
1. In the browser, use the organization selector (top right corner) to select the Dagster Compass organization if needed. You may need to be elevated to admin in the Dagster Compass organization. Add the app to the organization.
1. From the command output, copy the bot token and configure your environment variable. For use with the `local-with-onboarding.csbot.config.yaml`, it should be set as `SLACK_BOT_TOKEN_ENTERPRISE_GRID_LOCAL_DEV`.
1. Go to the Slack config page for the dagster compass org > integrations > installed apps. Find your app and add it to some existing workspace. In the side panel, there should be a checkbox to add your app to future workspaces by default. Enable it.
1. Start the services:

   ```bash
   # Option 1: Start everything together (recommended - includes Temporal)
   uv run compass-dev local-dev --config=local-with-onboarding.csbot.config.yaml

   # Option 2: Start bot only
   uv run slackbot start --config=local-with-onboarding.csbot.config.yaml
   ```

   This will start the bot with the onboarding flow enabled and a fresh database.

1. Generate a local referral token:
   ```bash
   uv run compass-dev create-referral-token local
   ```
1. Use the generated referral token to start the onboarding flow, navigating to `http://localhost:3000/onboarding?token=<referral_token>`:
1. Check your email to join the slack channel, and then click `Connect your data` in the newly created Slack channel to continue on with the onboarding flow.
1. Note: you can configure the channels, bot instances, connections, etc, in `seed_data/enterprise_grid_slack` folder.

## Infrastructure

Compass is deployed on a [Render](https://render.com]) webservice, using a Render Postgres instance as K/V store.

### Staging Instance

The `@Compass (staging)` instance lives in an environment called `dev` in Render.

Infrastructure for the dev/staging instance is specified in [`render.yaml`](./render.yaml), a Render [Blueprint](https://render.com/docs/infrastructure-as-code), the native Infrastructure-as-Code format.
It is synchronized on merges to `master`.

The code for the dev/staging instance is built and deployed on merges to `master`, as part of [`staging.Dockerfile`](./staging.Dockerfile).
The compass bot configuration for staging is found in [`staging.csbot.config.yaml`](./staging.csbot.config.yaml)

### (Replica) Production Instance

The `@Compass (temp prod replica)` instance (soon the base `@Compass` instance) lives in an environment called `production` in Render.

Infrastructure for the (replica) pprod instance is specified in [`render.yaml in dagster-io/dagster-compass-production-render-blueprint repo`](https://github.com/dagster-io/dagster-compass-production-render-blueprint/blob/main/render.yaml) as Render supports only one blueprint per repository.
It is synchronized on merges to `master` in that repo.

The code for the (replica) prod instance is built and deployed on merges to the `release` branch, as part of [`prod.Dockerfile`](./prod.Dockerfile).
The compass bot configuration for staging is found in [`dagsterlabs.csbot.config.yaml`](./dagsterlabs.csbot.config.yaml)

## Adjusting organization configuration for deployed instances

For deployed (staging + prod) instances, organization configuration is stored in Postgres in Render.

You'll first need to get the external Postgres connection string from the Render UI. You can do this by clicking on `compass-bot-db` (staging) or `prod-compass-bot-db` (prod) and clicking `Connect` on the top right.

The `compass-dev instance` command suite lets you interact with the list of bot instances configured in the database.

### Listing bot instances

```bash
$ compass-dev instance list $PROD_POSTGRES_URI
1: #dagster-compass-demo
2: #ask-data
3: #dagster-compass-georgian
4: #dagster-compass-octave
```

### Getting instance config

```bash
$ compass-dev instance pull $PROD_POSTGRES_URI

bots:
  '#ask-data':
    bot_email: compassbot@dagster.io
    channel_name: '#ask-data'
    connections:
      dev_bigquery:
        init_sql: []
        url: bigquery://elementl-dev?location=us&credentials_path={{ secret_file('compass_dagster_bigquery',
          'DAGSTER_BIGQUERY_PRIVATE_KEY_PATH') }}
      purina_snowflake:
        init_sql: []
        url: snowflake://na94824.us-east-1/DWH_REPORTING_READER?warehouse=PURINA&role=DWH_REPORTING_READER&user=pete_bot&private_key_file={{
          secret_file('dagster_purina_snowflake', 'SNOWFLAKE_PRIVATE_KEY_PATH') }}
    contextstore_github_repo: petehunt/dagsterlabs-contextstore
    governance_alerts_channel: '#ask-data-governance'
    mcp_server_configs:
    - headers: '{"X-API-Key": "{{ secret(''you_search_api_key'', ''YOU_SEARCH_API_KEY'')
        }}"}'
      url: https://ydc-mcp-server.onrender.com/mcp
    team_id: TCC8P0589
 ...
```

### Adding or updating a bot instance

`my_org_config.yaml`

```yaml
bots:
  "#ask-data":
    bot_email: compassbot@dagster.io
    channel_name: "#ask-data"
    connections:
      dev_bigquery:
        init_sql: []
        url:
          bigquery://elementl-dev?location=us&credentials_path={{ secret_file('compass_dagster_bigquery',
          'DAGSTER_BIGQUERY_PRIVATE_KEY_PATH') }}
      purina_snowflake:
        init_sql: []
        url:
          snowflake://na94824.us-east-1/DWH_REPORTING_READER?warehouse=PURINA&role=DWH_REPORTING_READER&user=pete_bot&private_key_file={{
          secret_file('dagster_purina_snowflake', 'SNOWFLAKE_PRIVATE_KEY_PATH') }}
    contextstore_github_repo: petehunt/dagsterlabs-contextstore
    governance_alerts_channel: "#ask-data-governance"
    mcp_server_configs:
      - headers:
          '{"X-API-Key": "{{ secret(''you_search_api_key'', ''YOU_SEARCH_API_KEY'')
          }}"}'
        url: https://ydc-mcp-server.onrender.com/mcp
    team_id: TCC8P0589
```

### Creating referral tokens

Generate and insert referral tokens into the database for user onboarding:

```bash
# Create a referral token in the production database
$ compass-dev create-referral-token prod
✅ Successfully created referral token: 123e4567-e89b-12d3-a456-426614174000
📊 Database output: INSERT 0 1

# Create a referral token in the staging database
$ compass-dev create-referral-token staging
✅ Successfully created referral token: 987fcdeb-51d2-43a8-b123-987654321000
📊 Database output: INSERT 0 1
```

This command:

- Generates a UUID v4 token
- Inserts it into the `referral_tokens` table in the specified database tier
- Returns the generated token for use in user onboarding flows

### Access the admin panel

- [go/compass-admin](https://go/compass-admin) for Compass prod
- [go/compass-admin-staging](https://go/compass-admin-staging) for Compass staging

### Test the admin panel locally

You can run the admin panel standalone or together with the Slack bot:

**Option 1: Run everything together (recommended for development)**

```bash
uv run compass-dev local-dev --config local.csbot.config.yaml
```

This starts both the Slack bot and admin panel. Navigate to `http://localhost:8080` to access the admin panel.

**Option 2: Run admin panel only**

1. Create a Slack app and [Configure Environment Variables](#4-configure-environment-variables)
2. Spin up the admin panel:
   ```bash
   uv run compass-admin --config local.csbot.config.yaml
   ```
3. Navigate to `http://localhost:8080`

## Deployment

### Docker Images

The project uses unified Docker images for all services to simplify deployment and ensure consistency:

- **`staging.Dockerfile`**: Single image for all staging services (slackbot, admin panel, temporal worker)

Each service runs a different command from the same image:

```yaml
# Slackbot (default)
CMD: uv run --frozen slackbot start --config staging.csbot.config.yaml

# Admin Panel
CMD: uv run --frozen compass-admin --host 0.0.0.0 --port 8080 --config staging.csbot.config.yaml

# Temporal Worker
CMD: uv run --frozen compass-temporal-worker start --config staging.csbot.config.yaml
```

### Render Deployment

The `render.yaml` file defines all infrastructure including:

- `compass-bot`: Main Slack bot service
- `compass-admin-panel-staging`: Admin panel web interface
- `compass-temporal-worker-staging`: Temporal workflow worker
- `temporal-staging`: Temporal server instance
- Database instances for bot data and Temporal

All services share the unified Docker image but use different `dockerCommand` overrides in `render.yaml` to run different entrypoints.
