---
title: Agent-Agnostic Strategy
category: architecture
description: Research and strategy for making erk work with multiple coding agents beyond Claude Code
read_when:
  - "planning agent abstraction"
  - "evaluating alternative coding agents"
  - "designing AgentRuntime gateway"
---

# Agent-Agnostic Strategy: Supporting Multiple Coding Agents

Erk is currently tightly coupled to Claude Code. This document captures research into making erk work with multiple terminal-based coding agents: **OpenAI Codex CLI**, **OpenCode**, **GitHub Copilot**, and **Pi**.

## Target Agents

### Claude Code (Current)

- **Maintainer**: Anthropic
- **Language**: TypeScript
- **Instructions**: `CLAUDE.md` (proprietary format, but `AGENTS.md` also read)
- **Config**: JSON (`~/.claude/settings.json`)
- **Hooks**: Shell scripts configured in `settings.json`, 4 event types (UserPromptSubmit, PreToolUse, PostToolUse, Notification + 6 more)
- **Commands**: Markdown files in `.claude/commands/`
- **Skills**: Markdown files in `.claude/skills/`
- **Sessions**: JSONL files in `~/.claude/projects/<project-hash>/`
- **Non-interactive**: `claude -p "prompt" --output-format stream-json`
- **MCP**: Client support
- **Models**: Anthropic only
- **Unique features**: Plan mode with ExitPlanMode tool, `${CLAUDE_SESSION_ID}` substitution, permission modes (`acceptEdits`, `plan`, `dangerously-skip-permissions`)

### OpenAI Codex CLI

