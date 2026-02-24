from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    slack_bot_token: str = Field(..., alias="SLACK_BOT_TOKEN")
    slack_app_token: str = Field(..., alias="SLACK_APP_TOKEN")

    max_slack_code_block_chars: int = 2800
    max_one_shot_message_chars: int = 1200
    one_shot_progress_tail_lines: int = 40
    one_shot_progress_update_interval_seconds: float = 1.0
    one_shot_failure_tail_lines: int = 60
    one_shot_timeout_seconds: float = 900.0
