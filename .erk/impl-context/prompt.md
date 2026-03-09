Add a new tool to the erk-mcp server that allows users to view release notes by invoking the `erk release-notes` command.

Requirements:
- Add a new MCP tool named something like `mcp_plan_release_notes` or `erk_release_notes`
- The tool should invoke the `erk release-notes` CLI command and return its output
- The tool should have a helpful description so that AI assistants know to call it when users ask "what's new" or want to see release notes or a changelog
- The tool should require no parameters (or have sensible optional ones if needed)
- Follow the existing patterns and conventions used in the erk-mcp server codebase
- Make sure the tool is properly registered alongside the other tools in the MCP server

Please explore the codebase to understand the existing tool patterns, implement the new tool, and submit a PR.
