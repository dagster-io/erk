"""User cron job storage management."""

from datetime import datetime
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from attr import dataclass
from croniter import croniter

from csbot.contextengine.contextstore_protocol import (
    ContextStore,
    UserCronJob,
)
from csbot.contextengine.protocol import ContextStoreManager
from csbot.slackbot.storage.interface import CRONJOB_PR_TITLE_PREFIX
from csbot.slackbot.usercron.models import (
    AddUserCronJobResult,
    DeleteUserCronJobResult,
    UpdateUserCronJobResult,
)
from csbot.utils.misc import normalize_channel_name

NO_CHANNEL_SENTINEL = "<general>"


@runtime_checkable
class UserCronStorageProtocol(Protocol):
    """Protocol for sync cron job management operations."""

    def get_cron_jobs(self) -> dict[str, UserCronJob]:
        """Get all cron jobs."""
        ...

    async def add_cron_job(
        self,
        cron_job_name: str,
        cron_string: str,
        question: str,
        thread: str,
        attribution: str | None,
    ) -> AddUserCronJobResult:
        """Add a cron job."""
        ...

    async def update_cron_job(
        self, cron_job_name: str, additional_context: str, attribution: str | None
    ) -> UpdateUserCronJobResult:
        """Update a cron job by appending additional context to the question."""
        ...

    async def delete_cron_job(
        self, cron_job_name: str, attribution: str | None
    ) -> DeleteUserCronJobResult:
        """Delete a cron job."""
        ...


@dataclass(frozen=True)
class CronJobIdentifier:
    channel: str | None
    name: str

    @classmethod
    def from_string(cls, s: str):
        try:
            maybe_channel, name = s.split("/")
        except ValueError:
            raise ValueError(
                f"Malformed CronJobIdentifier: {s} (expected <channel_name>/<job_name>)"
            )
        if maybe_channel == NO_CHANNEL_SENTINEL:
            channel = None
        else:
            channel = maybe_channel
        return cls(channel=channel, name=name)


