"""Tests for check command."""

from pathlib import Path
from typing import cast

from click.testing import CliRunner

from erk.cli.commands.kit.check import (
    check,
    check_artifact_sync,
    compare_artifact_lists,
    validate_kit_fields,
)
from erk.kits.io.state import save_project_config
from erk.kits.models.config import InstalledKit, ProjectConfig
from erk.kits.models.types import SourceType


def test_compare_artifact_lists_no_differences() -> None:
    """Test compare_artifact_lists when artifacts match exactly."""
    manifest_artifacts = {
        "command": ["commands/test/foo.md"],
        "skill": ["skills/test/bar.md"],
    }
    installed_artifacts = [
        ".claude/commands/test/foo.md",
        ".claude/skills/test/bar.md",
    ]

    missing, obsolete = compare_artifact_lists(manifest_artifacts, installed_artifacts)

    assert len(missing) == 0
    assert len(obsolete) == 0


def test_compare_artifact_lists_missing_artifacts() -> None:
    """Test compare_artifact_lists detects missing artifacts."""
    manifest_artifacts = {
        "command": ["commands/test/foo.md", "commands/test/bar.md"],
        "skill": ["skills/test/baz.md"],
    }
    installed_artifacts = [
        ".claude/commands/test/foo.md",
    ]

    missing, obsolete = compare_artifact_lists(manifest_artifacts, installed_artifacts)

    assert len(missing) == 2
    assert ".claude/commands/test/bar.md" in missing
    assert ".claude/skills/test/baz.md" in missing
    assert len(obsolete) == 0


def test_compare_artifact_lists_obsolete_artifacts() -> None:
    """Test compare_artifact_lists detects obsolete artifacts."""
    manifest_artifacts = {
        "command": ["commands/test/foo.md"],
    }
    installed_artifacts = [
        ".claude/commands/test/foo.md",
        ".claude/commands/test/old.md",
        ".claude/skills/test/deprecated.md",
    ]

    missing, obsolete = compare_artifact_lists(manifest_artifacts, installed_artifacts)

    assert len(missing) == 0
    assert len(obsolete) == 2
    assert ".claude/commands/test/old.md" in obsolete
    assert ".claude/skills/test/deprecated.md" in obsolete


def test_compare_artifact_lists_both_missing_and_obsolete() -> None:
    """Test compare_artifact_lists detects both missing and obsolete."""
    manifest_artifacts = {
        "command": ["commands/test/foo.md", "commands/test/new.md"],
    }
    installed_artifacts = [
        ".claude/commands/test/foo.md",
        ".claude/commands/test/old.md",
    ]

    missing, obsolete = compare_artifact_lists(manifest_artifacts, installed_artifacts)

    assert len(missing) == 1
    assert ".claude/commands/test/new.md" in missing
    assert len(obsolete) == 1
    assert ".claude/commands/test/old.md" in obsolete


def test_compare_artifact_lists_empty_manifest() -> None:
    """Test compare_artifact_lists with empty manifest."""
    manifest_artifacts: dict[str, list[str]] = {}
    installed_artifacts = [
        ".claude/commands/test/foo.md",
    ]

    missing, obsolete = compare_artifact_lists(manifest_artifacts, installed_artifacts)

    assert len(missing) == 0
    assert len(obsolete) == 1
    assert ".claude/commands/test/foo.md" in obsolete


def test_compare_artifact_lists_empty_installed() -> None:
    """Test compare_artifact_lists with no installed artifacts."""
    manifest_artifacts = {
        "command": ["commands/test/foo.md"],
    }
    installed_artifacts: list[str] = []

    missing, obsolete = compare_artifact_lists(manifest_artifacts, installed_artifacts)

    assert len(missing) == 1
    assert ".claude/commands/test/foo.md" in missing
    assert len(obsolete) == 0


def test_compare_artifact_lists_both_empty() -> None:
    """Test compare_artifact_lists with both empty."""
    manifest_artifacts: dict[str, list[str]] = {}
    installed_artifacts: list[str] = []

    missing, obsolete = compare_artifact_lists(manifest_artifacts, installed_artifacts)

    assert len(missing) == 0
    assert len(obsolete) == 0


