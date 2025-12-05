---
title: Agent Command vs CLI Command Boundaries
read_when:
  - "deciding between agent and CLI commands"
  - "understanding command boundaries"
  - "choosing implementation approach"
---

# Agent Command vs CLI Command Boundaries

## Overview

Erk has two types of commands:

1. **Agent commands** (`.claude/commands/`) - Markdown files executed by Claude Code
2. **CLI commands** (`src/erk/cli/`) - Python Click commands

This document clarifies when to use each and how they can work together.

## Use Agent Commands When

The operation requires:

### Natural Language Analysis

- Categorizing content (documentation gaps, error types)
- Summarizing large text or code
- Understanding intent or semantics
- Extracting meaning from unstructured data

**Examples:**

- `/erk:create-extraction-plan` - Analyzes sessions for documentation gaps
- `/erk:craft-plan` - Creates implementation plans from requirements

### Code Generation

- Writing new code based on context
- Generating boilerplate or templates
- Creating documentation from code
- Synthesizing code from specifications

### Documentation Extraction

- Identifying gaps in documentation
- Generating suggestions from experience
- Creating structured docs from conversations
- Extracting patterns from multiple sources

### Multi-Step Reasoning

- Complex decision trees based on context
- Evaluating trade-offs between approaches
- Planning with multiple considerations
- Context-dependent logic that can't be easily codified

### Codebase Exploration

- Understanding patterns across files
- Finding related code
- Analyzing architecture
- Discovering implicit relationships

## Use CLI Commands When

The operation is:

### Deterministic

- Same input always produces same output
- Logic can be expressed as explicit conditions
- No interpretation or judgment required
- Testable with fixed expectations

**Examples:**

- `erk pr land` - Merges PR, deletes worktree (fixed git operations)
- `erk wt create` - Creates worktree (deterministic git commands)

### Data Transformation

- Parsing structured data (JSON, YAML, TOML)
- Formatting or converting between formats
- Filtering or sorting data
- Validating input against schema

### External Tool Orchestration

- Running git commands
- Calling GitHub CLI (gh)
- Executing Graphite CLI (gt)
- Coordinating multiple tools

### File System Operations

- Creating, moving, deleting files/directories
- Reading or writing configuration
- Managing worktree structure
- Handling path operations

### State Management

- Tracking worktrees
- Managing branches
- Recording issue associations
- Maintaining metadata

## Hybrid Pattern: CLI Spawning Agent

When a CLI command needs AI capabilities, use this pattern:

### Pattern Structure

1. **CLI handles prerequisites** (Python)
   - Validate inputs
   - Check preconditions
   - Gather context
2. **CLI spawns agent command** (Claude)
   - Pass necessary context
   - Let agent perform AI work
   - Capture results
3. **CLI handles results and cleanup** (Python)
   - Parse agent output
   - Update state
   - Perform deterministic follow-up

### Example: Hypothetical Enhancement

```python
# erk pr land (CLI command)
@click.command("land")
@click.pass_obj
def land(ctx: ErkContext) -> None:
    """Land PR and optionally create extraction plan."""

    # 1. CLI: Validate and gather context
    pr_number = get_current_pr_number(ctx)
    if pr_number is None:
        click.echo("Error: No PR found", err=True)
        raise SystemExit(1)

    # 2. Agent: Analyze sessions for doc gaps (if .impl/ exists)
    impl_dir = ctx.repo_root / ".impl"
    if impl_dir.exists():
        # Spawn Claude to analyze sessions
        run_subprocess_with_context(
            [
                "claude",
                "--print",
                "--verbose",
                "--permission-mode", "bypassPermissions",
                f"/erk:analyze-sessions-for-extraction {pr_number}",
            ],
            operation_context="analyze sessions for documentation extraction",
            cwd=ctx.repo_root,
        )

    # 3. CLI: Deterministic cleanup
    ctx.github.merge_pr(pr_number)
    ctx.git.delete_worktree(ctx.current_worktree_path)
```

### When to Use This Pattern

- CLI command encounters situation requiring judgment
- Analysis or generation needed mid-workflow
- User wants optional AI enhancement
- Deterministic operations surround AI work

## Decision Tree

```
Does operation require understanding/generating natural language?
├─ Yes → Agent command
└─ No → Does it require reasoning about code semantics?
         ├─ Yes → Agent command
         └─ No → Can it be expressed as explicit conditions?
                  ├─ Yes → CLI command
                  └─ No → Does it need to work without AI?
                           ├─ Yes → CLI command (may spawn agent)
                           └─ No → Agent command
```

## Examples by Type

### Agent Commands

| Command                        | Why Agent?                       |
| ------------------------------ | -------------------------------- |
| `/erk:create-extraction-plan`  | NL analysis of session content   |
| `/erk:craft-plan`              | Multi-step reasoning for plans   |
| `/erk:plan-implement`          | Code generation + reasoning      |
| `/erk:sessions-list`           | May involve filtering by meaning |

### CLI Commands

| Command           | Why CLI?                      |
| ----------------- | ----------------------------- |
| `erk wt create`   | Deterministic git operations  |
| `erk pr land`     | Fixed workflow of git + gh    |
| `erk checkout`    | Path resolution + git         |
| `erk pr check`    | Validate against known rules  |

### Hybrid (CLI spawning Agent)

| Command (Hypothetical)          | CLI Part                     | Agent Part              |
| ------------------------------- | ---------------------------- | ----------------------- |
| `erk pr land --extract-docs`    | Merge, delete worktree       | Session analysis        |
| `erk plan enhance`              | Load plan, save output       | Plan improvement        |
| `erk sessions summarize <IDs>`  | Validate IDs, format output  | Generate summary        |

## Testing Implications

### Agent Commands

- Manual testing (run via Claude Code)
- End-to-end validation
- Hard to unit test (AI behavior varies)
- Focus on output format validation

### CLI Commands

- Unit tests with fakes
- Integration tests with real git/gh
- Test coverage requirements
- Deterministic assertions

### Hybrid

- Mock agent subprocess call in tests
- Validate context passed to agent
- Test CLI logic independently
- E2E tests for full workflow

## Cost Considerations

### Agent Commands

- Incur LLM API costs
- Slower (network latency + inference)
- Variable performance
- May require retries

### CLI Commands

- No LLM costs
- Fast execution
- Predictable performance
- Reliable

Choose CLI when possible to minimize cost and maximize speed.

## Related Topics

- [Claude CLI Integration](claude-cli-integration.md) - How to spawn Claude from Python
- [Subprocess Wrappers](subprocess-wrappers.md) - Error handling patterns
- [Erk Architecture](erk-architecture.md) - Overall system design
