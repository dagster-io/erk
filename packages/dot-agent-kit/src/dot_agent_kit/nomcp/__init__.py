"""
nomcp: MCP-Hidden CLI Wrapper Pattern

Use MCP servers without MCP. Turn any MCP server into a kit with CLI commands + skill.

The core class is MCPWrapper which connects to MCP servers as a client and allows
calling tools via a simple Python API.

Example usage:

    from dot_agent_kit.nomcp import MCPWrapper

    # Create a wrapper for an MCP server
    wrapper = MCPWrapper(command=["uvx", "mcp-server-github"])

    # List available tools
    async with wrapper:
        tools = await wrapper.list_tools()
        result = await wrapper.call("search_repositories", q="python testing")
"""

from dot_agent_kit.nomcp.models import MCPClientABC, MCPTool, MCPToolInfo, MCPToolResult
from dot_agent_kit.nomcp.wrapper import MCPWrapper

__all__ = ["MCPWrapper", "MCPClientABC", "MCPTool", "MCPToolInfo", "MCPToolResult"]