def test_check_artifact_sync_both_files_identical(tmp_path: Path) -> None:
    """Test sync check when both files exist and are identical."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    bundled_base = tmp_path / "bundled"
    bundled_base.mkdir()

    # Create identical files
    local_path = project_dir / ".claude" / "skills" / "test" / "SKILL.md"
    local_path.parent.mkdir(parents=True)
    local_path.write_text("test content", encoding="utf-8")

    bundled_path = bundled_base / "skills" / "test" / "SKILL.md"
    bundled_path.parent.mkdir(parents=True)
    bundled_path.write_text("test content", encoding="utf-8")

    result = check_artifact_sync(
        project_dir,
        ".claude/skills/test/SKILL.md",
        bundled_base,
    )

    assert result.is_in_sync is True
    assert result.reason is None


def test_check_artifact_sync_local_missing(tmp_path: Path) -> None:
    """Test sync check when local file is missing."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    bundled_base = tmp_path / "bundled"
    bundled_base.mkdir()

    # Create only bundled file
    bundled_path = bundled_base / "skills" / "test" / "SKILL.md"
    bundled_path.parent.mkdir(parents=True)
    bundled_path.write_text("test content", encoding="utf-8")

    result = check_artifact_sync(
        project_dir,
        ".claude/skills/test/SKILL.md",
        bundled_base,
    )

    assert result.is_in_sync is False
    assert result.reason == "Local artifact missing"


def test_check_artifact_sync_bundled_missing(tmp_path: Path) -> None:
    """Test sync check when bundled file is missing."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    bundled_base = tmp_path / "bundled"
    bundled_base.mkdir()

    # Create only local file
    local_path = project_dir / ".claude" / "skills" / "test" / "SKILL.md"
    local_path.parent.mkdir(parents=True)
    local_path.write_text("test content", encoding="utf-8")

    result = check_artifact_sync(
        project_dir,
        ".claude/skills/test/SKILL.md",
        bundled_base,
    )

    assert result.is_in_sync is False
    assert result.reason == "Bundled artifact missing"


def test_check_artifact_sync_content_differs(tmp_path: Path) -> None:
    """Test sync check when files exist but content differs."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    bundled_base = tmp_path / "bundled"
    bundled_base.mkdir()

    # Create files with different content
    local_path = project_dir / ".claude" / "skills" / "test" / "SKILL.md"
    local_path.parent.mkdir(parents=True)
    local_path.write_text("local content", encoding="utf-8")

    bundled_path = bundled_base / "skills" / "test" / "SKILL.md"
    bundled_path.parent.mkdir(parents=True)
    bundled_path.write_text("bundled content", encoding="utf-8")

    result = check_artifact_sync(
        project_dir,
        ".claude/skills/test/SKILL.md",
        bundled_base,
    )

    assert result.is_in_sync is False
    assert result.reason == "Content differs"


def test_check_artifact_sync_path_handling_with_claude_prefix(tmp_path: Path) -> None:
    """Test that .claude/ prefix is properly stripped when checking bundled path."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    bundled_base = tmp_path / "bundled"
    bundled_base.mkdir()

    # Create identical files
    local_path = project_dir / ".claude" / "skills" / "test" / "SKILL.md"
    local_path.parent.mkdir(parents=True)
    local_path.write_text("test content", encoding="utf-8")

    # Bundled path should NOT have .claude/ prefix
    bundled_path = bundled_base / "skills" / "test" / "SKILL.md"
    bundled_path.parent.mkdir(parents=True)
    bundled_path.write_text("test content", encoding="utf-8")

    # Pass artifact path with .claude/ prefix
    result = check_artifact_sync(
        project_dir,
        ".claude/skills/test/SKILL.md",
        bundled_base,
    )

    assert result.is_in_sync is True


def test_check_command_no_artifacts(tmp_path: Path) -> None:
    """Test check command when no artifacts exist."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()
        config = ProjectConfig(version="1", kits={})
        save_project_config(project_dir, config)

        result = runner.invoke(check, ["--verbose"])

        assert result.exit_code == 0
        assert "No kits installed" in result.output
        assert "All checks passed" in result.output


