---
title: Multi-Agent Portability Research
read_when:
  - "supporting agents other than Claude Code"
  - "making erk work with OpenCode, Codex, or Copilot"
  - "designing agent-agnostic session tracking"
  - "evaluating spec-driven development tools"
research_date: "2026-01-18"
status: "research - may become outdated"
---

# Multi-Agent Portability Research

**Research Date:** January 18, 2026

**Status:** This document captures point-in-time research. Tool landscapes evolve rapidly - verify current state before implementation.

## Executive Summary

Erk is currently tightly coupled to Claude Code. This research explores:

1. **Spec-driven development tools** (Spec Kit, Tessl, Kiro) that achieve multi-agent support
2. **Emerging standards** (AGENTS.md, Agent Skills) for agent interoperability
3. **Concrete paths** to support additional agents (OpenCode, Codex, Copilot, Gemini)
4. **Session abstraction** for agent-agnostic plan tracking

Key finding: The plan format (GitHub Issues) and `.impl/` folder are already portable. Only the command/skill layer ties erk to Claude Code.

---

## Part 1: Spec-Driven Development Landscape

### GitHub Spec Kit

**Repository:** https://github.com/github/spec-kit

**Philosophy:** "Code serves specifications" - specs are primary, code is generated expression.

**Workflow:**
```
/speckit.specify  → specs/001-feature/spec.md (requirements)
/speckit.plan     → specs/001-feature/plan.md (architecture)
/speckit.tasks    → specs/001-feature/tasks.md (work items)
/speckit.implement → Execute tasks
```

**Multi-agent support:** 18+ agents via `--ai` flag:
```bash
specify init my-project --ai claude    # .claude/commands/
specify init my-project --ai copilot   # .github/agents/
specify init my-project --ai cursor    # .cursor/commands/
specify init my-project --ai gemini    # .gemini/commands/
```

**Key insight:** Specs are portable Markdown files. Commands are generated per-agent as glue code.

### Tessl

**Website:** https://tessl.io/

**Approach:**
- Specs stored in codebase as "long-term memory"
- **Spec Registry** with 10,000+ pre-built specifications
- Plans created before changes, updated during execution
- MCP server mode for agent integration

**Differentiator:** Shared spec registry across projects/teams.

### Kiro (Amazon/AWS)

**Website:** https://kiro.dev/

**Features:**
- VS Code fork with native spec-driven development
- **Persistent context across sessions** via `.kiro/steering/` markdown files
- Three phases: user stories → technical design → trackable tasks
- Autonomous agent can run for hours/days across repos

**Differentiator:** Built-in persistence and Jira/GitHub integration.

### Comparison to Erk

| Aspect | Spec Kit | Tessl | Kiro | Erk |
|--------|----------|-------|------|-----|
| Plan storage | Git repo (`specs/`) | Git repo (`.spec.md`) | `.kiro/` files | GitHub Issues |
| Multi-agent | Yes (18+) | Via MCP | No (Claude only) | No (Claude only) |
| Registry | No | Yes (10k+ specs) | No | No |
| Remote execution | No | No | Yes (autonomous) | Yes (GitHub Actions) |
| Issue lifecycle | Manual | Manual | Jira integration | Auto-close on merge |

---

## Part 2: Emerging Standards

### AGENTS.md

**Website:** https://agents.md

**Adoption:** 60,000+ repos, Linux Foundation stewardship

**Supported agents:** OpenAI Codex, Google Jules, Cursor, Windsurf, GitHub Copilot, Gemini CLI, Devin, VS Code, Aider, and more.

**Purpose:** "README for agents" - separate human docs from agent instructions.

**Format:** Plain Markdown at repo root with project context, build commands, code conventions.

**Note:** Erk already has `AGENTS.md` - this is partially adopted.

### Agent Skills (SKILL.md)

**Repository:** https://github.com/skillmatic-ai/awesome-agent-skills

**Supported platforms:** Claude, OpenAI Codex, GitHub Copilot, Cursor, VS Code, Gemini CLI

**Architecture:** Progressive disclosure
- Discovery (~50 tokens): Lightweight metadata at startup
- Activation (~2-5K tokens): Full instructions when task-relevant
- Execution: Resources loaded dynamically

**Key claim:** "The npm moment for AI agents" - skills work across entire ecosystem.

---

## Part 3: Agent Comparison for Erk Support

### Feature Matrix

