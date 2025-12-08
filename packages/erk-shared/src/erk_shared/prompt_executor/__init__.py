"""Prompt executor abstraction for Claude CLI.

This module provides a minimal abstraction for executing single-shot prompts
via Claude CLI, enabling dependency injection for testing without mocks.

Usage:
    from erk_shared.prompt_executor import PromptExecutor, PromptResult
    from erk_shared.prompt_executor.fake import FakePromptExecutor
    from erk_shared.prompt_executor.real import RealPromptExecutor
"""

from erk_shared.prompt_executor.abc import PromptExecutor, PromptResult

__all__ = ["PromptExecutor", "PromptResult"]
