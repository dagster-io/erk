---
audit_result: edited
last_audited: '2026-02-08'
read_when:
- implementing Codex backend support in erk
- mapping PermissionMode to Codex sandbox flags
- building a CodexPromptExecutor or Codex-aware AgentLauncher
- understanding Claude CLI features that have no Codex equivalent
title: Codex CLI Reference for Erk Integration
tripwires:
- action: using --ask-for-approval with codex exec
  warning: codex exec hardcodes approval to Never. Only the TUI supports --ask-for-approval.
    This means exec and TUI need different flag sets for the same PermissionMode.
- action: using --system-prompt or --allowedTools with codex
  warning: Codex has no --system-prompt or --allowedTools. Prepend system prompt to
    user prompt. Tool restriction is not available — this affects execute_prompt()
    porting.
- action: using --output-format with codex
  warning: Codex has no --output-format. Use --json (boolean flag) for JSONL. Without
    --json, output goes to terminal. This affects execute_command_streaming() porting.
- action: using --print or --verbose with codex
  warning: codex exec is always headless (no --print needed). No --verbose flag exists.
- action: passing cwd as subprocess kwarg for codex
  warning: Unlike Claude (which uses subprocess cwd=), Codex requires an explicit
    --cd flag. Forgetting this means the agent runs in the wrong directory.
---

# Codex CLI Reference for Erk Integration

Ground-truth reference for how OpenAI's Codex CLI maps to erk's abstractions. Verified against https://github.com/openai/codex (Rust, Apache-2.0). Research date: February 2, 2026.

This document focuses on **integration decisions** — the flag gaps, behavioral mismatches, and design constraints that matter when porting erk's Claude-oriented abstractions to Codex. For exhaustive flag listings, run `codex exec --help` or `codex --help`.

## Two Execution Modes

Codex has two modes that map to erk's two launch patterns:

| Codex Mode              | Erk Abstraction                                 | Key Behavioral Difference                                  |
| ----------------------- | ----------------------------------------------- | ---------------------------------------------------------- |
| **TUI** (`codex`)       | `AgentLauncher.launch_interactive()` via execvp | Supports `--ask-for-approval` with 4 approval levels       |
| **Exec** (`codex exec`) | `PromptExecutor.execute_command_streaming()`    | Hardcodes approval to Never — no confirmation prompts ever |

**Why this matters:** The same `PermissionMode.edits` produces different Codex flags depending on mode. Exec uses `--full-auto`, but TUI uses `--sandbox workspace-write -a on-request`. This forces any future `permission_mode_to_codex()` to take a `mode: Literal["exec", "tui"]` parameter — unlike `permission_mode_to_claude()` which is mode-independent.

## Sandbox Model vs Permission Model

Claude and Codex have fundamentally different security philosophies, which is why the `PermissionMode` mapping isn't always clean:

- **Claude**: Permission-based. A single `--permission-mode` controls a behavior spectrum from "prompt for everything" to "bypass all prompts." The `--dangerously-skip-permissions` flag is a separate escalation layer on top.

- **Codex**: Sandbox-based with two orthogonal axes. `--sandbox` controls filesystem access levels (`read-only`, `workspace-write`, `danger-full-access`). Approval policy (`-a`) is independent — you can have a writable sandbox that still prompts for confirmation.

**Why this matters for erk:** The `PermissionMode` abstraction was designed around Claude's single-axis permission model. Codex's two-axis model (sandbox level x approval policy) doesn't map cleanly to a single enum value. The mapping table below is the resolved decision, but implementers should understand the underlying mismatch to avoid surprise when behaviors diverge.

## PermissionMode Cross-Backend Mapping

This is the single source of truth for how erk's `PermissionMode` enum maps to both backends. The Claude side is implemented in code.

<!-- Source: packages/erk-shared/src/erk_shared/context/types.py, _PERMISSION_MODE_TO_CLAUDE -->

See `_PERMISSION_MODE_TO_CLAUDE` and `permission_mode_to_claude()` in `packages/erk-shared/src/erk_shared/context/types.py` for the current Claude mapping implementation.

| Erk PermissionMode | Claude                             | Codex exec            | Codex TUI                                 |
| ------------------ | ---------------------------------- | --------------------- | ----------------------------------------- |
| `safe`             | `default`                          | `--sandbox read-only` | `--sandbox read-only -a untrusted`        |
| `edits`            | `acceptEdits`                      | `--full-auto`         | `--sandbox workspace-write -a on-request` |
| `plan`             | `plan`                             | `--sandbox read-only` | `--sandbox read-only -a never`            |
| `dangerous`        | + `--dangerously-skip-permissions` | `--yolo`              | `--yolo`                                  |

### Lossy Mappings

