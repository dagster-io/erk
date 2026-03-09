"""Types for remote GitHub PR operations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RemotePRInfo:
    """PR-specific fields from the GitHub REST API pulls endpoint.

    Contains head_ref_name and base_ref_name that the issues endpoint
    does not provide.
    """

    number: int
    title: str
    state: str
    url: str
    head_ref_name: str
    base_ref_name: str
    owner: str
    repo: str
    labels: list[str]


@dataclass(frozen=True)
class RemotePRNotFound:
    """Sentinel indicating a PR was not found."""

    pr_number: int
