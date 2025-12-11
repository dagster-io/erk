# Compass Admin Panel

A web administration interface for the Compass bot system that displays organizations in a comprehensive table view.

## Features

- **Organizations Table View**: Displays all organizations with key metrics in a clean table layout
- **Invite Tokens Management**: View all invite tokens with status, creation/consumption dates, and consuming organizations
- **Token Creation**: One-click button to create new invite tokens
- **Real-time Data**: Shows organization ID, name, plan type, bot count, and current month's usage
- **Stripe Integration**: Direct links to Stripe dashboard for customer and subscription management (automatically uses test URLs for sandbox keys)
- **Usage Monitoring**: Highlights organizations that exceed their plan limits in red
- **Configuration Loading**: Uses csbot configuration files to connect to the database
- **Multiple Database Support**: Works with PostgreSQL and SQLite databases

## Installation

```bash
uv sync --group dev
```

## Usage

### Running the Admin Panel

```bash
uv run compass-admin --config local.csbot.config.yaml
```

This loads the csbot configuration file and connects to the database to display organizations.

**Note**: The `--config` parameter is required. The admin panel needs a configuration file to connect to the database and display organization data.

### Command Line Options

- `--host HOST`: Host to bind the server to (default: localhost)
- `--port PORT`: Port to bind the server to (default: 8080)
- `--config CONFIG`: Path to csbot configuration file (required, e.g., local.csbot.config.yaml)

## Configuration

The admin panel uses the same configuration format as the csbot system. It reads the `database_uri` from the config file and supports:

- **PostgreSQL**: `postgresql://user:password@host:5432/database`
- **SQLite**: `sqlite:///path/to/file.db` or `/path/to/file.db`

## Development

```bash
# Type checking
uv run pyright src

# Code formatting and linting
uv run ruff check .
uv run ruff format .
```

## Pages

### Organizations Table

The main organizations table displays the following information:

- **ID**: Organization's unique identifier
- **Organization Name**: The organization's display name
- **Plan Type**: Subscription plan (Free, Starter, Team) with color-coded badges
- **Stripe Customer**: Direct link to the customer in Stripe dashboard (automatically uses test/sandbox URLs if Stripe keys contain "test")
- **Stripe Subscription**: Direct link to the subscription in Stripe dashboard (automatically uses test/sandbox URLs if Stripe keys contain "test")
- **Bots**: Number of bot instances configured for this organization
- **Usage / Limit**: Current month's usage vs plan limit (highlighted in red if over limit)

### Invite Tokens

The invite tokens page provides comprehensive token management:

- **Token**: UUID token (truncated for display, **click to copy onboarding link**)
- **Status**: Available (green) or Consumed (red)
- **Created**: When the token was generated
- **Consumed**: When the token was used (if applicable)
- **Organization**: Which organization used the token (with link back to organizations)
- **Create Button**: Generate new invite tokens with one click

**Onboarding Links**: Click any token to copy a complete onboarding link like:
`https://staging.dagstercompass.com/signup?referral-token=abc123...`

## Architecture

- `app.py`: Main application with aiohttp web server and organization table view
- `cli.py`: Command line interface for starting the server
- Uses csbot's configuration loading and database connection factories
- Modern table-based UI with hover effects and responsive design
- Queries bot_instances and usage_tracking tables for comprehensive data
