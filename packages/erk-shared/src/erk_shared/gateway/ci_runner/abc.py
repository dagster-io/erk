from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CICheckResult:
    passed: bool
    error_type: str | None


class CIRunner(ABC):
    @abstractmethod
    def run_check(self, *, name: str, cmd: list[str], cwd: Path) -> CICheckResult:
        pass
