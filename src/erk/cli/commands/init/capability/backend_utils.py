"""Shared utilities for capability CLI commands."""

from erk.core.context import ErkContext
from erk_shared.context.types import AgentBackend


def resolve_backend(ctx: ErkContext) -> AgentBackend:
    """Resolve agent backend from global config, defaulting to 'claude'."""
    if ctx.global_config is not None:
        return ctx.global_config.interactive_agent.backend
    return "claude"
