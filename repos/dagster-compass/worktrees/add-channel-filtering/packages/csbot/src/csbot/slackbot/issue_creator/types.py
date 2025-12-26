from typing import Protocol


class IssueCreator(Protocol):
    async def create_issue(self, title: str, body: str, attribution: str | None) -> str: ...
