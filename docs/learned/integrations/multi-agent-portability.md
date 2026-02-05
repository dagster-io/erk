---
title: Claude Code vs Codex CLI Comparison
read_when:
  - "adding Codex support to erk"
  - "understanding differences between Claude Code and Codex CLI"
  - "designing multi-backend agent support"
  - "mapping erk concepts to Codex equivalents"
verified_against_source: "2026-02-02"
codex_source_path: "/Users/schrockn/code/githubs/codex"
status: "verified against Codex source code"
last_audited: "2026-02-05"
audit_result: edited
---

> **Updated February 2026**: For ground-truth Codex CLI details verified against source code, see [Codex CLI Reference](codex/codex-cli-reference.md), [Codex JSONL Format](codex/codex-jsonl-format.md), and [Codex Skills System](codex/codex-skills-system.md).

# Multi-Agent Portability Research

**Verified:** February 2, 2026 against Codex source at `/Users/schrockn/code/githubs/codex`

This document compares Claude Code and OpenAI Codex CLI extensibility models to inform erk's multi-backend support.

---

## Key Architectural Differences

| Aspect               | Claude Code                       | Codex CLI                                          |
| -------------------- | --------------------------------- | -------------------------------------------------- |
| **Language**         | TypeScript (Node.js)              | Rust (native binary)                               |
| **Permission model** | Single axis (`--permission-mode`) | Dual axis (`--sandbox` + `--approval`)             |
| **Session tracking** | `CLAUDE_SESSION_ID` env var       | Internal `ThreadId` (no env var)                   |
| **Programmatic API** | Subprocess only                   | WebSocket app-server, MCP server, Rust lib         |
| **Hooks**            | Tool lifecycle hooks              | Execution policy rules                             |
| **Plan mode**        | Built-in `EnterPlanMode` tool     | No equivalent (agent-managed)                      |
| **Feature flags**    | No                                | Centralized enum (Experimental → Stable lifecycle) |
| **Skill scopes**     | Project only                      | User, Repo, System, Admin                          |
| **Skill metadata**   | Plain markdown                    | Markdown + YAML frontmatter + optional JSON        |

> **Note:** Custom prompts, skills, project instructions, MCP, and non-interactive execution are structurally similar. See each tool's documentation for syntax details.

---

## Permission Model Comparison

Claude Code uses a **single axis** — `--permission-mode`:

| Claude `--permission-mode` | Behavior                                  |
| -------------------------- | ----------------------------------------- |
| `default`                  | Prompt for all tool use                   |
| `acceptEdits`              | Auto-approve file edits, prompt for shell |
| `plan`                     | Read-only exploration mode                |
| `bypassPermissions`        | Skip all permission prompts               |

Codex uses **two orthogonal axes**:

**Sandbox axis** (`--sandbox`):

| Codex `SandboxPolicy` | Behavior                                                     |
| --------------------- | ------------------------------------------------------------ |
| `ReadOnly`            | Read-only filesystem access                                  |
| `WorkspaceWrite`      | Read-only except specified writable roots + optional network |
| `DangerFullAccess`    | No filesystem restrictions                                   |

**Approval axis** (`--approval`):

| Codex `AskForApproval` | Behavior                                   |
| ---------------------- | ------------------------------------------ |
| `UnlessTrusted`        | Auto-approve only known-safe read commands |
| `OnRequest`            | Model decides when to ask (default)        |
| `OnFailure`            | Auto-approve, escalate on failure          |
| `Never`                | Auto-approve all, never escalate           |

**Erk's `PermissionMode` mapping** is defined in `packages/erk-shared/src/erk_shared/context/types.py`. The type uses a simplified four-mode model that maps to both backends:

| Erk `PermissionMode` | Claude              | Codex exec            |
| -------------------- | ------------------- | --------------------- |
| `"safe"`             | `default`           | `--sandbox read-only` |
| `"edits"`            | `acceptEdits`       | `--full-auto`         |
| `"plan"`             | `plan`              | `--sandbox read-only` |
| `"dangerous"`        | `bypassPermissions` | `--yolo`              |

