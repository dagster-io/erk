"""Optional features registry for erk.

Features are optional bundles of workflows that can be installed
via `erk init --with-<feature-name>`.

Prompts are accessed via `erk exec get-prompt <name>` rather than being synced.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Feature:
    """An optional feature that can be installed in a project."""

    name: str
    description: str
    workflows: frozenset[str]


AVAILABLE_FEATURES: dict[str, Feature] = {
    "dignified-review": Feature(
        name="dignified-review",
        description="Automated Python code review against dignified-python standards",
        workflows=frozenset({"dignified-python-review.yml"}),
    ),
}


def get_feature(name: str) -> Feature | None:
    """Get a feature by name, returning None if not found."""
    return AVAILABLE_FEATURES.get(name)


def list_features() -> list[Feature]:
    """List all available features."""
    return list(AVAILABLE_FEATURES.values())
