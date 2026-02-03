# Plan: Document Codex CLI Research Findings

Create thorough documentation capturing ground-truth Codex research verified against the open-source Codex repo (`codex-rs/`). Emphasis on TUI interaction patterns relevant to how erk launches and communicates with agent backends.

## Documents to Create

All content below is verified against the Codex source code and should be written verbatim (with minor formatting adjustments for the learned-docs style).

**Source repo:** https://github.com/openai/codex (Rust, Apache-2.0). If any details need further verification or the implementation has changed since this research (February 2, 2026), clone and inspect the source — particularly `codex-rs/exec/src/cli.rs`, `codex-rs/tui/src/cli.rs`, `codex-rs/exec/src/exec_events.rs`, and `codex-rs/core/src/skills/`.

---

### Document 1: `docs/learned/integrations/codex-cli-reference.md`

```markdown
---
title: Codex CLI Reference
read_when:
  - "implementing Codex support in erk"
  - "mapping Claude CLI flags to Codex equivalents"
  - "understanding Codex sandbox and approval modes"
  - "launching Codex from Python subprocess"
tripwires:
  - action: "using --ask-for-approval with codex exec"
    warning: "codex exec does NOT support --ask-for-approval. It hardcodes approval to Never in headless mode. Only the TUI supports this flag."
  - action: "using --system-prompt or --allowedTools with codex"
    warning: "Codex has no --system-prompt or --allowedTools equivalent. Prepend system prompt to user prompt. Tool restriction is not available."
  - action: "using --output-format with codex"
    warning: "Codex does not have --output-format. Use --json (boolean flag) for JSONL output. Without --json, output goes directly to terminal."
  - action: "using --print or --verbose with codex"
    warning: "Codex exec mode is always non-interactive (no --print needed). There is no --verbose flag."
---

# Codex CLI Reference

Ground-truth reference for the OpenAI Codex CLI, verified against the open-source repository at `codex-rs/`. Research date: February 2, 2026.

**Source code**: https://github.com/openai/codex (Rust, Apache-2.0)

## Two Execution Modes

Codex has two distinct modes, analogous to Claude's modes:

| Mode | Invocation | Claude Equivalent | Purpose |
|---|---|---|---|
| **TUI** (interactive) | `codex [PROMPT]` | `claude [COMMAND]` | Interactive terminal UI |
| **Exec** (headless) | `codex exec [PROMPT]` | `claude --print COMMAND` | Non-interactive, scriptable |

Key behavioral difference: `codex exec` hardcodes approval policy to `Never` — it never prompts for confirmation. The TUI mode supports configurable approval via `--ask-for-approval`.

## Exec Mode Flags (`codex exec`)

Source: `codex-rs/exec/src/cli.rs`

### Core Flags

| Flag | Short | Type | Description |
|---|---|---|---|
| `PROMPT` | | positional | Prompt text (or `-` to read from stdin) |
| `--model` | `-m` | string | Model identifier (e.g., `o3`, `gpt-5.2-codex`) |
| `--json` | | bool | Output JSONL events to stdout (alias: `--experimental-json`) |
| `--output-last-message` | `-o` | path | Write agent's final message to file |
| `--cd` | `-C` | path | Set working directory for the agent |
| `--image` | `-i` | path[] | Attach image(s), comma-delimited or repeated |
| `--color` | | enum | `auto` (default), `always`, `never` |
| `--skip-git-repo-check` | | bool | Allow running outside a Git repo |
| `--add-dir` | | path[] | Additional writable directories |
| `--output-schema` | | path | JSON Schema for structured output |
| `--profile` | `-p` | string | Config profile name from config.toml |
| `--config` | `-c` | key=value | Override config.toml values (TOML syntax, repeatable) |

### Sandbox & Permission Flags

| Flag | Short | Type | Values |
|---|---|---|---|
| `--sandbox` | `-s` | enum | `read-only`, `workspace-write`, `danger-full-access` |
| `--full-auto` | | bool | Convenience: `--sandbox workspace-write` + auto-approve |
| `--dangerously-bypass-approvals-and-sandbox` | `--yolo` | bool | Skip all confirmations and sandboxing |

### Provider Flags

| Flag | Type | Description |
|---|---|---|
| `--oss` | bool | Use open-source provider (LM Studio, Ollama) |
| `--local-provider` | string | Specify: `lmstudio`, `ollama`, or `ollama-chat` |

### Exec Subcommands

**`codex exec resume [SESSION_ID]`** — Resume a previous session
- `--last` — Resume most recent session
- `--all` — Show all sessions (disables cwd filtering)

**`codex exec review`** — Run code review
- `--uncommitted` — Review staged/unstaged/untracked changes
- `--base BRANCH` — Review against base branch
- `--commit SHA` — Review changes in a commit
- `--title TITLE` — Commit title (requires `--commit`)

## TUI Mode Flags (`codex`)

Source: `codex-rs/tui/src/cli.rs`

Shares most exec flags plus these TUI-only additions:

| Flag | Short | Type | Values |
|---|---|---|---|
| `--ask-for-approval` | `-a` | enum | `untrusted`, `on-failure`, `on-request`, `never` |
| `--no-alt-screen` | | bool | Run inline, preserving terminal scrollback |
| `--search` | | bool | Enable live web search |

**Approval modes explained:**
- `untrusted` — Ask unless command is "trusted" (ls, cat, sed, etc.)
- `on-failure` — Run all commands; ask only on execution failure
- `on-request` — Model decides when to ask for approval
- `never` — Never ask (same as exec default)

## Claude-to-Codex Flag Mapping

| Claude Flag | Codex Equivalent | Notes |
|---|---|---|
| `--print` | (implicit in `codex exec`) | Exec mode is always non-interactive |
| `--verbose` | (none) | Not available |
| `--output-format stream-json` | `--json` | Boolean flag, always JSONL |
| `--output-format text` | `--output-last-message FILE` | Writes final message to file |
| `--permission-mode default` | `--sandbox read-only` | |
| `--permission-mode acceptEdits` | `--full-auto` | workspace-write + auto-approve |
| `--permission-mode plan` | `--sandbox read-only` | No direct plan mode equivalent |
| `--permission-mode bypassPermissions` | `--yolo` | |
| `--dangerously-skip-permissions` | `--yolo` | |
| `--allow-dangerously-skip-permissions` | (none) | No equivalent — Codex uses explicit sandbox levels |
| `--model MODEL` | `--model MODEL` | Same concept |
| `--system-prompt TEXT` | **NOT AVAILABLE** | Must prepend to user prompt |
| `--allowedTools TOOLS` | **NOT AVAILABLE** | No tool restriction in Codex |
| `--no-session-persistence` | **NOT AVAILABLE** | Sessions always persist to `~/.codex/threads/` |
| `--max-turns N` | **NOT AVAILABLE** | No turn limit flag |
| `cwd` (subprocess arg) | `--cd DIR` | Explicit flag in Codex |

## Permission/Sandbox Mapping for Erk

How erk's planned `SandboxMode` maps to both backends:

| Erk SandboxMode | Claude `--permission-mode` | Codex exec | Codex TUI |
|---|---|---|---|
| `safe` | `default` | `--sandbox read-only` | `--sandbox read-only -a untrusted` |
| `edits` | `acceptEdits` | `--full-auto` | `--sandbox workspace-write -a on-request` |
| `plan` | `plan` | `--sandbox read-only` | `--sandbox read-only -a never` |
| `dangerous` | + `--dangerously-skip-permissions` | `--yolo` | `--yolo` |

## TUI Interaction Pattern for Erk

Erk launches agent TUIs via `os.execvp()` which replaces the current process. The key difference:

- **Claude**: `os.execvp("claude", ["claude", "--permission-mode", "acceptEdits", "/command"])`
- **Codex**: `os.execvp("codex", ["codex", "--sandbox", "workspace-write", "-a", "on-request", "--cd", str(worktree_path)])`

Codex TUI does NOT support slash commands. The prompt (if any) is a positional argument. Erk skills would need to be installed as Codex skills and invoked via `$skill-name` syntax in the prompt.

## Related Documentation

- [Codex JSONL Format](codex-jsonl-format.md) — Streaming output event format
- [Codex Skills System](codex-skills-system.md) — Skill discovery and invocation
- [Multi-Agent Portability](multi-agent-portability.md) — Broader multi-agent research
- [PromptExecutor Patterns](../architecture/prompt-executor-patterns.md) — How erk abstracts agent backends
- [Interactive Agent Configuration](../reference/interactive-claude-config.md) — Current config system (will evolve)
```

