"""Tests for MCPWrapper (Layer 4: Business Logic Tests over Fakes)."""

import pytest

from dot_agent_kit.nomcp.wrapper import (
    MCPServerNotConnectedError,
    MCPToolNotFoundError,
    MCPWrapper,
)
from tests.unit.nomcp.fake_mcp_client import FakeMCPClient, create_fake_tool


class TestMCPWrapperInit:
    """Tests for MCPWrapper initialization."""

    def test_requires_command_or_url(self) -> None:
        """Must provide either command or url."""
        with pytest.raises(ValueError, match="Either command or url must be provided"):
            MCPWrapper()

    def test_cannot_provide_both_command_and_url(self) -> None:
        """Cannot provide both command and url."""
        with pytest.raises(ValueError, match="Cannot provide both command and url"):
            MCPWrapper(command=["test"], url="http://example.com")

    def test_can_create_with_command(self) -> None:
        """Can create wrapper with command."""
        wrapper = MCPWrapper(command=["uvx", "mcp-server-test"])
        assert wrapper._command == ["uvx", "mcp-server-test"]
        assert wrapper._url is None

    def test_can_create_with_url(self) -> None:
        """Can create wrapper with URL."""
        wrapper = MCPWrapper(url="http://localhost:8080/mcp")
        assert wrapper._url == "http://localhost:8080/mcp"
        assert wrapper._command is None

    def test_can_provide_env(self) -> None:
        """Can provide environment variables."""
        wrapper = MCPWrapper(
            command=["test"],
            env={"API_KEY": "secret"},
        )
        assert wrapper._env == {"API_KEY": "secret"}

    def test_can_provide_cwd(self) -> None:
        """Can provide working directory."""
        wrapper = MCPWrapper(
            command=["test"],
            cwd="/tmp/test",
        )
        assert wrapper._cwd is not None
        assert str(wrapper._cwd) == "/tmp/test"


class TestMCPWrapperConnection:
    """Tests for MCPWrapper connection lifecycle."""

    @pytest.mark.asyncio
    async def test_not_connected_initially(self) -> None:
        """Wrapper is not connected initially."""
        fake_client = FakeMCPClient()
        wrapper = MCPWrapper(_client=fake_client)
        assert wrapper.is_connected is False

    @pytest.mark.asyncio
    async def test_connect_enters_client_context(self) -> None:
        """Connecting enters the client async context."""
        fake_client = FakeMCPClient()
        wrapper = MCPWrapper(_client=fake_client)

        await wrapper.connect()
        assert wrapper.is_connected is True
        assert fake_client.is_connected is True

    @pytest.mark.asyncio
    async def test_disconnect_exits_client_context(self) -> None:
        """Disconnecting exits the client async context."""
        fake_client = FakeMCPClient()
        wrapper = MCPWrapper(_client=fake_client)

        await wrapper.connect()
        await wrapper.disconnect()

        assert wrapper.is_connected is False
        assert fake_client.is_connected is False

    @pytest.mark.asyncio
    async def test_context_manager_connects_and_disconnects(self) -> None:
        """Async context manager connects on enter and disconnects on exit."""
        fake_client = FakeMCPClient()
        wrapper = MCPWrapper(_client=fake_client)

        async with wrapper as w:
            assert w.is_connected is True
            assert fake_client.is_connected is True

        assert wrapper.is_connected is False
        assert fake_client.is_connected is False

    @pytest.mark.asyncio
    async def test_connect_is_idempotent(self) -> None:
        """Multiple connect calls don't cause issues."""
        fake_client = FakeMCPClient()
        wrapper = MCPWrapper(_client=fake_client)

        await wrapper.connect()
        await wrapper.connect()  # Should be no-op

        assert wrapper.is_connected is True

    @pytest.mark.asyncio
    async def test_disconnect_is_idempotent(self) -> None:
        """Multiple disconnect calls don't cause issues."""
        fake_client = FakeMCPClient()
        wrapper = MCPWrapper(_client=fake_client)

        await wrapper.connect()
        await wrapper.disconnect()
        await wrapper.disconnect()  # Should be no-op

        assert wrapper.is_connected is False


