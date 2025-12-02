"""Tests for nomcp data models (Layer 3: Pure Unit Tests)."""

from dot_agent_kit.nomcp.models import MCPTool, MCPToolParameter, MCPToolResult


class TestMCPToolParameter:
    """Tests for MCPToolParameter dataclass."""

    def test_create_required_parameter(self) -> None:
        """Can create a required parameter."""
        param = MCPToolParameter(
            name="query",
            description="Search query string",
            type="string",
            required=True,
        )
        assert param.name == "query"
        assert param.description == "Search query string"
        assert param.type == "string"
        assert param.required is True

    def test_create_optional_parameter(self) -> None:
        """Can create an optional parameter."""
        param = MCPToolParameter(
            name="limit",
            description="Max results",
            type="integer",
            required=False,
        )
        assert param.name == "limit"
        assert param.required is False

    def test_parameters_are_frozen(self) -> None:
        """Parameters are immutable."""
        param = MCPToolParameter(
            name="test",
            description="test desc",
            type="string",
            required=True,
        )
        try:
            param.name = "modified"  # type: ignore[misc]
            # Should not get here
            raise AssertionError("Expected FrozenInstanceError")
        except Exception:
            pass


class TestMCPTool:
    """Tests for MCPTool dataclass."""

    def test_create_tool_with_no_parameters(self) -> None:
        """Can create a tool with no parameters."""
        tool = MCPTool(
            name="ping",
            description="Ping the server",
            parameters=[],
        )
        assert tool.name == "ping"
        assert tool.description == "Ping the server"
        assert tool.parameters == []

    def test_create_tool_with_parameters(self) -> None:
        """Can create a tool with parameters."""
        params = [
            MCPToolParameter(
                name="query",
                description="Search query",
                type="string",
                required=True,
            ),
            MCPToolParameter(
                name="limit",
                description="Max results",
                type="integer",
                required=False,
            ),
        ]
        tool = MCPTool(
            name="search",
            description="Search repositories",
            parameters=params,
        )
        assert tool.name == "search"
        assert len(tool.parameters) == 2
        assert tool.parameters[0].name == "query"
        assert tool.parameters[1].name == "limit"


class TestMCPToolResult:
    """Tests for MCPToolResult dataclass."""

    def test_create_successful_result(self) -> None:
        """Can create a successful result."""
        result = MCPToolResult(
            data={"repos": [{"name": "test"}]},
        )
        assert result.data == {"repos": [{"name": "test"}]}
        assert result.is_error is False
        assert result.error_message is None

    def test_create_error_result(self) -> None:
        """Can create an error result."""
        result = MCPToolResult(
            data=None,
            is_error=True,
            error_message="Connection failed",
        )
        assert result.data is None
        assert result.is_error is True
        assert result.error_message == "Connection failed"

    def test_default_is_error_is_false(self) -> None:
        """Default is_error is False."""
        result = MCPToolResult(data="test")
        assert result.is_error is False
