"""Dataclasses for representing diffs between ContextStore instances."""

from typing import TYPE_CHECKING

from attr import dataclass

from csbot.contextengine.contextstore_protocol import (
    ChannelContext,
    ContextStoreProject,
    Dataset,
    DatasetDocumentation,
    NamedContext,
    UserCronJob,
)

if TYPE_CHECKING:
    from csbot.contextengine.contextstore_protocol import ContextStore


@dataclass(frozen=True)
class ProjectDiff:
    """Diff for ContextStoreProject."""

    project_name_changed: bool
    new_project_name: str | None  # New project name (if changed)
    version_changed: bool
    new_version: int | None  # New version (if changed)
    teams_added: dict[str, list[str]]  # team_name -> members
    teams_removed: set[str]
    teams_modified: dict[
        str, tuple[list[str], list[str]]
    ]  # team_name -> (old_members, new_members)


@dataclass(frozen=True)
class DatasetDiff:
    """Diff for a single dataset."""

    dataset: Dataset
    documentation_changed: bool
    old_documentation: DatasetDocumentation | None
    new_documentation: DatasetDocumentation | None


@dataclass(frozen=True)
class NamedContextDiff:
    """Diff for a single named context entry."""

    group: str
    name: str
    topic_changed: bool
    incorrect_understanding_changed: bool
    correct_understanding_changed: bool
    search_keywords_changed: bool
    old_context: NamedContext | None
    new_context: NamedContext | None


@dataclass(frozen=True)
class CronJobDiff:
    """Diff for a single cron job."""

    name: str
    cron_changed: bool
    question_changed: bool
    thread_changed: bool
    old_cron_job: UserCronJob | None
    new_cron_job: UserCronJob | None


@dataclass(frozen=True)
class ChannelContextDiff:
    """Diff for a single channel's context."""

    channel_name: str
    system_prompt_changed: bool
    cron_jobs_added: dict[str, UserCronJob]
    cron_jobs_removed: set[str]
    cron_jobs_modified: list[CronJobDiff]
    context_added: list[NamedContext]
    context_removed: list[NamedContext]
    context_modified: list[NamedContextDiff]
    old_channel_context: ChannelContext | None
    new_channel_context: ChannelContext | None


@dataclass(frozen=True)
class ContextStoreDiff:
    """Complete diff between two ContextStore instances."""

    # Project changes
    project_diff: ProjectDiff | None

    # System prompt changes
    system_prompt_changed: bool
    new_system_prompt: str | None  # The new system prompt value (if changed)

    # Dataset changes
    datasets_added: list[tuple[Dataset, DatasetDocumentation]]
    datasets_removed: list[Dataset]
    datasets_modified: list[DatasetDiff]

    # General context changes
    general_context_added: list[NamedContext]
    general_context_removed: list[NamedContext]
    general_context_modified: list[NamedContextDiff]

    # General cron jobs changes
    general_cronjobs_added: dict[str, UserCronJob]
    general_cronjobs_removed: set[str]
    general_cronjobs_modified: list[CronJobDiff]

    # Channel changes
    channels_added: dict[str, ChannelContext]  # channel_name -> ChannelContext
    channels_removed: set[str]
    channels_modified: list[ChannelContextDiff]

    def has_changes(self) -> bool:
        """Check if there are any changes between the two context stores."""
        return (
            self.project_diff is not None
            or self.system_prompt_changed
            or len(self.datasets_added) > 0
            or len(self.datasets_removed) > 0
            or len(self.datasets_modified) > 0
            or len(self.general_context_added) > 0
            or len(self.general_context_removed) > 0
            or len(self.general_context_modified) > 0
            or len(self.general_cronjobs_added) > 0
            or len(self.general_cronjobs_removed) > 0
            or len(self.general_cronjobs_modified) > 0
            or len(self.channels_added) > 0
            or len(self.channels_removed) > 0
            or len(self.channels_modified) > 0
        )