def test_check_command_valid_artifacts(tmp_path: Path) -> None:
    """Test check command with valid artifacts."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()

        # Create valid artifact
        skill_path = project_dir / ".claude" / "skills" / "test" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test",
            encoding="utf-8",
        )

        # Create config
        config = ProjectConfig(
            version="1",
            kits={
                "test-kit": InstalledKit(
                    kit_id="test-kit",
                    version="1.0.0",
                    source_type="package",
                    artifacts=["skills/test/SKILL.md"],
                ),
            },
        )
        save_project_config(project_dir, config)

        result = runner.invoke(check)

        assert result.exit_code == 0
        assert "All checks passed" in result.output


def test_check_command_invalid_artifacts(tmp_path: Path) -> None:
    """Test check command with invalid artifacts."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()

        # Create .claude directory but no artifacts
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()

        # Create config with artifact that doesn't exist
        config = ProjectConfig(
            version="1",
            kits={
                "test-kit": InstalledKit(
                    kit_id="test-kit",
                    version="1.0.0",
                    source_type="package",
                    artifacts=["skills/missing/SKILL.md"],
                ),
            },
        )
        save_project_config(project_dir, config)

        result = runner.invoke(check)

        assert result.exit_code == 1
        assert "✗" in result.output or "Invalid" in result.output


def test_check_command_no_bundled_kits(tmp_path: Path) -> None:
    """Test check command when no bundled kits are installed."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()

        # Create valid artifact from non-bundled source
        skill_path = project_dir / ".claude" / "skills" / "test" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test",
            encoding="utf-8",
        )

        # Create config with non-bundled kit
        config = ProjectConfig(
            version="1",
            kits={
                "test-kit": InstalledKit(
                    kit_id="test-kit",
                    version="1.0.0",
                    source_type="package",
                    artifacts=["skills/test/SKILL.md"],
                ),
            },
        )
        save_project_config(project_dir, config)

        result = runner.invoke(check, ["--verbose"])

        assert result.exit_code == 0
        assert "No bundled kits found to check" in result.output
        assert "All checks passed" in result.output


def test_check_command_verbose_flag(tmp_path: Path) -> None:
    """Test check command with verbose flag shows detailed output."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()

        # Create valid artifact
        skill_path = project_dir / ".claude" / "skills" / "test" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test",
            encoding="utf-8",
        )

        # Create config
        config = ProjectConfig(
            version="1",
            kits={
                "test-kit": InstalledKit(
                    kit_id="test-kit",
                    version="1.0.0",
                    source_type="package",
                    artifacts=["skills/test/SKILL.md"],
                ),
            },
        )
        save_project_config(project_dir, config)

        result = runner.invoke(check, ["--verbose"])

        assert result.exit_code == 0
        assert "✓" in result.output  # Should show checkmarks for valid artifacts


