"""Tests for context store promotion logic."""

from csbot.contextengine.contextstore_protocol import ContextStore, ContextStoreProject, UserCronJob
from csbot.contextengine.diff import compute_diff
from csbot.contextengine.promotion import promote_general_to_channel


def test_promote_general_cronjob_to_channel():
    """Test promoting a general cron job to a channel-specific cron job."""
    # Create base context store with no cron jobs
    base_store = ContextStore(
        project=ContextStoreProject(project_name="test/project", version=1),
        datasets=[],
        general_context=[],
        general_cronjobs={},
        channels={},
        system_prompt=None,
    )

    # Create head context store with one general cron job
    head_store = ContextStore(
        project=ContextStoreProject(project_name="test/project", version=1),
        datasets=[],
        general_context=[],
        general_cronjobs={
            "daily_report": UserCronJob(
                cron="0 9 * * *",
                question="What are the key metrics for today?",
                thread="Daily Report",
            )
        },
        channels={},
        system_prompt=None,
    )

    # Compute diff
    diff = compute_diff(base_store, head_store)

    # Verify diff shows the cron job was added
    assert len(diff.general_cronjobs_added) == 1
    assert "daily_report" in diff.general_cronjobs_added

    # Promote to channel-specific
    channel_name = "test-channel"
    promoted_store = promote_general_to_channel(head_store, diff, channel_name)

    # Verify the promoted store has the cron job in the channel
    assert channel_name in promoted_store.channels
    channel_context = promoted_store.channels[channel_name]
    assert len(channel_context.cron_jobs) == 1
    assert "daily_report" in channel_context.cron_jobs

    # Verify the cron job has the correct properties
    channel_cron_job = channel_context.cron_jobs["daily_report"]
    assert channel_cron_job.cron == "0 9 * * *"
    assert channel_cron_job.question == "What are the key metrics for today?"
    assert channel_cron_job.thread == "Daily Report"

    # Verify the cron job was removed from general
    assert len(promoted_store.general_cronjobs) == 0
    assert "daily_report" not in promoted_store.general_cronjobs
