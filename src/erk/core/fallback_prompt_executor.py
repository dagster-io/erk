"""Fallback prompt executor that tries API first, then CLI.

This module provides a composite PromptExecutor that routes
execute_prompt() through the Anthropic API when available, falling
back to the CLI executor. All other methods (streaming, interactive,
passthrough) delegate directly to the CLI executor.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from erk_shared.core.prompt_executor import (
    ExecutorEvent,
    PromptExecutor,
    PromptResult,
)

if TYPE_CHECKING:
    from erk_shared.context.types import PermissionMode


@dataclass(frozen=True)
class FallbackPromptExecutor(PromptExecutor):
    """Composite executor: API-first for prompts, CLI for everything else.

    Attributes:
        api_executor: Anthropic API executor (used for execute_prompt when available).
        cli_executor: CLI executor (Claude or Codex, used as fallback and for all
            streaming/interactive/passthrough operations).
    """

    api_executor: PromptExecutor
    cli_executor: PromptExecutor

    @property
    def prompt_label(self) -> str:
        if self.api_executor.is_available():
            return self.api_executor.prompt_label
        return self.cli_executor.prompt_label

    def is_available(self) -> bool:
        """Available if either executor is available."""
        return self.api_executor.is_available() or self.cli_executor.is_available()

    def execute_prompt(
        self,
        prompt: str,
        *,
        model: str,
        tools: list[str] | None,
        cwd: Path | None,
        system_prompt: str | None,
        dangerous: bool,
    ) -> PromptResult:
        """Execute prompt via API if available, otherwise via CLI."""
        if self.api_executor.is_available():
            return self.api_executor.execute_prompt(
                prompt,
                model=model,
                tools=tools,
                cwd=cwd,
                system_prompt=system_prompt,
                dangerous=dangerous,
            )
        return self.cli_executor.execute_prompt(
            prompt,
            model=model,
            tools=tools,
            cwd=cwd,
            system_prompt=system_prompt,
            dangerous=dangerous,
        )

    def execute_command_streaming(
        self,
        *,
        command: str,
        worktree_path: Path,
        dangerous: bool,
        verbose: bool = False,
        debug: bool = False,
        model: str | None = None,
        permission_mode: PermissionMode,
        allow_dangerous: bool = False,
    ) -> Iterator[ExecutorEvent]:
        """Always delegate streaming to CLI executor."""
        return self.cli_executor.execute_command_streaming(
            command=command,
            worktree_path=worktree_path,
            dangerous=dangerous,
            verbose=verbose,
            debug=debug,
            model=model,
            permission_mode=permission_mode,
            allow_dangerous=allow_dangerous,
        )

    def execute_interactive(
        self,
        *,
        worktree_path: Path,
        dangerous: bool,
        command: str,
        target_subpath: Path | None,
        model: str | None = None,
        permission_mode: PermissionMode,
    ) -> None:
        """Always delegate interactive to CLI executor."""
        return self.cli_executor.execute_interactive(
            worktree_path=worktree_path,
            dangerous=dangerous,
            command=command,
            target_subpath=target_subpath,
            model=model,
            permission_mode=permission_mode,
        )

    def execute_prompt_passthrough(
        self,
        prompt: str,
        *,
        model: str,
        tools: list[str] | None,
        cwd: Path,
        dangerous: bool,
    ) -> int:
        """Always delegate passthrough to CLI executor."""
        return self.cli_executor.execute_prompt_passthrough(
            prompt,
            model=model,
            tools=tools,
            cwd=cwd,
            dangerous=dangerous,
        )