def test_check_command_no_config(tmp_path: Path) -> None:
    """Test check command when no config file exists."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(check, ["--verbose"])

        assert result.exit_code == 0
        assert "No kits.toml found" in result.output
        assert "All checks passed" in result.output


def test_validate_kit_fields_all_valid() -> None:
    """Test validate_kit_fields with all valid fields."""
    kit = InstalledKit(
        kit_id="test-kit",
        source_type="bundled",
        version="1.0.0",
        artifacts=[".claude/skills/test/SKILL.md"],
    )
    errors = validate_kit_fields(kit)
    assert len(errors) == 0


def test_validate_kit_fields_empty_kit_id() -> None:
    """Test validate_kit_fields with empty kit_id."""
    kit = InstalledKit(
        kit_id="",
        source_type="bundled",
        version="1.0.0",
        artifacts=[".claude/skills/test/SKILL.md"],
    )
    errors = validate_kit_fields(kit)
    assert len(errors) == 1
    assert "kit_id is empty" in errors


def test_validate_kit_fields_empty_version() -> None:
    """Test validate_kit_fields with empty version."""
    kit = InstalledKit(
        kit_id="test-kit",
        source_type="bundled",
        version="",
        artifacts=[".claude/skills/test/SKILL.md"],
    )
    errors = validate_kit_fields(kit)
    assert len(errors) == 1
    assert "version is empty" in errors


def test_validate_kit_fields_invalid_source_type() -> None:
    """Test validate_kit_fields with invalid source_type."""
    kit = InstalledKit(
        kit_id="test-kit",
        source_type=cast(SourceType, "invalid"),
        version="1.0.0",
        artifacts=[".claude/skills/test/SKILL.md"],
    )
    errors = validate_kit_fields(kit)
    assert len(errors) == 1
    assert "Invalid source_type" in errors[0]


def test_validate_kit_fields_source_type_empty_string() -> None:
    """Test validate_kit_fields with empty string source_type."""
    kit = InstalledKit(
        kit_id="test-kit",
        source_type=cast(SourceType, ""),
        version="1.0.0",
        artifacts=[".claude/skills/test/SKILL.md"],
    )
    errors = validate_kit_fields(kit)
    assert len(errors) == 1
    assert "Invalid source_type" in errors[0]


def test_validate_kit_fields_source_type_whitespace() -> None:
    """Test validate_kit_fields with whitespace-only source_type."""
    kit = InstalledKit(
        kit_id="test-kit",
        source_type=cast(SourceType, "   "),
        version="1.0.0",
        artifacts=[".claude/skills/test/SKILL.md"],
    )
    errors = validate_kit_fields(kit)
    assert len(errors) == 1
    assert "Invalid source_type" in errors[0]


def test_validate_kit_fields_source_type_wrong_case() -> None:
    """Test validate_kit_fields with wrong case source_type."""
    # Test uppercase
    kit_upper = InstalledKit(
        kit_id="test-kit",
        source_type=cast(SourceType, "BUNDLED"),
        version="1.0.0",
        artifacts=[".claude/skills/test/SKILL.md"],
    )
    errors_upper = validate_kit_fields(kit_upper)
    assert len(errors_upper) == 1
    assert "Invalid source_type" in errors_upper[0]

    # Test capitalized
    kit_cap = InstalledKit(
        kit_id="test-kit",
        source_type=cast(SourceType, "Bundled"),
        version="1.0.0",
        artifacts=[".claude/skills/test/SKILL.md"],
    )
    errors_cap = validate_kit_fields(kit_cap)
    assert len(errors_cap) == 1
    assert "Invalid source_type" in errors_cap[0]


def test_validate_kit_fields_source_type_common_typos() -> None:
    """Test validate_kit_fields with common typos in source_type."""
    typos = ["bundle", "packages", "pkg", "bundles", "packge"]

    for typo in typos:
        kit = InstalledKit(
            kit_id="test-kit",
            source_type=cast(SourceType, typo),
            version="1.0.0",
            artifacts=[".claude/skills/test/SKILL.md"],
        )
        errors = validate_kit_fields(kit)
        assert len(errors) == 1, f"Expected error for typo: {typo}"
        assert "Invalid source_type" in errors[0], (
            f"Expected 'Invalid source_type' for typo: {typo}"
        )


def test_validate_kit_fields_source_type_with_surrounding_whitespace() -> None:
    """Test validate_kit_fields with valid source_type but surrounding whitespace."""
    kit = InstalledKit(
        kit_id="test-kit",
        source_type=cast(SourceType, " bundled "),
        version="1.0.0",
        artifacts=[".claude/skills/test/SKILL.md"],
    )
    errors = validate_kit_fields(kit)
    assert len(errors) == 1
    assert "Invalid source_type" in errors[0]


def test_validate_kit_fields_empty_artifacts() -> None:
    """Test validate_kit_fields with empty artifacts list.

    Bundled kits can have empty artifacts in dot-agent.toml since their
    artifacts are defined in the bundled kit.yaml instead.
    """
    kit = InstalledKit(
        kit_id="test-kit",
        source_type="bundled",
        version="1.0.0",
        artifacts=[],
    )
    errors = validate_kit_fields(kit)
    # Bundled kits are allowed to have empty artifacts in dot-agent.toml
    assert len(errors) == 0


def test_validate_kit_fields_multiple_errors() -> None:
    """Test validate_kit_fields with multiple validation errors.

    When source_type is invalid (not bundled or package), empty artifacts
    will still trigger an error.
    """
    kit = InstalledKit(
        kit_id="",
        source_type=cast(SourceType, "invalid"),
        version="",
        artifacts=[],
    )
    errors = validate_kit_fields(kit)
    assert len(errors) == 4
    assert any("kit_id is empty" in e for e in errors)
    assert any("version is empty" in e for e in errors)
    assert any("Invalid source_type" in e for e in errors)
    assert any("artifacts list is empty" in e for e in errors)


def test_check_command_bundled_kit_sync_in_sync(tmp_path: Path) -> None:
    """Test check command with bundled kit when artifacts are in sync."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()

        # Create .claude directory
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()

        # Create config with bundled kit
        # Note: We use "bundled:devrun" which is a real bundled kit in the package
        # Include all artifacts from the devrun kit
        config = ProjectConfig(
            version="1",
            kits={
                "devrun": InstalledKit(
                    kit_id="devrun",
                    version="0.1.0",
                    source_type="bundled",
                    artifacts=[
                        ".claude/agents/devrun/devrun.md",
                        ".claude/docs/devrun/tools/gt.md",
                        ".claude/docs/devrun/tools/make.md",
                        ".claude/docs/devrun/tools/prettier.md",
                        ".claude/docs/devrun/tools/pyright.md",
                        ".claude/docs/devrun/tools/pytest.md",
                        ".claude/docs/devrun/tools/ruff.md",
                    ],
                ),
            },
        )
        save_project_config(project_dir, config)

        # Create local artifacts that match bundled version
        # Read bundled artifact content
        from erk.kits.sources.bundled import BundledKitSource

        bundled_source = BundledKitSource()
        bundled_path = bundled_source._get_bundled_kit_path("devrun")
        if bundled_path is not None:
            # Create all required artifacts
            for artifact_rel in [
                "agents/devrun/devrun.md",
                "docs/devrun/tools/gt.md",
                "docs/devrun/tools/make.md",
                "docs/devrun/tools/prettier.md",
                "docs/devrun/tools/pyright.md",
                "docs/devrun/tools/pytest.md",
                "docs/devrun/tools/ruff.md",
            ]:
                bundled_artifact = bundled_path / artifact_rel
                if bundled_artifact.exists():
                    bundled_content = bundled_artifact.read_text(encoding="utf-8")

                    # Create local artifact with same content
                    local_artifact = claude_dir / artifact_rel
                    local_artifact.parent.mkdir(parents=True, exist_ok=True)
                    local_artifact.write_text(bundled_content, encoding="utf-8")

            result = runner.invoke(check)

            assert result.exit_code == 0
            assert "All checks passed" in result.output
            assert "Warning: Could not find bundled kit" not in result.output