| Feature | Claude Code | OpenAI Codex | GitHub Copilot | Gemini CLI | OpenCode |
|---------|-------------|--------------|----------------|------------|----------|
| **Command location** | `.claude/commands/` | `~/.codex/prompts/` | `.github/agents/` | `.gemini/commands/` | `.opencode/commands/` |
| **File format** | Markdown + YAML | Markdown + YAML | Markdown + YAML | **TOML** | Markdown + YAML |
| **Namespace syntax** | `/erk:name` | `/prompts:name` | `@agent-name` | `/namespace:name` | `/name` |
| **Arguments** | `$1`-`$9`, `$NAME` | `$1`-`$9`, `$NAME` | In prompt | In prompt template | `$1`-`$9`, `$NAME` |
| **Config format** | JSON | TOML | VS Code settings | JSON | JSON |
| **AGENTS.md support** | Via CLAUDE.md | Native | Native | Via GEMINI.md | Native |
| **MCP support** | Yes | Yes | Yes | Yes | Yes |
| **Non-interactive** | Yes | Yes | Via GitHub Actions | Yes | Yes (`opencode run`) |
| **Session ID env var** | `CLAUDE_SESSION_ID` | Unknown | Unknown | Unknown | `OPENCODE_SESSION_ID` (plugin) |

### Ease of Support Ranking

1. **OpenAI Codex** - Easiest
   - Nearly identical command format to Claude Code
   - Same argument syntax (`$1`-`$9`, `$NAME`)
   - TOML config (same as Claude)
   - Native AGENTS.md support

2. **OpenCode** - Very Easy
   - Same Markdown + YAML format
   - Same argument patterns
   - Open source (MIT), can inspect/contribute
   - Session ID via plugin (`OPENCODE_SESSION_ID`)

3. **GitHub Copilot** - Moderate
   - Same Markdown format but different schema
   - Multiple instruction formats (AGENTS.md, .instructions.md, copilot-instructions.md)
   - Invocation differs (`@agent-name` not `/command`)
   - Strong GitHub integration (beneficial for erk)

4. **Gemini CLI** - Harder
   - TOML format (not Markdown)
   - Simpler model, less expressive
   - Requires format conversion

### Recommendation

**Start with OpenCode** if prioritizing:
- Open source hedge against vendor lock-in
- MIT license, community-driven
- Session tracking via existing plugin

**Start with Codex** if prioritizing:
- Minimal migration effort
- OpenAI ecosystem alignment
- Same format as Claude Code

---

## Part 4: OpenCode Deep Dive

### Command Format

**Location:** `.opencode/commands/` (project) or `~/.config/opencode/commands/` (global)

**Format:**
```markdown
---
description: Brief explanation
agent: optional_agent_name
model: optional/model-override
subtask: boolean
---

Template content here with $ARGUMENTS, $1, $2 placeholders.
```

**Invocation:** `/command-name` or `/folder/command-name`

### Agent System

**Primary agents:** Main assistants (switch with Tab)
- `Build`: Default, all tools enabled
- `Plan`: Restricted for analysis (writes/bash set to `ask`)

**Subagents:** Invoked via `@agent-name` or by primary agents
- `General`: Research and multi-step tasks
- `Explore`: Fast codebase exploration

**Configuration:** Markdown files in `.opencode/agents/`:
```markdown
---
description: Specialized purpose
mode: subagent
model: provider/model-id
tools:
  write: false
  bash: false
---
System prompt instructions here.
```

### Non-Interactive Mode

Critical for CI/automation:
```bash
# Run single prompt
opencode run "Implement feature X"

# Run specific command
opencode run --command /erk/implement "issue #123"

# JSON output for parsing
opencode run --format json "analyze codebase"

# Attach to running server (faster)
opencode serve &
opencode run --attach http://localhost:4096 "prompt"
```

### Session Tracking

**Plugin required:** `opencode-session-metadata`

**Environment variables injected:**
- `OPENCODE_SESSION_ID`
- `OPENCODE_WORKSPACE_ROOT`
- `OPENCODE_SERVER`

**Storage:** `~/.local/share/opencode/storage/session-metadata/<project-id>/<session-id>.json`

---

## Part 5: Session Abstraction Design

### The Problem

Erk uses `CLAUDE_SESSION_ID` for:
- Linking plans to sessions (`created_from_session` in plan-header)
- Scratch storage paths (`~/.erk/scratch/<session-id>/`)
- Session-aware context in `erk learn`

This is Claude-specific. Need agent-agnostic abstraction.

