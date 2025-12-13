"""Create organization command for compass-dev CLI using automated onboarding flow."""

import asyncio
import traceback
import uuid
from typing import Literal

import click
from playwright.async_api import async_playwright

from csbot.compass_dev.utils.render import execute_sql_query
from csbot.slackbot.config import DatabaseConfig
from csbot.slackbot.storage.sqlite import create_sqlite_connection_factory


async def fill_onboarding_form(
    page, email: str, organization: str, base_url: str, token: str
) -> None:
    """Fill out the onboarding form using Playwright.

    Args:
        page: Playwright page object
        email: Email address for the organization
        organization: Organization name
        base_url: Base URL of the application (e.g., http://localhost:3000)
        token: Referral token to use for onboarding
    """
    onboarding_url = f"{base_url}/onboarding?token={token}"

    await page.goto(onboarding_url)

    # Wait for form elements to be present
    email_input = page.locator('input[name="email"]')
    organization_input = page.locator('input[name="organization"]')
    terms_input = page.locator('input[name="terms"]')
    submit_button = page.locator('button[type="submit"], input[type="submit"]')

    await email_input.wait_for(state="attached")
    await organization_input.wait_for(state="attached")
    await terms_input.wait_for(state="attached")
    await submit_button.wait_for(state="attached")

    # Fill form fields
    await email_input.fill(email)
    await organization_input.fill(organization)
    await terms_input.click()

    # Submit the form
    await submit_button.click(timeout=30000)

    # Wait for the success page or processing to complete
    await page.wait_for_load_state("domcontentloaded")

    # Wait a bit for background processing
    await asyncio.sleep(2)

    click.echo(f"✅ Successfully submitted onboarding form for {organization}")
    click.echo(f"   Email: {email}")
    click.echo(f"   Organization: {organization}")


def create_token(tier: str, token: str):
    try:
        if tier == "local":
            sql_conn_factory = create_sqlite_connection_factory(
                DatabaseConfig.from_sqlite_path("./compassbot.db")
            )
            with sql_conn_factory.with_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO referral_tokens (token) VALUES (?)", (token,))
                conn.commit()
            click.echo(f"✅ Created referral token: {token}")
            click.echo("📊 Token inserted into local SQLite database (compassbot.db)")
        else:
            insert_query = f"INSERT INTO referral_tokens (token) VALUES ('{token}')"
            assert tier == "staging" or tier == "prod"
            execute_sql_query(tier, insert_query)
            click.echo(f"✅ Created referral token: {token}")
    except Exception as e:
        click.echo(f"❌ Failed to create referral token: {e}", err=True)
        click.echo(traceback.format_exc(), err=True)
        raise click.ClickException(f"Database operation failed: {e}")


async def run_automated_onboarding(
    tier: Literal["prod", "staging", "local"],
    email: str,
    organization: str,
    headless: bool = True,
) -> None:
    """Run the automated onboarding flow.

    Args:
        tier: Database tier to use - 'prod', 'staging', or 'local'
        email: Email address for the organization
        organization: Organization name
        headless: Whether to run browser in headless mode
    """
    # Generate referral token
    token = str(uuid.uuid4())

    # Insert token into database
    await asyncio.to_thread(create_token, tier, token)

    # Determine base URL based on tier
    if tier == "local":
        base_url = "http://localhost:3000"
    elif tier == "staging":
        base_url = "https://staging.dagstercompass.com"
    else:  # prod
        base_url = "https://dagstercompass.com"

    # Launch Playwright and fill form
    click.echo(f"\n🌐 Opening browser to {base_url}/onboarding?token={token}")

    playwright = None
    browser = None
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=headless)
        page = await browser.new_page()
        page.set_default_navigation_timeout(30000)
        page.set_default_timeout(30000)

        await fill_onboarding_form(page, email, organization, base_url, token)

        click.echo("\n✅ Organization creation complete!")
        click.echo(f"   Base URL: {base_url}")
        click.echo(f"   Token: {token}")

        if not headless:
            click.echo("\n⏸  Browser left open for manual inspection. Close it when done.")
            await page.wait_for_timeout(300000)  # Wait 5 minutes

    except Exception as e:
        click.echo(f"\n❌ Failed to complete onboarding: {e}", err=True)
        click.echo(traceback.format_exc(), err=True)
        raise click.ClickException(f"Onboarding failed: {e}")
    finally:
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()


@click.command()
@click.argument("tier", type=click.Choice(["prod", "staging", "local"], case_sensitive=False))
@click.option("--email", required=True, help="Email address for the organization")
@click.option("--organization", required=True, help="Organization name")
@click.option(
    "--headless/--no-headless",
    default=True,
    help="Run browser in headless mode (default: headless)",
)
def create_org(
    tier: Literal["prod", "staging", "local"], email: str, organization: str, headless: bool
) -> None:
    """Create a new organization by automating the onboarding flow.

    This command creates a referral token, then uses Playwright to automatically
    fill out and submit the onboarding form at the appropriate environment URL.

    Args:
        tier: Database tier to use - 'prod', 'staging', or 'local'

    Examples:
        compass-dev create-org local --email test@example.com --organization "Test Company"
        compass-dev create-org staging --email admin@acme.com --organization "Acme Corp" --no-headless
    """
    asyncio.run(run_automated_onboarding(tier, email, organization, headless))
