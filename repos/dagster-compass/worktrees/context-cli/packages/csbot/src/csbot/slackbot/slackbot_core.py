import asyncio
import json
import os
import tempfile
from functools import cache
from pathlib import Path
from typing import Any, Literal

import jinja2
import yaml
from dotenv import find_dotenv, load_dotenv
from pydantic import BaseModel, Field, SecretStr, model_validator

from csbot.csbot_client.csbot_profile import ConnectionProfile
from csbot.local_context_store.github.config import (
    GitHubAppAuthSource,
    GithubAuthSource,
    PATGithubAuthSource,
)
from csbot.slackbot.config import DatabaseConfig
from csbot.slackbot.slackbot_dataviz import ChartConfig
from csbot.slackbot.slackbot_secrets import SecretStore
from csbot.slackbot.storage.interface import BotInstanceType, ProspectorDataType

# Connection name constants
PROSPECTOR_CONNECTION_NAME = "bigquery_compass_prospector_us"

# AI provider configuration
AIProvider = Literal["anthropic"]

# Model type aliases for each provider
AnthropicModel = Literal[
    "claude-opus-4-1-20250805",
    "claude-opus-4-20250514",
    "claude-sonnet-4-20250514",
    "claude-3-7-sonnet-20250219",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
    "claude-3-5-sonnet-20240620",
    "claude-3-haiku-20240307",
    "claude-3-opus-20240229",
    "claude-sonnet-4-5-20250929",
    "claude-haiku-4-5-20251001",
]


class AnthropicConfig(BaseModel):
    provider: Literal["anthropic"]
    api_key: SecretStr
    model: AnthropicModel = "claude-sonnet-4-20250514"


class BedrockConfig(BaseModel):
    provider: Literal["bedrock"]
    aws_access_key: str | None = None
    aws_secret_key: SecretStr | None = None
    aws_region: str | None = None
    inference_profile_arn: str

    @model_validator(mode="after")
    def validate_model(self):
        aws_params = [self.aws_access_key, self.aws_secret_key, self.aws_region]
        valid = all(aws_params) or not any(aws_params)
        if not valid:
            raise ValueError(
                "either all of (aws_access_key, aws_secret_key, aws_region) must be set, or none (in which case it will use AWS default credentials/region"
            )

        return self


AIConfig = AnthropicConfig | BedrockConfig


class BotGitHubConfig(BaseModel):
    """Configuration for GitHub integration supporting both PAT and GitHub App authentication."""

    # Personal Access Token configuration (simpler setup)
    token: SecretStr | None = Field(default=None)

    # GitHub App configuration (preferred for organizations)
    app_id: int | None = Field(default=None)
    installation_id: int | None = Field(default=None)
    private_key_path: str | None = Field(default=None)

    # GitHub App OAuth configuration (for user authorization flows)
    client_id: str | None = Field(default=None)
    client_secret: SecretStr | None = Field(default=None)

    # Internal caching for GitHub App tokens (not exposed in config)
    cached_token: str | None = Field(default=None, exclude=True)
    token_expires_at: int | None = Field(default=None, exclude=True)

    rate_limiting_monitor_enabled: bool = Field(default=False)

    def model_post_init(self, __context: Any) -> None:  # noqa: ARG002
        """Validate that either PAT or GitHub App config is provided."""
        has_token = self.token is not None
        has_app_config = all([self.app_id, self.installation_id, self.private_key_path])

        if not has_token and not has_app_config:
            raise ValueError(
                "Either 'token' (Personal Access Token) or GitHub App credentials "
                "(app_id, installation_id, private_key_path) must be provided"
            )

        if has_token and has_app_config:
            raise ValueError(
                "Cannot specify both 'token' and GitHub App credentials. "
                "Use either Personal Access Token or GitHub App authentication, not both."
            )

    def is_github_app(self) -> bool:
        """Check if this configuration uses GitHub App authentication."""
        return self.app_id is not None

    def get_auth_source(self) -> GithubAuthSource:
        """Get the authentication token, handling both PAT and GitHub App."""

        if self.is_github_app():
            assert self.app_id is not None
            assert self.installation_id is not None
            assert self.private_key_path is not None
            return GitHubAppAuthSource(
                app_id=self.app_id,
                installation_id=self.installation_id,
                private_key_path=self.private_key_path,
            )
        elif self.token:
            return PATGithubAuthSource(token=self.token.get_secret_value())

        raise ValueError("No valid GitHub authentication configuration found")