class TestMCPWrapperListTools:
    """Tests for MCPWrapper.list_tools()."""

    @pytest.mark.asyncio
    async def test_list_tools_requires_connection(self) -> None:
        """list_tools raises error if not connected."""
        fake_client = FakeMCPClient()
        wrapper = MCPWrapper(_client=fake_client)

        with pytest.raises(MCPServerNotConnectedError, match="Must connect"):
            await wrapper.list_tools()

    @pytest.mark.asyncio
    async def test_list_tools_returns_empty_list(self) -> None:
        """list_tools returns empty list when server has no tools."""
        fake_client = FakeMCPClient(tools=[])
        wrapper = MCPWrapper(_client=fake_client)

        async with wrapper:
            tools = await wrapper.list_tools()

        assert tools == []

    @pytest.mark.asyncio
    async def test_list_tools_returns_tool_info(self) -> None:
        """list_tools returns tool information."""
        fake_tool = create_fake_tool(
            name="search",
            description="Search for items",
            parameters={
                "query": {"type": "string", "description": "Search query"},
            },
            required=["query"],
        )
        fake_client = FakeMCPClient(tools=[fake_tool])
        wrapper = MCPWrapper(_client=fake_client)

        async with wrapper:
            tools = await wrapper.list_tools()

        assert len(tools) == 1
        tool = tools[0]
        assert tool.name == "search"
        assert tool.description == "Search for items"
        assert len(tool.parameters) == 1
        assert tool.parameters[0].name == "query"
        assert tool.parameters[0].type == "string"
        assert tool.parameters[0].required is True

    @pytest.mark.asyncio
    async def test_list_tools_handles_optional_parameters(self) -> None:
        """list_tools correctly marks optional parameters."""
        fake_tool = create_fake_tool(
            name="search",
            description="Search",
            parameters={
                "query": {"type": "string", "description": "Query"},
                "limit": {"type": "integer", "description": "Max results"},
            },
            required=["query"],  # limit is optional
        )
        fake_client = FakeMCPClient(tools=[fake_tool])
        wrapper = MCPWrapper(_client=fake_client)

        async with wrapper:
            tools = await wrapper.list_tools()

        params_by_name = {p.name: p for p in tools[0].parameters}
        assert params_by_name["query"].required is True
        assert params_by_name["limit"].required is False

    @pytest.mark.asyncio
    async def test_list_tools_caches_result(self) -> None:
        """list_tools caches the result."""
        fake_tool = create_fake_tool(name="test", description="Test")
        fake_client = FakeMCPClient(tools=[fake_tool])
        wrapper = MCPWrapper(_client=fake_client)

        async with wrapper:
            tools1 = await wrapper.list_tools()
            tools2 = await wrapper.list_tools()

        # Should be the same cached list
        assert tools1 is tools2


