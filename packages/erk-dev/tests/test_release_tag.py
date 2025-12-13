"""Tests for release-tag command using FakeGit."""

from pathlib import Path

from click.testing import CliRunner

from erk_dev.cli import cli
from erk_dev.context import ErkDevContext
from erk_shared.git.fake import FakeGit


class TestReleaseTagCommand:
    """Tests for release_tag_command CLI using FakeGit."""

    def test_creates_tag_for_current_version(self, tmp_path: Path) -> None:
        """Test creating a tag when none exists."""
        # Set up pyproject.toml with workspace marker and version
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[tool.uv.workspace]\nmembers = []\nversion = "1.2.3"\n', encoding="utf-8"
        )

        # Create FakeGit with no existing tags
        fake_git = FakeGit()

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli,
                ["release-tag"],
                obj=ErkDevContext(git=fake_git),
            )
            assert result.exit_code == 0
            assert "Created tag: v1.2.3" in result.output

            # Verify tag was created via FakeGit mutation tracking
            assert ("v1.2.3", "Release 1.2.3") in fake_git.created_tags

    def test_skips_when_tag_exists(self, tmp_path: Path) -> None:
        """Test skipping when tag already exists."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[tool.uv.workspace]\nmembers = []\nversion = "1.2.3"\n', encoding="utf-8"
        )

        # Create FakeGit with existing tag
        fake_git = FakeGit(existing_tags={"v1.2.3"})

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli,
                ["release-tag"],
                obj=ErkDevContext(git=fake_git),
            )
            assert result.exit_code == 0
            assert "Tag v1.2.3 already exists" in result.output

            # Verify no tag was created
            assert fake_git.created_tags == []

    def test_dry_run_does_not_create_tag(self, tmp_path: Path) -> None:
        """Test dry-run mode shows what would happen without doing it."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[tool.uv.workspace]\nmembers = []\nversion = "1.2.3"\n', encoding="utf-8"
        )

        # FakeGit for dry-run - will be wrapped in DryRunGit by command
        fake_git = FakeGit()

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli,
                ["release-tag", "--dry-run"],
                obj=ErkDevContext(git=fake_git),
            )
            assert result.exit_code == 0
            assert "[DRY RUN] Would run: git tag -a v1.2.3" in result.output

    def test_dry_run_with_push_shows_both_messages(self, tmp_path: Path) -> None:
        """Test dry-run mode with --push shows both dry-run messages."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[tool.uv.workspace]\nmembers = []\nversion = "1.2.3"\n', encoding="utf-8"
        )

        fake_git = FakeGit()

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli,
                ["release-tag", "--dry-run", "--push"],
                obj=ErkDevContext(git=fake_git),
            )
            assert result.exit_code == 0
            assert "[DRY RUN] Would run: git tag -a v1.2.3" in result.output
            assert "[DRY RUN] Would run: git push origin v1.2.3" in result.output

    def test_push_flag_pushes_tag(self, tmp_path: Path) -> None:
        """Test --push flag triggers tag push."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[tool.uv.workspace]\nmembers = []\nversion = "1.2.3"\n', encoding="utf-8"
        )

        fake_git = FakeGit()

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli,
                ["release-tag", "--push"],
                obj=ErkDevContext(git=fake_git),
            )
            assert result.exit_code == 0
            assert "Created tag: v1.2.3" in result.output
            assert "Pushed tag to origin" in result.output

            # Verify tag was created and pushed
            assert ("v1.2.3", "Release 1.2.3") in fake_git.created_tags
            assert ("origin", "v1.2.3") in fake_git.pushed_tags

    def test_fails_when_no_repo_root(self, tmp_path: Path) -> None:
        """Test error when no repository root found."""
        # No pyproject.toml with workspace marker
        fake_git = FakeGit()

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli,
                ["release-tag"],
                obj=ErkDevContext(git=fake_git),
            )
            assert result.exit_code != 0
            assert "Could not find repository root" in result.output

    def test_fails_when_no_version(self, tmp_path: Path) -> None:
        """Test error when no version in pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            "[tool.uv.workspace]\nmembers = []\n",
            encoding="utf-8",  # No version
        )

        fake_git = FakeGit()

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli,
                ["release-tag"],
                obj=ErkDevContext(git=fake_git),
            )
            assert result.exit_code != 0
            assert "Could not determine current version" in result.output
