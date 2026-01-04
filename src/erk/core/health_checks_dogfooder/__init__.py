"""Early dogfooder health checks for erk doctor command.

These checks are for temporary issues that affect early dogfooders and
can be deleted once the issues are resolved. The subpackage structure
makes it easy to remove individual checks or the entire package.

To delete one check:
    1. Remove the check's module file
    2. Remove from imports and EARLY_DOGFOODER_CHECK_NAMES below

To delete all dogfooder checks:
    1. Delete this directory (src/erk/core/health_checks_dogfooder/)
    2. Remove import from health_checks.py, remove run_early_dogfooder_checks() call
    3. Remove early dogfooder category handling from doctor.py
"""

from pathlib import Path

from erk.core.health_checks import CheckResult
from erk.core.health_checks_dogfooder.deprecated_dot_agent_config import (
    check_deprecated_dot_agent_config,
)
from erk.core.health_checks_dogfooder.legacy_claude_docs import (
    check_legacy_claude_docs,
)
from erk.core.health_checks_dogfooder.legacy_config_locations import (
    check_legacy_config_locations,
)
from erk.core.health_checks_dogfooder.legacy_erk_docs_agent import (
    check_legacy_erk_docs_agent,
)
from erk.core.health_checks_dogfooder.legacy_erk_kits_folder import (
    check_legacy_erk_kits_folder,
)
from erk.core.health_checks_dogfooder.legacy_hook_settings import (
    check_legacy_hook_settings,
)
from erk.core.health_checks_dogfooder.legacy_kit_yaml import (
    check_legacy_kit_yaml,
)
from erk.core.health_checks_dogfooder.legacy_kits_toml import (
    check_legacy_kits_toml,
)
from erk.core.health_checks_dogfooder.outdated_erk_skill import (
    check_outdated_erk_skill,
)

# Names of all early dogfooder checks - used by doctor.py for category grouping
EARLY_DOGFOODER_CHECK_NAMES: set[str] = {
    "deprecated-dot-agent-config",
    "legacy-claude-docs",
    "legacy-config",
    "legacy-erk-docs",
    "legacy-erk-kits-folder",
    "legacy-hook-settings",
    "legacy-kit-yaml",
    "legacy-kits-toml",
    "outdated-erk-skill",
}


def run_early_dogfooder_checks(
    repo_root: Path,
    metadata_dir: Path | None,
) -> list[CheckResult]:
    """Run all early dogfooder health checks.

    Args:
        repo_root: Path to the repository root
        metadata_dir: Path to ~/.erk/repos/<repo>/ metadata directory, if known

    Returns:
        List of CheckResult objects from all dogfooder checks
    """
    return [
        check_deprecated_dot_agent_config(repo_root),
        check_legacy_claude_docs(repo_root),
        check_legacy_config_locations(repo_root, metadata_dir),
        check_legacy_erk_docs_agent(repo_root),
        check_legacy_erk_kits_folder(repo_root),
        check_legacy_hook_settings(repo_root),
        check_legacy_kit_yaml(repo_root),
        check_legacy_kits_toml(repo_root),
        check_outdated_erk_skill(repo_root),
    ]