def test_check_command_detects_missing_artifacts(tmp_path: Path) -> None:
    """Test check detects artifacts in manifest but not installed."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()

        # Create .claude directory
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()

        # Create config with bundled kit that only has one artifact installed
        # but the bundled kit has more
        config = ProjectConfig(
            version="1",
            kits={
                "gt": InstalledKit(
                    kit_id="gt",
                    version="0.1.0",
                    source_type="bundled",
                    artifacts=[".claude/commands/gt/submit-branch.md"],
                ),
            },
        )
        save_project_config(project_dir, config)

        # Create local artifact that matches bundled version
        from erk.kits.sources.bundled import BundledKitSource

        bundled_source = BundledKitSource()
        bundled_path = bundled_source._get_bundled_kit_path("gt")
        if bundled_path is not None:
            # Copy only one artifact
            bundled_artifact = bundled_path / "commands" / "gt" / "submit-branch.md"
            if bundled_artifact.exists():
                bundled_content = bundled_artifact.read_text(encoding="utf-8")
                local_artifact = claude_dir / "commands" / "gt" / "submit-branch.md"
                local_artifact.parent.mkdir(parents=True)
                local_artifact.write_text(bundled_content, encoding="utf-8")

                result = runner.invoke(check)

                # Should fail because missing artifacts
                assert result.exit_code == 1
                assert "Missing artifacts (in manifest but not installed)" in result.output
                assert ".claude/commands/gt/submit-branch.md" in result.output
                assert ".claude/skills/gt-graphite/SKILL.md" in result.output
                assert "Some checks failed" in result.output


def test_check_command_detects_obsolete_artifacts(tmp_path: Path) -> None:
    """Test check detects artifacts installed but removed from manifest."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()

        # Create .claude directory
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()

        # Create a mock bundled kit with manifest
        mock_kit_dir = tmp_path / "mock_bundled_kit"
        mock_kit_dir.mkdir()

        # Create a minimal manifest
        manifest_path = mock_kit_dir / "kit.yaml"
        manifest_path.write_text(
            """name: test-kit
version: 1.0.0
description: Test kit
artifacts:
  command:
    - commands/test/foo.md
""",
            encoding="utf-8",
        )

        # Create the artifact in bundled location
        bundled_artifact = mock_kit_dir / "commands" / "test" / "foo.md"
        bundled_artifact.parent.mkdir(parents=True)
        bundled_artifact.write_text("content", encoding="utf-8")

        # Create config with obsolete artifact (not in manifest)
        config = ProjectConfig(
            version="1",
            kits={
                "test-kit": InstalledKit(
                    kit_id="test-kit",
                    version="1.0.0",
                    source_type="bundled",
                    artifacts=[
                        ".claude/commands/test/foo.md",
                        ".claude/commands/test/old-artifact.md",
                    ],
                ),
            },
        )
        save_project_config(project_dir, config)

        # Create both local artifacts (one is obsolete)
        local_artifact1 = claude_dir / "commands" / "test" / "foo.md"
        local_artifact1.parent.mkdir(parents=True)
        local_artifact1.write_text("content", encoding="utf-8")

        local_artifact2 = claude_dir / "commands" / "test" / "old-artifact.md"
        local_artifact2.write_text("obsolete content", encoding="utf-8")

        # Monkey patch BundledKitSource to return our mock kit
        from erk.kits.sources.bundled import BundledKitSource

        original_get_path = BundledKitSource._get_bundled_kit_path

        def mock_get_path(self: BundledKitSource, source: str) -> Path | None:
            if source == "test-kit":
                return mock_kit_dir
            return original_get_path(self, source)

        BundledKitSource._get_bundled_kit_path = mock_get_path

        result = runner.invoke(check)

        # Restore original method
        BundledKitSource._get_bundled_kit_path = original_get_path

        # Should fail because obsolete artifacts
        assert result.exit_code == 1
        assert "Obsolete artifacts (installed but not in manifest)" in result.output
        assert ".claude/commands/test/old-artifact.md" in result.output
        assert "Some checks failed" in result.output


