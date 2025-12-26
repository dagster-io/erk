"""Tests for the csadmin check command.

Tests validation of context store YAML files including project configuration,
context files, and cronjob files. Validates both V1 and V2 context store layouts.
"""

from pathlib import Path

import pytest

from csadmin.commands.check import (
    ValidationError_,
    _discover_yaml_files,
    _validate_context_files,
    _validate_cronjob_files,
    _validate_project_file,
    _validate_yaml_file,
)
from csadmin.models import ContextStoreProject, ProvidedContext, UserCronJob


@pytest.fixture
def test_stores_root() -> Path:
    """Path to the test context stores directory."""
    tests_dir = Path(__file__).parent.parent.parent
    return tests_dir / "csbot" / "tests" / "context_store_integration_tests" / "context_stores"


@pytest.fixture
def v1_store(test_stores_root: Path) -> Path:
    """Path to the V1 test context store."""
    return test_stores_root / "dagsterlabs_v0_2025_09_21"


@pytest.fixture
def v2_store(test_stores_root: Path) -> Path:
    """Path to the V2 test context store."""
    return test_stores_root / "dagsterlabs_v2_2025_09_21"


class TestProjectFileValidation:
    """Tests for contextstore_project.yaml validation."""

    def test_validate_v1_project_file(self, v1_store: Path) -> None:
        """V1 project file should validate successfully."""
        error = _validate_project_file(v1_store)
        assert error is None

    def test_validate_v2_project_file(self, v2_store: Path) -> None:
        """V2 project file should validate successfully."""
        error = _validate_project_file(v2_store)
        assert error is None

    def test_validate_missing_project_file(self, tmp_path: Path) -> None:
        """Missing project file should return parse error."""
        error = _validate_project_file(tmp_path)
        assert error is not None
        assert error.error_type == "parse"
        assert "does not exist" in error.message.lower()

    def test_validate_invalid_yaml_syntax(self, tmp_path: Path) -> None:
        """Invalid YAML syntax should return parse error."""
        project_file = tmp_path / "contextstore_project.yaml"
        project_file.write_text("project_name: [invalid: yaml: syntax")

        error = _validate_project_file(tmp_path)
        assert error is not None
        assert error.error_type == "parse"
        assert "yaml" in error.message.lower()

    def test_validate_invalid_schema(self, tmp_path: Path) -> None:
        """Valid YAML with invalid schema should return schema error."""
        project_file = tmp_path / "contextstore_project.yaml"
        project_file.write_text("project_name: invalid_name_without_slash\nteams: {}\n")

        error = _validate_project_file(tmp_path)
        assert error is not None
        assert error.error_type == "schema"


class TestContextFilesValidation:
    """Tests for context/**/*.yaml validation."""

    def test_validate_v1_context_files(self, v1_store: Path) -> None:
        """All V1 context files should validate successfully."""
        errors = _validate_context_files(v1_store)
        assert len(errors) == 0

    def test_validate_v2_context_files(self, v2_store: Path) -> None:
        """All V2 context files should validate successfully."""
        errors = _validate_context_files(v2_store)
        assert len(errors) == 0

    def test_validate_empty_context_directory(self, tmp_path: Path) -> None:
        """Empty context directory should return no errors."""
        (tmp_path / "context").mkdir()
        errors = _validate_context_files(tmp_path)
        assert len(errors) == 0

    def test_validate_missing_context_directory(self, tmp_path: Path) -> None:
        """Missing context directory should return no errors."""
        errors = _validate_context_files(tmp_path)
        assert len(errors) == 0

    def test_validate_invalid_context_file(self, tmp_path: Path) -> None:
        """Invalid context file should return schema error."""
        context_dir = tmp_path / "context" / "test_group"
        context_dir.mkdir(parents=True)
        context_file = context_dir / "test_context.yaml"
        context_file.write_text("topic: Test\n")  # Missing required fields

        errors = _validate_context_files(tmp_path)
        assert len(errors) == 1
        assert errors[0].error_type == "schema"

    def test_validate_context_file_structure(self, v1_store: Path) -> None:
        """Context files should have all required fields."""
        context_files = _discover_yaml_files(v1_store / "context", "**/*.yaml")
        assert len(context_files) > 0

        for file_path in context_files[:3]:  # Sample first 3 files
            error = _validate_yaml_file(file_path, ProvidedContext)
            assert error is None


