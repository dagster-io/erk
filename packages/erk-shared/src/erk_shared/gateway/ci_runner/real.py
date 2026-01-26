import shutil
import subprocess
from pathlib import Path

from erk_shared.gateway.ci_runner.abc import CICheckResult, CIRunner


class RealCIRunner(CIRunner):
    def run_check(self, *, name: str, cmd: list[str], cwd: Path) -> CICheckResult:
        # LBYL: Check if command exists first
        if shutil.which(cmd[0]) is None:
            return CICheckResult(passed=False, error_type="command_not_found")

        result = subprocess.run(cmd, cwd=cwd, check=False, capture_output=False)
        if result.returncode != 0:
            return CICheckResult(passed=False, error_type="command_failed")
        return CICheckResult(passed=True, error_type=None)
