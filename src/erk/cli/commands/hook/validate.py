"""Validate command for checking hooks configuration."""

import json
from pathlib import Path

import click
from pydantic import ValidationError

from erk.kits.cli.output import machine_output, user_output
from erk.kits.hooks.models import ClaudeSettings


@click.command(name="validate")
def validate_hooks() -> None:
    """Validate hooks configuration in settings.json."""
    settings_path = Path.cwd() / ".claude" / "settings.json"

    if not settings_path.exists():
        machine_output(
            "✓ No settings.json file (valid - no hooks configured)",
        )
        raise SystemExit(0)

    # Try to load and validate
    try:
        content = settings_path.read_text(encoding="utf-8")
        data = json.loads(content)
        ClaudeSettings.model_validate(data)
        user_output("✓ Hooks configuration is valid")
        raise SystemExit(0)
    except json.JSONDecodeError as e:
        user_output(f"✗ Invalid JSON in settings.json: {e}")
        raise SystemExit(1) from None
    except ValidationError as e:
        user_output("✗ Validation errors in settings.json:")
        for error in e.errors():
            loc = " -> ".join(str(x) for x in error["loc"])
            msg = error["msg"]
            user_output(f"  {loc}: {msg}")
        raise SystemExit(1) from None
