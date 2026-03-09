Add a new `release_notes` MCP tool to the erk-mcp server (packages/erk-mcp/src/erk_mcp/server.py) that allows MCP clients to access erk release notes and changelog information.

The tool should:
1. Be named `release_notes` (snake_case, matching the existing naming convention of `plan_list`, `plan_view`, `one_shot`)
2. Have an optional `version` parameter (str | None = None) that:
   - When None: shows the current version's release notes (calls `erk release-notes`)
   - When set to a version string like "0.2.1": shows that version's notes (calls `erk release-notes --version 0.2.1`)
   - When set to "all": shows the full changelog (calls `erk release-notes --all`)
3. Be registered in `create_mcp()` alongside the other tools
4. Have a helpful docstring that explains it's for "what's new" queries
5. Include tests in packages/erk-mcp/tests/test_server.py following the existing test patterns (mock `_run_erk`, test without version, with specific version, with "all")
6. Update the `test_registers_expected_tools` test to include `release_notes` in the expected tool set

Follow the exact same patterns as the existing tools in the file. Do not modify CHANGELOG.md.
