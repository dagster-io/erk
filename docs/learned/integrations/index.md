<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->

# Integrations Documentation

- **[bundled-artifacts.md](bundled-artifacts.md)** — classifying a new skill as portable vs Claude-only, adding or modifying force-include entries in pyproject.toml, debugging why editable installs resolve to unexpected artifact paths, understanding the artifact sync and health detection systems
- **[cmux-integration.md](cmux-integration.md)** — working with cmux workspace management, understanding erk's cmux integration points
- **[codex-integration.md](codex-integration.md)** — working with Codex executor or JSONL parsing, modifying permission mode mappings, adding new Codex event types or executor events, understanding how erk integrates with OpenAI Codex
- **[codex/codex-cli-reference.md](codex/codex-cli-reference.md)** — implementing Codex backend support in erk, mapping PermissionMode to Codex sandbox flags, building a CodexPromptExecutor or Codex-aware AgentLauncher, understanding Claude CLI features that have no Codex equivalent
- **[codex/codex-jsonl-format.md](codex/codex-jsonl-format.md)** — parsing codex exec --json output, implementing a CodexPromptExecutor, mapping Codex events to erk ExecutorEvent types, comparing Claude stream-json and Codex JSONL formats
- **[codex/codex-skills-system.md](codex/codex-skills-system.md)** — porting erk skills to Codex, implementing dual-target skill installation, understanding why Codex requires frontmatter that Claude doesn't, translating Claude slash commands for Codex execution
- **[github-review-decision.md](github-review-decision.md)** — implementing review decision indicators in the TUI, understanding how PR review status flows from GraphQL to the TUI display, debugging missing or incorrect review decision indicators
- **[issue-pr-closing-integration.md](issue-pr-closing-integration.md)** — linking PRs to issues for auto-close, debugging why issues didn't close when PR merged, working on plan number discovery in the submit pipeline, understanding cross-repo plan references
- **[linear-erk-mapping.md](linear-erk-mapping.md)** — Evaluating Linear as issue tracker for erk, Building Linear gateway, Understanding trade-offs between GitHub Issues and Linear
- **[linear-primitives.md](linear-primitives.md)** — Considering Linear as an alternative to GitHub Issues, Building a Linear gateway for erk, Understanding how other tools (Cursor, Devin) integrate with Linear
- **[mcp-integration.md](mcp-integration.md)** — adding new MCP tools to erk, configuring erk as an MCP server for Claude, understanding the erk-mcp package structure, debugging MCP tool calls from external clients
- **[multi-agent-portability.md](multi-agent-portability.md)** — adding Codex support to erk, understanding differences between Claude Code and Codex CLI, designing multi-backend agent support, mapping erk concepts to Codex equivalents
