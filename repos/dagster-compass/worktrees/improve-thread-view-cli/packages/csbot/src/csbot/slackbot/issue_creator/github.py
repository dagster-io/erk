import asyncio

from pygit2 import TYPE_CHECKING

from csbot.local_context_store.github.api import create_data_request_issue
from csbot.local_context_store.github.config import GithubConfig


class GithubIssueCreator:
    def __init__(self, github_config: GithubConfig):
        self._github_config = github_config

    async def create_issue(self, title: str, body: str, attribution: str | None) -> str:
        return await asyncio.to_thread(
            create_data_request_issue, self._github_config, title, body, attribution
        )


if TYPE_CHECKING:
    from csbot.slackbot.issue_creator.types import IssueCreator

    _: IssueCreator = GithubIssueCreator()  # type: ignore[abstract]
