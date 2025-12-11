"""Tests for slackbot configuration loading."""

from pathlib import Path
from typing import Any

import jinja2
import yaml

from csbot.slackbot.slackbot_core import CompassBotServerConfig


def get_mock_jinja_template_context(root: Path) -> dict[str, Any]:
    """Get a mock Jinja template context that returns empty strings for all functions.

    This allows config files to be validated without requiring actual secrets or environment variables.
    """

    def get_from_environ(key: str, default_value: str | None = None) -> str:
        # default_value=None means return empty string for all env vars
        return default_value if default_value is not None else "hello"

    def get_secret_file(secret_name: str, env_var_name: str | None = None) -> str:
        # env_var_name=None means return empty string for secret file paths
        return "hello"

    def get_secret_value(secret_name: str, env_var_name: str | None = None) -> str:
        # env_var_name=None means return empty string for secret values
        return "hello"

    def secret_exists(secret_name: str, env_var_name: str | None = None) -> bool:
        # env_var_name=None means secrets don't exist (return False)
        return False

    return {
        "env": get_from_environ,
        "secret_file": get_secret_file,
        "secret_exists": secret_exists,
        "root_path": str(root.absolute()),
        "secret": get_secret_value,
    }


def load_bot_server_config_from_yaml_with_mock_context(
    yaml_str: str, root: Path
) -> CompassBotServerConfig:
    """Load config from YAML with mock Jinja context (empty strings for all secrets/env vars)."""
    jinja_template_context = get_mock_jinja_template_context(root)

    yaml_str = jinja2.Template(yaml_str).render(**jinja_template_context)
    parsed = yaml.safe_load(yaml_str)

    # Handle legacy flat database_uri format - convert to nested db_config
    if "database_uri" in parsed and "db_config" not in parsed:
        db_config = {"database_uri": parsed["database_uri"]}
        if "seed_database_from" in parsed:
            db_config["seed_database_from"] = parsed["seed_database_from"]
            del parsed["seed_database_from"]
        parsed["db_config"] = db_config
        del parsed["database_uri"]

    return CompassBotServerConfig.model_validate(parsed)


def find_all_csbot_config_files() -> list[Path]:
    """Find all .csbot.config.yaml files in the git repository."""
    import pygit2

    repo = pygit2.Repository(Path(__file__).resolve())
    repo_root = Path(repo.workdir)
    config_files = list(repo_root.glob("*.csbot.config.yaml"))
    return config_files


def test_all_csbot_configs_can_load():
    """Test that all .csbot.config.yaml files in the repo can be loaded and validated.

    This test uses a mock Jinja context that returns empty strings for all
    environment variables and secrets, ensuring configs are structurally valid
    even without actual credentials.
    """
    config_files = find_all_csbot_config_files()

    # Ensure we found at least some config files
    assert len(config_files) > 0, "No .csbot.config.yaml files found in repository"

    for config_file in config_files:
        yaml_content = config_file.read_text()

        # Should be able to load and validate without exceptions
        try:
            config = load_bot_server_config_from_yaml_with_mock_context(
                yaml_content, config_file.parent
            )

            # Basic sanity checks
            assert config is not None
            assert isinstance(config, CompassBotServerConfig)
        except Exception as e:
            raise Exception(f"Failed to load config file {config_file}: {e}") from e