def compare_projects(old: ContextStoreProject, new: ContextStoreProject) -> ProjectDiff | None:
    """Compare two ContextStoreProject instances and return a diff."""
    project_name_changed = old.project_name != new.project_name
    version_changed = old.version != new.version

    old_teams = set(old.teams.keys())
    new_teams = set(new.teams.keys())
    teams_added = {name: new.teams[name] for name in new_teams - old_teams}
    teams_removed = old_teams - new_teams

    teams_modified = {}
    for team_name in old_teams & new_teams:
        old_members = old.teams[team_name]
        new_members = new.teams[team_name]
        if old_members != new_members:
            teams_modified[team_name] = (old_members, new_members)

    if project_name_changed or version_changed or teams_added or teams_removed or teams_modified:
        return ProjectDiff(
            project_name_changed=project_name_changed,
            new_project_name=new.project_name if project_name_changed else None,
            version_changed=version_changed,
            new_version=new.version if version_changed else None,
            teams_added=teams_added,
            teams_removed=teams_removed,
            teams_modified=teams_modified,
        )
    return None


def compare_datasets(
    old_datasets: list[tuple[Dataset, DatasetDocumentation]],
    new_datasets: list[tuple[Dataset, DatasetDocumentation]],
) -> tuple[list[tuple[Dataset, DatasetDocumentation]], list[Dataset], list[DatasetDiff]]:
    """Compare dataset lists and return added, removed, and modified datasets.

    Preserves the order from new_datasets for added datasets.
    """
    old_dataset_map = {dataset: doc for dataset, doc in old_datasets}
    new_dataset_map = {dataset: doc for dataset, doc in new_datasets}

    old_keys = set(old_dataset_map.keys())
    new_keys = set(new_dataset_map.keys())

    # Preserve order from new_datasets by iterating through it
    added = [(dataset, doc) for dataset, doc in new_datasets if dataset not in old_keys]
    removed = [dataset for dataset, _ in old_datasets if dataset not in new_keys]

    modified = []
    for dataset in old_keys & new_keys:
        old_doc = old_dataset_map[dataset]
        new_doc = new_dataset_map[dataset]
        if old_doc != new_doc:
            modified.append(
                DatasetDiff(
                    dataset=dataset,
                    documentation_changed=True,
                    old_documentation=old_doc,
                    new_documentation=new_doc,
                )
            )

    return added, removed, modified


def compare_named_contexts(
    old_contexts: list[NamedContext], new_contexts: list[NamedContext]
) -> tuple[list[NamedContext], list[NamedContext], list[NamedContextDiff]]:
    """Compare named context lists and return added, removed, and modified contexts.

    Preserves order from new_contexts for added contexts.
    """
    old_context_map = {(ctx.group, ctx.name): ctx for ctx in old_contexts}
    new_context_map = {(ctx.group, ctx.name): ctx for ctx in new_contexts}

    old_keys = set(old_context_map.keys())
    new_keys = set(new_context_map.keys())

    # Preserve order from new_contexts
    added = [ctx for ctx in new_contexts if (ctx.group, ctx.name) not in old_keys]
    removed = [ctx for ctx in old_contexts if (ctx.group, ctx.name) not in new_keys]

    modified = []
    for key in old_keys & new_keys:
        old_ctx = old_context_map[key]
        new_ctx = new_context_map[key]
        if old_ctx.context != new_ctx.context:
            group, name = key
            modified.append(
                NamedContextDiff(
                    group=group,
                    name=name,
                    topic_changed=old_ctx.context.topic != new_ctx.context.topic,
                    incorrect_understanding_changed=old_ctx.context.incorrect_understanding
                    != new_ctx.context.incorrect_understanding,
                    correct_understanding_changed=old_ctx.context.correct_understanding
                    != new_ctx.context.correct_understanding,
                    search_keywords_changed=old_ctx.context.search_keywords
                    != new_ctx.context.search_keywords,
                    old_context=old_ctx,
                    new_context=new_ctx,
                )
            )

    return added, removed, modified


