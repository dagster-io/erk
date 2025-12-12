"""Custom exceptions for kit resolution errors."""

from pathlib import Path


class DotAgentNonIdealStateException(Exception):
    """Base exception for all non-ideal states in erk.kits.

    This is the root exception for all expected error conditions that should
    display clean error messages to users without requiring --debug mode.
    """

    pass


class KitResolutionError(DotAgentNonIdealStateException):
    """Base exception for kit resolution errors.

    Inherits from DotAgentNonIdealStateException to ensure clean error display.
    """

    pass


class KitNotFoundError(KitResolutionError):
    """Kit does not exist in any configured source."""

    def __init__(self, kit_id: str, sources_checked: list[str]) -> None:
        self.kit_id = kit_id
        self.sources_checked = sources_checked
        super().__init__(
            f"Kit '{kit_id}' not found in any source. Sources checked: {', '.join(sources_checked)}"
        )


class ResolverNotConfiguredError(KitResolutionError):
    """No resolver is configured to handle this source type."""

    def __init__(self, source: str, available_types: list[str]) -> None:
        self.source = source
        self.available_types = available_types
        super().__init__(
            f"No resolver configured for source '{source}'. "
            f"Available resolvers: {', '.join(available_types) if available_types else 'none'}"
        )


class SourceAccessError(KitResolutionError):
    """Failed to access kit source (network, filesystem, etc.)."""

    def __init__(self, source_type: str, source: str, cause: Exception | None = None) -> None:
        self.source_type = source_type
        self.source = source
        self.cause = cause
        message = f"Failed to access {source_type} source '{source}'"
        if cause:
            message += f": {str(cause)}"
        super().__init__(message)


class KitManifestError(KitResolutionError):
    """Error loading or parsing kit manifest."""

    def __init__(self, manifest_path: Path, cause: Exception | None = None) -> None:
        self.manifest_path = manifest_path
        self.cause = cause
        message = f"Failed to load kit manifest from '{manifest_path}'"
        if cause:
            message += f": {str(cause)}"
        super().__init__(message)


class KitVersionError(KitResolutionError):
    """Kit version-related error (version mismatch, invalid version, etc.)."""

    def __init__(self, kit_id: str, message: str) -> None:
        self.kit_id = kit_id
        super().__init__(f"Version error for kit '{kit_id}': {message}")


# New exception types for specific non-ideal states


class SourceFormatError(KitResolutionError):
    """Invalid source format specification."""

    def __init__(self, source: str, expected_format: str | None = None) -> None:
        self.source = source
        self.expected_format = expected_format
        message = f"Invalid source format: '{source}'"
        if expected_format:
            message += f". {expected_format}"
        super().__init__(message)


class KitConfigurationError(KitResolutionError):
    """Kit configuration or manifest issues."""

    def __init__(self, message: str, kit_id: str | None = None) -> None:
        self.kit_id = kit_id
        if kit_id:
            message = f"Configuration error for kit '{kit_id}': {message}"
        super().__init__(message)


class HookConfigurationError(DotAgentNonIdealStateException):
    """Hook configuration validation errors.

    Inherits directly from DotAgentNonIdealStateException since hooks
    are separate from kit resolution.
    """

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        super().__init__(f"Hook configuration error in '{field}': {message}")


class ArtifactConflictError(DotAgentNonIdealStateException):
    """Artifact installation conflicts.

    Replaces FileExistsError for artifact conflicts.
    """

    def __init__(
        self, artifact_path: Path, suggestion: str = "Use --force to replace existing files"
    ) -> None:
        self.artifact_path = artifact_path
        self.suggestion = suggestion
        super().__init__(f"Artifact already exists: {artifact_path}\n{suggestion}")


class InvalidKitIdError(KitResolutionError):
    """Invalid kit ID format.

    Kit IDs must only contain lowercase letters, numbers, and hyphens.
    """

    def __init__(self, kit_id: str) -> None:
        self.kit_id = kit_id
        super().__init__(
            f"Invalid kit ID '{kit_id}': must only contain lowercase letters, numbers, and "
            f"hyphens (a-z, 0-9, -)"
        )
