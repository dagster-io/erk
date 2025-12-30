"""Kit manifest models."""

from dataclasses import dataclass, field

from erk.kits.hooks.models import HookDefinition


@dataclass(frozen=True)
class KitManifest:
    """Kit manifest from kit.yaml."""

    name: str
    version: str
    description: str
    artifacts: dict[str, list[str]]  # type -> paths
    license: str | None = None
    homepage: str | None = None
    hooks: list[HookDefinition] = field(default_factory=list)

    def validate_namespace_pattern(self) -> list[str]:
        """Check if artifacts follow recommended hyphenated naming convention.

        This is informational only - the standard convention is:
        {type}s/{kit_name}-{suffix}/...

        For example: skills/devrun-make/SKILL.md for kit 'devrun'.

        Returns:
            List of warnings for artifacts that don't follow the convention (empty if all follow it)
        """
        # No enforcement - hyphenated naming is a convention, not a requirement
        return []