class StripeConfig(BaseModel):
    """Configuration for Stripe integration."""

    token: SecretStr | None = Field(default=None)
    publishable_key: str | None = Field(default=None)
    free_product_id: str | None = Field(default=None)
    starter_product_id: str | None = Field(default=None)
    team_product_id: str | None = Field(default=None)
    design_partner_product_id: str | None = Field(default=None)
    default_product: str | None = Field(default=None)  # Can be "free", "starter", or "team"

    def get_default_product_id(self) -> str | None:
        """Get the product ID based on the default_product setting."""
        if not self.default_product:
            return None

        if self.default_product == "free":
            return self.free_product_id
        elif self.default_product == "starter":
            return self.starter_product_id
        elif self.default_product == "team":
            return self.team_product_id
        elif self.default_product == "design_partner":
            return self.design_partner_product_id
        else:
            raise ValueError(
                f"Invalid default_product: {self.default_product}. Must be 'free', 'starter', or 'team'."
            )


# Chart configuration schema for data visualization
chart_config_schema = ChartConfig.model_json_schema()


async def render_data_visualization(config: dict):
    try:
        ChartConfig.model_validate_json(json.dumps(config), strict=True)  # type: ignore  # Pydantic model_validate_json has complex generic return type
        return {"status": "OK"}
    except Exception as e:
        return {
            "status": "ERROR",
            "error": str(e),
        }


render_data_visualization.__doc__ = f"""
    Render a data visualization from a configuration.
    You should only call this towards the end of a thread, after all other tool calls
    have been completed.

    Args:
        config: A dictionary containing the configuration for the data visualization. It must
            adhere to the following JSON schema: `{json.dumps(chart_config_schema)}`

    Returns:
        An OK status if the configuration is valid, an ERROR status otherwise.
    """


class AbortPr(Exception):
    """Exception to abort a PR."""


class TemporalOSSConfig(BaseModel):
    """Configuration for local or self-hosted Temporal server."""

    type: Literal["oss"] = "oss"
    host: str
    port: int

    @property
    def connection_string(self) -> str:
        """Get the connection string in host:port format for Temporal client."""
        return f"{self.host}:{self.port}"

    @property
    def namespace(self) -> str:
        """Get the namespace (default for OSS Temporal)."""
        return "default"


class TemporalCloudConfig(BaseModel):
    """Configuration for Temporal Cloud with API key authentication."""

    type: Literal["cloud"] = "cloud"
    namespace: str
    endpoint: str
    api_key: SecretStr

    @property
    def connection_string(self) -> str:
        """Get the connection string for Temporal Cloud."""
        return self.endpoint


TemporalConfig = TemporalOSSConfig | TemporalCloudConfig


class OrganizationConfig(BaseModel):
    """Organization-level configuration shared across bot instances."""

    organization_id: int
    organization_name: str
    organization_industry: str | None = Field(default=None)
    stripe_customer_id: str | None = Field(default=None)
    stripe_subscription_id: str | None = Field(default=None)
    contextstore_github_repo: str | None = Field(default=None)


