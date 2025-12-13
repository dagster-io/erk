"""
Protocol definitions for the Context Engine.

This is a cross-cutting protocol file that spans all the domains that the context engine manages.
It defines shared interfaces, data models, and contracts used across different components of the
context engine, including context storage, dataset search, cron jobs, and git integration.
"""

from collections.abc import Callable, Mapping
from typing import Literal, Self

from attr import dataclass
from csadmin.models import ContextStoreProject, ProvidedContext, UserCronJob
from pydantic import BaseModel, Field

NO_CHANNEL_SENTINEL = "<general>"


class TableFrontmatter(BaseModel):
    """Frontmatter metadata for dataset documentation."""

    schema_hash: str
    columns: list[str] | None = None


class DatasetDocumentation(BaseModel, frozen=True):
    """Dataset documentation including frontmatter and summary (without frontmatter)."""

    frontmatter: TableFrontmatter | None
    summary: str


class ContextAddition(BaseModel):
    topic: str
    incorrect_understanding: str
    correct_understanding: str


class ContextAdditionRequest(ContextAddition):
    comment_for_reviewer: str | None


class AddContextParams(ContextAdditionRequest):
    pass


ContextAdditionRequestDecisionStatus = Literal["approved"] | Literal["rejected"]
ContextAdditionRequestStatus = Literal["pending"] | ContextAdditionRequestDecisionStatus


class SearchContextParams(BaseModel):
    query: str


class SearchDatasetsParams(BaseModel):
    query: str
    connection: str | None = Field(default=None)
    full: bool = False


class GitCommitInfo(BaseModel):
    hash: str
    author: str
    email: str
    message: str
    time: int


class GitInfo(BaseModel):
    repository: str
    branch: str
    last_commit: GitCommitInfo


class SearchContextResult(BaseModel):
    topic: str
    incorrect_understanding: str
    correct_understanding: str


class AddContextResult(BaseModel):
    context_review_url: str | None
    context_summary: str


class CtxInfo(BaseModel):
    project_config: ContextStoreProject
    git_info: GitInfo | None


class DatasetSearchResult(BaseModel):
    connection: str
    table: str
    docs_markdown: str | None
    object_id: str | None = Field(
        default=None, description="Object ID for manifest layout (V2 only)"
    )


class DatasetSearchResultWithConnectionSqlDialect(DatasetSearchResult):
    connection_sql_dialect: str


class Dataset(BaseModel, frozen=True):
    connection: str
    table_name: str


class NamedContext(BaseModel, frozen=True):
    group: str
    name: str
    context: ProvidedContext


@dataclass
class ContextIdentifier:
    channel: str | None
    group: str
    name: str

    @classmethod
    def from_string(cls, s: str):
        maybe_channel, group, name = s.split("/")
        if maybe_channel == NO_CHANNEL_SENTINEL:
            channel = None
        else:
            channel = maybe_channel
        return cls(channel=channel, group=group, name=name)


def _find_context(group: str, name: str, contexts: list[NamedContext]):
    for ctx in contexts:
        if ctx.group == group and ctx.name == name:
            return ctx.context

    available = ", ".join(f"{ctx.group}/{ctx.name}" for ctx in contexts)
    raise ValueError(
        f"Unable to find context with group={group}, name={name}. Available: {available}"
    )


class ChannelContext(BaseModel, frozen=True):
    cron_jobs: Mapping[str, UserCronJob]
    context: list[NamedContext]
    system_prompt: str | None = None

    def model_post_init(self, __context) -> None:
        """Sort context to ensure consistent ordering."""
        sorted_context = sorted(self.context, key=lambda x: (x.group, x.name))
        object.__setattr__(self, "context", sorted_context)

    def update_cronjob(self, name: str, cron_job: UserCronJob) -> Self:
        return self.model_copy(
            update={
                "cron_jobs": {
                    **self.cron_jobs,
                    name: cron_job,
                },
            },
        )

    def remove_cronjob(self, name: str) -> Self:
        cron_jobs = {**self.cron_jobs}
        del cron_jobs[name]
        return self.model_copy(
            update={
                "cron_jobs": cron_jobs,
            },
        )


class ContextStore(BaseModel, frozen=True):
    project: ContextStoreProject
    datasets: list[tuple[Dataset, DatasetDocumentation]]
    general_context: list[NamedContext]
    general_cronjobs: Mapping[str, UserCronJob]
    channels: Mapping[str, ChannelContext]
    system_prompt: str | None = None

    def model_post_init(self, __context) -> None:
        """Sort datasets and general_context to ensure consistent ordering."""
        # Sort datasets by (connection, table_name)
        sorted_datasets = sorted(self.datasets, key=lambda x: (x[0].connection, x[0].table_name))
        object.__setattr__(self, "datasets", sorted_datasets)

        # Sort general_context by (group, name)
        sorted_context = sorted(self.general_context, key=lambda x: (x.group, x.name))
        object.__setattr__(self, "general_context", sorted_context)

    def update_channel(self, channel: str, cb: Callable[[ChannelContext], ChannelContext]) -> Self:
        return self.model_copy(
            update={
                "channels": {**self.channels, channel: cb(self.channels[channel])},
            }
        )

    def get_context(self, context_id: ContextIdentifier) -> ProvidedContext:
        if context_id.channel is None:
            return _find_context(context_id.group, context_id.name, self.general_context)
        else:
            return _find_context(
                context_id.group, context_id.name, self.channels[context_id.channel].context
            )

    def add_or_update_dataset(self, dataset: Dataset, documentation: DatasetDocumentation) -> Self:
        for idx, (candidate_dataset, _) in enumerate(self.datasets):
            if dataset == candidate_dataset:
                return self.model_copy(
                    update={
                        "datasets": self.datasets[:idx]
                        + [(dataset, documentation)]
                        + self.datasets[idx + 1 :]
                    }
                )

        # dataset not found, add it
        new_datasets = sorted(
            [*self.datasets, (dataset, documentation)],
            key=lambda x: (x[0].connection, x[0].table_name),
        )
        return self.model_copy(update={"datasets": new_datasets})

    def remove_dataset(self, dataset: Dataset) -> Self:
        for idx, (candidate_dataset, _) in enumerate(self.datasets):
            if dataset == candidate_dataset:
                return self.model_copy(
                    update={"datasets": self.datasets[:idx] + self.datasets[idx + 1 :]}
                )
        available = ", ".join(
            f"{dataset.connection}/{dataset.table_name}" for dataset, _ in self.datasets
        )
        raise ValueError(f"Couldn't find dataset {dataset}. Datasets: {available}")