**`plan` → `read-only` is lossy.** Claude's `plan` mode has special agent behavior (explore and plan but don't implement). Codex has no plan mode concept — `--sandbox read-only` prevents writes but doesn't signal planning intent to the agent. Codex TUI adds `-a never` to suppress approval prompts, matching plan mode's non-interactive exploration, but the agent itself doesn't know it's in "plan mode."

**`dangerous` collapses two Claude flags into one.** Claude requires both `--permission-mode bypassPermissions` and `--dangerously-skip-permissions` (see [PermissionMode Abstraction](../../architecture/permission-modes.md) for why both are needed). Codex's `--yolo` handles both concepts in a single flag.

## Claude Features Missing from Codex

These gaps shape the design of erk's Codex integration. Each gap represents a decision point for porting.

| Claude Feature                         | Codex Status                 | Design Impact                                                                                |
| -------------------------------------- | ---------------------------- | -------------------------------------------------------------------------------------------- |
| `--system-prompt`                      | Not available                | Prompt construction becomes backend-aware — must prepend to user prompt                      |
| `--allowedTools`                       | Not available                | No tool restriction — Codex agents access all tools unconditionally                          |
| `--output-format stream-json`          | `--json` (boolean)           | Completely different JSONL event format (see [codex-jsonl-format.md](codex-jsonl-format.md)) |
| `--output-format text`                 | `--output-last-message FILE` | Codex writes to file instead of stdout — must read file after execution                      |
| `--no-session-persistence`             | Not available                | Codex always persists to `~/.codex/threads/`; no way to disable                              |
| `--max-turns`                          | Not available                | Must implement timeout/kill at the subprocess level                                          |
| `--verbose`                            | Not available                | No verbose mode for debugging                                                                |
| `--allow-dangerously-skip-permissions` | Not available                | Codex uses explicit sandbox levels instead of layered permission escalation                  |
| `cwd` (subprocess kwarg)               | `--cd DIR` flag              | Working directory must be a CLI flag, not a subprocess parameter                             |

**The `--system-prompt` gap is the most impactful.** The `PromptExecutor.execute_prompt()` ABC takes a `system_prompt` parameter that Claude implements via `--system-prompt` to replace the default system prompt for automation tasks. Codex has no equivalent — system instructions must be prepended to the user prompt, making the prompt construction layer backend-aware.

**The `--cd` difference is a subtle bug source.** Claude uses the subprocess `cwd=` kwarg and ignores `--cd`. Codex requires `--cd` explicitly — passing only `cwd=` to the subprocess means the Codex agent runs in the wrong directory while the subprocess itself is in the right one. A future `build_codex_args()` must always emit `--cd`.

## TUI Launch Differences

<!-- Source: packages/erk-shared/src/erk_shared/gateway/agent_launcher/real.py, build_claude_args -->

When building a Codex-aware `AgentLauncher` (parallel to `build_claude_args()` in `packages/erk-shared/src/erk_shared/gateway/agent_launcher/real.py`), these behavioral differences matter:

1. **No slash commands.** Claude's TUI accepts `/erk:plan-implement` as a positional command argument. Codex has no slash command system — prompt text is positional. Skills must be installed to `.codex/skills/` and invoked via `$skill-name` in the prompt. See [Codex Skills System](codex-skills-system.md) for the porting strategy.

2. **Working directory is a flag, not a subprocess kwarg.** Claude infers cwd from `os.chdir()` before `os.execvp()`. Codex requires `--cd` explicitly.

3. **Approval is TUI-only.** The `-a` / `--ask-for-approval` flag only exists in TUI mode. A `build_codex_args()` function must know which mode it's building for, unlike Claude where arg construction is mode-independent.

## Skill Portability

Not all erk skills can run on Codex. Skills referencing Claude-specific features (hooks, session logs, Claude Code commands) cannot be ported.

<!-- Source: src/erk/core/capabilities/codex_portable.py, codex_portable_skills -->

See `codex_portable_skills()` and `claude_only_skills()` in `src/erk/core/capabilities/codex_portable.py` for the canonical registry of which skills are portable vs Claude-only.

The `.codex/skills/` directory mapping is handled by the bundled artifact system.

<!-- Source: src/erk/artifacts/paths.py, get_bundled_codex_dir -->

See `get_bundled_codex_dir()` in `src/erk/artifacts/paths.py` for how editable vs wheel installs resolve the `.codex/` skill directory. In editable mode, `.claude/` is reused directly since the skill file format is identical between backends.

## Related Documentation

- [Codex JSONL Format](codex-jsonl-format.md) — Streaming event format (completely different from Claude's stream-json)
- [Codex Skills System](codex-skills-system.md) — Skill discovery, invocation, and porting strategy
- [PermissionMode Abstraction](../../architecture/permission-modes.md) — The enum and its Claude mapping implementation
- [PromptExecutor Patterns](../../architecture/prompt-executor-patterns.md) — Multi-backend design and leaky abstraction tracking
