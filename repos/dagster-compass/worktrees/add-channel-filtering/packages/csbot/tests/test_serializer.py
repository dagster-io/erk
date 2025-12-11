"""Tests for context store serializer."""

import asyncio
import tempfile
from pathlib import Path

import yaml

from csbot.contextengine.contextstore_protocol import UserCronJob
from csbot.contextengine.loader import load_context_store
from csbot.contextengine.serializer import serialize_context_store
from csbot.local_context_store.git.file_tree import FilesystemFileTree
from csbot.slackbot.usercron.storage import UserCronStorage
from tests.factories import context_store_builder
from tests.fakes.context_store_manager import FakeContextStoreManager


class TestSerializeContextStore:
    """Test serializing ContextStore to filesystem."""

    def test_serialize_minimal_context_store(self):
        """Test serializing a minimal context store with just project config."""
        context_store = context_store_builder().with_project("test/project").build()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Serialize
            serialize_context_store(context_store, temp_path)

            # Verify project config was written
            config_path = temp_path / "contextstore_project.yaml"
            assert config_path.exists()

            with open(config_path) as f:
                config = yaml.safe_load(f)
                assert config["project_name"] == "test/project"

    def test_serialize_with_system_prompt(self):
        """Test serializing context store with system prompt."""
        context_store = (
            context_store_builder()
            .with_project("test/project")
            .with_system_prompt("This is a test system prompt")
            .build()
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            serialize_context_store(context_store, temp_path)

            # Verify system prompt was written
            prompt_path = temp_path / "system_prompt.md"
            assert prompt_path.exists()
            assert prompt_path.read_text() == "This is a test system prompt"

    def test_serialize_with_general_cronjobs(self):
        """Test serializing context store with general cronjobs."""
        context_store = (
            context_store_builder()
            .with_project("test/project")
            .add_general_cronjob("daily_report")
            .with_cron("0 9 * * *")
            .with_question("What happened yesterday?")
            .with_thread("daily-thread")
            .build()
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            serialize_context_store(context_store, temp_path)

            # Verify cronjobs/daily_report.yaml was written
            cronjob_path = temp_path / "cronjobs" / "daily_report.yaml"
            assert cronjob_path.exists()

            with open(cronjob_path) as f:
                cronjob = yaml.safe_load(f)
                assert cronjob["cron"] == "0 9 * * *"
                assert cronjob["question"] == "What happened yesterday?"
                assert cronjob["thread"] == "daily-thread"

    def test_serialize_with_datasets_v1(self):
        """Test serializing context store with datasets (V1 layout)."""
        context_store = (
            context_store_builder()
            .with_project("test/project", version=1)
            .add_dataset("postgres_prod", "users")
            .with_markdown("# Users Table\nUser data")
            .add_dataset("postgres_prod", "orders")
            .with_markdown("# Orders Table\nOrder data")
            .build()
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            serialize_context_store(context_store, temp_path)

            # Verify V1 layout: docs/{connection}/{table}.md
            users_path = temp_path / "docs" / "postgres_prod" / "users.md"
            orders_path = temp_path / "docs" / "postgres_prod" / "orders.md"

            assert users_path.exists()
            assert orders_path.exists()
            assert "Users Table" in users_path.read_text()
            assert "Orders Table" in orders_path.read_text()

    def test_serialize_with_datasets_v2(self):
        """Test serializing context store with datasets (V2 manifest layout)."""
        context_store = (
            context_store_builder()
            .with_project("test/project", version=2)
            .add_dataset("snowflake_prod", "dim_customers")
            .with_markdown("# Customers Dimension\nCustomer data")
            .build()
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            serialize_context_store(context_store, temp_path)

            # Verify V2 layout: docs/{connection}/{table}/context/summary.md
            summary_path = (
                temp_path / "docs" / "snowflake_prod" / "dim_customers" / "context" / "summary.md"
            )

            assert summary_path.exists()
            assert "Customers Dimension" in summary_path.read_text()

    def test_serialize_with_general_context(self):
        """Test serializing context store with general context."""
        context_store = (
            context_store_builder()
            .with_project("test/project")
            .add_general_context("database", "connection_pooling")
            .with_topic("Connection Pooling")
            .with_incorrect("More connections are always better")
            .with_correct("Connection pools should be sized appropriately")
            .with_keywords("database, connections, performance")
            .build()
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            serialize_context_store(context_store, temp_path)

            # Verify context/{group}/{name}.yaml exists
            context_path = temp_path / "context" / "database" / "connection_pooling.yaml"
            assert context_path.exists()

            with open(context_path) as f:
                context_data = yaml.safe_load(f)
                assert context_data["topic"] == "Connection Pooling"
                assert (
                    context_data["incorrect_understanding"] == "More connections are always better"
                )
                assert context_data["search_keywords"] == "database, connections, performance"

    def test_serialize_with_channels(self):
        """Test serializing context store with channel-specific data."""
        context_store = (
            context_store_builder()
            .with_project("test/project")
            .new_channel("data-team")
            .with_channel_system_prompt("Channel-specific prompt")
            .add_channel_cronjob(
                "weekly_summary",
            )
            .with_cron(
                cron="0 0 * * 0",
            )
            .with_question(
                question="What happened this week?",
            )
            .with_thread(
                thread="weekly-thread",
            )
            .add_channel_context("reports", "weekly_report")
            .with_topic("Weekly Reports")
            .with_incorrect("Reports are generated manually")
            .with_correct("Reports are automated")
            .with_keywords("reports, automation")
            .build()
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            serialize_context_store(context_store, temp_path)

            channel_dir = temp_path / "channels" / "data-team"

            # Verify channel system prompt
            prompt_path = channel_dir / "system_prompt.md"
            assert prompt_path.exists()
            assert prompt_path.read_text() == "Channel-specific prompt"

            # Verify channel cronjobs
            cronjobs_path = channel_dir / "cronjobs" / "weekly_summary.yaml"
            assert cronjobs_path.exists()
            with open(cronjobs_path) as f:
                cronjob = UserCronJob.model_validate(yaml.safe_load(f))
                assert cronjob.question == "What happened this week?"

            # Verify channel context
            context_path = channel_dir / "context" / "reports" / "weekly_report.yaml"
            assert context_path.exists()
            with open(context_path) as f:
                context_data = yaml.safe_load(f)
                assert context_data["topic"] == "Weekly Reports"

    def test_roundtrip_serialization(self):
        """Test that load → serialize → load produces equivalent context stores."""
        # Build a complex context store
        original = (
            context_store_builder()
            .with_project("test/project")
            .with_project_teams({"data": ["alice", "bob"], "eng": ["charlie"]})
            .with_system_prompt("Global system prompt")
            .add_general_cronjob("job1")
            .with_cron("0 0 * * *")
            .with_question("Question?")
            .with_thread("thread1")
            .add_dataset("postgres", "users")
            .with_markdown("# Users\nUser data")
            .add_general_context("db", "ctx1")
            .with_topic("Topic 1")
            .with_incorrect("Wrong")
            .with_correct("Right")
            .with_keywords("keywords")
            .new_channel("team-a")
            .with_channel_system_prompt("Channel prompt")
            .add_channel_cronjob("job2", "0 1 * * *", "Q2?", "thread2")
            .add_channel_context("cat", "ctx2")
            .with_topic("Topic 2")
            .with_incorrect("Wrong2")
            .with_correct("Right2")
            .with_keywords("kw2")
            .build()
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Serialize
            serialize_context_store(original, temp_path)

            # Load back
            tree = FilesystemFileTree(temp_path)
            reloaded = load_context_store(tree)

            # Verify key fields match
            assert reloaded.project.project_name == original.project.project_name
            assert reloaded.project.teams == original.project.teams
            assert reloaded.system_prompt == original.system_prompt
            assert len(reloaded.general_cronjobs) == len(original.general_cronjobs)
            assert len(reloaded.datasets) == len(original.datasets)
            assert len(reloaded.general_context) == len(original.general_context)
            assert len(reloaded.channels) == len(original.channels)

            # Verify dataset content
            assert reloaded.datasets[0][0].connection == "postgres"
            assert reloaded.datasets[0][0].table_name == "users"
            assert "Users" in reloaded.datasets[0][1].summary

            # Verify general context
            assert reloaded.general_context[0].group == "db"
            assert reloaded.general_context[0].name == "ctx1"
            assert reloaded.general_context[0].context.topic == "Topic 1"

            # Verify channel data
            assert "team-a" in reloaded.channels
            channel = reloaded.channels["team-a"]
            assert channel.system_prompt == "Channel prompt"
            assert "job2" in channel.cron_jobs
            assert len(channel.context) == 1
            assert channel.context[0].context.topic == "Topic 2"

    def test_serialize_empty_context_store(self):
        """Test serializing an empty context store with only project config."""
        context_store = context_store_builder().with_project("empty/project").build()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            serialize_context_store(context_store, temp_path)

            # Only project config should exist
            assert (temp_path / "contextstore_project.yaml").exists()

            # Other directories should not exist
            assert not (temp_path / "docs").exists()
            assert not (temp_path / "context").exists()
            assert not (temp_path / "channels").exists()
            assert not (temp_path / "system_prompt.md").exists()

    def test_update_cron_job(self):
        original = (
            context_store_builder()
            .add_general_cronjob(
                "blah",
                "* * * * *",
                "hello?",
                "my thread",
            )
            .build()
        )

        async def f():
            provider = FakeContextStoreManager(original)
            storage = UserCronStorage(
                provider,
                None,
            )
            name, job = next(iter((await storage.get_cron_jobs()).items()))
            await storage.add_cron_job(
                name,
                job.cron,
                job.question,
                job.thread,
                None,
            )
            updated_context_store = provider.get_last_mutation().after
            return updated_context_store

        updated = asyncio.run(f())

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            serialize_context_store(updated, temp_path)
            assert (temp_path / "cronjobs" / "blah.yaml").exists()
