"""Capability groups - themed bundles of related capabilities.

Groups are virtual aliases that expand to their member capabilities.
Example: `erk init capability add python-dev` installs dignified-python,
fake-driven-testing, and devrun-agent.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CapabilityGroup:
    """A themed group of related capabilities."""

    name: str
    description: str
    members: tuple[str, ...]


# Group definitions
PYTHON_DEV_GROUP = CapabilityGroup(
    name="python-dev",
    description="Complete Python development setup",
    members=("dignified-python", "fake-driven-testing", "devrun-agent"),
)

GITHUB_WORKFLOW_GROUP = CapabilityGroup(
    name="github-workflow",
    description="GitHub integration",
    members=("gh", "erk-impl-workflow"),
)

GRAPHITE_WORKFLOW_GROUP = CapabilityGroup(
    name="graphite-workflow",
    description="Stacked PR workflow",
    members=("gt",),
)

SKILL_AUTHORING_GROUP = CapabilityGroup(
    name="skill-authoring",
    description="Creating Claude artifacts",
    members=("command-creator", "cli-skill-creator", "learned-docs"),
)


# Registry of all groups
CAPABILITY_GROUPS: dict[str, CapabilityGroup] = {
    group.name: group
    for group in [
        PYTHON_DEV_GROUP,
        GITHUB_WORKFLOW_GROUP,
        GRAPHITE_WORKFLOW_GROUP,
        SKILL_AUTHORING_GROUP,
    ]
}


def is_group(name: str) -> bool:
    """Check if name is a capability group.

    Args:
        name: The name to check

    Returns:
        True if name is a registered group
    """
    return name in CAPABILITY_GROUPS


def get_group(name: str) -> CapabilityGroup | None:
    """Get a capability group by name.

    Args:
        name: The group name

    Returns:
        The CapabilityGroup if found, None otherwise
    """
    return CAPABILITY_GROUPS.get(name)


def list_groups() -> list[CapabilityGroup]:
    """Get all registered capability groups.

    Returns:
        List of all registered groups
    """
    return list(CAPABILITY_GROUPS.values())


def expand_capability_names(names: list[str]) -> list[str]:
    """Expand group names to individual capabilities.

    If a name is a group, it expands to all member capabilities.
    Individual capability names pass through unchanged.
    Preserves order and removes duplicates.

    Args:
        names: List of capability or group names

    Returns:
        List of individual capability names (groups expanded)
    """
    seen: set[str] = set()
    result: list[str] = []

    for name in names:
        if name in CAPABILITY_GROUPS:
            # Expand group to members
            for member in CAPABILITY_GROUPS[name].members:
                if member not in seen:
                    seen.add(member)
                    result.append(member)
        else:
            # Individual capability
            if name not in seen:
                seen.add(name)
                result.append(name)

    return result