---

### Document 2: `docs/learned/integrations/codex-jsonl-format.md`

```markdown
---
title: Codex CLI JSONL Output Format
read_when:
  - "parsing codex exec --json output"
  - "implementing CodexPromptExecutor streaming"
  - "mapping Codex events to ExecutorEvent types"
  - "comparing Claude and Codex streaming formats"
tripwires:
  - action: "assuming Codex JSONL uses same format as Claude stream-json"
    warning: "Completely different formats. Claude uses type: assistant/user/result with nested message.content[]. Codex uses type: item.completed with flattened item fields. See codex-jsonl-format.md."
  - action: "looking for session_id in Codex JSONL"
    warning: "Codex JSONL does not include session_id in events. The thread_id is provided in the thread.started event only."
---

# Codex CLI JSONL Output Format

Reference for the JSONL event stream produced by `codex exec --json`. Verified against source code in `codex-rs/exec/src/exec_events.rs`.

## Overview

When `--json` is passed to `codex exec`, each line of stdout is a JSON object representing one event. Events use a two-level type discrimination system.

## Top-Level Event Types

Every JSONL line has a `type` field identifying the event kind:

| Event Type | Description | Key Fields |
|---|---|---|
| `thread.started` | Session initialization (always first event) | `thread_id` (string, UUID) |
| `turn.started` | User prompt sent to model | (empty object) |
| `turn.completed` | Turn finished successfully | `usage.{input_tokens, cached_input_tokens, output_tokens}` |
| `turn.failed` | Turn ended with error | `error.message` |
| `item.started` | New item begun (in progress) | `item.id`, `item.{type-specific fields}` |
| `item.updated` | Item status update | `item.id`, `item.{type-specific fields}` |
| `item.completed` | Item reached terminal state | `item.id`, `item.{type-specific fields}` |
| `error` | Unrecoverable stream error | `message` |

## Item Types (Second-Level Discrimination)

Item events (`item.started`, `item.updated`, `item.completed`) contain an `item` object with an `id` field and a flattened `type` field identifying the item kind:

| Item Type | Description | Key Fields |
|---|---|---|
| `agent_message` | Agent text response | `text` |
| `reasoning` | Agent reasoning summary | `text` |
| `command_execution` | Shell command execution | `command`, `aggregated_output`, `exit_code`, `status` |
| `file_change` | File modifications | `changes[].{path, kind}`, `status` |
| `mcp_tool_call` | MCP tool invocation | `server`, `tool`, `arguments`, `result`, `error`, `status` |
| `collab_tool_call` | Multi-agent collaboration | `tool`, `sender_thread_id`, `receiver_thread_ids`, `status` |
| `web_search` | Web search request | `id`, `query`, `action` |
| `todo_list` | Agent's to-do list | `items[].{text, completed}` |
| `error` | Non-fatal error notification | `message` |

## Two-Level Type Flattening

Codex uses Rust's `#[serde(flatten)]` on the item details, so both the item `id` and the type-specific fields appear at the same level in the JSON. This means an `item.completed` event for a command execution looks like:

