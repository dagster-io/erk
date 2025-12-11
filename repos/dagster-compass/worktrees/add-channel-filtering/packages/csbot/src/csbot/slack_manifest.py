"""
Pydantic models for Slack bot manifest files.
"""

from pydantic import BaseModel


class DisplayInformation(BaseModel):
    name: str
    description: str
    background_color: str


class BotUser(BaseModel):
    display_name: str
    always_online: bool


class SlashCommand(BaseModel):
    command: str
    url: str
    description: str
    should_escape: bool


class Features(BaseModel):
    bot_user: BotUser
    slash_commands: list[SlashCommand] | None = None


class Scopes(BaseModel):
    bot: list[str]
    user: list[str] | None = None


class OAuthConfig(BaseModel):
    scopes: Scopes


class EventSubscriptions(BaseModel):
    request_url: str | None = None
    bot_events: list[str]


class Interactivity(BaseModel):
    is_enabled: bool
    request_url: str | None = None


class Settings(BaseModel):
    event_subscriptions: EventSubscriptions
    interactivity: Interactivity
    org_deploy_enabled: bool
    socket_mode_enabled: bool
    token_rotation_enabled: bool


class SlackBotManifest(BaseModel):
    display_information: DisplayInformation
    features: Features
    oauth_config: OAuthConfig
    settings: Settings
