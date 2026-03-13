"""Tests for erk_mcp.server MCP tools and _run_erk_json wrapper."""

from __future__ import annotations

import asyncio
import json
import subprocess
from unittest.mock import MagicMock, patch

from erk_mcp.server import (
    ROOT_PROTECTED_RESOURCE_METADATA_PATH,
    MachineCommandTool,
    _build_machine_command_tools,
    _build_root_protected_resource_metadata,
    _run_erk_json,
    create_mcp,
)


class TestRunErkJson:
    """Tests for _run_erk_json subprocess wrapper with command path tuples."""

    @patch("erk_mcp.server.subprocess.run")
    def test_pipes_json_stdin(self, mock_run: patch) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["erk", "one-shot"],
            returncode=0,
            stdout='{"success": true}',
            stderr="",
        )

        result = _run_erk_json(("one-shot",), {"prompt": "Fix bug"})

        assert result == '{"success": true}'
        mock_run.assert_called_once_with(
            ["erk", "one-shot"],
            input='{"prompt": "Fix bug"}',
            capture_output=True,
            text=True,
            check=False,
            env=None,
        )

    @patch("erk_mcp.server.subprocess.run")
    def test_returns_stdout_on_nonzero_exit(self, mock_run: patch) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["erk", "one-shot"],
            returncode=1,
            stdout='{"success": false, "error_type": "auth_required"}',
            stderr="",
        )

        result = _run_erk_json(("one-shot",), {"prompt": "Do something"})

        assert result == '{"success": false, "error_type": "auth_required"}'

    @patch("erk_mcp.server.subprocess.run")
    def test_synthesizes_json_error_from_stderr_only_failure(self, mock_run: patch) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["erk", "json", "one-shot"],
            returncode=1,
            stdout="",
            stderr=(
                "Failed during: Creating draft PR\n"
                "HTTP 422 for repos/dagster-io/internal/issues/123/labels: Validation Failed\n"
            ),
        )

        result = _run_erk_json(("json", "one-shot"), {"prompt": "Do something"})

        assert json.loads(result) == {
            "success": False,
            "error_type": "cli_subprocess_error",
            "message": (
                "HTTP 422 for repos/dagster-io/internal/issues/123/labels: Validation Failed"
            ),
        }

    @patch("erk_mcp.server.subprocess.run")
    def test_subcommand_path_expands_correctly(self, mock_run: patch) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["erk", "pr", "list"],
            returncode=0,
            stdout='{"success": true, "plans": []}',
            stderr="",
        )

        result = _run_erk_json(("pr", "list"), {"state": "open"})

        assert result == '{"success": true, "plans": []}'
        mock_run.assert_called_once_with(
            ["erk", "pr", "list"],
            input='{"state": "open"}',
            capture_output=True,
            text=True,
            check=False,
            env=None,
        )

    @patch("erk_mcp.server.subprocess.run")
    def test_env_override_passed_to_subprocess(self, mock_run: patch) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["erk", "one-shot"],
            returncode=0,
            stdout='{"success": true}',
            stderr="",
        )
        env = {"GH_TOKEN": "user-token-abc", "PATH": "/usr/bin"}

        _run_erk_json(("one-shot",), {"prompt": "Fix bug"}, env_override=env)

        mock_run.assert_called_once_with(
            ["erk", "one-shot"],
            input='{"prompt": "Fix bug"}',
            capture_output=True,
            text=True,
            check=False,
            env={"GH_TOKEN": "user-token-abc", "PATH": "/usr/bin"},
        )