```json
{
  "type": "item.completed",
  "item": {
    "id": "item_0",
    "type": "command_execution",
    "command": "bash -lc 'echo hi'",
    "aggregated_output": "hi\n",
    "exit_code": 0,
    "status": "completed"
  }
}
```

Note: `item.type` is the item kind discriminator, while the top-level `type` is the event kind. Both are present in the same JSON object but at different nesting levels.

## Status Enums

### CommandExecutionStatus
`in_progress`, `completed`, `failed`, `declined`

### PatchApplyStatus (file_change)
`in_progress`, `completed`, `failed`

### PatchChangeKind (file_change changes)
`add`, `delete`, `update`

### McpToolCallStatus
`in_progress`, `completed`, `failed`

### CollabToolCallStatus
`in_progress`, `completed`, `failed`

### CollabAgentStatus
`pending_init`, `running`, `completed`, `errored`, `shutdown`, `not_found`

### CollabTool
`spawn_agent`, `send_input`, `wait`, `close_agent`

## Concrete JSON Examples

### thread.started
```json
{"type": "thread.started", "thread_id": "67e55044-10b1-426f-9247-bb680e5fe0c8"}
```

### turn.started
```json
{"type": "turn.started"}
```

### turn.completed
```json
{"type": "turn.completed", "usage": {"input_tokens": 1200, "cached_input_tokens": 200, "output_tokens": 345}}
```

