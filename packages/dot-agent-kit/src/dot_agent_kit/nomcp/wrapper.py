"""
MCPWrapper - Core class for connecting to MCP servers as a client.

This module provides the MCPWrapper class that wraps MCP servers and provides
a simple Python API for calling tools.
"""

import os
from pathlib import Path
from typing import Self, cast

from dot_agent_kit.nomcp.models import (
    MCPClientABC,
    MCPTool,
    MCPToolParameter,
    MCPToolResult,
)


class MCPWrapperError(Exception):
    """Base exception for MCPWrapper errors."""


class MCPServerNotConnectedError(MCPWrapperError):
    """Raised when trying to call tools before connecting to the server."""


class MCPToolNotFoundError(MCPWrapperError):
    """Raised when trying to call a tool that doesn't exist."""


class MCPToolCallError(MCPWrapperError):
    """Raised when a tool call fails."""


class MCPWrapper:
    """
    Wrapper for connecting to MCP servers as a client.

    This class manages the lifecycle of an MCP server process and provides
    methods for discovering and calling tools.

    Usage:
        wrapper = MCPWrapper(command=["uvx", "mcp-server-github"])

        async with wrapper:
            tools = await wrapper.list_tools()
            result = await wrapper.call("search_repositories", q="python")

    The MCP server is started lazily when entering the async context manager
    and stopped when exiting.
    """

    def __init__(
        self,
        command: list[str] | None = None,
        url: str | None = None,
        env: dict[str, str] | None = None,
        cwd: str | Path | None = None,
        *,
        _client: MCPClientABC | None = None,
    ) -> None:
        """
        Initialize the MCP wrapper.

        Args:
            command: Command to start the MCP server (e.g., ["uvx", "mcp-server-github"])
            url: URL for HTTP-based MCP servers (alternative to command)
            env: Environment variables to pass to the server process
            cwd: Working directory for the server process
            _client: Internal parameter for dependency injection (testing only)
        """
        # Allow _client injection without command/url for testing
        if _client is None:
            if command is None and url is None:
                raise ValueError("Either command or url must be provided")
            if command is not None and url is not None:
                raise ValueError("Cannot provide both command and url")

        self._command = command
        self._url = url
        self._env = env
        self._cwd = Path(cwd) if cwd else None
        self._injected_client = _client
        self._client: MCPClientABC | None = None
        self._is_connected = False
        self._cached_tools: list[MCPTool] | None = None

    @classmethod
    def from_kit(cls, kit_path: Path | None = None) -> Self:
        """
        Create an MCPWrapper from a kit's nomcp.yaml configuration.

        Args:
            kit_path: Path to the kit directory. If None, searches from current
                      directory upward for a kit with nomcp.yaml.

        Returns:
            Configured MCPWrapper instance.

        Raises:
            FileNotFoundError: If nomcp.yaml is not found.
            ValueError: If nomcp.yaml is invalid.
        """
        import yaml

        if kit_path is None:
            kit_path = cls._find_kit_path()

        nomcp_yaml = kit_path / "nomcp.yaml"
        if not nomcp_yaml.exists():
            raise FileNotFoundError(f"nomcp.yaml not found in {kit_path}")

        config = yaml.safe_load(nomcp_yaml.read_text(encoding="utf-8"))

        command = config.get("command")
        url = config.get("url")
        env = config.get("env")
        cwd = config.get("cwd")

        if command is not None and isinstance(command, str):
            # Split command string into list
            import shlex

            command = shlex.split(command)

        return cls(command=command, url=url, env=env, cwd=cwd)

    @staticmethod
    def _find_kit_path() -> Path:
        """Find the kit path by searching upward for kit.yaml."""
        current = Path.cwd()
        while current != current.parent:
            if (current / "kit.yaml").exists():
                return current
            current = current.parent
        raise FileNotFoundError("Could not find kit.yaml in any parent directory")

    async def __aenter__(self) -> Self:
        """Enter async context manager - connect to the MCP server."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Exit async context manager - disconnect from the MCP server."""
        await self.disconnect()

    async def connect(self) -> None:
        """
        Connect to the MCP server.

        For command-based servers, this starts the server process.
        For URL-based servers, this establishes the HTTP connection.
        """
        if self._is_connected:
            return

        # Use injected client if provided (for testing)
        if self._injected_client is not None:
            self._client = self._injected_client
            await self._client.__aenter__()
            self._is_connected = True
            return

        try:
            from fastmcp import Client
            from fastmcp.client.transports import StdioTransport
        except ImportError as e:
            raise MCPWrapperError(
                "fastmcp is required for MCPWrapper. Install with: pip install fastmcp"
            ) from e

        if self._command is not None:
            # Build environment for subprocess
            env = dict(os.environ)
            if self._env:
                env.update(self._env)

            transport = StdioTransport(
                command=self._command[0],
                args=self._command[1:] if len(self._command) > 1 else [],
                env=env,
                cwd=str(self._cwd) if self._cwd else None,
            )
            # Cast to MCPClientABC - fastmcp.Client implements the same interface
            self._client = cast(MCPClientABC, Client(transport))
        else:
            # URL-based transport
            self._client = cast(MCPClientABC, Client(self._url))

        # Enter the client context
        await self._client.__aenter__()
        self._is_connected = True

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if not self._is_connected or self._client is None:
            return

        await self._client.__aexit__(None, None, None)
        self._client = None
        self._is_connected = False
        self._cached_tools = None

    async def list_tools(self) -> list[MCPTool]:
        """
        List available tools from the MCP server.

        Returns:
            List of MCPTool objects describing available tools.

        Raises:
            MCPServerNotConnectedError: If not connected to the server.
        """
        if not self._is_connected or self._client is None:
            raise MCPServerNotConnectedError("Must connect to server first")

        if self._cached_tools is not None:
            return self._cached_tools

        raw_tools = await self._client.list_tools()

        tools = []
        for tool in raw_tools:
            parameters = []
            # Extract parameters from the tool's input schema
            input_schema = getattr(tool, "inputSchema", {})
            if input_schema is None:
                input_schema = {}
            properties = input_schema.get("properties", {})
            required_params = set(input_schema.get("required", []))

            for param_name, param_info in properties.items():
                parameters.append(
                    MCPToolParameter(
                        name=param_name,
                        description=param_info.get("description", ""),
                        type=param_info.get("type", "string"),
                        required=param_name in required_params,
                    )
                )

            tools.append(
                MCPTool(
                    name=tool.name,
                    description=getattr(tool, "description", "") or "",
                    parameters=parameters,
                )
            )

        self._cached_tools = tools
        return tools

    async def call(self, tool_name: str, **kwargs: object) -> MCPToolResult:
        """
        Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call.
            **kwargs: Arguments to pass to the tool.

        Returns:
            MCPToolResult with the tool's response.

        Raises:
            MCPServerNotConnectedError: If not connected to the server.
            MCPToolNotFoundError: If the tool doesn't exist.
            MCPToolCallError: If the tool call fails.
        """
        if not self._is_connected or self._client is None:
            raise MCPServerNotConnectedError("Must connect to server first")

        # Verify tool exists (caches tools on first call)
        tools = await self.list_tools()
        tool_names = {t.name for t in tools}
        if tool_name not in tool_names:
            raise MCPToolNotFoundError(
                f"Tool '{tool_name}' not found. Available tools: {', '.join(sorted(tool_names))}"
            )

        try:
            result = await self._client.call_tool(tool_name, kwargs)
            return MCPToolResult(data=result, is_error=False)
        except Exception as e:
            return MCPToolResult(
                data=None,
                is_error=True,
                error_message=str(e),
            )

    @property
    def is_connected(self) -> bool:
        """Return True if connected to the MCP server."""
        return self._is_connected
