"""Check command for validating artifacts and sync status."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import click
import tomli

from erk.kits.cli.output import user_output
from erk.kits.hooks.models import ClaudeSettings, HookDefinition, HookEntry
from erk.kits.hooks.settings import (
    extract_kit_id_from_command,
    load_settings,
)
from erk.kits.io.manifest import load_kit_manifest
from erk.kits.io.state import load_project_config
from erk.kits.models.artifact import ARTIFACT_TARGET_DIRS
from erk.kits.models.config import InstalledKit, ProjectConfig
from erk.kits.models.types import SOURCE_TYPE_BUNDLED, SOURCE_TYPE_PACKAGE
from erk.kits.operations.validation import validate_project
from erk.kits.sources.bundled import BundledKitSource


@dataclass(frozen=True)
class SyncCheckResult:
    """Result of checking sync status for one artifact."""

    artifact_path: Path
    is_in_sync: bool
    reason: str | None = None


@dataclass(frozen=True)
class ConfigValidationResult:
    """Result of validating configuration fields for one kit."""

    kit_id: str
    is_valid: bool
    errors: list[str]


@dataclass(frozen=True)
class InstalledHook:
    """A hook extracted from settings.json."""

    hook_id: str  # Extracted from command or environment variable
    command: str
    timeout: int
    lifecycle: str  # "UserPromptSubmit", etc.
    matcher: str


@dataclass(frozen=True)
class HookDriftIssue:
    """A single hook drift issue."""

    severity: Literal["error", "warning"]
    message: str
    expected: str | None
    actual: str | None


@dataclass(frozen=True)
class HookDriftResult:
    """Result of checking hook drift for one kit."""

    kit_id: str
    issues: list[HookDriftIssue]


@dataclass(frozen=True)
class HookValidationDetail:
    """Detailed information about hook validation process."""

    lifecycle: str
    command: str
    kit_id: str | None  # None if not a dot-agent managed hook
    hook_id: str | None  # None if not a dot-agent managed hook or parsing failed
    action: str  # "found_and_parsed", "skipped_not_dot_agent", "parse_error"
    error_message: str | None = None


@dataclass(frozen=True)
class UnknownFieldsResult:
    """Result of checking for unknown fields in configuration."""

    location: str  # e.g., "top-level" or "kits.my-kit"
    unknown_fields: list[str]


def detect_unknown_top_level_fields(data: dict) -> list[str]:
    """Detect unknown fields at the top level of kits.toml.

    Args:
        data: Raw TOML data as dictionary

    Returns:
        Sorted list of unknown field names
    """
    expected_fields = {"version", "kits"}
    actual_fields = set(data.keys())
    unknown_fields = actual_fields - expected_fields
    return sorted(unknown_fields)


def detect_unknown_kit_fields(kit_data: dict) -> list[str]:
    """Detect unknown fields in a kit definition.

    Args:
        kit_data: Raw kit configuration as dictionary

    Returns:
        Sorted list of unknown field names
    """
    expected_fields = {"kit_id", "source_type", "version", "artifacts", "hooks"}
    actual_fields = set(kit_data.keys())
    unknown_fields = actual_fields - expected_fields
    return sorted(unknown_fields)


def validate_unknown_fields(
    project_dir: Path,
    config: ProjectConfig,
) -> list[UnknownFieldsResult]:
    """Validate that no unknown fields exist in kits.toml.

    Args:
        project_dir: Project root directory
        config: Loaded project configuration

    Returns:
        List of UnknownFieldsResult objects (empty if all valid)
    """
    results = []

    # Reload raw TOML data
    toml_path = project_dir / ".erk" / "kits.toml"
    if not toml_path.exists():
        return results

    with open(toml_path, "rb") as f:
        data = tomli.load(f)

    # Check top-level fields
    top_level_unknown = detect_unknown_top_level_fields(data)
    if len(top_level_unknown) > 0:
        results.append(
            UnknownFieldsResult(
                location="top-level",
                unknown_fields=top_level_unknown,
            )
        )

    # Check kit-level fields
    kits_data = data.get("kits", {})
    for kit_name, kit_data in kits_data.items():
        kit_unknown = detect_unknown_kit_fields(kit_data)
        if len(kit_unknown) > 0:
            results.append(
                UnknownFieldsResult(
                    location=f"kits.{kit_name}",
                    unknown_fields=kit_unknown,
                )
            )

    return results


def validate_kit_fields(kit: InstalledKit) -> list[str]:
    """Validate all fields of an installed kit using LBYL checks.

    Args:
        kit: InstalledKit to validate

    Returns:
        List of error messages (empty if all valid)
    """
    errors = []

    # Validate kit_id is non-empty
    if not kit.kit_id:
        errors.append("kit_id is empty")

    # Validate source_type is valid
    if kit.source_type not in [SOURCE_TYPE_BUNDLED, SOURCE_TYPE_PACKAGE]:
        msg = (
            f"Invalid source_type: {kit.source_type}. "
            f"Must be '{SOURCE_TYPE_BUNDLED}' or '{SOURCE_TYPE_PACKAGE}'"
        )
        errors.append(msg)

    # Validate version is non-empty
    if not kit.version:
        errors.append("version is empty")

    # Validate artifacts list is non-empty (except for bundled kits which can
    # define artifacts in their bundled kit.yaml instead of kits.toml)
    if not kit.artifacts and kit.source_type != SOURCE_TYPE_BUNDLED:
        errors.append("artifacts list is empty")

    return errors


def validate_configuration(
    config_kits: dict[str, InstalledKit],
) -> list[ConfigValidationResult]:
    """Validate all installed kits in configuration.

    Args:
        config_kits: Dictionary of kit_id to InstalledKit

    Returns:
        List of validation results for each kit
    """
    results = []

    for kit_id, installed_kit in config_kits.items():
        field_errors = validate_kit_fields(installed_kit)

        result = ConfigValidationResult(
            kit_id=kit_id,
            is_valid=len(field_errors) == 0,
            errors=field_errors,
        )
        results.append(result)

    return results


def compare_artifact_lists(
    manifest_artifacts: dict[str, list[str]],
    installed_artifacts: list[str],
) -> tuple[list[str], list[str]]:
    """Compare manifest artifacts against installed artifacts.

    Args:
        manifest_artifacts: Dict of artifact type to list of relative paths from manifest
        installed_artifacts: List of installed artifact paths (relative to project root)

    Returns:
        Tuple of (missing, obsolete) artifact lists
    """
    # Build set of expected paths from manifest
    manifest_paths = set()
    for artifact_type, paths in manifest_artifacts.items():
        # Get base directory for this artifact type
        base_dir = ARTIFACT_TARGET_DIRS.get(artifact_type, ".claude")  # type: ignore[arg-type]
        for path in paths:
            # Transform manifest path to installed path
            # Manifest: "commands/gt/land-branch.md"
            # Installed: ".claude/commands/gt/land-branch.md" (for commands)
            # or ".github/workflows/erk/deploy.yml" (for workflows)
            full_path = f"{base_dir}/{path}"
            manifest_paths.add(full_path)

    installed_paths = set(installed_artifacts)

    missing = sorted(manifest_paths - installed_paths)
    obsolete = sorted(installed_paths - manifest_paths)

    return missing, obsolete


def check_artifact_sync(
    project_dir: Path,
    artifact_rel_path: str,
    bundled_base: Path,
) -> SyncCheckResult:
    """Check if an artifact is in sync with bundled source."""
    # Normalize artifact path: remove base directory prefix if present
    # Handles both .claude/ and .github/ prefixes
    normalized_path = artifact_rel_path
    for base_dir in ARTIFACT_TARGET_DIRS.values():
        prefix = f"{base_dir}/"
        if normalized_path.startswith(prefix):
            normalized_path = normalized_path[len(prefix) :]
            break

    # Local path is stored in artifact_rel_path (relative to project root)
    local_path = project_dir / artifact_rel_path

    # Corresponding bundled path
    bundled_path = bundled_base / normalized_path

    # Check if both exist
    if not local_path.exists():
        return SyncCheckResult(
            artifact_path=local_path,
            is_in_sync=False,
            reason="Local artifact missing",
        )

    if not bundled_path.exists():
        return SyncCheckResult(
            artifact_path=local_path,
            is_in_sync=False,
            reason="Bundled artifact missing",
        )

    # Compare content
    local_content = local_path.read_bytes()
    bundled_content = bundled_path.read_bytes()

    if local_content != bundled_content:
        return SyncCheckResult(
            artifact_path=local_path,
            is_in_sync=False,
            reason="Content differs",
        )

    return SyncCheckResult(
        artifact_path=local_path,
        is_in_sync=True,
    )


def _process_hook_entry(
    hook_entry: HookEntry,
    lifecycle: str,
) -> HookValidationDetail:
    """Process a single hook entry and return validation details.

    Args:
        hook_entry: Hook entry from settings.json
        lifecycle: Lifecycle event name (e.g., "UserPromptSubmit")

    Returns:
        HookValidationDetail with processing information
    """
    # Try to extract kit ID
    command_kit_id = extract_kit_id_from_command(hook_entry.command)

    if command_kit_id is None:
        # Not a dot-agent managed hook
        return HookValidationDetail(
            lifecycle=lifecycle,
            command=hook_entry.command,
            kit_id=None,
            hook_id=None,
            action="skipped_not_dot_agent",
        )

    # Try to extract hook ID
    hook_id_match = re.search(r"ERK_HOOK_ID=(\S+)", hook_entry.command)
    if hook_id_match:
        hook_id = hook_id_match.group(1)
        return HookValidationDetail(
            lifecycle=lifecycle,
            command=hook_entry.command,
            kit_id=command_kit_id,
            hook_id=hook_id,
            action="found_and_parsed",
        )

    # dot-agent hook but missing hook ID
    return HookValidationDetail(
        lifecycle=lifecycle,
        command=hook_entry.command,
        kit_id=command_kit_id,
        hook_id=None,
        action="parse_error",
        error_message="Missing ERK_HOOK_ID environment variable",
    )


def _extract_hooks_for_kit(
    settings: ClaudeSettings,
    kit_id: str,
    expected_hooks: list[HookDefinition],
) -> list[InstalledHook]:
    """Extract hooks for specific kit from settings.json with strict validation.

    Uses extract_kit_id_from_command() to identify kit ownership.
    Validates extracted hook IDs against expected format and manifest.

    Args:
        settings: Loaded settings object
        kit_id: Kit ID to filter for
        expected_hooks: List of hook definitions from manifest (for validation)

    Returns:
        List of InstalledHook objects for this kit

    Raises:
        ValueError: If hook ID format is invalid (not matching ^[a-z0-9-]+$)
        ValueError: If extracted hook ID is not in expected_hooks list
    """
    results: list[InstalledHook] = []

    if not settings.hooks:
        return results

    for lifecycle, groups in settings.hooks.items():
        for group in groups:
            # Extract matcher from the MatcherGroup
            matcher = group.matcher

            for hook_entry in group.hooks:
                # Extract kit ID from command
                command_kit_id = extract_kit_id_from_command(hook_entry.command)

                if command_kit_id == kit_id:
                    # Extract hook ID from command
                    # Format: ERK_KIT_ID=kit-name ERK_HOOK_ID=hook-id python3 ...
                    import re

                    hook_id_match = re.search(r"ERK_HOOK_ID=(\S+)", hook_entry.command)
                    if not hook_id_match:
                        raise ValueError(
                            f"Hook command for kit '{kit_id}' is missing "
                            f"ERK_HOOK_ID environment variable. "
                            f"Command: {hook_entry.command}"
                        )

                    hook_id = hook_id_match.group(1)

                    # Validate hook ID format (must be lowercase kebab-case)
                    format_pattern = r"^[a-z0-9-]+$"
                    if not re.match(format_pattern, hook_id):
                        raise ValueError(
                            f"Invalid hook ID format: '{hook_id}' for kit '{kit_id}'. "
                            f"Hook IDs must match pattern {format_pattern} "
                            f"(lowercase letters, numbers, and hyphens only)"
                        )

                    # Validate hook ID exists in manifest
                    expected_hook_ids = {hook.id for hook in expected_hooks}
                    if hook_id not in expected_hook_ids:
                        expected_ids_str = ", ".join(f"'{id}'" for id in sorted(expected_hook_ids))
                        raise ValueError(
                            f"Hook ID '{hook_id}' for kit '{kit_id}' not found in manifest. "
                            f"Expected hook IDs: [{expected_ids_str}]"
                        )

                    results.append(
                        InstalledHook(
                            hook_id=hook_id,
                            command=hook_entry.command,
                            timeout=hook_entry.timeout,
                            lifecycle=lifecycle,
                            matcher=matcher,
                        )
                    )

    return results


def _detect_hook_drift(
    kit_id: str,
    expected_hooks: list[HookDefinition],
    installed_hooks: list[InstalledHook],
) -> HookDriftResult | None:
    """Compare expected hooks against installed hooks.

    Args:
        kit_id: Kit ID being checked
        expected_hooks: Hooks defined in kit.yaml
        installed_hooks: Hooks found in settings.json

    Returns:
        HookDriftResult if drift detected, None if all aligned
    """
    issues: list[HookDriftIssue] = []

    # Build lookup maps
    expected_by_id = {hook.id: hook for hook in expected_hooks}
    installed_by_id = {hook.hook_id: hook for hook in installed_hooks}

    # Check each expected hook
    for expected_hook in expected_hooks:
        if expected_hook.id not in installed_by_id:
            # Missing hook
            issues.append(
                HookDriftIssue(
                    severity="error",
                    message=f"Missing hook: '{expected_hook.id}' not found in settings.json",
                    expected=expected_hook.id,
                    actual=None,
                )
            )
        else:
            # Check if command format matches expectations
            installed = installed_by_id[expected_hook.id]

            # Expected format: "ERK_KIT_ID={kit_id} ERK_HOOK_ID={hook_id} {invocation}"
            expected_env_prefix = f"ERK_KIT_ID={kit_id} ERK_HOOK_ID={expected_hook.id}"
            expected_command = f"{expected_env_prefix} {expected_hook.invocation}"

            # Check if command matches expected format
            if installed.command != expected_command:
                issues.append(
                    HookDriftIssue(
                        severity="warning",
                        message=f"Command mismatch for '{expected_hook.id}'",
                        expected=expected_command,
                        actual=installed.command,
                    )
                )

            # Check if matcher matches expectations
            # Normalize None to "*" for comparison
            expected_matcher = expected_hook.matcher if expected_hook.matcher is not None else "*"
            if installed.matcher != expected_matcher:
                issues.append(
                    HookDriftIssue(
                        severity="warning",
                        message=f"Matcher mismatch for '{expected_hook.id}'",
                        expected=expected_matcher,
                        actual=installed.matcher,
                    )
                )

    # Check for obsolete hooks
    for installed_hook in installed_hooks:
        if installed_hook.hook_id not in expected_by_id:
            issues.append(
                HookDriftIssue(
                    severity="warning",
                    message=f"Obsolete hook: '{installed_hook.hook_id}' found in settings.json "
                    f"but not defined in kit.yaml",
                    expected=None,
                    actual=installed_hook.hook_id,
                )
            )

    if len(issues) == 0:
        return None

    return HookDriftResult(kit_id=kit_id, issues=issues)


def validate_hook_configuration(
    project_dir: Path,
    config: ProjectConfig,
) -> tuple[list[HookDriftResult], list[HookValidationDetail]]:
    """Check if installed hooks match kit expectations.

    Only validates bundled kits. Skips validation if kit.yaml has no hooks field.

    Args:
        project_dir: Project root directory
        config: Loaded project configuration

    Returns:
        Tuple of (drift_results, validation_details)
        - drift_results: List of HookDriftResult objects (empty if no drift)
        - validation_details: List of detailed hook processing information
    """
    results: list[HookDriftResult] = []
    validation_details: list[HookValidationDetail] = []

    # Load settings.json
    settings_path = project_dir / ".claude" / "settings.json"
    if not settings_path.exists():
        return results, validation_details

    settings = load_settings(settings_path)

    # First pass: collect all hooks with details (for verbose output)
    if settings.hooks:
        for lifecycle, groups in settings.hooks.items():
            for group in groups:
                for hook_entry in group.hooks:
                    detail = _process_hook_entry(hook_entry, lifecycle)
                    validation_details.append(detail)

    bundled_source = BundledKitSource()

    for kit_id, installed_kit in config.kits.items():
        # Only check bundled kits
        if installed_kit.source_type != SOURCE_TYPE_BUNDLED:
            continue

        # Get bundled kit path
        bundled_path = bundled_source._get_bundled_kit_path(kit_id)
        if bundled_path is None:
            continue

        # Load manifest
        manifest_path = bundled_path / "kit.yaml"
        if not manifest_path.exists():
            continue

        manifest = load_kit_manifest(manifest_path)

        # Skip if no hooks defined in manifest
        if not manifest.hooks or len(manifest.hooks) == 0:
            continue

        # Extract installed hooks for this kit
        # If extraction fails (invalid format, hook not in manifest), treat as drift
        try:
            installed_hooks = _extract_hooks_for_kit(settings, kit_id, manifest.hooks)
        except ValueError as e:
            # Hook extraction failed - create an error drift result
            results.append(
                HookDriftResult(
                    kit_id=kit_id,
                    issues=[
                        HookDriftIssue(
                            severity="error",
                            message=str(e),
                            expected=None,
                            actual=None,
                        )
                    ],
                )
            )
            continue

        # Detect drift
        drift_result = _detect_hook_drift(kit_id, manifest.hooks, installed_hooks)

        if drift_result is not None:
            results.append(drift_result)

    return results, validation_details


@click.command()
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed validation information",
)
def check(verbose: bool) -> None:
    """Validate installed artifacts and check bundled kit sync status."""
    project_dir = Path.cwd()

    # Check if config exists
    config = load_project_config(project_dir)
    config_exists = config is not None

    # Part 1: Validate configuration
    if verbose:
        user_output(click.style("🔍 Configuration Validation", fg="white", bold=True))

    # Check if there are kits to validate
    if not config_exists or len(config.kits) == 0:
        if verbose:
            user_output("No kits installed - skipping configuration validation")
        config_passed = True
    else:
        # Validate all installed kits
        validation_results = validate_configuration(config.kits)
        valid_count = sum(1 for r in validation_results if r.is_valid)
        invalid_count = len(validation_results) - valid_count

        # Show results
        if verbose or invalid_count > 0:
            for result in validation_results:
                if result.is_valid:
                    status = click.style("✓", fg="green")
                else:
                    status = click.style("✗", fg="red")
                user_output(f"{status} {click.style(result.kit_id, fg='cyan')}")

                if not result.is_valid:
                    for error in result.errors:
                        user_output(f"  - {error}")

        # Summary
        if verbose:
            user_output()
            user_output(f"Validated {len(validation_results)} kit configuration(s):")
            valid_check = click.style("✓", fg="green")
            valid_num = click.style(str(valid_count), fg="green")
            user_output(f"  {valid_check} Valid: {valid_num}")

            if invalid_count > 0:
                invalid_check = click.style("✗", fg="red")
                invalid_num = click.style(str(invalid_count), fg="red")
                user_output(f"  {invalid_check} Invalid: {invalid_num}")
            else:
                success_msg = "✨ All kit configurations are valid!"
                user_output(click.style(success_msg, fg="green", bold=True))

        if invalid_count > 0:
            config_passed = False
        else:
            config_passed = True

    if verbose:
        user_output()

    # Part 2: Validate artifacts (silent validation, errors will be reported in sync check)
    validation_results = validate_project(project_dir)

    if len(validation_results) == 0:
        validation_passed = True
    else:
        invalid_count = sum(1 for r in validation_results if not r.is_valid)

        # Only show errors, not the full list
        if invalid_count > 0:
            user_output(click.style("📋 Artifact Validation Errors", fg="white", bold=True))
            for result in validation_results:
                if not result.is_valid:
                    status = click.style("✗", fg="red")
                    rel_path = result.artifact_path.relative_to(project_dir)
                    user_output(f"{status} {click.style(str(rel_path), fg='cyan')}")
                    for error in result.errors:
                        user_output(f"  - {error}")
            user_output()
            validation_passed = False
        else:
            validation_passed = True

    # Part 3: Check bundled kit sync status
    if verbose:
        user_output(click.style("🔄 Bundled Kit Sync Status", fg="white", bold=True))

    sync_passed = True
    if not config_exists:
        if verbose:
            user_output("No kits.toml found - skipping sync check")
    elif len(config.kits) == 0:
        if verbose:
            user_output("No kits installed - skipping sync check")
    else:
        bundled_source = BundledKitSource()
        all_results: list[tuple[str, list, list[str], list[str]]] = []

        for kit_id_iter, installed in config.kits.items():
            # Only check kits from bundled source
            if installed.source_type != SOURCE_TYPE_BUNDLED:
                continue

            # Get bundled kit base path
            bundled_path = bundled_source._get_bundled_kit_path(installed.kit_id)
            if bundled_path is None:
                user_output(f"Warning: Could not find bundled kit: {installed.kit_id}")
                continue

            # Check each artifact
            kit_results = []
            for artifact_path in installed.artifacts:
                result = check_artifact_sync(project_dir, artifact_path, bundled_path)
                kit_results.append(result)

            # Load manifest and check for missing/obsolete artifacts
            missing_artifacts: list[str] = []
            obsolete_artifacts: list[str] = []

            manifest_path = bundled_path / "kit.yaml"
            if manifest_path.exists():
                manifest = load_kit_manifest(manifest_path)
                missing_artifacts, obsolete_artifacts = compare_artifact_lists(
                    manifest.artifacts,
                    installed.artifacts,
                )

            all_results.append((kit_id_iter, kit_results, missing_artifacts, obsolete_artifacts))

        if len(all_results) == 0:
            if verbose:
                user_output("No bundled kits found to check")
            sync_passed = True
        else:
            # Display results
            total_artifacts = 0
            in_sync_count = 0
            out_of_sync_count = 0
            missing_count = 0
            obsolete_count = 0

            for kit_id_iter, results, missing, obsolete in all_results:
                total_artifacts += len(results)
                kit_in_sync = sum(1 for r in results if r.is_in_sync)
                kit_out_of_sync = len(results) - kit_in_sync

                in_sync_count += kit_in_sync
                out_of_sync_count += kit_out_of_sync
                missing_count += len(missing)
                obsolete_count += len(obsolete)

                has_issues = kit_out_of_sync > 0 or len(missing) > 0 or len(obsolete) > 0
                if verbose or has_issues:
                    user_output(f"\nKit: {click.style(kit_id_iter, fg='cyan')}")
                    for result in results:
                        if result.is_in_sync:
                            status = click.style("✓", fg="green")
                        else:
                            status = click.style("✗", fg="red")
                        rel_path = result.artifact_path.relative_to(project_dir)
                        user_output(f"  {status} {click.style(str(rel_path), fg='cyan')}")

                        if not result.is_in_sync and result.reason is not None:
                            reason_msg = f"      {result.reason}"
                            user_output(click.style(reason_msg, fg="white", dim=True))

                    # Show missing artifacts
                    if len(missing) > 0:
                        user_output()
                        user_output("  Missing artifacts (in manifest but not installed):")
                        for missing_path in missing:
                            user_output(f"    - {missing_path}")

                    # Show obsolete artifacts
                    if len(obsolete) > 0:
                        user_output()
                        user_output("  Obsolete artifacts (installed but not in manifest):")
                        for obsolete_path in obsolete:
                            user_output(f"    - {obsolete_path}")

            # Summary
            if verbose:
                user_output()
                kit_count = len(all_results)
                summary = f"Checked {total_artifacts} artifact(s) from {kit_count} bundled kit(s):"
                user_output(summary)
                sync_check = click.style("✓", fg="green")
                sync_num = click.style(str(in_sync_count), fg="green")
                user_output(f"  {sync_check} In sync: {sync_num}")

                if out_of_sync_count > 0:
                    out_check = click.style("✗", fg="red")
                    out_num = click.style(str(out_of_sync_count), fg="red")
                    user_output(f"  {out_check} Out of sync: {out_num}")

                if missing_count > 0:
                    miss_check = click.style("⚠", fg="yellow")
                    miss_num = click.style(str(missing_count), fg="yellow")
                    user_output(f"  {miss_check} Missing: {miss_num}")

                if obsolete_count > 0:
                    obs_check = click.style("⚠", fg="yellow")
                    obs_num = click.style(str(obsolete_count), fg="yellow")
                    user_output(f"  {obs_check} Obsolete: {obs_num}")
            else:
                # In non-verbose mode, still print missing/obsolete counts if there are issues
                if missing_count > 0:
                    miss_check = click.style("⚠", fg="yellow")
                    miss_num = click.style(str(missing_count), fg="yellow")
                    user_output(f"  {miss_check} Missing: {miss_num}")

                if obsolete_count > 0:
                    obs_check = click.style("⚠", fg="yellow")
                    obs_num = click.style(str(obsolete_count), fg="yellow")
                    user_output(f"  {obs_check} Obsolete: {obs_num}")

            if out_of_sync_count > 0 or missing_count > 0 or obsolete_count > 0:
                if verbose:
                    user_output()
                    user_output("Run 'erk kit sync --force' to update artifacts")
                sync_passed = False
            else:
                if verbose:
                    user_output()
                    success_msg = "✨ All artifacts are in sync!"
                    user_output(click.style(success_msg, fg="green", bold=True))
                sync_passed = True

    if verbose:
        user_output()

    # Part 4: Hook configuration validation
    if verbose:
        user_output(click.style("🪝 Hook Configuration Validation", fg="white", bold=True))

    hook_passed = True
    if not config_exists:
        if verbose:
            user_output("No kits.toml found - skipping hook validation")
    elif len(config.kits) == 0:
        if verbose:
            user_output("No kits installed - skipping hook validation")
    else:
        hook_results, validation_details = validate_hook_configuration(project_dir, config)

        # Display hook information in verbose mode
        if verbose and len(validation_details) > 0:
            user_output()

            for detail in validation_details:
                lifecycle_display = click.style(f"[{detail.lifecycle}]", fg="blue")

                if detail.action == "found_and_parsed":
                    status = click.style("✓", fg="green")
                    msg = (
                        f"{status} {lifecycle_display} Found dot-agent hook: "
                        f"kit={click.style(detail.kit_id or '', fg='cyan')}, "
                        f"hook={click.style(detail.hook_id or '', fg='cyan')}"
                    )
                    user_output(msg)
                    # Show the actual hook command
                    cmd_msg = f"      Command: {detail.command}"
                    user_output(click.style(cmd_msg, fg="white", dim=True))

                elif detail.action == "skipped_not_dot_agent":
                    status = click.style("⊘", fg="yellow")
                    msg = (
                        f"{status} {lifecycle_display} Skipped: Not a dot-agent managed hook "
                        f"(no ERK_KIT_ID found)"
                    )
                    user_output(msg)
                    # Show command preview (first 80 chars)
                    if len(detail.command) > 80:
                        cmd_preview = detail.command[:80] + "..."
                    else:
                        cmd_preview = detail.command
                    cmd_msg = f"      Command: {cmd_preview}"
                    user_output(click.style(cmd_msg, fg="white", dim=True))

                elif detail.action == "parse_error":
                    status = click.style("✗", fg="red")
                    kit_display = click.style(detail.kit_id or "unknown", fg="red")
                    msg = (
                        f"{status} {lifecycle_display} Parse error for kit "
                        f"{kit_display}: {detail.error_message}"
                    )
                    user_output(msg)

            user_output()

        if len(hook_results) == 0:
            if verbose:
                success_msg = "✨ No hook drift detected - all hooks are in sync!"
                user_output(click.style(success_msg, fg="green", bold=True))
            hook_passed = True
        else:
            # Display drift issues
            if verbose:
                for drift_result in hook_results:
                    user_output()
                    user_output(f"Kit: {click.style(drift_result.kit_id, fg='cyan')}")

                    for issue in drift_result.issues:
                        if issue.severity == "error":
                            status = click.style("✗", fg="red")
                        else:
                            status = click.style("⚠", fg="yellow")
                        user_output(f"  {status} {issue.message}")

                        if issue.expected is not None:
                            expected_msg = f"      Expected: {issue.expected}"
                            user_output(click.style(expected_msg, fg="white", dim=True))
                        if issue.actual is not None:
                            actual_msg = f"      Actual:   {issue.actual}"
                            user_output(click.style(actual_msg, fg="white", dim=True))

                # Summary
                user_output()
                kit_count = len(hook_results)
                error_count = sum(
                    1 for r in hook_results for i in r.issues if i.severity == "error"
                )
                warning_count = sum(
                    1 for r in hook_results for i in r.issues if i.severity == "warning"
                )

                user_output(f"Checked hook configuration for {kit_count} kit(s):")
                if error_count > 0:
                    error_check = click.style("✗", fg="red")
                    error_num = click.style(str(error_count), fg="red")
                    user_output(f"  {error_check} Errors: {error_num}")
                if warning_count > 0:
                    warn_check = click.style("⚠", fg="yellow")
                    warn_num = click.style(str(warning_count), fg="yellow")
                    user_output(f"  {warn_check} Warnings: {warn_num}")

                user_output()
                sync_msg = "Run 'erk kit sync --force' to update hook configuration"
                user_output(sync_msg)
            hook_passed = False

    if verbose:
        user_output()

    # Part 5: Unknown Field Detection
    if verbose:
        user_output(click.style("🔎 Unknown Field Detection", fg="white", bold=True))

    unknown_fields_passed = True
    if not config_exists:
        if verbose:
            user_output("No kits.toml found - skipping unknown field detection")
    else:
        unknown_field_results = validate_unknown_fields(project_dir, config)

        if len(unknown_field_results) == 0:
            if verbose:
                success_msg = "✨ No unknown fields detected - configuration is clean!"
                user_output(click.style(success_msg, fg="green", bold=True))
        else:
            # Display warnings
            if verbose:
                user_output()
            for result in unknown_field_results:
                fields_str = ", ".join(result.unknown_fields)
                warning_icon = click.style("⚠", fg="yellow")
                location = click.style(result.location, fg="cyan")
                msg = f"{warning_icon} {location}: {fields_str}"
                user_output(msg)

            # Summary
            if verbose:
                user_output()
                total_unknown = sum(len(r.unknown_fields) for r in unknown_field_results)
                location_count = len(unknown_field_results)
                warn_msg = f"Found {total_unknown} unknown field(s) in {location_count} location(s)"
                user_output(click.style(warn_msg, fg="yellow"))
                user_output()
                help_msg = "Note: Unknown fields are warnings only and do not fail the check"
                user_output(click.style(help_msg, fg="white", dim=True))

    # Overall result
    if verbose:
        user_output()
        user_output(click.style("=" * 40, fg="white", dim=True))

    all_passed = (
        config_passed
        and validation_passed
        and sync_passed
        and hook_passed
        and unknown_fields_passed
    )
    if all_passed:
        user_output(click.style("✅ All checks passed!", fg="green", bold=True))
    else:
        user_output(click.style("Some checks failed", fg="red", bold=True))
        raise SystemExit(1)
