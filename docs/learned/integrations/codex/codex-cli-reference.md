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

| Mode                  | Invocation            | Claude Equivalent        | Purpose                     |
| --------------------- | --------------------- | ------------------------ | --------------------------- |
| **TUI** (interactive) | `codex [PROMPT]`      | `claude [COMMAND]`       | Interactive terminal UI     |
| **Exec** (headless)   | `codex exec [PROMPT]` | `claude --print COMMAND` | Non-interactive, scriptable |

Key behavioral difference: `codex exec` hardcodes approval policy to `Never` — it never prompts for confirmation. The TUI mode supports configurable approval via `--ask-for-approval`.

## Exec Mode Flags (`codex exec`)

Source: `codex-rs/exec/src/cli.rs`

### Core Flags

| Flag                    | Short | Type       | Description                                                  |
| ----------------------- | ----- | ---------- | ------------------------------------------------------------ |
| `PROMPT`                |       | positional | Prompt text (or `-` to read from stdin)                      |
| `--model`               | `-m`  | string     | Model identifier (e.g., `o3`, `gpt-5.2-codex`)               |
| `--json`                |       | bool       | Output JSONL events to stdout (alias: `--experimental-json`) |
| `--output-last-message` | `-o`  | path       | Write agent's final message to file                          |
| `--cd`                  | `-C`  | path       | Set working directory for the agent                          |
| `--image`               | `-i`  | path[]     | Attach image(s), comma-delimited or repeated                 |
| `--color`               |       | enum       | `auto` (default), `always`, `never`                          |
| `--skip-git-repo-check` |       | bool       | Allow running outside a Git repo                             |
| `--add-dir`             |       | path[]     | Additional writable directories                              |
| `--output-schema`       |       | path       | JSON Schema for structured output                            |
| `--profile`             | `-p`  | string     | Config profile name from config.toml                         |
| `--config`              | `-c`  | key=value  | Override config.toml values (TOML syntax, repeatable)        |

### Sandbox & Permission Flags

| Flag                                         | Short    | Type | Values                                                  |
| -------------------------------------------- | -------- | ---- | ------------------------------------------------------- |
| `--sandbox`                                  | `-s`     | enum | `read-only`, `workspace-write`, `danger-full-access`    |
| `--full-auto`                                |          | bool | Convenience: `--sandbox workspace-write` + auto-approve |
| `--dangerously-bypass-approvals-and-sandbox` | `--yolo` | bool | Skip all confirmations and sandboxing                   |

### Provider Flags

| Flag               | Type   | Description                                     |
| ------------------ | ------ | ----------------------------------------------- |
| `--oss`            | bool   | Use open-source provider (LM Studio, Ollama)    |
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

| Flag                 | Short | Type | Values                                           |
| -------------------- | ----- | ---- | ------------------------------------------------ |
| `--ask-for-approval` | `-a`  | enum | `untrusted`, `on-failure`, `on-request`, `never` |
| `--no-alt-screen`    |       | bool | Run inline, preserving terminal scrollback       |
| `--search`           |       | bool | Enable live web search                           |

**Approval modes explained:**

- `untrusted` — Ask unless command is "trusted" (ls, cat, sed, etc.)
- `on-failure` — Run all commands; ask only on execution failure
- `on-request` — Model decides when to ask for approval
- `never` — Never ask (same as exec default)

## Claude-to-Codex Flag Mapping

| Claude Flag                            | Codex Equivalent             | Notes                                              |
| -------------------------------------- | ---------------------------- | -------------------------------------------------- |
| `--print`                              | (implicit in `codex exec`)   | Exec mode is always non-interactive                |
| `--verbose`                            | (none)                       | Not available                                      |
| `--output-format stream-json`          | `--json`                     | Boolean flag, always JSONL                         |
| `--output-format text`                 | `--output-last-message FILE` | Writes final message to file                       |
| `--permission-mode default`            | `--sandbox read-only`        |                                                    |
| `--permission-mode acceptEdits`        | `--full-auto`                | workspace-write + auto-approve                     |
| `--permission-mode plan`               | `--sandbox read-only`        | No direct plan mode equivalent                     |
| `--permission-mode bypassPermissions`  | `--yolo`                     |                                                    |
| `--dangerously-skip-permissions`       | `--yolo`                     |                                                    |
| `--allow-dangerously-skip-permissions` | (none)                       | No equivalent — Codex uses explicit sandbox levels |
| `--model MODEL`                        | `--model MODEL`              | Same concept                                       |
| `--system-prompt TEXT`                 | **NOT AVAILABLE**            | Must prepend to user prompt                        |
| `--allowedTools TOOLS`                 | **NOT AVAILABLE**            | No tool restriction in Codex                       |
| `--no-session-persistence`             | **NOT AVAILABLE**            | Sessions always persist to `~/.codex/threads/`     |
| `--max-turns N`                        | **NOT AVAILABLE**            | No turn limit flag                                 |
| `cwd` (subprocess arg)                 | `--cd DIR`                   | Explicit flag in Codex                             |

## Permission/Sandbox Mapping for Erk

How erk's planned `SandboxMode` maps to both backends:

| Erk SandboxMode | Claude `--permission-mode`         | Codex exec            | Codex TUI                                 |
| --------------- | ---------------------------------- | --------------------- | ----------------------------------------- |
| `safe`          | `default`                          | `--sandbox read-only` | `--sandbox read-only -a untrusted`        |
| `edits`         | `acceptEdits`                      | `--full-auto`         | `--sandbox workspace-write -a on-request` |
| `plan`          | `plan`                             | `--sandbox read-only` | `--sandbox read-only -a never`            |
| `dangerous`     | + `--dangerously-skip-permissions` | `--yolo`              | `--yolo`                                  |

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
