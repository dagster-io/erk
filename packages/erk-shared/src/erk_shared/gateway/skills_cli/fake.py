"""Fake implementation of the Skills CLI gateway for testing."""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.gateway.skills_cli.abc import SkillsCli
from erk_shared.gateway.skills_cli.types import SkillsCliResult


@dataclass(frozen=True)
class AddSkillsCall:
    """Record of an add_skills call for test assertions."""

    source: str
    skill_names: list[str]
    agents: list[str]
    cwd: Path | None


@dataclass(frozen=True)
class RemoveSkillsCall:
    """Record of a remove_skills call for test assertions."""

    skill_names: list[str]
    agents: list[str]
    cwd: Path | None


class FakeSkillsCli(SkillsCli):
    """Test double for the Skills CLI gateway.

    Constructor injection controls return values; mutation tracking
    records calls for test assertions.
    """

    def __init__(
        self,
        *,
        available: bool,
        list_result: SkillsCliResult | None = None,
        add_result: SkillsCliResult | None = None,
        remove_result: SkillsCliResult | None = None,
    ) -> None:
        self._available = available
        self._list_result = (
            list_result
            if list_result is not None
            else SkillsCliResult(success=True, exit_code=0, message="")
        )
        self._add_result = (
            add_result
            if add_result is not None
            else SkillsCliResult(success=True, exit_code=0, message="")
        )
        self._remove_result = (
            remove_result
            if remove_result is not None
            else SkillsCliResult(success=True, exit_code=0, message="")
        )
        self._add_calls: list[AddSkillsCall] = []
        self._remove_calls: list[RemoveSkillsCall] = []

    def is_available(self) -> bool:
        return self._available

    def list_skills(self, *, source: str) -> SkillsCliResult:
        return self._list_result

    def add_skills(
        self,
        *,
        source: str,
        skill_names: list[str],
        agents: list[str],
        cwd: Path | None,
    ) -> SkillsCliResult:
        self._add_calls.append(
            AddSkillsCall(
                source=source,
                skill_names=list(skill_names),
                agents=list(agents),
                cwd=cwd,
            )
        )
        return self._add_result

    def remove_skills(
        self,
        *,
        skill_names: list[str],
        agents: list[str],
        cwd: Path | None,
    ) -> SkillsCliResult:
        self._remove_calls.append(
            RemoveSkillsCall(
                skill_names=list(skill_names),
                agents=list(agents),
                cwd=cwd,
            )
        )
        return self._remove_result

    @property
    def add_calls(self) -> list[AddSkillsCall]:
        """For test assertions."""
        return list(self._add_calls)

    @property
    def remove_calls(self) -> list[RemoveSkillsCall]:
        """For test assertions."""
        return list(self._remove_calls)