### turn.failed
```json
{"type": "turn.failed", "error": {"message": "boom"}}
```

### error (stream-level)
```json
{"type": "error", "message": "retrying"}
```

### item.completed — agent_message
```json
{"type": "item.completed", "item": {"id": "item_0", "type": "agent_message", "text": "hello"}}
```

### item.completed — reasoning
```json
{"type": "item.completed", "item": {"id": "item_0", "type": "reasoning", "text": "thinking..."}}
```

### item.started — command_execution (in progress)
```json
{"type": "item.started", "item": {"id": "item_0", "type": "command_execution", "command": "bash -lc 'echo hi'", "aggregated_output": "", "exit_code": null, "status": "in_progress"}}
```

### item.completed — command_execution (success)
```json
{"type": "item.completed", "item": {"id": "item_0", "type": "command_execution", "command": "bash -lc 'echo hi'", "aggregated_output": "hi\n", "exit_code": 0, "status": "completed"}}
```

### item.completed — command_execution (failure)
```json
{"type": "item.completed", "item": {"id": "item_0", "type": "command_execution", "command": "sh -c 'exit 1'", "aggregated_output": "", "exit_code": 1, "status": "failed"}}
```

### item.completed — file_change
```json
{"type": "item.completed", "item": {"id": "item_0", "type": "file_change", "changes": [{"path": "a/added.txt", "kind": "add"}, {"path": "b/deleted.txt", "kind": "delete"}, {"path": "c/modified.txt", "kind": "update"}], "status": "completed"}}
```

### item.started — mcp_tool_call
```json
{"type": "item.started", "item": {"id": "item_0", "type": "mcp_tool_call", "server": "server_a", "tool": "tool_x", "arguments": {"key": "value"}, "result": null, "error": null, "status": "in_progress"}}
```

### item.completed — mcp_tool_call (success)
```json
{"type": "item.completed", "item": {"id": "item_0", "type": "mcp_tool_call", "server": "server_a", "tool": "tool_x", "arguments": {"key": "value"}, "result": {"content": [], "structured_content": null}, "error": null, "status": "completed"}}
```

### item.completed — mcp_tool_call (failure)
```json
{"type": "item.completed", "item": {"id": "item_0", "type": "mcp_tool_call", "server": "server_b", "tool": "tool_y", "arguments": {"param": 42}, "result": null, "error": {"message": "tool exploded"}, "status": "failed"}}
```

### item.started — todo_list
```json
{"type": "item.started", "item": {"id": "item_0", "type": "todo_list", "items": [{"text": "step one", "completed": false}, {"text": "step two", "completed": false}]}}
```

