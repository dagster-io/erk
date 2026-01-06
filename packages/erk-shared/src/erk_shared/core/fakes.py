"""Fake implementations for erk-specific ABCs.

These fakes are used in tests and in contexts (like erk-kits) that
don't need the real erk implementations.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

from erk_shared.core.claude_executor import (
    ClaudeEvent,
    ClaudeExecutor,
    PromptResult,
)
from erk_shared.core.plan_list_service import PlanListData, PlanListService
from erk_shared.core.planner_registry import PlannerRegistry, RegisteredPlanner
from erk_shared.core.script_writer import ScriptResult, ScriptWriter
from erk_shared.github.types import GitHubRepoLocation


class InteractiveCall(NamedTuple):
    """Record of an execute_interactive call."""

    worktree_path: Path
    dangerous: bool
    command: str
    target_subpath: Path | None
    model: str | None


class PromptCall(NamedTuple):
    """Record of an execute_prompt call."""

    prompt: str
    model: str
    tools: list[str] | None
    cwd: Path | None
    system_prompt: str | None


class FakeClaudeExecutor(ClaudeExecutor):
    """Fake ClaudeExecutor for testing.

    Attributes:
        is_available: Whether Claude CLI should appear available
        interactive_calls: List of InteractiveCall records
        prompt_calls: List of PromptCall records
        prompt_results: Queue of PromptResult to return from execute_prompt
        streaming_events: Events to yield from execute_command_streaming
    """

    def __init__(
        self,
        *,
        is_available: bool = True,
        prompt_results: list[PromptResult] | None = None,
        streaming_events: list[ClaudeEvent] | None = None,
    ) -> None:
        self.is_available_value = is_available
        self.interactive_calls: list[InteractiveCall] = []
        self.prompt_calls: list[PromptCall] = []
        self.prompt_results = list(prompt_results) if prompt_results else []
        self.streaming_events = list(streaming_events) if streaming_events else []
        self._prompt_result_index = 0

    def is_claude_available(self) -> bool:
        return self.is_available_value

    def execute_command_streaming(
        self,
        *,
        command: str,
        worktree_path: Path,
        dangerous: bool,
        verbose: bool = False,
        debug: bool = False,
        model: str | None = None,
    ) -> Iterator[ClaudeEvent]:
        yield from self.streaming_events

    def execute_interactive(
        self,
        *,
        worktree_path: Path,
        dangerous: bool,
        command: str,
        target_subpath: Path | None,
        model: str | None = None,
    ) -> None:
        self.interactive_calls.append(
            InteractiveCall(
                worktree_path=worktree_path,
                dangerous=dangerous,
                command=command,
                target_subpath=target_subpath,
                model=model,
            )
        )

    def execute_prompt(
        self,
        prompt: str,
        *,
        model: str,
        tools: list[str] | None,
        cwd: Path | None,
        system_prompt: str | None,
    ) -> PromptResult:
        self.prompt_calls.append(
            PromptCall(
                prompt=prompt,
                model=model,
                tools=tools,
                cwd=cwd,
                system_prompt=system_prompt,
            )
        )
        if self._prompt_result_index < len(self.prompt_results):
            result = self.prompt_results[self._prompt_result_index]
            self._prompt_result_index += 1
            return result
        return PromptResult(success=True, output="", error=None)


class FakeScriptWriter(ScriptWriter):
    """Fake ScriptWriter for testing.

    Records script writes without touching filesystem.
    """

    def __init__(self) -> None:
        self.written_scripts: list[ScriptResult] = []

    def write_activation_script(
        self,
        content: str,
        *,
        command_name: str,
        comment: str,
    ) -> ScriptResult:
        result = ScriptResult(
            path=Path(f"/fake/scripts/{command_name}.sh"),
            content=f"# {comment}\n{content}",
        )
        self.written_scripts.append(result)
        return result


@dataclass
class FakePlannerRegistry(PlannerRegistry):
    """Fake PlannerRegistry for testing.

    Stores planners in memory.
    """

    planners: dict[str, RegisteredPlanner] = field(default_factory=dict)
    default_name: str | None = None

    def list_planners(self) -> list[RegisteredPlanner]:
        return list(self.planners.values())

    def get(self, name: str) -> RegisteredPlanner | None:
        return self.planners.get(name)

    def get_default(self) -> RegisteredPlanner | None:
        if self.default_name is None:
            return None
        return self.planners.get(self.default_name)

    def get_default_name(self) -> str | None:
        return self.default_name

    def set_default(self, name: str) -> None:
        if name not in self.planners:
            raise ValueError(f"No planner with name '{name}' exists")
        self.default_name = name

    def register(self, planner: RegisteredPlanner) -> None:
        if planner.name in self.planners:
            raise ValueError(f"Planner with name '{planner.name}' already exists")
        self.planners[planner.name] = planner

    def unregister(self, name: str) -> None:
        if name not in self.planners:
            raise ValueError(f"No planner with name '{name}' exists")
        del self.planners[name]
        if self.default_name == name:
            self.default_name = None

    def mark_configured(self, name: str) -> None:
        if name not in self.planners:
            raise ValueError(f"No planner with name '{name}' exists")
        planner = self.planners[name]
        self.planners[name] = RegisteredPlanner(
            name=planner.name,
            gh_name=planner.gh_name,
            repository=planner.repository,
            configured=True,
            registered_at=planner.registered_at,
            last_connected_at=planner.last_connected_at,
        )

    def update_last_connected(self, name: str, timestamp: datetime) -> None:
        if name not in self.planners:
            raise ValueError(f"No planner with name '{name}' exists")
        planner = self.planners[name]
        self.planners[name] = RegisteredPlanner(
            name=planner.name,
            gh_name=planner.gh_name,
            repository=planner.repository,
            configured=planner.configured,
            registered_at=planner.registered_at,
            last_connected_at=timestamp,
        )


class FakePlanListService(PlanListService):
    """Fake PlanListService for testing.

    Returns pre-configured data.
    """

    def __init__(self, data: PlanListData | None = None) -> None:
        self._data = data or PlanListData(issues=[], pr_linkages={}, workflow_runs={})

    def get_plan_list_data(
        self,
        *,
        location: GitHubRepoLocation,
        labels: list[str],
        state: str | None = None,
        limit: int | None = None,
        skip_workflow_runs: bool = False,
        creator: str | None = None,
    ) -> PlanListData:
        return self._data
