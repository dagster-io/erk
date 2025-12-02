"""Fake MCP client for testing MCPWrapper (Layer 1: Fake Infrastructure)."""

from typing import Self

from dot_agent_kit.nomcp.models import MCPClientABC, MCPToolInfo


class FakeMCPClient(MCPClientABC):
    """
    Fake MCP client that implements the MCPClientABC interface.

    This fake allows testing MCPWrapper without connecting to real MCP servers.
    """

    def __init__(
        self,
        tools: list[MCPToolInfo] | None = None,
        call_results: dict[str, object] | None = None,
        call_errors: dict[str, Exception] | None = None,
    ) -> None:
        """
        Initialize the fake client.

        Args:
            tools: List of tools to return from list_tools.
            call_results: Dict mapping tool names to their results.
            call_errors: Dict mapping tool names to exceptions to raise.
        """
        self._tools = tools or []
        self._call_results = call_results or {}
        self._call_errors = call_errors or {}
        self._is_connected = False
        self._call_history: list[tuple[str, dict[str, object]]] = []

    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        self._is_connected = True
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Exit async context manager."""
        self._is_connected = False

    async def list_tools(self) -> list[MCPToolInfo]:
        """Return configured tools."""
        return self._tools

    async def call_tool(self, tool_name: str, arguments: dict[str, object]) -> object:
        """
        Call a tool and return the configured result.

        Args:
            tool_name: Name of the tool to call.
            arguments: Arguments to pass to the tool.

        Returns:
            Configured result for this tool.

        Raises:
            Exception: If tool is configured to raise an error.
        """
        # Record the call
        self._call_history.append((tool_name, arguments))

        # Check for configured error
        if tool_name in self._call_errors:
            raise self._call_errors[tool_name]

        # Return configured result or empty dict
        return self._call_results.get(tool_name, {})

    @property
    def is_connected(self) -> bool:
        """Return True if connected."""
        return self._is_connected

    @property
    def call_history(self) -> list[tuple[str, dict[str, object]]]:
        """Return list of (tool_name, arguments) tuples for all calls made."""
        return self._call_history


def create_fake_tool(
    name: str,
    description: str = "",
    parameters: dict[str, dict[str, str]] | None = None,
    required: list[str] | None = None,
) -> MCPToolInfo:
    """
    Helper to create an MCPToolInfo with parameters.

    Args:
        name: Tool name.
        description: Tool description.
        parameters: Dict of param_name -> {type, description}.
        required: List of required parameter names.

    Returns:
        MCPToolInfo instance.
    """
    input_schema: dict[str, object] = {
        "type": "object",
        "properties": {},
        "required": required or [],
    }

    if parameters:
        props: dict[str, dict[str, str]] = {}
        for param_name, param_info in parameters.items():
            props[param_name] = {
                "type": param_info.get("type", "string"),
                "description": param_info.get("description", ""),
            }
        input_schema["properties"] = props

    return MCPToolInfo(
        name=name,
        description=description,
        inputSchema=input_schema,
    )
