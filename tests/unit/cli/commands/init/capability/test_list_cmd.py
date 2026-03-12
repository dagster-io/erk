"""Tests for erk init capability list command."""

import re

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.context.types import GlobalConfig
from tests.fakes.gateway.erk_installation import FakeErkInstallation
from tests.fakes.gateway.git import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_capability_list_shows_available_capabilities() -> None:
    """Test that list command shows all registered capabilities."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "capability", "list"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Check main header
        assert "Erk capabilities:" in result.output
        # Check a project capability with scope label
        assert "learned-docs" in result.output
        assert "[project]" in result.output
        assert "Autolearning documentation system" in result.output
        # Check a user capability with scope label
        assert "statusline" in result.output
        assert "[user]" in result.output


def test_capability_list_works_without_repo() -> None:
    """Test that list command works outside a git repository."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        # FakeGit returns None for git_common_dir when not in a repo
        git_ops = FakeGit(git_common_dirs={})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "capability", "list"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "learned-docs" in result.output


def test_capability_list_shows_group_headers() -> None:
    """Test that list command shows group headers in alphabetical order."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "capability", "list"], obj=test_ctx)

        assert result.exit_code == 0, result.output

        # Collect group headers from output (lines like "  [Code Reviews]")
        header_pattern = re.compile(r"^\s+\[([^\]]+)\]$", re.MULTILINE)
        headers = [m.group(1) for m in header_pattern.finditer(result.output)]

        # Must have at least some group headers
        assert len(headers) > 0, "No group headers found in output"

        # Known tags should appear as display names
        assert "Code Reviews" in headers
        assert "Documentation" in headers

        # "Other" must appear last
        assert headers[-1] == "Other", f"Expected 'Other' last, got: {headers}"

        # All headers except "Other" should be in alphabetical order
        tagged_headers = [h for h in headers if h != "Other"]
        assert tagged_headers == sorted(tagged_headers), (
            f"Group headers not in alphabetical order: {tagged_headers}"
        )


def test_capability_list_sorts_alphabetically_within_groups() -> None:
    """Test that capabilities are sorted alphabetically within each group."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "capability", "list"], obj=test_ctx)

        assert result.exit_code == 0, result.output

        # Split output into groups by header lines
        header_pattern = re.compile(r"^\s+\[([^\]]+)\]$", re.MULTILINE)
        capability_pattern = re.compile(r"^\s+[✓○?]\s+(\S+)\s+\[\w+\]", re.MULTILINE)

        # Find positions of all headers and capability lines
        header_positions = [(m.start(), m.group(1)) for m in header_pattern.finditer(result.output)]
        cap_positions = [
            (m.start(), m.group(1)) for m in capability_pattern.finditer(result.output)
        ]

        # Build groups: assign each capability to the nearest preceding header
        groups: dict[str, list[str]] = {}
        for cap_pos, cap_name in cap_positions:
            # Find the last header that appears before this capability
            group_name = "Other"
            for header_pos, header_name in header_positions:
                if header_pos < cap_pos:
                    group_name = header_name
            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append(cap_name)

        # Verify each group is sorted alphabetically
        for group_name, cap_names in groups.items():
            assert cap_names == sorted(cap_names), (
                f"Group '{group_name}' capabilities not sorted: {cap_names}"
            )

        # Verify we found groups with multiple capabilities
        assert any(len(names) > 1 for names in groups.values()), (
            "Expected at least one group with multiple capabilities"
        )
