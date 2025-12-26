from typing import Any

from pydantic import BaseModel, Field


class ConnectionProfile(BaseModel):
    url: str
    connect_args: dict[str, Any] = Field(default_factory=dict)
    init_sql: list[str] = Field(default_factory=list)
    additional_sql_dialect: str | None


class ProjectProfile(BaseModel):
    connections: dict[str, ConnectionProfile] = Field(default_factory=dict)