class UserCronStorage:
    """Sync implementation of user-defined cron job storage operations."""

    def __init__(
        self,
        context_store_manager: ContextStoreManager,
        normalized_channel_name: str | None,
    ) -> None:
        if (
            normalized_channel_name
            and normalize_channel_name(normalized_channel_name) != normalized_channel_name
        ):
            raise ValueError(f"Channel name was not normalized: {normalized_channel_name}")
        self.context_store_manager = context_store_manager
        self.normalized_channel_name = normalized_channel_name

    def _get_cron_jobs_by_id(
        self, context_store: ContextStore
    ) -> dict[CronJobIdentifier, UserCronJob]:
        rv = {}
        for cron_job_name, cron_job in context_store.general_cronjobs.items():
            rv[CronJobIdentifier(channel=None, name=cron_job_name)] = cron_job
        for channel_name, channel in context_store.channels.items():
            if self.normalized_channel_name and self.normalized_channel_name != channel_name:
                continue
            for cron_job_name, cron_job in channel.cron_jobs.items():
                rv[CronJobIdentifier(channel=channel_name, name=cron_job_name)] = cron_job
        return rv

    async def get_cron_jobs(self) -> dict[str, UserCronJob]:
        context_store = await self.context_store_manager.get_context_store()
        return {
            f"{key.channel or NO_CHANNEL_SENTINEL}/{key.name}": job
            for key, job in self._get_cron_jobs_by_id(context_store).items()
        }

    async def add_cron_job(
        self,
        cron_job_name: str,
        cron_string: str,
        question: str,
        thread: str,
        attribution: str | None,
    ) -> AddUserCronJobResult:
        """Add a cron job."""
        try:
            cron_job_id = CronJobIdentifier.from_string(cron_job_name)
        except ValueError:
            cron_job_id = CronJobIdentifier(channel=None, name=cron_job_name)

        cron_job = UserCronJob(cron=cron_string, question=question, thread=thread)

        now = datetime.now()
        try:
            croniter(cron_job.cron, now).get_next(datetime)
        except Exception as e:
            raise ValueError(
                f"Cron job '{cron_job_name}' has invalid schedule '{cron_string}': {e}"
            ) from e

        body = f"New cron job:\n\nThread: {cron_job.thread}\nQuestion: {cron_job.question}"
        if attribution:
            body = f"{attribution}\n\n{body}"

        context_store = await self.context_store_manager.get_context_store()

        if cron_job_id.channel is None:
            updated = context_store.model_copy(
                update={
                    "general_cronjobs": {
                        **context_store.general_cronjobs,
                        cron_job_id.name: cron_job,
                    }
                }
            )
        else:
            updated = context_store.update_channel(
                cron_job_id.channel,
                lambda channel: channel.update_cronjob(cron_job_id.name, cron_job),
            )

        mutation_token = await self.context_store_manager.mutate(
            f"CRONJOB: {cron_job.thread}", body, False, before=context_store, after=updated
        )

        return AddUserCronJobResult(cron_job_review_url=mutation_token)

    async def update_cron_job(
        self, cron_job_name: str, additional_context: str, attribution: str | None
    ) -> UpdateUserCronJobResult:
        """Update a cron job by appending additional context to the question."""
        context_store = await self.context_store_manager.get_context_store()
        cron_job_id = CronJobIdentifier.from_string(cron_job_name)
        existing_cron_jobs = self._get_cron_jobs_by_id(context_store)
        if cron_job_id not in existing_cron_jobs:
            raise ValueError(f"Scheduled analysis '{cron_job_name}' not found")

        existing_cron_job = existing_cron_jobs[cron_job_id]

        updated_question = (
            f"{existing_cron_job.question}\n\nAdditional context: {additional_context}"
        )
        updated_cron_job = UserCronJob(
            cron=existing_cron_job.cron, question=updated_question, thread=existing_cron_job.thread
        )

        body = f"Updated cron job: {cron_job_name}\n\nAdded context: {additional_context}"
        if attribution:
            body = f"{attribution}\n\n{body}"

        if cron_job_id.channel:
            update = context_store.update_channel(
                cron_job_id.channel,
                lambda channel_context: channel_context.update_cronjob(
                    cron_job_id.name, updated_cron_job
                ),
            )
        else:
            update = context_store.model_copy(
                update={
                    "general_cronjobs": {
                        **context_store.general_cronjobs,
                        cron_job_id.name: updated_cron_job,
                    },
                },
            )

        mutation_token = await self.context_store_manager.mutate(
            f"{CRONJOB_PR_TITLE_PREFIX} {existing_cron_job.thread}",
            body,
            False,
            before=context_store,
            after=update,
        )

        return UpdateUserCronJobResult(cron_job_review_url=mutation_token)

    async def delete_cron_job(
        self, cron_job_name: str, attribution: str | None
    ) -> DeleteUserCronJobResult:
        """Delete a cron job."""
        context_store = await self.context_store_manager.get_context_store()
        cron_job_id = CronJobIdentifier.from_string(cron_job_name)
        existing_cron_jobs = self._get_cron_jobs_by_id(context_store)
        if cron_job_id not in existing_cron_jobs:
            raise ValueError(f"Scheduled analysis '{cron_job_name}' not found")

        existing_cron_job = existing_cron_jobs[cron_job_id]

        body = f"Deleted cron job: {cron_job_name}\n\nThread: {existing_cron_job.thread}"
        if attribution:
            body = f"{attribution}\n\n{body}"

        if cron_job_id.channel:
            update = context_store.update_channel(
                cron_job_id.channel,
                lambda channel_context: channel_context.remove_cronjob(cron_job_id.name),
            )
        else:
            cronjobs = {**context_store.general_cronjobs}
            del cronjobs[cron_job_id.name]
            update = context_store.model_copy(update={"general_cronjobs": cronjobs})

        mutation_token = await self.context_store_manager.mutate(
            f"CRONJOB DELETE: {existing_cron_job.thread}",
            body,
            False,
            before=context_store,
            after=update,
        )

        return DeleteUserCronJobResult(cron_job_review_url=mutation_token)


# Type checking to ensure UserCronStorage implements the protocol correctly
if TYPE_CHECKING:
    _: UserCronStorageProtocol = UserCronStorage(...)  # type: ignore[abstract]
