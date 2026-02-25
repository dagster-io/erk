from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    slack_bot_token: str = Field(..., alias="SLACK_BOT_TOKEN")
    slack_app_token: str = Field(..., alias="SLACK_APP_TOKEN")

    # Agent config — optional so the bot can start for Slack-only commands
    # (plan list, one-shot, ping) even without agent wiring.
    anthropic_api_key: str | None = Field(None, alias="ANTHROPIC_API_KEY")
    erk_repo_path: str | None = Field(None, alias="ERK_REPO_PATH")
    erk_model: str = Field("claude-sonnet-4-20250514", alias="ERK_MODEL")
    max_turns: int = Field(10, alias="ERK_MAX_TURNS")

    enable_suggested_replies: bool = True
    max_slack_code_block_chars: int = 2800
    max_one_shot_message_chars: int = 1200
    one_shot_progress_tail_lines: int = 40
    one_shot_progress_update_interval_seconds: float = 1.0
    one_shot_failure_tail_lines: int = 60
    one_shot_timeout_seconds: float = 900.0
