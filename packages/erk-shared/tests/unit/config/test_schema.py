"""Tests for the config schema module."""

from erk_shared.config.schema import (
    ConfigLevel,
    FieldMetadata,
    GlobalConfigSchema,
    RepoConfigSchema,
    get_field_metadata,
    get_global_config_fields,
    get_global_config_key_names,
    get_global_only_keys,
    get_overridable_keys,
    get_repo_config_fields,
    is_global_config_key,
    iter_displayable_fields,
)


class TestGlobalConfigSchema:
    """Tests for GlobalConfigSchema metadata."""

    def test_has_expected_fields(self) -> None:
        """Schema contains all expected global config fields."""
        field_names = set(GlobalConfigSchema.model_fields.keys())
        expected_fields = {
            "erk_root",
            "use_graphite",
            "github_planning",
            "fix_conflicts_require_dangerous_flag",
            "show_hidden_commands",
            "prompt_learn_on_land",
            "shell_integration",
        }
        assert field_names == expected_fields

    def test_erk_root_is_global_only(self) -> None:
        """erk_root should be marked as global-only."""
        meta = get_field_metadata(GlobalConfigSchema, "erk_root")
        assert meta.level == ConfigLevel.GLOBAL_ONLY
        assert meta.cli_key == "erk_root"

    def test_use_graphite_is_overridable(self) -> None:
        """use_graphite should be overridable at repo/local level."""
        meta = get_field_metadata(GlobalConfigSchema, "use_graphite")
        assert meta.level == ConfigLevel.OVERRIDABLE
        assert meta.cli_key == "use_graphite"

    def test_all_fields_have_descriptions(self) -> None:
        """All schema fields should have descriptions."""
        for meta in get_global_config_fields():
            assert meta.description, f"Field {meta.field_name} missing description"


class TestRepoConfigSchema:
    """Tests for RepoConfigSchema metadata."""

    def test_has_expected_fields(self) -> None:
        """Schema contains all expected repo config fields."""
        field_names = set(RepoConfigSchema.model_fields.keys())
        expected_fields = {
            "trunk_branch",
            "pool_max_slots",
            "pool_checkout_shell",
            "pool_checkout_commands",
            "env",
            "post_create_shell",
            "post_create_commands",
            "plans_repo",
        }
        assert field_names == expected_fields

    def test_trunk_branch_has_special_marker(self) -> None:
        """trunk-branch lives in pyproject.toml, should be marked."""
        meta = get_field_metadata(RepoConfigSchema, "trunk_branch")
        assert meta.cli_key == "trunk-branch"
        assert meta.level == ConfigLevel.REPO_ONLY

    def test_env_is_marked_dynamic(self) -> None:
        """env field should be marked as dynamic for env.* pattern."""
        meta = get_field_metadata(RepoConfigSchema, "env")
        assert meta.dynamic is True
        assert meta.cli_key == "env.<name>"

    def test_pool_max_slots_has_default_display(self) -> None:
        """pool_max_slots should have a default_display value."""
        meta = get_field_metadata(RepoConfigSchema, "pool_max_slots")
        assert meta.default_display == 4
        assert meta.cli_key == "pool.max_slots"


class TestFieldMetadata:
    """Tests for FieldMetadata extraction."""

    def test_get_field_metadata_returns_all_expected_attributes(self) -> None:
        """get_field_metadata returns complete metadata."""
        meta = get_field_metadata(GlobalConfigSchema, "prompt_learn_on_land")
        assert isinstance(meta, FieldMetadata)
        assert meta.field_name == "prompt_learn_on_land"
        assert meta.cli_key == "prompt_learn_on_land"
        assert meta.description != ""
        assert meta.level == ConfigLevel.OVERRIDABLE


class TestIterDisplayableFields:
    """Tests for iter_displayable_fields."""

    def test_iterates_all_global_fields(self) -> None:
        """Should iterate all non-internal global fields."""
        fields = list(iter_displayable_fields(GlobalConfigSchema))
        assert len(fields) == 7

    def test_iterates_all_repo_fields(self) -> None:
        """Should iterate all non-internal repo fields."""
        fields = list(get_repo_config_fields())
        assert len(fields) == 8

    def test_preserves_field_order(self) -> None:
        """Fields should be returned in definition order."""
        field_names = [meta.field_name for meta in get_global_config_fields()]
        expected_order = [
            "erk_root",
            "use_graphite",
            "github_planning",
            "fix_conflicts_require_dangerous_flag",
            "show_hidden_commands",
            "prompt_learn_on_land",
            "shell_integration",
        ]
        assert field_names == expected_order


class TestHelperFunctions:
    """Tests for schema helper functions."""

    def test_get_overridable_keys(self) -> None:
        """get_overridable_keys returns correct set."""
        keys = get_overridable_keys()
        assert "erk_root" not in keys
        assert "use_graphite" in keys
        assert "github_planning" in keys
        assert "prompt_learn_on_land" in keys
        assert "shell_integration" in keys

    def test_get_global_only_keys(self) -> None:
        """get_global_only_keys returns correct set."""
        keys = get_global_only_keys()
        assert "erk_root" in keys
        assert "use_graphite" not in keys

    def test_get_global_config_key_names(self) -> None:
        """get_global_config_key_names returns all global keys."""
        keys = get_global_config_key_names()
        assert "erk_root" in keys
        assert "use_graphite" in keys
        assert len(keys) == 7

    def test_is_global_config_key_positive(self) -> None:
        """is_global_config_key returns True for global keys."""
        assert is_global_config_key("erk_root") is True
        assert is_global_config_key("use_graphite") is True

    def test_is_global_config_key_negative(self) -> None:
        """is_global_config_key returns False for non-global keys."""
        assert is_global_config_key("trunk_branch") is False
        assert is_global_config_key("nonexistent") is False
