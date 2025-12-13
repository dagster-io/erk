"""User cron job data models."""

from pydantic import BaseModel

from csbot.contextengine.contextstore_protocol import UserCronJob

__all__ = [
    "UserCronJob",
    "AddUserCronJobResult",
    "UpdateUserCronJobResult",
    "DeleteUserCronJobResult",
]


class AddUserCronJobResult(BaseModel):
    """Result of adding a cron job."""

    cron_job_review_url: str


class UpdateUserCronJobResult(BaseModel):
    """Result of updating a cron job."""

    cron_job_review_url: str


class DeleteUserCronJobResult(BaseModel):
    """Result of deleting a cron job."""

    cron_job_review_url: str
