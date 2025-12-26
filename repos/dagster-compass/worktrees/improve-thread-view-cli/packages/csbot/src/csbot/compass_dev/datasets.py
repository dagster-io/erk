"""Dataset utility commands for compass-dev CLI."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import click
from dotenv import find_dotenv, load_dotenv

from csbot.agents.factory import create_agent_from_config
from csbot.compass_dev.utils.context_store_manager import FakeContextStoreManager
from csbot.contextengine.contextstore_protocol import Dataset
from csbot.contextengine.diff import compute_diff
from csbot.contextengine.loader import load_context_store
from csbot.csbot_client.csbot_profile import ConnectionProfile, ProjectProfile
from csbot.ctx_admin.dataset_documentation import analyze_table_schema, update_dataset
from csbot.local_context_store.git.file_tree import FilesystemFileTree
from csbot.slackbot.channel_bot.handlers.github_pr_handler import GitHubPRHandler
from csbot.slackbot.slackbot_core import load_bot_server_config_from_yaml

logger = logging.getLogger(__name__)

# Configure snowflake connector to reduce noise
logging.getLogger("snowflake.connector.connection").setLevel(logging.WARNING)


class ConsoleStream:
    """Console implementation of StreamProtocol for CLI usage.

    Converts Block Kit blocks to markdown and prints to console.
    """

    async def update(self, blocks):
        """Update the stream with new blocks.

        Args:
            blocks: Sequence of Block objects to display
        """
        click.echo()
        for block in blocks:
            markdown = block.to_markdown()
            if markdown:
                click.echo(markdown)

    async def finish(self):
        """Finish the stream."""
        click.echo()
        click.echo("-" * 80)


def find_datasets_by_table_names(context_store, *table_names: str) -> tuple[str, list[Dataset]]:
    """Find datasets by table names and ensure they're all from the same connection.

    Args:
        context_store: ContextStore to search in
        *table_names: Variable number of table names to find

    Returns:
        Tuple of (connection_name, list of Dataset objects)

    Raises:
        Exception: If tables not found or from different connections
    """
    datasets = []
    connection = None

    for table_name in table_names:
        found = None
        for candidate, _ in context_store.datasets:
            if candidate.table_name == table_name:
                found = candidate
                break

        if found is None:
            available = [d.table_name for d, _ in context_store.datasets]
            raise Exception(
                f"Unable to find dataset with table '{table_name}'. "
                f"Available: {', '.join(available)}"
            )

        # Check connection consistency
        if connection is None:
            connection = found.connection
        elif connection != found.connection:
            raise Exception(
                f"Tables are from different connections: "
                f"'{table_names[0]}' from '{connection}', "
                f"'{table_name}' from '{found.connection}'"
            )

        datasets.append(found)

    if connection is None:
        raise Exception("No datasets found")

    return connection, datasets


@click.group()
def datasets():
    """Dataset utility commands."""
    pass


@datasets.command()
@click.option(
    "--config-file",
    required=True,
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Path to bot configuration YAML file",
)
@click.option(
    "--url",
    required=True,
    help="Database connection URL",
)
@click.option(
    "--table",
    required=True,
    help="Table name to analyze",
)
@click.option(
    "--context-store-dir",
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Path to context store directory",
)
def analyze(config_file: str, url: str, table: str, context_store_dir: Path):
    """Analyze a table schema and update context store documentation.

    This command:
    1. Creates a ProjectProfile from the database URL
    2. Analyzes the table schema
    3. Loads the existing context store
    4. Calls update_dataset to generate documentation
    5. Prints the diff between original and updated context stores

    Example:
        compass-dev datasets analyze \\
            --config-file local.csbot.config.yaml \\
            --url "postgresql://user:pass@localhost/db" \\
            --table "users" \\
            --context-store-dir /path/to/context-store
    """
    load_dotenv(find_dotenv(usecwd=True), override=True)

    if not url.startswith("jsonconfig:"):
        raise Exception(str(url))
    click.echo("🔍 Analyzing table and updating context store")
    click.echo("=" * 80)
    click.echo()

    # Load bot config
    click.echo("📁 Loading bot configuration...")
    config_path = Path(config_file)
    config_yaml = config_path.read_text(encoding="utf-8")
    bot_config = load_bot_server_config_from_yaml(config_yaml, config_path.parent.absolute())

    # Load context store
    click.echo(f"📂 Loading context store from: {context_store_dir}")
    try:
        tree = FilesystemFileTree(context_store_dir)
        original_context_store = load_context_store(tree)
        click.echo("   ✅ Context store loaded")
        click.echo(f"   Project: {original_context_store.project.project_name}")
        click.echo(f"   Datasets: {len(original_context_store.datasets)}")
        click.echo()
    except Exception as e:
        click.echo(f"   ❌ Error loading context store: {e}", err=True)
        import traceback

        traceback.print_exc()
        raise click.Abort()

    dataset = None
    for candidate, _ in original_context_store.datasets:
        if candidate.table_name == table:
            dataset = candidate

    if dataset is None:
        raise Exception(f"Unable to find dataset with table {table}")

    # Create profile with the connection
    profile = ProjectProfile(
        connections={dataset.connection: ConnectionProfile(url=url, additional_sql_dialect=None)},
    )

    # Create dataset
    click.echo(f"📊 Analyzing table: {dataset.table_name}")

    # Analyze table schema
    try:
        schema_analysis = analyze_table_schema(logger, profile, dataset)

        click.echo("   ✅ Schema analyzed successfully")
        click.echo(f"   Schema hash: {schema_analysis.schema_hash}")
        click.echo(f"   Columns: {len(schema_analysis.columns)}")
        click.echo()

    except Exception as e:
        click.echo(f"   ❌ Error analyzing schema: {e}", err=True)
        import traceback

        traceback.print_exc()
        raise click.Abort()

    # Update dataset using AI agent
    click.echo("🤖 Generating documentation with AI...")
    try:
        agent = create_agent_from_config(bot_config.ai_config)
        with ThreadPoolExecutor(max_workers=4) as executor:
            updated_context_store = update_dataset(
                logger=logger,
                context_store=original_context_store,
                profile=profile,
                dataset=dataset,
                table_schema_analysis=schema_analysis,
                agent=agent,
                column_analysis_threadpool=executor,
            )

        click.echo("   ✅ Documentation generated")
        click.echo()

    except Exception as e:
        click.echo(f"   ❌ Error generating documentation: {e}", err=True)
        import traceback

        traceback.print_exc()
        raise click.Abort()

    # Compute diff
    click.echo("📝 Computing diff between original and updated context stores...")
    click.echo()

    diff = compute_diff(original_context_store, updated_context_store)

    # Print diff summary
    click.echo("=" * 80)
    click.echo("DIFF SUMMARY")
    click.echo("=" * 80)
    click.echo()

    if not diff.has_changes():
        click.echo("✅ No changes detected")
        return

    # Project changes
    if diff.project_diff:
        click.echo("📋 Project Changes:")
        if diff.project_diff.project_name_changed:
            click.echo(f"   - Project name changed to: {diff.project_diff.new_project_name}")
        if diff.project_diff.version_changed:
            click.echo(f"   - Version changed to: {diff.project_diff.new_version}")
        if diff.project_diff.teams_added:
            click.echo(f"   - Teams added: {list(diff.project_diff.teams_added.keys())}")
        if diff.project_diff.teams_removed:
            click.echo(f"   - Teams removed: {list(diff.project_diff.teams_removed)}")
        if diff.project_diff.teams_modified:
            click.echo(f"   - Teams modified: {list(diff.project_diff.teams_modified.keys())}")
        click.echo()

    # System prompt changes
    if diff.system_prompt_changed:
        click.echo("📝 System Prompt Changed")
        if diff.new_system_prompt:
            click.echo(f"   New value: {diff.new_system_prompt[:100]}...")
        else:
            click.echo("   Removed")
        click.echo()

    # Dataset changes
    if diff.datasets_added or diff.datasets_removed or diff.datasets_modified:
        click.echo("📊 Dataset Changes:")
        if diff.datasets_added:
            click.echo(f"   Added ({len(diff.datasets_added)}):")
            for dataset, doc in diff.datasets_added:
                click.echo(f"      - {dataset.connection}/{dataset.table_name}")
                if doc.frontmatter:
                    click.echo(f"        Schema hash: {doc.frontmatter.schema_hash}")

        if diff.datasets_removed:
            click.echo(f"   Removed ({len(diff.datasets_removed)}):")
            for dataset in diff.datasets_removed:
                click.echo(f"      - {dataset.connection}/{dataset.table_name}")

        if diff.datasets_modified:
            click.echo(f"   Modified ({len(diff.datasets_modified)}):")
            for dataset_diff in diff.datasets_modified:
                click.echo(
                    f"      - {dataset_diff.dataset.connection}/{dataset_diff.dataset.table_name}"
                )
                if dataset_diff.old_documentation and dataset_diff.new_documentation:
                    if (
                        dataset_diff.old_documentation.frontmatter
                        and dataset_diff.new_documentation.frontmatter
                    ):
                        old_hash = dataset_diff.old_documentation.frontmatter.schema_hash
                        new_hash = dataset_diff.new_documentation.frontmatter.schema_hash
                        if old_hash != new_hash:
                            click.echo(f"        Schema hash: {old_hash} → {new_hash}")
        click.echo()

    # General context changes
    if diff.general_context_added or diff.general_context_removed or diff.general_context_modified:
        click.echo("📚 General Context Changes:")
        if diff.general_context_added:
            click.echo(f"   Added: {len(diff.general_context_added)}")
        if diff.general_context_removed:
            click.echo(f"   Removed: {len(diff.general_context_removed)}")
        if diff.general_context_modified:
            click.echo(f"   Modified: {len(diff.general_context_modified)}")
        click.echo()

    # General cronjob changes
    if (
        diff.general_cronjobs_added
        or diff.general_cronjobs_removed
        or diff.general_cronjobs_modified
    ):
        click.echo("⏰ General Cron Job Changes:")
        if diff.general_cronjobs_added:
            click.echo(f"   Added: {list(diff.general_cronjobs_added.keys())}")
        if diff.general_cronjobs_removed:
            click.echo(f"   Removed: {list(diff.general_cronjobs_removed)}")
        if diff.general_cronjobs_modified:
            click.echo(f"   Modified: {[j.name for j in diff.general_cronjobs_modified]}")
        click.echo()

    # Channel changes
    if diff.channels_added or diff.channels_removed or diff.channels_modified:
        click.echo("📢 Channel Changes:")
        if diff.channels_added:
            click.echo(f"   Added: {list(diff.channels_added.keys())}")
        if diff.channels_removed:
            click.echo(f"   Removed: {list(diff.channels_removed)}")
        if diff.channels_modified:
            click.echo(f"   Modified: {[c.channel_name for c in diff.channels_modified]}")
        click.echo()

    click.echo("=" * 80)

    # Show detailed dataset documentation if it was updated
    if diff.datasets_modified or diff.datasets_added:
        click.echo()
        click.echo("📄 Generated Documentation Preview:")
        click.echo("-" * 80)

        # Find the dataset we just updated
        for dataset_item, doc in updated_context_store.datasets:
            if dataset_item == dataset:
                click.echo(doc.summary[:500])
                if len(doc.summary) > 500:
                    click.echo(f"\n... ({len(doc.summary) - 500} more characters)")
                break

    click.echo()
    click.echo("✅ Analysis complete")


@datasets.command()
@click.option(
    "--config-file",
    required=True,
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Path to bot configuration YAML file",
)
@click.option(
    "--url",
    required=True,
    help="Database connection URL (jsonconfig: format)",
)
@click.option(
    "--table",
    required=True,
    help="Table name to create PR for",
)
@click.option(
    "--context-store-dir",
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Path to context store directory",
)
def create_dataset_schema_pr(config_file: str, url: str, table: str, context_store_dir: Path):
    """Create a GitHub PR for dataset schema update.

    This command:
    1. Loads the context store from the directory
    2. Finds the dataset by table name
    3. Analyzes the table schema
    4. Calls GitHubPRHandler.create_dataset_schema_pr()
    5. Uses FakeContextStoreManager to capture the mutation
    6. Prints the PR details and diff

    Example:
        compass-dev datasets create-pr \\
            --config-file local.csbot.config.yaml \\
            --url "jsonconfig:..." \\
            --table "users" \\
            --context-store-dir /path/to/context-store
    """

    load_dotenv(find_dotenv(usecwd=True), override=True)

    click.echo("🔧 Creating dataset schema PR")
    click.echo("=" * 80)
    click.echo()

    # Load bot config
    click.echo("📁 Loading bot configuration...")
    config_path = Path(config_file)
    config_yaml = config_path.read_text(encoding="utf-8")
    bot_config = load_bot_server_config_from_yaml(config_yaml, config_path.parent.absolute())

    # Load context store
    click.echo(f"📂 Loading context store from: {context_store_dir}")
    try:
        tree = FilesystemFileTree(context_store_dir)
        original_context_store = load_context_store(tree)
        click.echo("   ✅ Context store loaded")
        click.echo(f"   Project: {original_context_store.project.project_name}")
        click.echo(f"   Datasets: {len(original_context_store.datasets)}")
        click.echo()
    except Exception as e:
        click.echo(f"   ❌ Error loading context store: {e}", err=True)
        import traceback

        traceback.print_exc()
        raise click.Abort()

    # Find the dataset using helper
    try:
        connection_name, datasets = find_datasets_by_table_names(original_context_store, table)
        dataset = datasets[0]
        click.echo(f"   ✅ Found dataset: {dataset.connection}/{dataset.table_name}")
        click.echo()
    except Exception as e:
        click.echo(f"   ❌ {e}", err=True)
        raise click.Abort()

    # Create profile
    profile = ProjectProfile(
        connections={dataset.connection: ConnectionProfile(url=url, additional_sql_dialect=None)},
    )

    # Analyze schema
    click.echo(f"📊 Analyzing table schema: {dataset.table_name}")
    try:
        schema_analysis = analyze_table_schema(logger, profile, dataset)
        click.echo("   ✅ Schema analyzed")
        click.echo(f"   Schema hash: {schema_analysis.schema_hash}")
        click.echo(f"   Columns: {len(schema_analysis.columns)}")
        click.echo()
    except Exception as e:
        click.echo(f"   ❌ Error analyzing schema: {e}", err=True)
        import traceback

        traceback.print_exc()
        raise click.Abort()

    # Create fake provider and mutator
    fake_provider = FakeContextStoreManager(original_context_store)

    # Create GitHubPRHandler
    pr_handler = GitHubPRHandler(fake_provider)

    # Create agent
    agent = create_agent_from_config(bot_config.ai_config)

    # Call create_dataset_schema_pr
    click.echo("🚀 Creating dataset schema PR...")
    try:
        pr_url = asyncio.run(
            pr_handler.create_dataset_schema_pr(
                dataset=dataset,
                table_schema_analysis=schema_analysis,
                profile=profile,
                agent=agent,
            )
        )

        click.echo(f"   ✅ PR created: {pr_url}")
        click.echo()

    except Exception as e:
        click.echo(f"   ❌ Error creating PR: {e}", err=True)
        import traceback

        traceback.print_exc()
        raise click.Abort()

    # Get the mutation details
    try:
        mutation = fake_provider.get_last_mutation()

        click.echo("=" * 80)
        click.echo("PR DETAILS")
        click.echo("=" * 80)
        click.echo()
        click.echo(f"Title: {mutation.title}")
        click.echo(f"Body:\n{mutation.body}")
        click.echo()

        # Compute and display diff
        click.echo("=" * 80)
        click.echo("CONTEXT STORE DIFF")
        click.echo("=" * 80)
        click.echo()

        diff = compute_diff(mutation.before, mutation.after)

        if not diff.has_changes():
            click.echo("⚠️  No changes detected in mutation")
        else:
            # Show dataset changes
            if diff.datasets_modified:
                click.echo(f"📊 Modified Datasets ({len(diff.datasets_modified)}):")
                for dataset_diff in diff.datasets_modified:
                    click.echo(
                        f"   - {dataset_diff.dataset.connection}/{dataset_diff.dataset.table_name}"
                    )
                    if dataset_diff.old_documentation and dataset_diff.new_documentation:
                        old_fm = dataset_diff.old_documentation.frontmatter
                        new_fm = dataset_diff.new_documentation.frontmatter
                        if old_fm and new_fm and old_fm.schema_hash != new_fm.schema_hash:
                            click.echo(
                                f"     Schema hash: {old_fm.schema_hash[:16]}... → {new_fm.schema_hash[:16]}..."
                            )

                        # Show summary preview
                        new_summary = dataset_diff.new_documentation.summary
                        click.echo("     Documentation preview:")
                        click.echo(f"     {new_summary[:200]}...")

            if diff.datasets_added:
                click.echo(f"📊 Added Datasets ({len(diff.datasets_added)}):")
                for ds, doc in diff.datasets_added:
                    click.echo(f"   - {ds.connection}/{ds.table_name}")

    except Exception as e:
        click.echo(f"   ⚠️  Could not retrieve mutation details: {e}", err=True)

    click.echo()
    click.echo("✅ PR creation complete")