### Proposed Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SessionRegistry                           │
│  (tries each provider until one returns a session)          │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ ClaudeProvider  │  │ OpenCodeProvider│  │ CodexProvider   │
│                 │  │                 │  │                 │
│ CLAUDE_SESSION_ │  │ OPENCODE_       │  │ CODEX_SESSION_  │
│ ID env var      │  │ SESSION_ID      │  │ ID (hypothetical)│
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### SessionInfo Dataclass

```python
@dataclass(frozen=True)
class SessionInfo:
    """Agent-agnostic session information."""
    id: str
    agent: str  # "claude" | "opencode" | "codex" | "unknown"
    project_path: Path | None
    started_at: datetime | None
    storage_path: Path | None  # Where to find session logs
```

### Provider Protocol

```python
class SessionProvider(Protocol):
    def get_current_session(self) -> SessionInfo | None:
        """Return current session, or None if not in agent context."""
        ...

    @property
    def agent_name(self) -> str:
        """Return the agent name this provider handles."""
        ...
```

### Usage

```python
# Before (Claude-specific)
session_id = os.environ.get("CLAUDE_SESSION_ID")

# After (agent-agnostic)
from erk_shared.session import create_default_registry

registry = create_default_registry()
session = registry.get_current_session()

if session:
    plan_header["created_from_session"] = session.id
    plan_header["created_by_agent"] = session.agent
```

### Plan Schema Update

```yaml
# Current
created_from_session: "abc123"

# Proposed
created_from_session: "abc123"
created_by_agent: "claude"  # or "opencode", "codex"
```

---

## Part 6: Implementation Roadmap

### Phase 1: Abstract Session Layer (2-3 days)

1. Create `SessionInfo` dataclass
2. Create `SessionProvider` protocol
3. Implement `ClaudeSessionProvider`
4. Create `SessionRegistry`
5. Update erk code to use registry

### Phase 2: Command Template System (3-5 days)

1. Create `.erk/templates/` directory structure
2. Define Jinja2 templates for each agent
3. Implement `erk init --agent <name>` command
4. Generate agent-specific command files

### Phase 3: Add OpenCode Support (1 week)

1. Create OpenCode templates
2. Implement `OpenCodeSessionProvider`
3. Document OpenCode prerequisites (session-metadata plugin)
4. Test full workflow: plan → issue → implement → PR

### Phase 4: Documentation and Polish (2-3 days)

1. Update AGENTS.md with multi-agent instructions
2. Create agent-specific quick-start guides
3. Add migration guide for existing users

---

## Part 7: What Gets Lost

### Claude-Specific Features Without Equivalent

| Feature | Claude | Portable Alternative | Gap |
|---------|--------|---------------------|-----|
| Hooks | Automatic context injection | Instructions file (static) | No dynamic injection |
| Plan Mode | `EnterPlanMode` tool | Agent reads `.impl/plan.md` | No approval workflow |
| TodoWrite | Built-in tool | `progress.md` file | Less integrated |
| Extended thinking | Model feature | None | Model-specific |
| Skill triggers | Automatic loading | Explicit `@agent` invocation | Manual |

### Graceful Degradation Strategy

- Claude gets full experience (hooks, session tracking, plan mode)
- Other agents get core workflow (plan → implement → PR)
- Features degrade gracefully, not fail hard

---

## References

### Primary Sources

- [GitHub Spec Kit](https://github.com/github/spec-kit)
- [Spec Kit Blog Post](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/)
- [Tessl](https://tessl.io/)
- [Kiro](https://kiro.dev/)
- [AGENTS.md](https://agents.md)
- [Agent Skills](https://github.com/skillmatic-ai/awesome-agent-skills)

### Agent Documentation

- [OpenCode Commands](https://opencode.ai/docs/commands/)
- [OpenCode Agents](https://opencode.ai/docs/agents/)
- [OpenCode Config](https://opencode.ai/docs/config/)
- [OpenCode Session Metadata Plugin](https://github.com/crayment/opencode-session-metadata)
- [Codex CLI Slash Commands](https://developers.openai.com/codex/cli/slash-commands/)
- [Codex Custom Prompts](https://developers.openai.com/codex/custom-prompts/)
- [GitHub Copilot Custom Agents](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/create-custom-agents)
- [Gemini CLI Custom Commands](https://geminicli.com/docs/cli/custom-commands/)

### Related Erk Documentation

- [Planning Workflow](../planning/workflow.md)
- [Plan Schema](../planning/plan-schema.md)
- [Session Discovery](../architecture/session-discovery.md)