def compare_cron_jobs(
    old_jobs: dict[str, UserCronJob], new_jobs: dict[str, UserCronJob]
) -> tuple[dict[str, UserCronJob], set[str], list[CronJobDiff]]:
    """Compare cron job dictionaries and return added, removed, and modified jobs."""
    old_keys = set(old_jobs.keys())
    new_keys = set(new_jobs.keys())

    added = new_keys - old_keys
    removed = old_keys - new_keys

    modified = []
    for name in old_keys & new_keys:
        old_job = old_jobs[name]
        new_job = new_jobs[name]
        if old_job != new_job:
            modified.append(
                CronJobDiff(
                    name=name,
                    cron_changed=old_job.cron != new_job.cron,
                    question_changed=old_job.question != new_job.question,
                    thread_changed=old_job.thread != new_job.thread,
                    old_cron_job=old_job,
                    new_cron_job=new_job,
                )
            )

    return {key: new_jobs[key] for key in added}, removed, modified


def compare_channel_contexts(
    old_channels: dict[str, ChannelContext], new_channels: dict[str, ChannelContext]
) -> tuple[dict[str, ChannelContext], set[str], list[ChannelContextDiff]]:
    """Compare channel context dictionaries and return added, removed, and modified channels."""
    old_keys = set(old_channels.keys())
    new_keys = set(new_channels.keys())

    added = {name: new_channels[name] for name in new_keys - old_keys}
    removed = old_keys - new_keys

    modified = []
    for channel_name in old_keys & new_keys:
        old_channel = old_channels[channel_name]
        new_channel = new_channels[channel_name]

        system_prompt_changed = old_channel.system_prompt != new_channel.system_prompt

        cron_jobs_added, cron_jobs_removed, cron_jobs_modified = compare_cron_jobs(
            dict(old_channel.cron_jobs), dict(new_channel.cron_jobs)
        )

        (
            context_added,
            context_removed,
            context_modified,
        ) = compare_named_contexts(list(old_channel.context), list(new_channel.context))

        if (
            system_prompt_changed
            or cron_jobs_added
            or cron_jobs_removed
            or cron_jobs_modified
            or context_added
            or context_removed
            or context_modified
        ):
            modified.append(
                ChannelContextDiff(
                    channel_name=channel_name,
                    system_prompt_changed=system_prompt_changed,
                    cron_jobs_added=cron_jobs_added,
                    cron_jobs_removed=cron_jobs_removed,
                    cron_jobs_modified=cron_jobs_modified,
                    context_added=context_added,
                    context_removed=context_removed,
                    context_modified=context_modified,
                    old_channel_context=old_channel,
                    new_channel_context=new_channel,
                )
            )

    return added, removed, modified


def compute_diff(old_store: "ContextStore", new_store: "ContextStore") -> ContextStoreDiff:
    """Compute the complete diff between two ContextStore instances.

    Args:
        old_store: The original context store
        new_store: The new context store to compare against

    Returns:
        A ContextStoreDiff containing all differences between the stores
    """
    # Compare projects
    project_diff = compare_projects(old_store.project, new_store.project)

    # Compare system prompts
    system_prompt_changed = old_store.system_prompt != new_store.system_prompt

    # Compare datasets
    datasets_added, datasets_removed, datasets_modified = compare_datasets(
        old_store.datasets, new_store.datasets
    )

    # Compare general context
    (
        general_context_added,
        general_context_removed,
        general_context_modified,
    ) = compare_named_contexts(old_store.general_context, new_store.general_context)

    # Compare general cron jobs
    (
        general_cronjobs_added,
        general_cronjobs_removed,
        general_cronjobs_modified,
    ) = compare_cron_jobs(dict(old_store.general_cronjobs), dict(new_store.general_cronjobs))

    # Compare channels
    channels_added, channels_removed, channels_modified = compare_channel_contexts(
        dict(old_store.channels), dict(new_store.channels)
    )

    return ContextStoreDiff(
        project_diff=project_diff,
        system_prompt_changed=system_prompt_changed,
        new_system_prompt=new_store.system_prompt if system_prompt_changed else None,
        datasets_added=datasets_added,
        datasets_removed=datasets_removed,
        datasets_modified=datasets_modified,
        general_context_added=general_context_added,
        general_context_removed=general_context_removed,
        general_context_modified=general_context_modified,
        general_cronjobs_added=general_cronjobs_added,
        general_cronjobs_removed=general_cronjobs_removed,
        general_cronjobs_modified=general_cronjobs_modified,
        channels_added=channels_added,
        channels_removed=channels_removed,
        channels_modified=channels_modified,
    )