For the complete cross-backend mapping including Codex TUI modes and dual-axis breakdowns, see [Codex CLI Reference](codex/codex-cli-reference.md#permissionsandbox-mapping-for-erk).

> **Note:** The dual-axis model means some Codex configurations have no direct `PermissionMode` equivalent. The mapping above covers erk's use cases.

---

## Extensibility Architecture

### Architectural Differences in Prompt Discovery

Both systems use markdown files as custom prompts/commands and skills. The key architectural differences:

- **Scope model**: Claude scopes prompts to projects only; Codex supports user, repo, system, and admin scopes
- **Skill metadata**: Codex skills declare dependencies and interfaces via YAML frontmatter + JSON; Claude skills are plain markdown
- **Skill injection**: Codex wraps skills in XML tags with metadata; Claude loads raw markdown
- **Project instructions**: Both support hierarchical discovery (`CLAUDE.md` / `AGENTS.md`), but Codex adds a global instructions file and can be disabled via flag/env var

For exact file paths and invocation syntax, see each tool's documentation.

---

## Session Tracking

**Claude Code:**

- Exposes `CLAUDE_SESSION_ID` as environment variable
- Erk reads this directly in hooks and commands
- Simple, reliable

**Codex:**

- Uses internal `ThreadId` (UUID) managed by `ThreadManager`
- **No environment variable exposed**
- Session info emitted as `SessionConfigured` event during execution
- Access options:
  1. Parse `SessionConfigured` event from `codex exec --json` output
  2. Use the app-server WebSocket API
  3. Read rollout state from `~/.codex/` directory
  4. Use resume/fork commands with thread ID

**Implication for erk:** Cannot use the same `os.environ.get()` pattern for Codex. Need either event parsing or app-server integration.

---

## Non-Interactive Execution

**Claude Code:**

```bash
claude -p "prompt"                    # Run prompt, exit
claude -p "prompt" --output-format stream-json  # Structured events
```

**Codex:**

```bash
codex exec "prompt"                   # Run prompt, exit
codex exec --json "prompt"            # Streaming JSONL events
codex -q "prompt"                     # Quiet/non-interactive mode
```

Both support structured event output for programmatic consumption.

**Codex extras:**

- `codex exec --sandbox <mode> --approval <mode>` — per-execution permission control
- `codex resume [SESSION_ID]` — resume previous session
- `codex fork [SESSION_ID]` — fork from previous session
- `codex app-server` — WebSocket API server for IDE/desktop clients

---

## Execution Policy (Codex-Specific)

Codex has a rule-based execution policy system (no Claude equivalent):

- Rules stored in `~/.codex/rules/`
- Heuristic and prefix-based command matching
- Controls which shell commands are auto-approved vs require confirmation
- Managed by `codex_execpolicy` crate

Claude's closest equivalent is the `permissions.allow` list in `~/.claude/settings.json`.

---

## Key Source Files (Codex)

Most-referenced entry points for erk integration work:

| Aspect                    | File                                                  |
| ------------------------- | ----------------------------------------------------- |
| Sandbox/approval policies | `codex-rs/protocol/src/protocol.rs`                   |
| Thread/session management | `codex-rs/core/src/thread_manager.rs`                 |
| Non-interactive execution | `codex-rs/exec/src/cli.rs`                            |
| User instructions         | `codex-rs/core/src/instructions/user_instructions.rs` |
| App server (WebSocket)    | `codex-rs/app-server/src/`                            |

For the complete source tree, browse the [Codex repository](https://github.com/openai/codex) directly.

---

## Implications for Erk Multi-Backend

### What's easy

- **Custom prompts**: Nearly identical format, can generate per-backend
- **Skills**: Both have `SKILL.md` — Codex has richer metadata but same core concept
- **AGENTS.md**: Codex supports it natively (Claude uses CLAUDE.md)
- **Non-interactive execution**: Both support structured event output

### What needs design

- **Permission mapping**: Codex's dual-axis model needs thoughtful mapping from erk's `PermissionMode`
- **Session tracking**: No env var in Codex — need event parsing or API integration
- **Action registry**: Both have commands/prompts but in different locations with different namespace syntax — suggests a declarative registry that generates both
- **TUI integration**: Codex's app-server WebSocket API is a richer integration point than Claude's subprocess-only model