class TestCronjobFilesValidation:
    """Tests for cronjobs/*.yaml validation."""

    def test_validate_v1_cronjob_files(self, v1_store: Path) -> None:
        """All V1 cronjob files should validate successfully."""
        errors = _validate_cronjob_files(v1_store)
        assert len(errors) == 0

    def test_validate_v2_cronjob_files(self, v2_store: Path) -> None:
        """All V2 cronjob files should validate successfully."""
        errors = _validate_cronjob_files(v2_store)
        assert len(errors) == 0

    def test_validate_empty_cronjobs_directory(self, tmp_path: Path) -> None:
        """Empty cronjobs directory should return no errors."""
        (tmp_path / "cronjobs").mkdir()
        errors = _validate_cronjob_files(tmp_path)
        assert len(errors) == 0

    def test_validate_missing_cronjobs_directory(self, tmp_path: Path) -> None:
        """Missing cronjobs directory should return no errors."""
        errors = _validate_cronjob_files(tmp_path)
        assert len(errors) == 0

    def test_validate_invalid_cronjob_file(self, tmp_path: Path) -> None:
        """Invalid cronjob file should return schema error."""
        cronjobs_dir = tmp_path / "cronjobs"
        cronjobs_dir.mkdir()
        cronjob_file = cronjobs_dir / "test_cron.yaml"
        cronjob_file.write_text("cron: '0 9 * * *'\n")  # Missing question and thread

        errors = _validate_cronjob_files(tmp_path)
        assert len(errors) == 1
        assert errors[0].error_type == "schema"

    def test_validate_cronjob_file_structure(self, v1_store: Path) -> None:
        """Cronjob files should have all required fields."""
        cronjob_files = _discover_yaml_files(v1_store / "cronjobs", "*.yaml")
        assert len(cronjob_files) > 0

        for file_path in cronjob_files[:3]:  # Sample first 3 files
            error = _validate_yaml_file(file_path, UserCronJob)
            assert error is None


class TestYamlFileDiscovery:
    """Tests for YAML file discovery."""

    def test_discover_context_files_v1(self, v1_store: Path) -> None:
        """Should discover all context files in V1 store."""
        files = _discover_yaml_files(v1_store / "context", "**/*.yaml")
        assert len(files) > 0
        # V1 store has files in org_and_people, sales_definitions, uncategorized
        assert any("org_and_people" in str(f) for f in files)

    def test_discover_context_files_v2(self, v2_store: Path) -> None:
        """Should discover all context files in V2 store."""
        files = _discover_yaml_files(v2_store / "context", "**/*.yaml")
        assert len(files) > 0

    def test_discover_cronjob_files(self, v1_store: Path) -> None:
        """Should discover all cronjob files."""
        files = _discover_yaml_files(v1_store / "cronjobs", "*.yaml")
        assert len(files) > 0

    def test_discover_files_in_nonexistent_directory(self, tmp_path: Path) -> None:
        """Should return empty list for nonexistent directory."""
        files = _discover_yaml_files(tmp_path / "nonexistent", "*.yaml")
        assert len(files) == 0

    def test_discover_files_sorted_order(self, v1_store: Path) -> None:
        """Discovered files should be in sorted order by full path."""
        files = _discover_yaml_files(v1_store / "context", "**/*.yaml")
        file_paths = [str(f) for f in files]
        assert file_paths == sorted(file_paths)


class TestValidationErrorDataclass:
    """Tests for ValidationError_ dataclass."""

    def test_validation_error_immutable(self) -> None:
        """ValidationError_ should be immutable."""
        error = ValidationError_(
            file_path=Path("test.yaml"),
            error_type="parse",
            message="Test error",
        )

        with pytest.raises(AttributeError):
            error.file_path = Path("other.yaml")  # type: ignore[misc]

    def test_validation_error_fields(self) -> None:
        """ValidationError_ should have correct fields."""
        error = ValidationError_(
            file_path=Path("test.yaml"),
            error_type="schema",
            message="Schema validation failed",
        )

        assert error.file_path == Path("test.yaml")
        assert error.error_type == "schema"
        assert error.message == "Schema validation failed"


