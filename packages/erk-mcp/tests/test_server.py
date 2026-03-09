"""Tests for erk_mcp.server MCP tools and _run_erk wrapper."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from erk_mcp.server import _run_erk, create_mcp, one_shot, plan_list, plan_view, release_notes


class TestRunErk:
    """Tests for _run_erk subprocess wrapper."""

    @patch("erk_mcp.server.subprocess.run")
    def test_success_returns_completed_process(self, mock_run: patch) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["erk", "exec", "dash-data"],
            returncode=0,
            stdout="output",
            stderr="",
        )

        result = _run_erk(["exec", "dash-data"])

        assert result.stdout == "output"
        mock_run.assert_called_once_with(
            ["erk", "exec", "dash-data"],
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("erk_mcp.server.subprocess.run")
    def test_nonzero_exit_raises_runtime_error(self, mock_run: patch) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["erk", "bad-cmd"],
            returncode=1,
            stdout="",
            stderr="command not found",
        )

        with pytest.raises(
            RuntimeError,
            match="erk bad-cmd failed \\(exit 1\\): command not found",
        ):
            _run_erk(["bad-cmd"])

    @patch("erk_mcp.server.subprocess.run")
    def test_error_message_includes_all_args(self, mock_run: patch) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["erk", "exec", "dash-data", "--state", "open"],
            returncode=2,
            stdout="",
            stderr="  some error  ",
        )

        with pytest.raises(
            RuntimeError,
            match=r"erk exec dash-data --state open failed \(exit 2\): some error",
        ):
            _run_erk(["exec", "dash-data", "--state", "open"])


class TestPlanList:
    """Tests for plan_list MCP tool."""

    @patch("erk_mcp.server._run_erk")
    def test_without_state_filter(self, mock_run_erk: patch) -> None:
        mock_run_erk.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout='[{"id": 1}]', stderr=""
        )

        result = plan_list(state=None)

        assert result == '[{"id": 1}]'
        mock_run_erk.assert_called_once_with(["exec", "dash-data"])

    @patch("erk_mcp.server._run_erk")
    def test_with_state_filter(self, mock_run_erk: patch) -> None:
        mock_run_erk.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout='[{"id": 1, "state": "open"}]', stderr=""
        )

        result = plan_list(state="open")

        assert result == '[{"id": 1, "state": "open"}]'
        mock_run_erk.assert_called_once_with(["exec", "dash-data", "--state", "open"])

    @patch("erk_mcp.server._run_erk")
    def test_with_closed_state(self, mock_run_erk: patch) -> None:
        mock_run_erk.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="[]", stderr=""
        )

        result = plan_list(state="closed")

        assert result == "[]"
        mock_run_erk.assert_called_once_with(["exec", "dash-data", "--state", "closed"])


class TestPlanView:
    """Tests for plan_view MCP tool."""

    @patch("erk_mcp.server._run_erk")
    def test_returns_plan_info(self, mock_run_erk: patch) -> None:
        mock_run_erk.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout='{"title": "My Plan", "body": "# Plan"}', stderr=""
        )

        result = plan_view(plan_id=42)

        assert result == '{"title": "My Plan", "body": "# Plan"}'
        mock_run_erk.assert_called_once_with(["exec", "get-plan-info", "42", "--include-body"])

    @patch("erk_mcp.server._run_erk")
    def test_converts_plan_id_to_string(self, mock_run_erk: patch) -> None:
        mock_run_erk.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="{}", stderr=""
        )

        plan_view(plan_id=100)

        args = mock_run_erk.call_args[0][0]
        assert args[2] == "100"
        assert isinstance(args[2], str)


class TestOneShot:
    """Tests for one_shot MCP tool."""

    @patch("erk_mcp.server._run_erk")
    def test_passes_prompt_to_erk(self, mock_run_erk: patch) -> None:
        mock_run_erk.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="PR: https://github.com/...", stderr=""
        )

        result = one_shot(prompt="Fix the bug in auth")

        assert result == "PR: https://github.com/..."
        mock_run_erk.assert_called_once_with(["one-shot", "Fix the bug in auth"])

    @patch("erk_mcp.server._run_erk")
    def test_propagates_runtime_error(self, mock_run_erk: patch) -> None:
        mock_run_erk.side_effect = RuntimeError("erk one-shot failed (exit 1): timeout")

        with pytest.raises(RuntimeError, match="timeout"):
            one_shot(prompt="Do something")


class TestReleaseNotes:
    """Tests for release_notes MCP tool."""

    @patch("erk_mcp.server._run_erk")
    def test_without_version(self, mock_run_erk: patch) -> None:
        mock_run_erk.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="Release notes for erk 0.3.0\n...", stderr=""
        )

        result = release_notes(version=None)

        assert result == "Release notes for erk 0.3.0\n..."
        mock_run_erk.assert_called_once_with(["release-notes"])

    @patch("erk_mcp.server._run_erk")
    def test_with_specific_version(self, mock_run_erk: patch) -> None:
        mock_run_erk.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="[0.2.1] - 2025-12-11\n...", stderr=""
        )

        result = release_notes(version="0.2.1")

        assert result == "[0.2.1] - 2025-12-11\n..."
        mock_run_erk.assert_called_once_with(["release-notes", "--version", "0.2.1"])

    @patch("erk_mcp.server._run_erk")
    def test_with_all_versions(self, mock_run_erk: patch) -> None:
        mock_run_erk.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="# erk Changelog\n...", stderr=""
        )

        result = release_notes(version="all")

        assert result == "# erk Changelog\n..."
        mock_run_erk.assert_called_once_with(["release-notes", "--all"])


class TestCreateMcp:
    """Tests for create_mcp() factory function."""

    def test_returns_fastmcp_instance(self) -> None:
        from fastmcp import FastMCP

        server = create_mcp()

        assert isinstance(server, FastMCP)

    def test_server_has_correct_name(self) -> None:
        from erk_mcp.server import DEFAULT_MCP_NAME

        server = create_mcp()

        assert server.name == DEFAULT_MCP_NAME

    def test_registers_expected_tools(self) -> None:
        import asyncio

        server = create_mcp()
        tools = asyncio.run(server.list_tools())
        tool_names = {t.name for t in tools}

        assert tool_names == {"plan_list", "plan_view", "one_shot", "release_notes"}
