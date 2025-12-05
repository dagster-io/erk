# Claude CLI Integration Patterns Documentation

## Objective

Document patterns for invoking Claude Code CLI from Python code and clarify when agent commands vs pure Python CLI commands are appropriate.

## Source Information

- **Session ID(s):** 42a1ff36-66b7-45e4-930d-572e375d5d19
- **Context:** Planning session for extending erk pr land with extraction plan creation

## Documentation Items

### A1. Claude CLI Invocation from Python

**Type:** Category A (Learning Gap)
**Location:** `docs/agent/architecture/claude-cli-integration.md`
**Routing:** `| Invoke Claude from Python | → [docs/agent/architecture/claude-cli-integration.md](docs/agent/architecture/claude-cli-integration.md) |`
**Action:** New doc
**Priority:** High
**Effort:** Medium

**Why needed:** Session required exploring `RealClaudeCliOps` pattern to understand how to spawn Claude CLI from Python. This pattern is used in `dot-agent run command execute` but not documented for reuse.

**Draft content:**

```markdown
# Claude CLI Integration from Python

## Overview

When erk CLI commands need Claude AI capabilities (analysis, generation, etc.), they can spawn Claude Code CLI as a subprocess. This document covers the patterns for doing so.

## When to Spawn Claude CLI

Use this pattern when:
- Your Python CLI command needs AI analysis (e.g., categorizing documentation gaps)
- The operation requires Claude's reasoning capabilities
- You want to reuse existing agent commands from Python code

Do NOT use this pattern when:
- Pure Python logic suffices (parsing, file operations, git commands)
- You're already inside a Claude Code session (use tools directly)

## Non-Interactive Mode (`--print`)

For automated/scripted execution where no user interaction is needed:

```python
import subprocess

result = subprocess.run(
    [
        "claude",
        "--print",
        "--verbose",
        "--permission-mode", "bypassPermissions",
        "--output-format", "stream-json",
        "/erk:my-command",
    ],
    cwd=working_directory,
)

if result.returncode \!= 0:
    # Handle failure
    raise SystemExit(1)
```

Key flags:
- `--print`: Non-interactive, runs command and exits
- `--verbose`: Required for stream-json with --print
- `--permission-mode bypassPermissions`: Skip permission prompts
- `--output-format stream-json`: JSONL output for parsing

## Interactive Mode

For operations requiring user input during execution:

```python
result = subprocess.run(
    ["claude", "/erk:my-command"],
    cwd=working_directory,
)
```

Use interactive mode when:
- User needs to make selections during execution
- Confirmation prompts are required
- The agent command has multi-step user interaction

## Reference Implementation

See `packages/dot-agent-kit/src/dot_agent_kit/data/kits/command/kit_cli_commands/command/ops.py`:
- `RealClaudeCliOps`: Production implementation with streaming output
- `FakeClaudeCliOps`: Test double for unit testing
```

---

### A2. Agent Command vs CLI Command Boundaries

**Type:** Category A (Learning Gap)
**Location:** `docs/agent/architecture/command-boundaries.md`
**Routing:** `| Agent vs CLI command | → [docs/agent/architecture/command-boundaries.md](docs/agent/architecture/command-boundaries.md) |`
**Action:** New doc
**Priority:** High
**Effort:** Quick

**Why needed:** Session had back-and-forth about whether extraction analysis could be pure Python or needed Claude. The boundary between agent commands (require AI) and CLI commands (pure Python) isn't documented.

**Draft content:**

```markdown
# Agent Command vs CLI Command Boundaries

## Overview

Erk has two types of commands:
1. **Agent commands** (`.claude/commands/`) - Markdown files executed by Claude Code
2. **CLI commands** (`src/erk/cli/`) - Python Click commands

This document clarifies when to use each.

## Use Agent Commands When

The operation requires:
- **Natural language analysis** - Categorizing, summarizing, understanding intent
- **Code generation** - Writing new code based on context
- **Documentation extraction** - Identifying gaps, generating suggestions
- **Multi-step reasoning** - Complex decision trees based on context
- **Codebase exploration** - Understanding patterns, finding related code

Examples:
- `/erk:create-extraction-plan` - Analyzes sessions for documentation gaps
- `/erk:craft-plan` - Creates implementation plans from requirements

## Use CLI Commands When

The operation is:
- **Deterministic** - Same input always produces same output
- **Data transformation** - Parsing, formatting, converting
- **External tool orchestration** - Git, GitHub CLI, Graphite
- **File system operations** - Creating, moving, deleting files
- **State management** - Tracking worktrees, branches, issues

Examples:
- `erk pr land` - Merges PR, deletes worktree (deterministic git operations)
- `erk wt create` - Creates worktree (git operations)
- `dot-agent run erk create-extraction-plan` - Creates GitHub issue (API call)

## Hybrid Pattern: CLI Spawning Agent

When a CLI command needs AI capabilities:

1. CLI handles prerequisites and validation (Python)
2. CLI spawns `claude --print /agent-command` for AI work
3. CLI handles results and cleanup (Python)

Example: `erk pr land` could spawn `/erk:land-extraction` for AI-based session analysis, then continue with deterministic cleanup.

## Decision Tree

```
Does operation require understanding/generating natural language?
├─ Yes → Agent command
└─ No → Does it require reasoning about code semantics?
         ├─ Yes → Agent command
         └─ No → CLI command (may spawn agent if needed)
```
```