### item.updated — todo_list
```json
{"type": "item.updated", "item": {"id": "item_0", "type": "todo_list", "items": [{"text": "step one", "completed": true}, {"text": "step two", "completed": false}]}}
```

## Key Structural Differences from Claude

| Aspect | Claude stream-json | Codex --json |
|---|---|---|
| Top-level type values | `assistant`, `user`, `result` | `thread.started`, `turn.*`, `item.*`, `error` |
| Message nesting | `message.content[]` array with typed blocks | Flat item fields via `#[serde(flatten)]` |
| Tool use reporting | `tool_use` blocks in `assistant` messages | `command_execution` and `file_change` items |
| Tool results | `tool_result` blocks in `user` messages | Included in `item.completed` fields |
| Session ID | `session_id` at top level of every event | `thread_id` in `thread.started` only |
| Completion signal | `type: "result"` with `num_turns`, `is_error` | `turn.completed` with `usage` |
| Error reporting | Non-zero exit code + stderr | `turn.failed` or `error` events |

## Event-to-ExecutorEvent Mapping for Erk

When building a `CodexPromptExecutor`, map Codex events to erk's `ExecutorEvent` union:

| Codex Event | Erk ExecutorEvent |
|---|---|
| `item.completed` + `agent_message` | `TextEvent(content=text)` |
| `item.started` + `command_execution` | `SpinnerUpdateEvent(status=command)` |
| `item.completed` + `command_execution` | `ToolEvent(summary=...)` |
| `item.completed` + `file_change` | `ToolEvent(summary=...)` |
| `item.started` + `mcp_tool_call` | `SpinnerUpdateEvent(status=tool)` |
| `item.completed` + `mcp_tool_call` | `ToolEvent(summary=...)` |
| `turn.failed` | `ErrorEvent(message=...)` |
| `error` | `ErrorEvent(message=...)` |
| PR URLs found in `agent_message` text | `PrUrlEvent`, `PrNumberEvent`, `PrTitleEvent` |
| `thread.started` | (ignored — extract thread_id for logging) |
| `turn.started` | (ignored) |
| `turn.completed` | (ignored — usage tracking only) |
| `item.started/updated` + `todo_list` | `SpinnerUpdateEvent` (optional) |
| `item.completed` + `reasoning` | (ignored or logged) |

## Related Documentation

- [Codex CLI Reference](codex-cli-reference.md) — CLI flags and sandbox modes
- [Claude CLI Stream-JSON Format](../reference/claude-cli-stream-json.md) — Claude's equivalent format
- [PromptExecutor Patterns](../architecture/prompt-executor-patterns.md) — How erk abstracts streaming
```

---

### Document 3: `docs/learned/integrations/codex-skills-system.md`

```markdown
---
title: Codex Skills System
read_when:
  - "porting erk skills to Codex"
  - "understanding Codex skill discovery and invocation"
  - "creating dual-format skills for Claude and Codex"
  - "comparing Claude and Codex skill architectures"
tripwires:
  - action: "assuming Codex custom prompts are the current approach"
    warning: "Custom prompts (~/.codex/prompts/*.md) are the older mechanism, deprecated in favor of skills. Target .codex/skills/ instead."
---

# Codex Skills System

How Codex skills work, verified against `codex-rs/core/src/skills/`. Research date: February 2, 2026.

## Skill Directory Structure

Each skill is a directory containing a `SKILL.md` file:

```
.codex/skills/my-skill/
├── SKILL.md              # Required: YAML frontmatter + instructions
├── scripts/              # Optional: executable code
├── references/           # Optional: additional documentation
├── assets/               # Optional: templates, icons
└── agents/
    └── openai.yaml       # Optional: UI metadata, MCP dependencies
```

## SKILL.md Format

YAML frontmatter is required with `name` and `description`:

```yaml
---
name: my-skill-name
description: What this skill does and when to use it
metadata:
  short-description: Brief one-liner
---

# Skill Instructions

Markdown body with detailed instructions for the agent.
Only loaded when the skill is activated (progressive disclosure).
```

