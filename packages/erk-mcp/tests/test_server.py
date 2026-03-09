"""Tests for erk_mcp.server MCP tools and _run_erk wrapper."""

from __future__ import annotations

import asyncio
import subprocess
from unittest.mock import patch

import pytest

from erk_mcp.server import (
    JsonCommandTool,
    _build_json_command_tools,
    _run_erk,
    _run_erk_json,
    create_mcp,
    plan_list,
    plan_view,
    release_notes,
)


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


class TestReleaseNotes:
    """Tests for release_notes MCP tool."""

    @patch("erk_mcp.server._run_erk")
    def test_without_version(self, mock_run_erk: patch) -> None:
        stdout = "[0.2.1] - 2025-01-15\n  Added:\n    • New feature"
        mock_run_erk.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=stdout, stderr=""
        )

        result = release_notes(version=None)

        assert result == stdout
        mock_run_erk.assert_called_once_with(["release-notes"])

    @patch("erk_mcp.server._run_erk")
    def test_with_specific_version(self, mock_run_erk: patch) -> None:
        mock_run_erk.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="[0.2.0] notes", stderr=""
        )

        result = release_notes(version="0.2.0")

        assert result == "[0.2.0] notes"
        mock_run_erk.assert_called_once_with(["release-notes", "--version", "0.2.0"])

    @patch("erk_mcp.server._run_erk")
    def test_with_all_versions(self, mock_run_erk: patch) -> None:
        mock_run_erk.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="Full changelog", stderr=""
        )

        result = release_notes(version="all")

        assert result == "Full changelog"
        mock_run_erk.assert_called_once_with(["release-notes", "--all"])


class TestRunErkJson:
    """Tests for _run_erk_json subprocess wrapper."""

    @patch("erk_mcp.server.subprocess.run")
    def test_pipes_json_stdin_with_json_flag(self, mock_run: patch) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["erk", "one-shot", "--json"],
            returncode=0,
            stdout='{"success": true}',
            stderr="",
        )

        result = _run_erk_json("one-shot", {"prompt": "Fix bug"})

        assert result == '{"success": true}'
        mock_run.assert_called_once_with(
            ["erk", "one-shot", "--json"],
            input='{"prompt": "Fix bug"}',
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("erk_mcp.server.subprocess.run")
    def test_returns_stdout_on_nonzero_exit(self, mock_run: patch) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["erk", "one-shot", "--json"],
            returncode=1,
            stdout='{"success": false, "error_type": "auth_required"}',
            stderr="",
        )

        result = _run_erk_json("one-shot", {"prompt": "Do something"})

        assert result == '{"success": false, "error_type": "auth_required"}'


class TestJsonCommandTool:
    """Tests for JsonCommandTool dynamic MCP tool."""

    @patch("erk_mcp.server.subprocess.run")
    def test_filters_none_values(self, mock_run: patch) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout='{"success": true}', stderr=""
        )
        tool = JsonCommandTool(
            name="test_tool",
            cli_command="test-cmd",
            description="Test",
            parameters={"type": "object", "properties": {"a": {"type": "string"}}},
        )

        asyncio.run(tool.run({"prompt": "hello", "model": None}))

        call_args = mock_run.call_args
        assert call_args[1]["input"] == '{"prompt": "hello"}'

    @patch("erk_mcp.server.subprocess.run")
    def test_keeps_false_booleans(self, mock_run: patch) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout='{"success": true}', stderr=""
        )
        tool = JsonCommandTool(
            name="test_tool",
            cli_command="test-cmd",
            description="Test",
            parameters={"type": "object", "properties": {"a": {"type": "string"}}},
        )

        asyncio.run(tool.run({"prompt": "hello", "dry_run": False}))

        call_args = mock_run.call_args
        assert call_args[1]["input"] == '{"prompt": "hello", "dry_run": false}'

    @patch("erk_mcp.server.subprocess.run")
    def test_passes_through_truthy_values(self, mock_run: patch) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout='{"success": true}', stderr=""
        )
        tool = JsonCommandTool(
            name="test_tool",
            cli_command="test-cmd",
            description="Test",
            parameters={"type": "object", "properties": {"a": {"type": "string"}}},
        )

        asyncio.run(tool.run({"prompt": "hello", "model": "opus", "dry_run": True}))

        call_args = mock_run.call_args
        assert call_args[1]["input"] == '{"prompt": "hello", "model": "opus", "dry_run": true}'

    @patch("erk_mcp.server.subprocess.run")
    def test_uses_correct_cli_command(self, mock_run: patch) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout='{"success": true}', stderr=""
        )
        tool = JsonCommandTool(
            name="my_tool",
            cli_command="my-command",
            description="Test",
            parameters={"type": "object", "properties": {"x": {"type": "string"}}},
        )

        asyncio.run(tool.run({"x": "val"}))

        mock_run.assert_called_once_with(
            ["erk", "my-command", "--json"],
            input='{"x": "val"}',
            capture_output=True,
            text=True,
            check=False,
        )

    def test_discovered_tools_include_one_shot(self) -> None:
        tools = _build_json_command_tools()
        tool_names = {t.name for t in tools}
        assert "one_shot" in tool_names

    def test_one_shot_tool_has_correct_cli_command(self) -> None:
        tools = _build_json_command_tools()
        one_shot_tool = [t for t in tools if t.name == "one_shot"][0]
        assert one_shot_tool.cli_command == "one-shot"


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
        server = create_mcp()
        tools = asyncio.run(server.list_tools())
        tool_names = {t.name for t in tools}

        assert tool_names == {"plan_list", "plan_view", "release_notes", "one_shot"}
