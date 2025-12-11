"""Promotion logic for context store changes.

This module handles promoting general context store changes to channel-specific changes.
"""

from csbot.contextengine.contextstore_protocol import ChannelContext, ContextStore
from csbot.contextengine.diff import ContextStoreDiff


def promote_general_to_channel(
    store: ContextStore, diff: ContextStoreDiff, channel_name: str
) -> ContextStore:
    """Promote general changes to channel-specific changes.

    This function takes a context store and a diff, and promotes all general additions
    (context and cron jobs) to be channel-specific instead.

    Args:
        store: The context store to promote changes in
        diff: The diff containing changes to promote
        channel_name: The channel name to promote changes to

    Returns:
        A new ContextStore with general additions promoted to channel-specific
    """
    promoted_store = store

    # Ensure channel exists
    if channel_name not in promoted_store.channels:
        promoted_store = promoted_store.model_copy(
            update={
                "channels": {
                    **promoted_store.channels,
                    channel_name: ChannelContext(cron_jobs={}, context=[], system_prompt=None),
                }
            }
        )

    # Promote general context to channel context
    if diff.general_context_added:
        channel_context = promoted_store.channels[channel_name]
        new_context_list = list(channel_context.context) + diff.general_context_added
        promoted_store = promoted_store.update_channel(
            channel_name,
            lambda ch: ch.model_copy(update={"context": new_context_list}),
        )

        # Remove from general context
        new_general_context = [
            ctx for ctx in promoted_store.general_context if ctx not in diff.general_context_added
        ]
        promoted_store = promoted_store.model_copy(update={"general_context": new_general_context})

    # Promote general cron jobs to channel cron jobs
    if diff.general_cronjobs_added:
        channel_context = promoted_store.channels[channel_name]
        new_cron_jobs = dict(channel_context.cron_jobs)
        for job_name in diff.general_cronjobs_added:
            if job_name in store.general_cronjobs:
                new_cron_jobs[job_name] = store.general_cronjobs[job_name]

        promoted_store = promoted_store.update_channel(
            channel_name,
            lambda ch: ch.model_copy(update={"cron_jobs": new_cron_jobs}),
        )

        # Remove from general cron jobs
        new_general_cronjobs = {
            name: job
            for name, job in promoted_store.general_cronjobs.items()
            if name not in diff.general_cronjobs_added
        }
        promoted_store = promoted_store.model_copy(
            update={"general_cronjobs": new_general_cronjobs}
        )

    return promoted_store