def test_check_command_missing_and_obsolete_together(tmp_path: Path) -> None:
    """Test check detects both missing and obsolete artifacts."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()

        # Create .claude directory
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()

        # Create a mock bundled kit with manifest
        mock_kit_dir = tmp_path / "mock_bundled_kit"
        mock_kit_dir.mkdir()

        # Create a manifest with two artifacts
        manifest_path = mock_kit_dir / "kit.yaml"
        manifest_path.write_text(
            """name: test-kit
version: 1.0.0
description: Test kit
artifacts:
  command:
    - commands/test/foo.md
    - commands/test/bar.md
""",
            encoding="utf-8",
        )

        # Create artifacts in bundled location
        bundled_foo = mock_kit_dir / "commands" / "test" / "foo.md"
        bundled_foo.parent.mkdir(parents=True)
        bundled_foo.write_text("foo content", encoding="utf-8")

        bundled_bar = mock_kit_dir / "commands" / "test" / "bar.md"
        bundled_bar.write_text("bar content", encoding="utf-8")

        # Create config with one matching artifact and one obsolete
        # (missing bar.md)
        config = ProjectConfig(
            version="1",
            kits={
                "test-kit": InstalledKit(
                    kit_id="test-kit",
                    version="1.0.0",
                    source_type="bundled",
                    artifacts=[
                        ".claude/commands/test/foo.md",
                        ".claude/commands/test/obsolete.md",
                    ],
                ),
            },
        )
        save_project_config(project_dir, config)

        # Create local artifacts
        local_foo = claude_dir / "commands" / "test" / "foo.md"
        local_foo.parent.mkdir(parents=True)
        local_foo.write_text("foo content", encoding="utf-8")

        local_obsolete = claude_dir / "commands" / "test" / "obsolete.md"
        local_obsolete.write_text("obsolete content", encoding="utf-8")

        # Monkey patch BundledKitSource
        from erk.kits.sources.bundled import BundledKitSource

        original_get_path = BundledKitSource._get_bundled_kit_path

        def mock_get_path(self: BundledKitSource, source: str) -> Path | None:
            if source == "test-kit":
                return mock_kit_dir
            return original_get_path(self, source)

        BundledKitSource._get_bundled_kit_path = mock_get_path

        result = runner.invoke(check)

        # Restore original method
        BundledKitSource._get_bundled_kit_path = original_get_path

        # Should fail with both missing and obsolete
        assert result.exit_code == 1
        assert "Missing artifacts (in manifest but not installed)" in result.output
        assert ".claude/commands/test/bar.md" in result.output
        assert "Obsolete artifacts (installed but not in manifest)" in result.output
        assert ".claude/commands/test/obsolete.md" in result.output
        assert "⚠ Missing: 1" in result.output
        assert "⚠ Obsolete: 1" in result.output
        assert "Some checks failed" in result.output


def test_check_command_perfect_sync_no_missing_no_obsolete(tmp_path: Path) -> None:
    """Test check passes when all artifacts match manifest exactly."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()

        # Create .claude directory
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()

        # Use real bundled kit (gt) and install all artifacts
        config = ProjectConfig(
            version="1",
            kits={
                "gt": InstalledKit(
                    kit_id="gt",
                    version="0.1.0",
                    source_type="bundled",
                    artifacts=[
                        ".claude/commands/gt/pr-submit.md",
                        ".claude/skills/gt-graphite/SKILL.md",
                        ".claude/skills/gt-graphite/references/gt-reference.md",
                    ],
                ),
            },
        )
        save_project_config(project_dir, config)

        # Copy all artifacts from bundled kit
        from erk.kits.sources.bundled import BundledKitSource

        bundled_source = BundledKitSource()
        bundled_path = bundled_source._get_bundled_kit_path("gt")
        if bundled_path is not None:
            for artifact_rel in [
                "commands/gt/pr-submit.md",
                "skills/gt-graphite/SKILL.md",
                "skills/gt-graphite/references/gt-reference.md",
            ]:
                bundled_artifact = bundled_path / artifact_rel
                if bundled_artifact.exists():
                    bundled_content = bundled_artifact.read_text(encoding="utf-8")
                    local_artifact = claude_dir / artifact_rel
                    local_artifact.parent.mkdir(parents=True, exist_ok=True)
                    local_artifact.write_text(bundled_content, encoding="utf-8")

            result = runner.invoke(check)

            # Debug: print output if test fails
            if result.exit_code != 0:
                print(f"\n=== Check command output ===\n{result.output}\n=== End output ===")

            assert result.exit_code == 0
            assert "All checks passed" in result.output
            assert "Missing artifacts" not in result.output
            assert "Obsolete artifacts" not in result.output
