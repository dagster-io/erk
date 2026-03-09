"""Real implementation of the Skills CLI gateway using npx."""

import shutil

from erk_shared.gateway.skills_cli.abc import SkillsCli
from erk_shared.gateway.skills_cli.types import SkillsCliResult
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealSkillsCli(SkillsCli):
    """Production implementation that invokes npx skills."""

    def is_available(self) -> bool:
        """Check if npx is available on PATH."""
        return shutil.which("npx") is not None

    def list_skills(self, *, source: str) -> SkillsCliResult:
        """List available skills from a source repository."""
        cmd = ["npx", "skills", "add", source, "--list"]
        result = run_subprocess_with_context(
            cmd=cmd,
            operation_context=f"list skills from {source}",
            check=False,
        )
        return SkillsCliResult(
            success=result.returncode == 0,
            exit_code=result.returncode,
            message=result.stdout,
        )

    def add_skills(
        self,
        *,
        source: str,
        skill_names: list[str],
        agents: list[str],
    ) -> SkillsCliResult:
        """Install skills from a source repository."""
        cmd = ["npx", "skills", "add", source]
        for name in skill_names:
            cmd.extend(["--skill", name])
        for agent in agents:
            cmd.extend(["-a", agent])
        cmd.extend(["-y", "--no-telemetry"])
        result = run_subprocess_with_context(
            cmd=cmd,
            operation_context=f"install skills from {source}",
            check=False,
        )
        return SkillsCliResult(
            success=result.returncode == 0,
            exit_code=result.returncode,
            message=result.stdout,
        )

    def remove_skills(
        self,
        *,
        skill_names: list[str],
        agents: list[str],
    ) -> SkillsCliResult:
        """Remove installed skills."""
        cmd = ["npx", "skills", "remove"]
        for name in skill_names:
            cmd.extend(["--skill", name])
        for agent in agents:
            cmd.extend(["-a", agent])
        cmd.append("-y")
        result = run_subprocess_with_context(
            cmd=cmd,
            operation_context="remove skills",
            check=False,
        )
        return SkillsCliResult(
            success=result.returncode == 0,
            exit_code=result.returncode,
            message=result.stdout,
        )