class TestMCPWrapperCallTool:
    """Tests for MCPWrapper.call()."""

    @pytest.mark.asyncio
    async def test_call_requires_connection(self) -> None:
        """call raises error if not connected."""
        fake_client = FakeMCPClient()
        wrapper = MCPWrapper(_client=fake_client)

        with pytest.raises(MCPServerNotConnectedError, match="Must connect"):
            await wrapper.call("test")

    @pytest.mark.asyncio
    async def test_call_raises_for_unknown_tool(self) -> None:
        """call raises MCPToolNotFoundError for unknown tool."""
        fake_tool = create_fake_tool(name="known_tool", description="Known")
        fake_client = FakeMCPClient(tools=[fake_tool])
        wrapper = MCPWrapper(_client=fake_client)

        async with wrapper:
            with pytest.raises(MCPToolNotFoundError, match="unknown_tool"):
                await wrapper.call("unknown_tool")

    @pytest.mark.asyncio
    async def test_call_returns_result(self) -> None:
        """call returns successful result from tool."""
        fake_tool = create_fake_tool(name="search", description="Search")
        expected_result = {"repos": [{"name": "test-repo"}]}
        fake_client = FakeMCPClient(
            tools=[fake_tool],
            call_results={"search": expected_result},
        )
        wrapper = MCPWrapper(_client=fake_client)

        async with wrapper:
            result = await wrapper.call("search", query="test")

        assert result.is_error is False
        assert result.data == expected_result

    @pytest.mark.asyncio
    async def test_call_passes_arguments(self) -> None:
        """call passes arguments to the tool."""
        fake_tool = create_fake_tool(name="search", description="Search")
        fake_client = FakeMCPClient(tools=[fake_tool])
        wrapper = MCPWrapper(_client=fake_client)

        async with wrapper:
            await wrapper.call("search", query="test", limit=10)

        assert len(fake_client.call_history) == 1
        tool_name, args = fake_client.call_history[0]
        assert tool_name == "search"
        assert args == {"query": "test", "limit": 10}

    @pytest.mark.asyncio
    async def test_call_handles_tool_error(self) -> None:
        """call returns error result when tool fails."""
        fake_tool = create_fake_tool(name="failing_tool", description="Fails")
        fake_client = FakeMCPClient(
            tools=[fake_tool],
            call_errors={"failing_tool": RuntimeError("Tool failed")},
        )
        wrapper = MCPWrapper(_client=fake_client)

        async with wrapper:
            result = await wrapper.call("failing_tool")

        assert result.is_error is True
        assert result.error_message == "Tool failed"
        assert result.data is None


class TestMCPWrapperFromKit:
    """Tests for MCPWrapper.from_kit() class method."""

    def test_from_kit_raises_if_nomcp_yaml_not_found(self, tmp_path: object) -> None:
        """from_kit raises FileNotFoundError if nomcp.yaml doesn't exist."""
        from pathlib import Path

        kit_dir = Path(str(tmp_path))

        with pytest.raises(FileNotFoundError, match="nomcp.yaml not found"):
            MCPWrapper.from_kit(kit_dir)

    def test_from_kit_parses_command_list(self, tmp_path: object) -> None:
        """from_kit correctly parses command as list."""
        from pathlib import Path

        kit_dir = Path(str(tmp_path))
        nomcp_yaml = kit_dir / "nomcp.yaml"
        nomcp_yaml.write_text(
            """
command:
  - uvx
  - mcp-server-github
""",
            encoding="utf-8",
        )

        wrapper = MCPWrapper.from_kit(kit_dir)
        assert wrapper._command == ["uvx", "mcp-server-github"]

    def test_from_kit_parses_command_string(self, tmp_path: object) -> None:
        """from_kit correctly parses command as string (splitting into list)."""
        from pathlib import Path

        kit_dir = Path(str(tmp_path))
        nomcp_yaml = kit_dir / "nomcp.yaml"
        nomcp_yaml.write_text(
            """
command: uvx mcp-server-github --verbose
""",
            encoding="utf-8",
        )

        wrapper = MCPWrapper.from_kit(kit_dir)
        assert wrapper._command == ["uvx", "mcp-server-github", "--verbose"]

    def test_from_kit_parses_url(self, tmp_path: object) -> None:
        """from_kit correctly parses URL configuration."""
        from pathlib import Path

        kit_dir = Path(str(tmp_path))
        nomcp_yaml = kit_dir / "nomcp.yaml"
        nomcp_yaml.write_text(
            """
url: http://localhost:8080/mcp
""",
            encoding="utf-8",
        )

        wrapper = MCPWrapper.from_kit(kit_dir)
        assert wrapper._url == "http://localhost:8080/mcp"

    def test_from_kit_parses_env(self, tmp_path: object) -> None:
        """from_kit correctly parses environment variables."""
        from pathlib import Path

        kit_dir = Path(str(tmp_path))
        nomcp_yaml = kit_dir / "nomcp.yaml"
        nomcp_yaml.write_text(
            """
command:
  - test
env:
  API_KEY: secret
  LOG_LEVEL: DEBUG
""",
            encoding="utf-8",
        )

        wrapper = MCPWrapper.from_kit(kit_dir)
        assert wrapper._env == {"API_KEY": "secret", "LOG_LEVEL": "DEBUG"}