class CompassBotSingleChannelConfig(BaseModel):
    channel_name: str
    bot_email: str
    team_id: str
    connections: dict[str, ConnectionProfile]
    governance_alerts_channel: str
    scaffold_branch_enabled: bool = Field(
        default=False
    )  # Feature flag: disabled by default for safety
    organization: OrganizationConfig
    instance_type: BotInstanceType = Field(
        default=BotInstanceType.STANDARD
    )  # Bot instance type (determines feature availability)
    icp_text: str | None = Field(default=None)  # ICP for prospector instances
    prospector_data_types: list[ProspectorDataType] = Field(
        default_factory=list
    )  # Data types for prospector instances (empty for non-prospector)
    data_documentation_repos: set[str] = Field(
        default_factory=set
    )  # Shared dataset documentation repos to merge with org context store

    # Convenience properties for backward compatibility
    @property
    def organization_id(self) -> int:
        return self.organization.organization_id

    @property
    def organization_name(self) -> str:
        return self.organization.organization_name

    @property
    def organization_industry(self) -> str | None:
        return self.organization.organization_industry

    @property
    def stripe_customer_id(self) -> str | None:
        return self.organization.stripe_customer_id

    @property
    def stripe_subscription_id(self) -> str | None:
        return self.organization.stripe_subscription_id

    @property
    def contextstore_github_repo(self) -> str | None:
        return self.organization.contextstore_github_repo

    @property
    def is_prospector(self) -> bool:
        """Check if this is a prospector bot instance.

        A channel is in prospector mode if it has any connection with a shared
        data_documentation_contextstore_github_repo configured (typically prospector dataset).
        """
        return len(self.data_documentation_repos) > 0

    @property
    def is_community_prospector(self) -> bool:
        """Check if this is a community prospector bot instance."""
        return self.instance_type == BotInstanceType.COMMUNITY_PROSPECTOR

    def should_restart(self, other: "CompassBotSingleChannelConfig") -> bool:
        return set(self.connections.keys()) != set(other.connections.keys())


class RenderSecretStoreConfig(BaseModel):
    render_service_id: str
    render_api_key: SecretStr


class ProspectorDataConnectionConfig(BaseModel):
    """Configuration for pre-configured data connections (used by prospector organizations)."""

    type: str
    config: dict[str, Any]
    table_names: list[str] | None = Field(default=None)


class ThreadHealthHoneycombLogging(BaseModel):
    dataset: str
    api_key: str


class ThreadHealthInspectorConfig(BaseModel):
    # 1/sample_rate threads will be checked
    sample_rate: int = Field(gt=0)  # Must be greater than 0

    # the health inspection will take place this many seconds after
    # the bot starts streaming the response
    start_delay_seconds: int = Field(default=300)

    honeycomb: ThreadHealthHoneycombLogging | None = Field(default=None)


class CompassBotServerConfig(BaseModel):
    slack_signing_secret: SecretStr | None = Field(
        default=None
    )  # Optional: only needed for HTTP mode
    slack_app_token: SecretStr | None = Field(
        default=None
    )  # Optional: only needed for websocket mode
    compass_bot_token: SecretStr
    slack_admin_token: SecretStr | None = Field(default=None)
    compass_dev_tools_bot_token: SecretStr | None = Field(default=None)
    ai_config: AIConfig
    github: BotGitHubConfig
    stripe: StripeConfig = Field(default_factory=StripeConfig)
    db_config: DatabaseConfig
    http_port: int = Field(default=3000)  # Standard development port, commonly available
    http_host: str = Field(
        default="0.0.0.0"
    )  # Bind to all interfaces for container/cloud deployment
    public_url: str
    mode: str  # "http" or "websocket"
    jwt_secret: SecretStr
    secret_store: RenderSecretStoreConfig | None = Field(default=None)
    bots: dict[str, CompassBotSingleChannelConfig] | None = Field(default=None)
    dagster_admins_to_invite: list[str] = Field(default_factory=list)
    prospector_data_connection: ProspectorDataConnectionConfig | None = Field(
        default=None
    )  # Pre-configured connection for prospector organizations
    prospector_contextstore_repo: (
        str  # Shared read-only GitHub repo for all prospector organizations
    )
    segment_write_key: SecretStr | None = Field(default=None)
    segment_orgs_enabled: list[str] | None = Field(default=None)
    is_local: bool = Field(default=False)  # Whether running in local development mode
    temporal: TemporalConfig
    thread_health_inspector_config: ThreadHealthInspectorConfig | None = Field(default=None)

    # if enabled, the app will conditionally start up in canary mode which
    # will just check that all services are operational
    canary_enabled: bool = Field(default=False)


