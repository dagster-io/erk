Investigate and fix the `erk one-shot` MCP tool (`mcp_erk_mcp_one_shot`) not returning any output. When the tool is invoked, it should return the PR URL and workflow run URL after dispatching, but currently it returns an empty string `""`.

Requirements:
- Explore the erk-mcp server codebase to find the implementation of the `one-shot` tool
- Identify why the tool is returning an empty string instead of the expected PR URL and workflow run URL
- Fix the issue so that the tool returns meaningful output, including at minimum:
  - The PR URL
  - The workflow run URL
- Follow existing patterns and conventions in the codebase
- Submit a PR with the fix
