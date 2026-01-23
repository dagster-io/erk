"""Pydantic schemas for erk configuration.

These schemas serve as the single source of truth for:
- Configuration field names and CLI keys
- Field descriptions (for `erk config keys`)
- Configuration levels (global-only vs overridable vs repo-only)
- Display formatting
"""

from __future__ import annotations

from collections.abc import Iterator
from enum import Enum

from pydantic import BaseModel, Field


class ConfigLevel(str, Enum):
    """Defines where a configuration key can be set.

    GLOBAL_ONLY: Can only be set in ~/.erk/config.toml
    OVERRIDABLE: Can be set at global, repo (.erk/config.toml), or local level
    REPO_ONLY: Can only be set in repository config (not global)
    """

    GLOBAL_ONLY = "global_only"
    OVERRIDABLE = "overridable"
    REPO_ONLY = "repo_only"


class GlobalConfigSchema(BaseModel):
    """Schema for global configuration keys.

    Fields are defined in display order for `erk config list/keys`.
    Each field's json_schema_extra contains metadata for display and parsing.
    """

    erk_root: str = Field(
        description="Root directory for erk data (~/.erk by default)",
        json_schema_extra={"level": ConfigLevel.GLOBAL_ONLY, "cli_key": "erk_root"},
    )
    use_graphite: bool = Field(
        description="Enable Graphite integration for stack management",
        json_schema_extra={"level": ConfigLevel.OVERRIDABLE, "cli_key": "use_graphite"},
    )
    github_planning: bool = Field(
        description="Enable GitHub issues integration for planning",
        json_schema_extra={"level": ConfigLevel.OVERRIDABLE, "cli_key": "github_planning"},
    )
    fix_conflicts_require_dangerous_flag: bool = Field(
        description="Require --dangerous flag for fix-conflicts",
        json_schema_extra={
            "level": ConfigLevel.OVERRIDABLE,
            "cli_key": "fix_conflicts_require_dangerous_flag",
        },
    )
    show_hidden_commands: bool = Field(
        description="Show deprecated/hidden commands in help output",
        json_schema_extra={"level": ConfigLevel.OVERRIDABLE, "cli_key": "show_hidden_commands"},
    )
    prompt_learn_on_land: bool = Field(
        description="Prompt about running learn before landing plan PRs",
        json_schema_extra={"level": ConfigLevel.OVERRIDABLE, "cli_key": "prompt_learn_on_land"},
    )
    shell_integration: bool = Field(
        description="Enable auto-navigation shell integration (opt-in)",
        json_schema_extra={"level": ConfigLevel.OVERRIDABLE, "cli_key": "shell_integration"},
    )


class RepoConfigSchema(BaseModel):
    """Schema for repository-level configuration keys.

    Fields are defined in display order for `erk config keys`.
    """

    trunk_branch: str | None = Field(
        description="The main/master branch name for the repository",
        json_schema_extra={
            "level": ConfigLevel.REPO_ONLY,
            "cli_key": "trunk-branch",
            "special": "pyproject",  # Lives in pyproject.toml
        },
    )
    pool_max_slots: int | None = Field(
        description="Maximum number of pool slots for worktree pool",
        json_schema_extra={
            "level": ConfigLevel.REPO_ONLY,
            "cli_key": "pool.max_slots",
            "dataclass_attr": "pool_size",
            "default_display": 4,
        },
    )
    pool_checkout_shell: str | None = Field(
        description="Shell to use for pool checkout commands",
        json_schema_extra={"level": ConfigLevel.REPO_ONLY, "cli_key": "pool.checkout.shell"},
    )
    pool_checkout_commands: list[str] = Field(
        description="Commands to run after checking out a worktree from pool",
        json_schema_extra={"level": ConfigLevel.REPO_ONLY, "cli_key": "pool.checkout.commands"},
    )
    env: dict[str, str] = Field(
        description="Environment variables to set in worktrees",
        json_schema_extra={
            "level": ConfigLevel.REPO_ONLY,
            "cli_key": "env.<name>",
            "dynamic": True,
        },
    )
    post_create_shell: str | None = Field(
        description="Shell to use for post-create commands",
        json_schema_extra={"level": ConfigLevel.REPO_ONLY, "cli_key": "post_create.shell"},
    )
    post_create_commands: list[str] = Field(
        description="Commands to run after creating a worktree",
        json_schema_extra={"level": ConfigLevel.REPO_ONLY, "cli_key": "post_create.commands"},
    )
    plans_repo: str | None = Field(
        description="Repository for storing plan issues (owner/repo format)",
        json_schema_extra={"level": ConfigLevel.REPO_ONLY, "cli_key": "plans.repo"},
    )


class FieldMetadata:
    """Extracted metadata for a configuration field."""

    def __init__(
        self,
        *,
        field_name: str,
        cli_key: str,
        description: str,
        level: ConfigLevel,
        default: object,
        default_display: object,
        dynamic: bool,
    ) -> None:
        self.field_name = field_name
        self.cli_key = cli_key
        self.description = description
        self.level = level
        self.default = default
        self.default_display = default_display
        self.dynamic = dynamic


def get_field_metadata(model: type[BaseModel], field_name: str) -> FieldMetadata:
    """Extract metadata from a Pydantic field definition.

    Args:
        model: The Pydantic model class
        field_name: Name of the field to extract metadata for

    Returns:
        FieldMetadata with cli_key, description, level, and default info
    """
    field_info = model.model_fields[field_name]
    extra = field_info.json_schema_extra
    if extra is None:
        extra = {}
    # Cast to dict since json_schema_extra could be callable
    if callable(extra):
        extra = {}
    return FieldMetadata(
        field_name=field_name,
        cli_key=extra.get("cli_key", field_name),
        description=field_info.description or "",
        level=extra.get("level", ConfigLevel.REPO_ONLY),
        default=field_info.default,
        default_display=extra.get("default_display"),
        dynamic=extra.get("dynamic", False),
    )


def iter_displayable_fields(model: type[BaseModel]) -> Iterator[FieldMetadata]:
    """Iterate through model fields in definition order with metadata.

    Fields with `internal=True` in json_schema_extra are skipped.

    Args:
        model: The Pydantic model class

    Yields:
        FieldMetadata for each displayable field
    """
    for field_name, field_info in model.model_fields.items():
        extra = field_info.json_schema_extra
        if extra is None:
            extra = {}
        if callable(extra):
            extra = {}
        if extra.get("internal", False):
            continue
        yield get_field_metadata(model, field_name)


def get_global_config_fields() -> Iterator[FieldMetadata]:
    """Get all global configuration fields in display order."""
    return iter_displayable_fields(GlobalConfigSchema)


def get_repo_config_fields() -> Iterator[FieldMetadata]:
    """Get all repository configuration fields in display order."""
    return iter_displayable_fields(RepoConfigSchema)


def get_overridable_keys() -> set[str]:
    """Get the set of global keys that can be overridden at repo/local level."""
    return {
        meta.field_name
        for meta in get_global_config_fields()
        if meta.level == ConfigLevel.OVERRIDABLE
    }


def get_global_only_keys() -> set[str]:
    """Get the set of keys that can ONLY be set at global level."""
    return {
        meta.field_name
        for meta in get_global_config_fields()
        if meta.level == ConfigLevel.GLOBAL_ONLY
    }


def get_global_config_key_names() -> set[str]:
    """Get the set of all global config field names (for validation)."""
    return {meta.field_name for meta in get_global_config_fields()}


def is_global_config_key(key: str) -> bool:
    """Check if a key is a global configuration key."""
    return key in get_global_config_key_names()
