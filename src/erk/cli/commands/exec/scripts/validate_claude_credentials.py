#!/usr/bin/env python3
"""Validate Claude credentials before running CI workflows.

This command performs early validation of Claude API credentials to fail fast
with clear error messages when secrets are missing or invalid. This is intended
for use in GitHub Actions workflows.

Usage:
    erk exec validate-claude-credentials

Output:
    JSON object with success status and validation message

Exit Codes:
    0: Success (credentials validated)
    1: Error (credentials missing or invalid)

Examples:
    $ erk exec validate-claude-credentials
    {
      "success": true,
      "message": "Claude credentials validated successfully"
    }

    $ erk exec validate-claude-credentials  # with missing secrets
    {
      "success": false,
      "error": "credentials-missing",
      "message": "Neither CLAUDE_CODE_OAUTH_TOKEN nor ANTHROPIC_API_KEY is set"
    }

    $ erk exec validate-claude-credentials  # with expired key
    {
      "success": false,
      "error": "authentication-failed",
      "message": "Claude authentication failed - API key may be expired or invalid"
    }
"""

import json
import os
from dataclasses import asdict, dataclass
from typing import Literal

import click

from erk_shared.context.helpers import require_prompt_executor
from erk_shared.core.prompt_executor import PromptExecutor


@dataclass(frozen=True)
class ValidationSuccess:
    """Success result when credentials are valid."""

    success: Literal[True]
    message: str


@dataclass(frozen=True)
class ValidationError:
    """Error result when credentials are missing or invalid."""

    success: Literal[False]
    error: Literal["credentials-missing", "authentication-failed"]
    message: str


def _check_env_vars() -> bool:
    """Check if at least one credential environment variable is set.

    Returns:
        True if CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY is set
    """
    oauth_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    return bool(oauth_token) or bool(api_key)


def _validate_credentials_impl(
    *,
    prompt_executor: PromptExecutor,
) -> ValidationSuccess | ValidationError:
    """Validate Claude credentials by checking env vars and making API call.

    First checks that at least one credential environment variable is set,
    then validates the credential by making a minimal API call via PromptExecutor.

    Args:
        prompt_executor: Executor to use for the validation API call

    Returns:
        ValidationSuccess if credentials are valid, ValidationError otherwise
    """
    # LBYL: Check environment variables first
    if not _check_env_vars():
        return ValidationError(
            success=False,
            error="credentials-missing",
            message="Neither CLAUDE_CODE_OAUTH_TOKEN nor ANTHROPIC_API_KEY is set",
        )

    # Validate by making a minimal API call
    result = prompt_executor.execute_prompt(
        "respond with ok",
        model="haiku",
        tools=None,
        cwd=None,
        system_prompt=None,
        dangerous=False,
    )

    if not result.success:
        return ValidationError(
            success=False,
            error="authentication-failed",
            message="Claude authentication failed - API key may be expired or invalid",
        )

    return ValidationSuccess(
        success=True,
        message="Claude credentials validated successfully",
    )


@click.command(name="validate-claude-credentials")
@click.pass_context
def validate_claude_credentials(ctx: click.Context) -> None:
    """Validate Claude credentials for CI workflows.

    Checks that at least one credential is set (CLAUDE_CODE_OAUTH_TOKEN or
    ANTHROPIC_API_KEY) and validates it by making a minimal API call.
    Fails fast with clear error messages when credentials are missing or invalid.
    """
    prompt_executor = require_prompt_executor(ctx)
    result = _validate_credentials_impl(prompt_executor=prompt_executor)

    # Output JSON result
    click.echo(json.dumps(asdict(result), indent=2))

    # Exit with error code if validation failed
    if isinstance(result, ValidationError):
        raise SystemExit(1)