def apply_diff(context_store: "ContextStore", *diffs: ContextStoreDiff) -> "ContextStore":
    """Apply one or more ContextStoreDiffs to a ContextStore sequentially.

    Args:
        context_store: The base ContextStore to apply diffs to
        *diffs: One or more ContextStoreDiff objects to apply in order

    Returns:
        New ContextStore with all diffs applied
    """
    result = context_store

    for diff in diffs:
        # Apply project changes
        if diff.project_diff:
            # Apply project name change
            if diff.project_diff.project_name_changed and diff.project_diff.new_project_name:
                current_project = result.project
                result = result.model_copy(
                    update={
                        "project": current_project.model_copy(
                            update={"project_name": diff.project_diff.new_project_name}
                        )
                    }
                )

            # Apply version change
            if diff.project_diff.version_changed and diff.project_diff.new_version is not None:
                current_project = result.project
                result = result.model_copy(
                    update={
                        "project": current_project.model_copy(
                            update={"version": diff.project_diff.new_version}
                        )
                    }
                )

            # Apply team additions
            if diff.project_diff.teams_added:
                current_project = result.project
                new_teams = {**current_project.teams, **diff.project_diff.teams_added}
                result = result.model_copy(
                    update={"project": current_project.model_copy(update={"teams": new_teams})}
                )

            # Apply team modifications
            if diff.project_diff.teams_modified:
                current_project = result.project
                new_teams = dict(current_project.teams)
                for team_name, (
                    old_members,
                    new_members,
                ) in diff.project_diff.teams_modified.items():
                    new_teams[team_name] = new_members

                result = result.model_copy(
                    update={"project": current_project.model_copy(update={"teams": new_teams})}
                )

            # Apply team removals
            if diff.project_diff.teams_removed:
                current_project = result.project
                new_teams = {
                    name: members
                    for name, members in current_project.teams.items()
                    if name not in diff.project_diff.teams_removed
                }
                result = result.model_copy(
                    update={"project": current_project.model_copy(update={"teams": new_teams})}
                )

        # Apply system prompt changes
        if diff.system_prompt_changed:
            result = result.model_copy(update={"system_prompt": diff.new_system_prompt})

        # Apply dataset modifications
        for dataset_diff in diff.datasets_modified:
            if dataset_diff.new_documentation:
                result = result.add_or_update_dataset(
                    dataset_diff.dataset, dataset_diff.new_documentation
                )

        # Apply dataset additions (new datasets)
        for dataset_added in diff.datasets_added:
            result = result.model_copy(
                update={
                    "datasets": sorted(
                        [*result.datasets, dataset_added],
                        key=lambda ds: (ds[0].connection, ds[0].table_name),
                    )
                },
            )

        for dataset_removed in diff.datasets_removed:
            result = result.remove_dataset(dataset_removed)

        # Apply general context additions
        if diff.general_context_added:
            result = result.model_copy(
                update={
                    "general_context": sorted(
                        [
                            *result.general_context,
                            *diff.general_context_added,
                        ],
                        key=lambda c: (c.group, c.name),
                    )
                }
            )

        # Apply general context removals
        if diff.general_context_removed:
            removed_keys = {(ctx.group, ctx.name) for ctx in diff.general_context_removed}
            new_contexts = [
                ctx for ctx in result.general_context if (ctx.group, ctx.name) not in removed_keys
            ]
            result = result.model_copy(update={"general_context": new_contexts})

        # Apply general context modifications
        for ctx_diff in diff.general_context_modified:
            if ctx_diff.new_context:
                # Remove old, add new
                new_contexts = [
                    ctx
                    for ctx in result.general_context
                    if not (ctx.group == ctx_diff.group and ctx.name == ctx_diff.name)
                ]
                new_contexts.append(ctx_diff.new_context)
                new_contexts.sort(key=lambda ctx: (ctx.group, ctx.name))
                result = result.model_copy(update={"general_context": new_contexts})

        # Apply general cronjob additions
        if diff.general_cronjobs_added:
            result = result.model_copy(
                update={
                    "general_cronjobs": {
                        **result.general_cronjobs,
                        **diff.general_cronjobs_added,
                    }
                }
            )

        # Apply general cronjob removals
        if diff.general_cronjobs_removed:
            new_cronjobs = {
                name: job
                for name, job in result.general_cronjobs.items()
                if name not in diff.general_cronjobs_removed
            }
            result = result.model_copy(update={"general_cronjobs": new_cronjobs})

        # Apply general cronjob modifications
        for job_diff in diff.general_cronjobs_modified:
            if job_diff.new_cron_job:
                result = result.model_copy(
                    update={
                        "general_cronjobs": {
                            **result.general_cronjobs,
                            job_diff.name: job_diff.new_cron_job,
                        }
                    }
                )

        # Apply channel removals
        if diff.channels_removed:
            new_channels = {
                name: ctx
                for name, ctx in result.channels.items()
                if name not in diff.channels_removed
            }
            result = result.model_copy(update={"channels": new_channels})

        # Apply channel additions
        if diff.channels_added:
            result = result.model_copy(
                update={"channels": {**result.channels, **diff.channels_added}}
            )

        # Apply channel modifications
        for channel_diff in diff.channels_modified:
            # Get the current channel context or create a new one
            if channel_diff.channel_name in result.channels:
                current_channel = result.channels[channel_diff.channel_name]
            else:
                current_channel = ChannelContext(cron_jobs={}, context=[], system_prompt=None)

            # Apply system prompt change
            updated_channel = current_channel
            if channel_diff.system_prompt_changed and channel_diff.new_channel_context:
                updated_channel = updated_channel.model_copy(
                    update={"system_prompt": channel_diff.new_channel_context.system_prompt}
                )

            # Apply context additions
            if channel_diff.context_added:
                new_contexts = [*updated_channel.context, *channel_diff.context_added]
                new_contexts.sort(key=lambda ctx: (ctx.group, ctx.name))
                updated_channel = updated_channel.model_copy(update={"context": new_contexts})

            # Apply context modifications
            for ctx_diff in channel_diff.context_modified:
                if ctx_diff.new_context:
                    # Remove old, add new
                    new_contexts = [
                        ctx
                        for ctx in updated_channel.context
                        if not (ctx.group == ctx_diff.group and ctx.name == ctx_diff.name)
                    ]
                    new_contexts.append(ctx_diff.new_context)
                    new_contexts.sort(key=lambda ctx: (ctx.group, ctx.name))
                    updated_channel = updated_channel.model_copy(update={"context": new_contexts})

            # Apply context removals
            if channel_diff.context_removed:
                removed_keys = {(ctx.group, ctx.name) for ctx in channel_diff.context_removed}
                new_contexts = [
                    ctx
                    for ctx in updated_channel.context
                    if (ctx.group, ctx.name) not in removed_keys
                ]
                updated_channel = updated_channel.model_copy(update={"context": new_contexts})

            # Apply cronjob additions
            if channel_diff.cron_jobs_added:
                updated_channel = updated_channel.model_copy(
                    update={
                        "cron_jobs": {**updated_channel.cron_jobs, **channel_diff.cron_jobs_added}
                    }
                )

            # Apply cronjob modifications
            for job_diff in channel_diff.cron_jobs_modified:
                if job_diff.new_cron_job:
                    updated_channel = updated_channel.model_copy(
                        update={
                            "cron_jobs": {
                                **updated_channel.cron_jobs,
                                job_diff.name: job_diff.new_cron_job,
                            }
                        }
                    )

            # Apply cronjob removals
            if channel_diff.cron_jobs_removed:
                new_cron_jobs = {
                    name: job
                    for name, job in updated_channel.cron_jobs.items()
                    if name not in channel_diff.cron_jobs_removed
                }
                updated_channel = updated_channel.model_copy(update={"cron_jobs": new_cron_jobs})

            # Update the channel in the result
            result = result.model_copy(
                update={
                    "channels": {
                        **result.channels,
                        channel_diff.channel_name: updated_channel,
                    }
                }
            )

    return result
