"""Prompt executor abstraction for Claude CLI.

This module provides a minimal abstraction for executing single-shot prompts
via Claude CLI, enabling dependency injection for testing without mocks.

Import from submodules:
- erk_shared.prompt_executor.abc: PromptExecutor, PromptResult
- erk_shared.prompt_executor.fake: FakePromptExecutor
- erk_shared.prompt_executor.real: RealPromptExecutor
"""
