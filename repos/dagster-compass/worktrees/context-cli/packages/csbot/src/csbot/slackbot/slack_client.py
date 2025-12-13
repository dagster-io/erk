"""Factory for creating Slack clients with retry handlers configured."""

from slack_sdk.web.async_client import AsyncWebClient


def create_slack_client(token: str) -> AsyncWebClient:
    return AsyncWebClient(token=token)