def get_jinja_template_context_with_secret_store(
    root: Path, secret_store: SecretStore, org_id: int
) -> dict[str, Any]:
    """Get a Jinja template context for the config."""

    @cache
    def pull_from_secret_manager_to_file(secret_name: str) -> str:
        with tempfile.NamedTemporaryFile(delete=False) as file:
            Path(file.name).write_text(
                asyncio.run(secret_store.get_secret_contents(org_id, secret_name))
            )
            return file.name

    @cache
    def pull_from_secret_manager_to_string(secret_name: str) -> str:
        return asyncio.run(secret_store.get_secret_contents(org_id, secret_name))

    return {
        **get_jinja_template_context(root),
        "pull_from_secret_manager_to_file": pull_from_secret_manager_to_file,
        "pull_from_secret_manager_to_string": pull_from_secret_manager_to_string,
    }


def get_jinja_template_context(root: Path | None = None) -> dict[str, Any]:
    """Get a Jinja template context for the config."""

    # interpolate env vars with jinja2
    def get_from_environ(key: str, default_value: str | None = None) -> str:
        if key in os.environ:
            return os.environ[key]
        if default_value:
            return default_value
        raise ValueError(f"Environment variable {key} not found")

    def get_secret_file(secret_name: str, env_var_name: str | None = None) -> str:
        if env_var_name and env_var_name in os.environ:
            value = os.environ[env_var_name]
            if not Path(value).exists():
                raise ValueError(f"Secret file {value} not found")
            return value
        raise ValueError(f"Secret {secret_name} not found")

    def get_secret_value(secret_name: str, env_var_name: str | None = None) -> str:
        if env_var_name and env_var_name in os.environ:
            return os.environ[env_var_name]
        raise ValueError(f"Secret {secret_name} not found")

    def secret_exists(secret_name: str, env_var_name: str | None = None) -> bool:
        try:
            get_secret_file(secret_name, env_var_name)
            return True
        except ValueError:
            return False

    config: dict[Any, Any] = {
        "env": get_from_environ,
        "secret_file": get_secret_file,
        "secret_exists": secret_exists,
        "secret": get_secret_value,
    }
    if root:
        config["root_path"] = str(root.absolute())

    return config


def load_db_config_from_path(config_path: str | Path) -> DatabaseConfig:
    # interpolate env vars with jinja2
    jinja_template_context = get_jinja_template_context()

    p = Path(config_path) if isinstance(config_path, str) else config_path
    raw_yaml = p.read_text()
    yaml_str = jinja2.Template(raw_yaml).render(**jinja_template_context)
    parsed = yaml.safe_load(yaml_str)

    return DatabaseConfig.model_validate(parsed)


def load_bot_server_config_from_yaml(yaml_str: str, root: Path) -> CompassBotServerConfig:
    # interpolate env vars with jinja2
    jinja_template_context = get_jinja_template_context(root)

    yaml_str = jinja2.Template(yaml_str).render(**jinja_template_context)
    parsed = yaml.safe_load(yaml_str)

    return CompassBotServerConfig.model_validate(parsed)


def load_bot_server_config_from_path(config_path: str | Path) -> CompassBotServerConfig:
    load_dotenv(find_dotenv(usecwd=True), override=True)

    p = Path(config_path) if isinstance(config_path, str) else config_path
    config_yaml = p.read_text()
    bot_config = load_bot_server_config_from_yaml(config_yaml, p.parent.absolute())
    return bot_config
