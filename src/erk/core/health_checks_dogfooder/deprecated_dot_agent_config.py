"""Check for deprecated [tool.dot-agent] config in pyproject.toml.

This is a temporary check for early dogfooders. Delete this file once
all users have migrated to [tool.erk].
"""

from pathlib import Path

import tomli

from erk.core.health_checks import CheckResult


def check_deprecated_dot_agent_config(repo_root: Path) -> CheckResult:
    """Check for deprecated [tool.dot-agent] config in pyproject.toml.

    This check detects the old configuration format and suggests migration
    to [tool.erk].

    Args:
        repo_root: Path to the repository root

    Returns:
        CheckResult indicating whether deprecated config was found
    """
    pyproject_path = repo_root / "pyproject.toml"
    if not pyproject_path.exists():
        return CheckResult(
            name="deprecated dot-agent config",
            passed=True,
            message="No deprecated [tool.dot-agent] config found",
        )

    with open(pyproject_path, "rb") as f:
        data = tomli.load(f)

    # Check for [tool.dot-agent] section with dev_mode
    if "tool" not in data:
        return CheckResult(
            name="deprecated dot-agent config",
            passed=True,
            message="No deprecated [tool.dot-agent] config found",
        )
    if "dot-agent" not in data["tool"]:
        return CheckResult(
            name="deprecated dot-agent config",
            passed=True,
            message="No deprecated [tool.dot-agent] config found",
        )

    tool_config = data["tool"]["dot-agent"]
    if "dev_mode" not in tool_config:
        return CheckResult(
            name="deprecated dot-agent config",
            passed=True,
            message="No deprecated [tool.dot-agent] config found",
        )

    # Found deprecated config - return failure with remediation
    return CheckResult(
        name="deprecated dot-agent config",
        passed=False,
        message="Deprecated [tool.dot-agent] config in pyproject.toml",
        details=(
            "dev_mode should now be configured under [tool.erk]\n"
            "\n"
            "Remediation:\n"
            "  1. Edit pyproject.toml\n"
            "  2. Replace [tool.dot-agent] with [tool.erk]\n"
            "  3. Keep dev_mode = true under [tool.erk]"
        ),
    )
