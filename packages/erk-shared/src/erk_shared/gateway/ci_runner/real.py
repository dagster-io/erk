import subprocess
from pathlib import Path

from erk_shared.gateway.ci_runner.abc import CICheckResult, CIRunner


class RealCIRunner(CIRunner):
    def run_check(self, *, name: str, cmd: list[str], cwd: Path) -> CICheckResult:
        try:
            subprocess.run(cmd, cwd=cwd, check=True, capture_output=False)
            return CICheckResult(passed=True, error_type=None)
        except subprocess.CalledProcessError:
            return CICheckResult(passed=False, error_type="command_failed")
        except FileNotFoundError:
            return CICheckResult(passed=False, error_type="command_not_found")