class TestCompleteStoreValidation:
    """Integration tests validating complete context stores."""

    def test_v1_store_completely_valid(self, v1_store: Path) -> None:
        """V1 store should have no validation errors."""
        project_error = _validate_project_file(v1_store)
        context_errors = _validate_context_files(v1_store)
        cronjob_errors = _validate_cronjob_files(v1_store)

        assert project_error is None
        assert len(context_errors) == 0
        assert len(cronjob_errors) == 0

    def test_v2_store_completely_valid(self, v2_store: Path) -> None:
        """V2 store should have no validation errors."""
        project_error = _validate_project_file(v2_store)
        context_errors = _validate_context_files(v2_store)
        cronjob_errors = _validate_cronjob_files(v2_store)

        assert project_error is None
        assert len(context_errors) == 0
        assert len(cronjob_errors) == 0

    def test_v1_store_has_expected_files(self, v1_store: Path) -> None:
        """V1 store should have expected file counts."""
        context_files = _discover_yaml_files(v1_store / "context", "**/*.yaml")
        cronjob_files = _discover_yaml_files(v1_store / "cronjobs", "*.yaml")

        # V1 store should have context files in multiple categories
        assert len(context_files) >= 30  # Based on actual fixture
        assert len(cronjob_files) >= 10  # Based on actual fixture

    def test_v2_store_has_version_field(self, v2_store: Path) -> None:
        """V2 store should have version: 2 in project file."""
        project_file = v2_store / "contextstore_project.yaml"
        assert project_file.exists()

        error = _validate_yaml_file(project_file, ContextStoreProject)
        assert error is None

        # Read and verify version
        import yaml

        with project_file.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data.get("version") == 2


class TestChannelSpecificValidation:
    """Tests for channel-specific context and cronjob validation."""

    def test_validate_channel_context_empty(self, tmp_path: Path) -> None:
        """Empty channels directory should return no errors."""
        (tmp_path / "channels").mkdir()
        errors = _validate_context_files(tmp_path)
        assert len(errors) == 0

    def test_validate_channel_cronjobs_empty(self, tmp_path: Path) -> None:
        """Empty channels directory should return no errors for cronjobs."""
        (tmp_path / "channels").mkdir()
        errors = _validate_cronjob_files(tmp_path)
        assert len(errors) == 0

    def test_validate_channel_context_with_files(self, tmp_path: Path) -> None:
        """Valid channel context files should validate."""
        channel_context_dir = tmp_path / "channels" / "sales" / "context" / "deals"
        channel_context_dir.mkdir(parents=True)

        context_file = channel_context_dir / "pipeline.yaml"
        context_file.write_text(
            "topic: Sales Pipeline\n"
            "incorrect_understanding: We have 3 stages\n"
            "correct_understanding: We have 5 stages\n"
            "search_keywords: sales pipeline stages\n"
        )

        errors = _validate_context_files(tmp_path)
        assert len(errors) == 0

    def test_validate_channel_cronjob_with_files(self, tmp_path: Path) -> None:
        """Valid channel cronjob files should validate."""
        channel_cronjobs_dir = tmp_path / "channels" / "sales" / "cronjobs"
        channel_cronjobs_dir.mkdir(parents=True)

        cronjob_file = channel_cronjobs_dir / "daily_report.yaml"
        cronjob_file.write_text(
            "cron: '0 9 * * *'\nquestion: What were yesterday's sales?\nthread: daily-sales\n"
        )

        errors = _validate_cronjob_files(tmp_path)
        assert len(errors) == 0

    def test_validate_invalid_channel_context(self, tmp_path: Path) -> None:
        """Invalid channel context should return error."""
        channel_context_dir = tmp_path / "channels" / "sales" / "context" / "deals"
        channel_context_dir.mkdir(parents=True)

        context_file = channel_context_dir / "invalid.yaml"
        context_file.write_text("topic: Incomplete\n")  # Missing required fields

        errors = _validate_context_files(tmp_path)
        assert len(errors) == 1
        assert errors[0].error_type == "schema"

    def test_validate_invalid_channel_cronjob(self, tmp_path: Path) -> None:
        """Invalid channel cronjob should return error."""
        channel_cronjobs_dir = tmp_path / "channels" / "sales" / "cronjobs"
        channel_cronjobs_dir.mkdir(parents=True)

        cronjob_file = channel_cronjobs_dir / "invalid.yaml"
        cronjob_file.write_text("cron: '0 9 * * *'\n")  # Missing question and thread

        errors = _validate_cronjob_files(tmp_path)
        assert len(errors) == 1
        assert errors[0].error_type == "schema"
