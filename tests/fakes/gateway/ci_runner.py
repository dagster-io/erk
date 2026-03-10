from dataclasses import dataclass
from pathlib import Path

from erk_shared.gateway.ci_runner.abc import CICheckResult, CIRunner


@dataclass(frozen=True)
class RunCall:
    name: str
    cmd: list[str]
    cwd: Path


class FakeCIRunner(CIRunner):
    def __init__(
        self,
        *,
        failing_checks: set[str] | None,
        missing_commands: set[str] | None,
    ) -> None:
        self._failing_checks = failing_checks if failing_checks is not None else set()
        self._missing_commands = missing_commands if missing_commands is not None else set()
        self._run_calls: list[RunCall] = []

    @classmethod
    def create_passing_all(cls) -> "FakeCIRunner":
        """Create a FakeCIRunner where all checks pass."""
        return cls(failing_checks=None, missing_commands=None)

    def run_check(self, *, name: str, cmd: list[str], cwd: Path) -> CICheckResult:
        self._run_calls.append(RunCall(name=name, cmd=cmd, cwd=cwd))

        if name in self._missing_commands:
            return CICheckResult(passed=False, error_type="command_not_found")

        if name in self._failing_checks:
            return CICheckResult(passed=False, error_type="command_failed")

        return CICheckResult(passed=True, error_type=None)

    @property
    def run_calls(self) -> list[RunCall]:
        return list(self._run_calls)

    @property
    def check_names_run(self) -> list[str]:
        return [call.name for call in self._run_calls]