class TestMachineCommandTool:
    """Tests for MachineCommandTool dynamic MCP tool."""

    @patch("erk_mcp.server.subprocess.run")
    def test_filters_none_values(self, mock_run: patch) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout='{"success": true}', stderr=""
        )
        tool = MachineCommandTool(
            name="test_tool",
            cli_command_path=("test-cmd",),
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
        tool = MachineCommandTool(
            name="test_tool",
            cli_command_path=("test-cmd",),
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
        tool = MachineCommandTool(
            name="test_tool",
            cli_command_path=("test-cmd",),
            description="Test",
            parameters={"type": "object", "properties": {"a": {"type": "string"}}},
        )

        asyncio.run(tool.run({"prompt": "hello", "model": "opus", "dry_run": True}))

        call_args = mock_run.call_args
        assert call_args[1]["input"] == '{"prompt": "hello", "model": "opus", "dry_run": true}'

    @patch("erk_mcp.server.subprocess.run")
    def test_uses_correct_cli_command_path(self, mock_run: patch) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout='{"success": true}', stderr=""
        )
        tool = MachineCommandTool(
            name="my_tool",
            cli_command_path=("my-command",),
            description="Test",
            parameters={"type": "object", "properties": {"x": {"type": "string"}}},
        )

        asyncio.run(tool.run({"x": "val"}))

        mock_run.assert_called_once_with(
            ["erk", "my-command"],
            input='{"x": "val"}',
            capture_output=True,
            text=True,
            check=False,
            env=None,
        )

    @patch("erk_mcp.server.subprocess.run")
    def test_subcommand_path_in_tool(self, mock_run: patch) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout='{"success": true}', stderr=""
        )
        tool = MachineCommandTool(
            name="pr_list",
            cli_command_path=("pr", "list"),
            description="List plans",
            parameters={"type": "object", "properties": {}},
        )

        asyncio.run(tool.run({"state": "open"}))

        mock_run.assert_called_once_with(
            ["erk", "pr", "list"],
            input='{"state": "open"}',
            capture_output=True,
            text=True,
            check=False,
            env=None,
        )

    @patch("erk_mcp.server.subprocess.run")
    def test_injects_authenticated_github_token(self, mock_run: patch) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout='{"success": true}', stderr=""
        )
        tool = MachineCommandTool(
            name="test_tool",
            cli_command_path=("test-cmd",),
            description="Test",
            parameters={"type": "object", "properties": {}},
        )

        with patch("erk_mcp.server.os.environ", {"PATH": "/usr/bin"}):
            with patch(
                "erk_mcp.server.get_authenticated_github_token",
                return_value="oauth-upstream-gh-token",
            ):
                asyncio.run(tool.run({"prompt": "hello"}))

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["env"] == {
            "PATH": "/usr/bin",
            "GH_TOKEN": "oauth-upstream-gh-token",
        }

    @patch("erk_mcp.server.subprocess.run")
    def test_no_env_override_when_no_context_var(self, mock_run: patch) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout='{"success": true}', stderr=""
        )
        tool = MachineCommandTool(
            name="test_tool",
            cli_command_path=("test-cmd",),
            description="Test",
            parameters={"type": "object", "properties": {}},
        )

        asyncio.run(tool.run({"prompt": "hello"}))

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["env"] is None

    def test_create_mcp_uses_auth_provider_from_env(self) -> None:
        mock_auth_provider = MagicMock()
        mock_auth_provider.base_url = "https://erk.example.com"
        mock_auth_provider.issuer_url = "https://erk.example.com"
        mock_auth_provider.required_scopes = ["repo"]

        with patch(
            "erk_mcp.server.build_auth_provider_from_env",
            return_value=mock_auth_provider,
        ):
            server = create_mcp()

        assert server.auth is mock_auth_provider
        route_paths = [route.path for route in server._get_additional_http_routes()]
        assert ROOT_PROTECTED_RESOURCE_METADATA_PATH in route_paths

    def test_create_mcp_skips_oauth_compat_routes_without_auth_provider(self) -> None:
        with patch(
            "erk_mcp.server.build_auth_provider_from_env",
            return_value=None,
        ):
            server = create_mcp()

        assert server._get_additional_http_routes() == []

    def test_discovered_tools_include_one_shot(self) -> None:
        tools = _build_machine_command_tools()
        tool_names = {t.name for t in tools}
        assert "one_shot" in tool_names

    def test_one_shot_tool_has_correct_command_path(self) -> None:
        tools = _build_machine_command_tools()
        one_shot_tool = [t for t in tools if t.name == "one_shot"][0]
        assert one_shot_tool.cli_command_path == ("json", "one-shot")

    def test_discovered_tools_include_pr_list(self) -> None:
        tools = _build_machine_command_tools()
        tool_names = {t.name for t in tools}
        assert "pr_list" in tool_names

    def test_pr_list_tool_has_subcommand_path(self) -> None:
        tools = _build_machine_command_tools()
        pr_list_tool = [t for t in tools if t.name == "pr_list"][0]
        assert pr_list_tool.cli_command_path == ("json", "pr", "list")

    def test_discovered_tools_include_pr_view(self) -> None:
        tools = _build_machine_command_tools()
        tool_names = {t.name for t in tools}
        assert "pr_view" in tool_names

    def test_pr_view_tool_has_subcommand_path(self) -> None:
        tools = _build_machine_command_tools()
        pr_view_tool = [t for t in tools if t.name == "pr_view"][0]
        assert pr_view_tool.cli_command_path == ("json", "pr", "view")


class TestCreateMcp:
    """Tests for create_mcp() factory function."""

    def test_returns_fastmcp_instance(self) -> None:
        from fastmcp import FastMCP

        server = create_mcp()

        assert isinstance(server, FastMCP)


class TestRootProtectedResourceMetadata:
    def test_returns_none_without_auth(self) -> None:
        assert _build_root_protected_resource_metadata(None) is None

    def test_builds_metadata_for_root_alias(self) -> None:
        auth = MagicMock()
        auth.base_url = "https://erk.example.com"
        auth.issuer_url = "https://issuer.example.com"
        auth.required_scopes = ["repo"]

        metadata = _build_root_protected_resource_metadata(auth)

        assert metadata is not None
        assert str(metadata.resource) == "https://erk.example.com/mcp"
        assert [str(url) for url in metadata.authorization_servers] == [
            "https://issuer.example.com/"
        ]
        assert metadata.scopes_supported == ["repo"]

    def test_server_has_correct_name(self) -> None:
        from erk_mcp.server import DEFAULT_MCP_NAME

        server = create_mcp()

        assert server.name == DEFAULT_MCP_NAME

    def test_registers_expected_tools(self) -> None:
        server = create_mcp()
        tools = asyncio.run(server.list_tools())
        tool_names = {t.name for t in tools}

        assert tool_names == {"pr_list", "pr_view", "one_shot"}