### Frontmatter Validation

Source: `codex-rs/core/src/skills/loader.rs`

| Field | Required | Max Length | Notes |
|---|---|---|---|
| `name` | Yes | 64 chars | Skill identifier |
| `description` | Yes | 1024 chars | Used for implicit matching |
| `metadata.short-description` | No | 1024 chars | Brief description |

### agents/openai.yaml (Optional)

UI metadata and MCP dependencies:

| Field | Type | Description |
|---|---|---|
| `display_name` | string | Human-readable name |
| `short_description` | string | Brief description for UI |
| `icon_small` | path | Small icon file |
| `icon_large` | path | Large icon file |
| `brand_color` | string | Brand color for UI |
| `default_prompt` | string (max 1024) | Default prompt when skill is selected |
| `dependencies.tools[]` | list | MCP tool dependencies (type, value, transport, etc.) |

## Discovery Scopes

Skills are loaded from multiple roots in priority order:

| Scope | Path | Priority |
|---|---|---|
| Repo | `.codex/skills/` (project-level) | Highest |
| User | `$CODEX_HOME/skills/` (user-installed) | |
| System | `$CODEX_HOME/skills/.system/` (embedded) | |
| Admin | `/etc/codex/skills/` (on Unix) | Lowest |

Deduplication: if a skill name appears in multiple scopes, the highest-priority version wins. Skills are sorted by scope priority, then by name.

Scan limits: max depth 6, max 2000 skill directories per root.

## Invocation

### Explicit
- `$skill-name` mention in the prompt text
- `/skills` command menu in TUI

### Implicit
Codex auto-activates skills when the task description matches the skill's `description` field.

### Progressive Disclosure
At session startup, only `name` and `description` are loaded into context (~50 tokens per skill). The full SKILL.md body is loaded only when the skill is invoked (~2-5K tokens). This is different from Claude, which loads all skill content into context.

## Comparison with Claude Skills

| Aspect | Claude Code Skills | Codex Skills |
|---|---|---|
| Location | `.claude/skills/` | `.codex/skills/` |
| File format | `SKILL.md` with optional YAML frontmatter | `SKILL.md` with required YAML frontmatter |
| Required frontmatter | None (content-only is valid) | `name` and `description` required |
| Invocation | `@` references, auto-loaded, hook triggers | `$skill-name` mention, implicit matching |
| Loading behavior | All skills loaded into context at startup | Progressive: metadata at startup, body on invocation |
| Script support | No (instructions only) | Yes (`scripts/` directory for executable code) |
| UI metadata | No | Yes (`agents/openai.yaml`) |
| Scope levels | Repo (`.claude/`) or user (`~/.claude/`) | Repo, user, system, admin (4 levels) |
| Commands | Separate `.claude/commands/` system | Merged into skills (no separate commands) |
| Hooks | PreToolUse, PostToolUse, etc. | Not available |

## Porting Strategy for Erk

Claude's `.claude/skills/` SKILL.md files are structurally compatible with Codex. Key steps for dual-format support:

1. **Ensure frontmatter compatibility**: Codex requires `name` and `description` in YAML frontmatter. Add these to existing erk skills that lack them.

2. **Install to both directories**: When erk installs skills to a project, write to both `.claude/skills/` and `.codex/skills/`.

3. **Handle commands**: Claude has a separate `.claude/commands/` system. Codex merges commands into skills. Erk commands would need to be represented as Codex skills.

4. **Script support**: Codex skills can include `scripts/` with executable code. This could replace some of erk's hook-based behavior.

5. **No hooks in Codex**: Safety-net hooks (like dignified-python injection on `.py` edits) have no Codex equivalent. Bake critical instructions into the skill body or AGENTS.md.

## Slash Command Translation

Claude uses `/erk:plan-implement` to invoke commands. Codex has no slash commands. Options:

- **$skill-name syntax**: Translate `/erk:plan-implement` to a prompt containing `$erk-plan-implement`. Requires the skill to be installed in `.codex/skills/`.
- **Prompt injection**: Read the skill's SKILL.md content and include it in the prompt text directly. More robust but bypasses Codex's skill discovery.

The reliability of `$skill-name` invocation in `codex exec` mode needs testing before committing to an approach.

## Related Documentation

- [Codex CLI Reference](codex-cli-reference.md) — CLI flags and modes
- [Multi-Agent Portability](multi-agent-portability.md) — Broader multi-agent research
```

---

### Document 4: Update `docs/learned/integrations/multi-agent-portability.md`

Add a note after the frontmatter pointing to the new ground-truth docs, and fix the stale Codex information in the Feature Matrix.

**Changes:**

1. After the `---` closing frontmatter, add:

```
> **Updated February 2026**: For ground-truth Codex CLI details verified against source code, see [Codex CLI Reference](codex-cli-reference.md), [Codex JSONL Format](codex-jsonl-format.md), and [Codex Skills System](codex-skills-system.md).
```

2. In the Feature Matrix table (Part 3), update the Codex column:
   - "Command location" → `.codex/skills/` (not `~/.codex/prompts/`)
   - "Namespace syntax" → `$skill-name` (not `/prompts:name`)

3. In "Ease of Support Ranking", update Codex bullet points:
   - Change "Nearly identical command format" to "Skills format is structurally compatible with Claude skills"
   - Change "Same argument syntax" to "SKILL.md uses same markdown + YAML frontmatter pattern"
   - Add: "JSONL streaming format is completely different — requires dedicated parser"
   - Add: "No --system-prompt, --allowedTools, or hooks"

---

### Document 5: Update `docs/learned/architecture/prompt-executor-patterns.md`

Add a "Multi-Backend Design" section at the end, before "Related Topics".

**New section:**

```markdown
## Multi-Backend Design

The `PromptExecutor` ABC is designed to support multiple agent backends. The current sole implementation is `ClaudePromptExecutor`, but the interface is intentionally abstract enough to support others.

### Key Abstraction Points

- **`is_available()`** — Each backend checks for its own binary (`claude`, `codex`, etc.)
- **`execute_interactive()`** — Uses `os.execvp()` to replace the process. The binary name is determined by the executor implementation, not the caller. Callers should use `os.execvp(cmd_args[0], cmd_args)` rather than hardcoding `os.execvp("claude", ...)`.
- **`execute_command_streaming()`** — Each backend has its own JSONL format. The executor parses backend-specific events and yields the common `ExecutorEvent` union types.
- **`execute_prompt()`** — Backend-specific flags (e.g., `--system-prompt` for Claude, which has no Codex equivalent) are handled internally by each executor.

### Leaky Abstraction Warning

Several commands bypass `PromptExecutor` and call the `claude` binary directly via `os.execvp()`. These are tracked for refactoring:
- `src/erk/cli/commands/plan/replan_cmd.py`
- `src/erk/cli/commands/objective/next_plan_cmd.py`
- `src/erk/cli/commands/objective/reconcile_cmd.py`
- `src/erk/core/interactive_claude.py` (helper that builds `["claude", ...]` args)

For multi-backend support, these should route through `PromptExecutor` or a backend-aware arg builder.

### Related Codex Documentation

- [Codex CLI Reference](../integrations/codex-cli-reference.md) — Flag mapping between Claude and Codex
- [Codex JSONL Format](../integrations/codex-jsonl-format.md) — Codex streaming event format
```

---

## Post-Write Steps

1. Run `erk docs sync` to regenerate index files
2. Run `make fast-ci` to validate formatting

## Verification

1. All new docs have valid YAML frontmatter with `title` and `read_when`
2. No embedded function implementations (per learned-docs skill rules) — only JSON format examples and CLI flag tables
3. Cross-references between docs use correct relative paths
4. `erk docs sync` succeeds
5. `make fast-ci` passes