- **Maintainer**: OpenAI
- **Language**: Rust
- **Repo**: [github.com/openai/codex](https://github.com/openai/codex)
- **Instructions**: `AGENTS.md` (open standard under Linux Foundation)
- **Config**: TOML (`~/.codex/config.toml`)
- **Hooks**: Not supported (community PR #9796 proposed but OpenAI not accepting contributions)
- **Commands**: No custom slash commands (built-in only: `/model`, `/review`, `/diff`, `/compact`, `/new`, `/resume`, `/fork`)
- **Skills**: Not supported
- **Sessions**: JSONL files in `~/.codex/sessions/`, resume via `codex resume`
- **Non-interactive**: `codex exec "prompt"` with JSON output
- **MCP**: Full support (client and server modes)
- **Models**: OpenAI default (gpt-5-codex), multi-provider via `config.toml` `[model_providers.*]`
- **Unique features**: Seatbelt/Landlock/AppContainer sandboxing, execution policies, approval modes (auto/read-only/full-access), `codex mcp` server mode, GitHub Action (`codex-action@v1`)
- **Built-in tools**: `shell`, `read_file`, `list_dir`, `glob_file_search`, `rg`, `git`, `apply_patch`, `todo_write/update_plan`, `web_search` (opt-in)

### OpenCode

- **Maintainer**: SST (originally anomalyco)
- **Language**: TypeScript/Go
- **Repo**: [github.com/sst/opencode](https://github.com/sst/opencode)
- **Instructions**: `AGENTS.md` + `CLAUDE.md` as fallback
- **Config**: JSON/JSONC (`opencode.json` or `opencode.jsonc`)
- **Hooks**: JS/TS plugin modules with 22+ lifecycle events (NOT shell scripts)
- **Commands**: Markdown files in `.opencode/commands/` (very similar to Claude Code)
- **Skills**: `SKILL.md` files (compatible with Copilot Agent Skills standard)
- **Sessions**: SQLite storage (not JSONL), `opencode run -c` to resume
- **Non-interactive**: `opencode run "prompt"` or `opencode -p "prompt" --format json`
- **MCP**: Full support (local stdio + remote HTTP/SSE + OAuth)
- **Models**: 75+ providers via AI SDK (Anthropic, OpenAI, Google, Bedrock, Groq, OpenRouter, etc.)
- **Unique features**: Custom agents (primary + subagent system), custom tools via JS/TS, GitHub Actions integration (`/opencode` in issues/PRs), web UI mode (`opencode web`), client/server architecture
- **Built-in tools**: 13 tools (read, write, edit, patch, grep, glob, list, bash, webfetch, question, lsp, todowrite/todoread, skill)

### GitHub Copilot Agent

- **Maintainer**: GitHub/Microsoft
- **Instructions**: `AGENTS.md` + `CLAUDE.md` + `.github/copilot-instructions.md` + `.instructions.md`
- **Config**: YAML (`.github/` directory structure)
- **Hooks**: Shell scripts in `.github/hooks/*.json`, 4 events (sessionStart, sessionEnd, userPromptSubmitted, preToolUse)
- **Commands**: Custom agents via `.agent.md` files in `.github/agents/`
- **Skills**: `SKILL.md` folders in `.github/skills/` or `.claude/skills/` (reads both)
- **Sessions**: GitHub Actions container-based (cloud agent), VS Code session (IDE agent)
- **Non-interactive**: `copilot -p "prompt"` (CLI), issue assignment (cloud agent)
- **MCP**: Client support (configured in repo settings or `copilot-setup-steps.yml`)
- **Models**: Multi-provider (OpenAI GPT-5, Anthropic Claude, Google Gemini, xAI Grok)
- **Unique features**: Cloud-based autonomous agent (assigns to GitHub issues, creates PRs), three surfaces (VS Code, CLI, cloud), `copilot-setup-steps.yml` for environment setup, premium request credits
- **CLI**: `copilot` command (npm `@github/copilot`), default model Claude Sonnet 4.5

### Pi

- **Maintainer**: Mario Zechner (badlogic)
- **Language**: TypeScript
- **Repo**: [github.com/badlogic/pi-mono](https://github.com/badlogic/pi-mono)
- **Instructions**: `AGENTS.md` + `CLAUDE.md` (natively compatible)
- **Config**: JSON (`~/.pi/agent/settings.json`, `.pi/settings.json`)
- **Hooks**: TypeScript event API (`pi.on("tool_call", ...)`, `pi.on("session", ...)`)
- **Commands**: Prompt templates in `.pi/prompts/` (Markdown with `{{variable}}` syntax)
- **Skills**: Markdown skill files in `.pi/skills/` (Agent Skills standard)
- **Sessions**: JSONL with tree structure in `~/.pi/agent/sessions/`, branching via `/tree`
- **Non-interactive**: Print mode, JSON mode, RPC mode, SDK mode
- **MCP**: Not built-in (philosophy: build it yourself via extensions)
- **Models**: 15+ providers via API keys + OAuth subscriptions (Claude, GPT, Gemini, Bedrock, etc.)
- **Unique features**: Radical minimalism (~1000 token system prompt, 4 default tools), TypeScript extension API (`pi.on()`, `pi.registerTool()`, `pi.send()`), pi packages (npm/git installable bundles of extensions/skills/prompts/themes), hot-reload, cross-provider session handoffs
- **Built-in tools**: 4 only (read, write, edit, bash) + optional read-only variants (grep, find, ls)

## Capability Comparison Matrix

| Capability              | Claude Code                   | Codex CLI                    | OpenCode                   | Copilot                               | Pi                              |
| ----------------------- | ----------------------------- | ---------------------------- | -------------------------- | ------------------------------------- | ------------------------------- |
| `AGENTS.md` support     | Yes                           | Yes (primary)                | Yes (primary)              | Yes                                   | Yes                             |
| `CLAUDE.md` support     | Yes (primary)                 | Fallback                     | Fallback                   | Fallback                              | Fallback                        |
| Custom slash commands   | `.claude/commands/` (MD)      | None                         | `.opencode/commands/` (MD) | `.agent.md` files                     | `.pi/prompts/` (MD)             |
| Skills/knowledge files  | `.claude/skills/` (MD)        | None                         | `SKILL.md` folders         | `.github/skills/` + `.claude/skills/` | `.pi/skills/` (MD)              |
| Shell-script hooks      | Yes (settings.json)           | No                           | No (JS/TS plugins instead) | Yes (`.github/hooks/`)                | No (TS event API instead)       |
| Non-interactive CLI     | `claude -p`                   | `codex exec`                 | `opencode run` / `-p`      | `copilot -p`                          | Print/JSON/RPC modes            |
| Streaming output format | stream-json (JSONL)           | JSON                         | JSON                       | Unknown                               | Unknown                         |
| Session resume          | `--resume` flag               | `codex resume`               | `opencode run -c`          | N/A (cloud)                           | `/tree`, `/fork`                |
| Session storage         | JSONL (`~/.claude/projects/`) | JSONL (`~/.codex/sessions/`) | SQLite                     | Cloud (Actions)                       | JSONL (`~/.pi/agent/sessions/`) |
| MCP support             | Client                        | Client + server              | Client (local + remote)    | Client                                | None (extension-based)          |
| Multi-model             | No (Anthropic only)           | Yes (via providers)          | Yes (75+ via AI SDK)       | Yes (4 providers)                     | Yes (15+ providers)             |
| Custom tools            | MCP only                      | MCP only                     | Native JS/TS + MCP         | MCP + `.agent.md`                     | Extensions (TS)                 |
| Plan mode               | Yes (ExitPlanMode tool)       | No                           | Yes (Plan agent)           | No                                    | No (build via extension)        |
| GitHub integration      | Via `gh` CLI                  | GitHub Action                | GitHub App + Actions       | Native (issue assignment)             | Via `gh` CLI                    |

## Erk's Current Claude Code Coupling Points

### 1. Hook System (HIGH coupling)

**Files**: `.claude/settings.json`, `src/erk/capabilities/hooks.py`, `src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py`

Erk registers 4 hooks in Claude Code's `settings.json`:

- `UserPromptSubmit`: `erk exec user-prompt-hook`
- `PreToolUse` (ExitPlanMode): `erk exec exit-plan-mode-hook`
- `PostToolUse` (Write|Edit): `uv run ruff format "${file_path}"`
- `PreToolUse` (Write|Edit): `erk exec pre-tool-use-hook`

The exit-plan-mode hook (619 lines) is the most complex -- it intercepts ExitPlanMode, prompts the user to save or implement, and coordinates via marker files.

**Agent compatibility**: Only Copilot has a similar shell-hook model. OpenCode uses JS/TS plugins. Pi uses TypeScript events. Codex has no hooks at all.

### 2. Slash Commands (MEDIUM coupling)

**Files**: `.claude/commands/` (30+ Markdown files)

Commands use `${CLAUDE_SESSION_ID}` substitution and assume Claude Code's command execution model. The Markdown format is similar across Claude Code, OpenCode, and Pi.

**Agent compatibility**: OpenCode supports nearly identical Markdown commands. Pi uses prompt templates with `{{variable}}` syntax. Codex has no custom command support. Copilot uses `.agent.md` files.

### 3. Skills (MEDIUM coupling)

**Files**: `.claude/skills/` (15+ Markdown files)

Skills are Markdown files with YAML frontmatter. They're loaded on-demand by Claude Code.

**Agent compatibility**: Copilot reads `.claude/skills/` directly. OpenCode uses `SKILL.md` with similar frontmatter. Pi has its own skill format. Codex has no skill support.

### 4. Session Logs (HIGH coupling, well-abstracted)

**Gateway**: `erk_shared.gateway.claude_installation` (ABC + Real + Fake)

Reads JSONL files from `~/.claude/projects/`. Methods: `has_project()`, `find_sessions()`, `read_session()`, `get_session_path()`, `find_plan_for_session()`.

**Agent compatibility**: Codex and Pi also use JSONL but with different schemas. OpenCode uses SQLite. Copilot sessions are cloud-based. The existing gateway ABC is the right seam for abstraction.

### 5. CLI Executor (HIGH coupling, partially abstracted)

**Gateway**: `ClaudeExecutor` ABC in `erk_shared.core.claude_executor`

Methods: `execute_interactive()`, `execute_command_streaming()`, `execute_command()`, `execute_prompt()`, `execute_prompt_passthrough()`, `is_claude_available()`.

Builds commands like: `claude --permission-mode acceptEdits --output-format stream-json -p "prompt"`

**Agent compatibility**: Each agent has completely different CLI flags. This is the primary abstraction point.

### 6. Stream-JSON Output Parsing (HIGH coupling)

**File**: `src/erk/core/claude_executor.py` (`_parse_stream_json_line()`)

Parses Claude Code's specific JSONL event format: `type: "assistant"`, `type: "user"`, `type: "result"`. Extracts PR URLs, issue numbers, turn counts.

**Agent compatibility**: Each agent has its own output format. This parser must be per-agent.

### 7. Session ID / Markers (MEDIUM coupling)

**Pattern**: `${CLAUDE_SESSION_ID}` in commands, `.erk/scratch/sessions/<session-id>/` marker files

Used for: hook coordination, session tracking, plan-saved markers, objective context markers.

**Agent compatibility**: Each agent has its own session ID mechanism. The marker system itself is agent-agnostic (it just needs a session ID string).

### 8. Settings / Configuration (HIGH coupling)

**Files**: `.claude/settings.json`, `src/erk/core/claude_settings.py`, capabilities system

Manages: permissions, hooks, statusline. The `erk init` command writes to `.claude/settings.json`.

**Agent compatibility**: Each agent has completely different config formats (TOML, JSON, YAML). The capabilities system would need agent-specific config writers.

## Abstraction Strategy

### Key Insight: AGENTS.md as the Universal Instruction Layer

`AGENTS.md` is now an [open standard under the Linux Foundation](https://agents.md/). All five agents read it natively. Erk already uses `AGENTS.md` as its primary instruction file (with `CLAUDE.md` routing to it). This layer requires no abstraction work.

### Recommended Approach: Agent Runtime Gateway

Introduce an `AgentRuntime` gateway ABC that abstracts the differences between agents. Each agent gets an adapter implementing this interface.

```
AgentRuntime (ABC)
├── ClaudeCodeRuntime (current behavior)
├── OpenCodeRuntime (first target)
├── CodexRuntime (future)
├── CopilotRuntime (future)
└── PiRuntime (future)
```

The gateway should abstract these operations:

1. **Detection**: Is this agent installed? What version?
2. **Interactive launch**: Replace current process with the agent TUI
3. **Non-interactive execution**: Run a prompt, stream output events
4. **Output parsing**: Normalize agent-specific output into erk domain events
5. **Configuration**: Generate agent-specific config (hooks, permissions, etc.)
6. **Session access**: Read session history (JSONL, SQLite, etc.)

### What Changes vs What Stays

**Stays the same (agent-agnostic already)**:

- `AGENTS.md` / `docs/learned/` documentation
- Git/GitHub/Graphite operations (via `gh`, `gt`)
- `.impl/` folder structure for plans
- `.erk/` scratch directory and marker files
- GitHub issue/PR workflows
- `erk exec` scripts (they shell out to `erk`, not `claude`)

**Must be abstracted**:

- `ClaudeExecutor` → `AgentRuntime` gateway
- `ClaudeInstallation` → `AgentInstallation` gateway (session/settings access)
- `.claude/settings.json` management → per-agent config writers
- Hook registration → per-agent hook installation
- Stream-JSON parsing → per-agent output normalizers
- Command deployment → per-agent command format generators
- Skill deployment → per-agent skill format generators
- Capabilities system → agent-aware capability installers

### OpenCode as First Target

OpenCode is the recommended first non-Claude-Code target because:

1. **Closest feature parity**: Has commands (`.opencode/commands/`), agents, tools, sessions, and GitHub integration
2. **AGENTS.md native**: Reads `AGENTS.md` and `CLAUDE.md` with no changes
3. **Similar command format**: Markdown commands with `$ARGUMENTS` (nearly identical to Claude Code)
4. **75+ model providers**: Supports Anthropic models, so the same underlying LLM can be used
5. **MCP support**: Can use existing MCP integrations
6. **Active community**: 70K+ GitHub stars, rapid development

**Key differences to handle**:

- Hooks are JS/TS plugins, not shell scripts → need a plugin generator or skip hooks initially
- Sessions are SQLite, not JSONL → need a SQLite session reader
- Config is `opencode.json`, not `.claude/settings.json` → need an OpenCode config writer
- Streaming output format differs → need an OpenCode output parser
- No plan mode with ExitPlanMode → need to handle plan workflow differently

### Migration Path for Commands and Skills

Most erk commands and skills can be mechanically translated:

| Claude Code                         | OpenCode                                           | Translation                         |
| ----------------------------------- | -------------------------------------------------- | ----------------------------------- |
| `.claude/commands/erk/plan-save.md` | `.opencode/commands/erk-plan-save.md`              | Rename, adjust `${}` → `$ARGUMENTS` |
| `.claude/skills/dignified-python/`  | `SKILL.md` in `.opencode/skills/dignified-python/` | Add YAML frontmatter                |
| `${CLAUDE_SESSION_ID}`              | Context from command execution                     | Different injection mechanism       |

### Hook Strategy Per Agent

| Agent       | Hook Strategy                                                      |
| ----------- | ------------------------------------------------------------------ |
| Claude Code | Shell scripts in `settings.json` (current)                         |
| OpenCode    | Generate `.opencode/plugin/erk-hooks.ts` plugin                    |
| Codex       | No hooks available -- degrade gracefully, use `codex exec` wrapper |
| Copilot     | Shell scripts in `.github/hooks/*.json` (similar to Claude Code)   |
| Pi          | Generate `.pi/extensions/erk-hooks.ts` extension                   |

### Session Access Strategy Per Agent

| Agent       | Session Location             | Format       | Reader                                   |
| ----------- | ---------------------------- | ------------ | ---------------------------------------- |
| Claude Code | `~/.claude/projects/<hash>/` | JSONL        | Existing `RealClaudeInstallation`        |
| OpenCode    | SQLite database              | SQLite       | New `OpenCodeInstallation`               |
| Codex       | `~/.codex/sessions/`         | JSONL        | New `CodexInstallation` (similar schema) |
| Copilot     | Cloud-based (GitHub Actions) | API          | New `CopilotInstallation` (GitHub API)   |
| Pi          | `~/.pi/agent/sessions/`      | JSONL (tree) | New `PiInstallation`                     |

## Open Questions

1. **Should erk auto-detect the agent or require explicit configuration?** Auto-detection (check which CLIs are in PATH) is user-friendly but ambiguous when multiple are installed. A config flag (`erk.agent = "opencode"`) is explicit but requires setup.

2. **How deep should the abstraction go?** Options range from "just swap the CLI binary" (minimal) to "fully normalize all agent concepts" (maximum). The gateway pattern suggests a middle ground.

3. **What happens to plan mode for agents that lack it?** Claude Code and OpenCode have plan mode; Codex, Pi, and (local) Copilot do not. Erk could implement plan mode externally via prompt engineering.

4. **Should erk maintain parallel config directories?** (`.claude/` + `.opencode/` + etc.) or consolidate into `.erk/agent/`?

5. **How to handle hooks for Codex (which has none)?** Options: wrapper script that calls `codex exec` with pre/post hooks, or accept reduced functionality.

## References

- [AGENTS.md Open Standard](https://agents.md/)
- [OpenAI Codex CLI](https://github.com/openai/codex) | [Docs](https://developers.openai.com/codex/cli/)
- [OpenCode](https://github.com/sst/opencode) | [Docs](https://opencode.ai/docs/)
- [GitHub Copilot Agent](https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-coding-agent)
- [Pi Coding Agent](https://github.com/badlogic/pi-mono) | [Blog Post](https://mariozechner.at/posts/2025-11-30-pi-coding-agent/)
- [Armin Ronacher on Pi](https://lucumr.pocoo.org/2026/1/31/pi/)
- [Terminal-Bench 2.0 Leaderboard](https://www.tbench.ai/leaderboard/terminal-bench/2.0)
