---
title: Agent Command vs CLI Command Boundaries
read_when:
  - "deciding between agent command vs CLI command"
  - "determining when to use AI vs pure Python"
  - "designing hybrid commands"
  - "understanding command type trade-offs"
---

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
- **Plan creation** - Designing implementation approaches from requirements
- **Context enrichment** - Adding insights and discoveries to existing content

Examples:

- `/erk:create-extraction-plan` - Analyzes sessions for documentation gaps
- `/erk:craft-plan` - Creates implementation plans from requirements
- `/erk:plan-implement` - Executes implementation plans with AI guidance

## Use CLI Commands When

The operation is:

- **Deterministic** - Same input always produces same output
- **Data transformation** - Parsing, formatting, converting
- **External tool orchestration** - Git, GitHub CLI, Graphite
- **File system operations** - Creating, moving, deleting files
- **State management** - Tracking worktrees, branches, issues
- **API calls** - GitHub API, other external services
- **Validation** - Checking prerequisites, verifying state

Examples:

- `erk pr land` - Merges PR, deletes worktree (deterministic git operations)
- `erk wt create` - Creates worktree (git operations)
- `dot-agent run erk create-extraction-plan` - Creates GitHub issue (API call)
- `erk checkout` - Switches to worktree (file system + git)

## Hybrid Pattern: CLI Spawning Agent

When a CLI command needs AI capabilities:

1. CLI handles prerequisites and validation (Python)
2. CLI spawns `claude --print /agent-command` for AI work
3. CLI handles results and cleanup (Python)

Example: `erk pr land` could spawn `/erk:land-extraction` for AI-based session analysis, then continue with deterministic cleanup.

See [Claude CLI Integration](claude-cli-integration.md) for implementation patterns.

## Decision Tree

```
Does operation require understanding/generating natural language?
├─ Yes → Agent command
└─ No → Does it require reasoning about code semantics?
         ├─ Yes → Agent command
         └─ No → CLI command (may spawn agent if needed)
```

## Detailed Comparison

| Aspect               | Agent Command                              | CLI Command                                                          |
| -------------------- | ------------------------------------------ | -------------------------------------------------------------------- |
| **Implementation**   | Markdown file in `.claude/commands/`       | Python function with `@click.command()`                              |
| **Execution**        | Via Claude Code CLI (`claude /command`)    | Via erk CLI (`erk command`) or kit CLI (`dot-agent run erk command`) |
| **AI Capabilities**  | Full access to Claude's reasoning          | None (unless spawns agent)                                           |
| **File I/O**         | Via Claude tools (Read, Write, Edit)       | Direct Python `pathlib` operations                                   |
| **Error Handling**   | Claude's conversation-based error recovery | Python exceptions and error codes                                    |
| **User Interaction** | Natural language conversation              | CLI prompts and flags                                                |
| **Testing**          | Manual or integration tests                | Unit tests with fakes                                                |
| **Performance**      | Slower (AI inference)                      | Fast (pure Python)                                                   |
| **Cost**             | API tokens                                 | Free (local execution)                                               |
| **Determinism**      | Non-deterministic (AI varies)              | Deterministic (same input → same output)                             |

## Real-World Examples

### Example 1: Documentation Gap Analysis

**Task**: Analyze session logs to identify documentation gaps

**Why agent command?**

- Requires understanding conversation context
- Needs to categorize gaps by type (learning, reminder, clarification)
- Must reason about which gaps are worth documenting
- Generates natural language summaries

**Implementation**: `/erk:create-extraction-plan` (agent command)

### Example 2: Create GitHub Issue from Plan

**Task**: Take an extraction plan and create a GitHub issue

**Why CLI command?**

- Deterministic API call to GitHub
- Requires authentication and error handling
- Needs to format JSON for GitHub API
- No AI reasoning required

**Implementation**: `dot-agent run erk create-extraction-plan` (kit CLI command)

### Example 3: Implement a Plan

**Task**: Execute implementation steps from a plan file

**Why agent command?**

- Requires code generation based on plan
- Needs to reason about implementation approach
- Must adapt to discovered complexity
- Provides conversational progress updates

**Implementation**: `/erk:plan-implement` (agent command)

### Example 4: Merge PR and Clean Up Worktree

**Task**: Merge a PR using gh CLI, then delete the worktree

**Why CLI command?**

- Deterministic sequence of git and gh commands
- No AI reasoning needed
- Fast execution required
- Clear error conditions

**Implementation**: `erk pr land` (CLI command)

### Example 5: Session Log Analysis with Cleanup

**Task**: Analyze session for insights, then archive logs

**Why hybrid?**

- Analysis requires AI (agent)
- Archiving is deterministic (CLI)

**Implementation**:

```python
# CLI command
def analyze_and_archive(session_id: str) -> int:
    # Phase 1: AI analysis (spawn agent)
    result = subprocess.run(
        ["claude", "--print", "/erk:analyze-session"],
        cwd=f".erk/sessions/{session_id}",
    )
    if result.returncode != 0:
        return 1

    # Phase 2: Deterministic archiving (Python)
    session_dir = Path(f".erk/sessions/{session_id}")
    archive_dir = Path(".erk/archives")
    shutil.move(session_dir, archive_dir / session_id)

    return 0
```

## Guidelines for New Commands

When creating a new command, ask:

1. **Does it need to understand code semantics or natural language?**
   - Yes → Agent command
   - No → Continue

2. **Does it need to generate code or documentation?**
   - Yes → Agent command
   - No → Continue

3. **Is the operation deterministic?**
   - Yes → CLI command
   - No → Agent command

4. **Does it orchestrate external tools (git, gh, etc)?**
   - Yes → CLI command
   - No → Continue

5. **Would a hybrid approach (CLI + agent) work better?**
   - Consider splitting: CLI for orchestration, agent for AI work

## Anti-Patterns

### ❌ Anti-Pattern 1: AI for Deterministic Operations

```markdown
<!-- BAD: Agent command for simple file copy -->

# /copy-file

Copy source.txt to dest.txt using the Write tool.
```

**Why bad?** No AI reasoning needed. Pure file operation.

**Better**: CLI command with `shutil.copy()`

### ❌ Anti-Pattern 2: Python for Complex Reasoning

```python
# BAD: CLI command trying to categorize documentation gaps
def categorize_gaps(session_log: str) -> list[str]:
    # Trying to parse natural language with regexes
    if "I don't understand" in session_log:
        return ["learning-gap"]
    # This will never work well
```

**Why bad?** Natural language understanding requires AI.

**Better**: Agent command with Claude's reasoning

### ❌ Anti-Pattern 3: Agent for API Calls

```markdown
<!-- BAD: Agent command for GitHub API -->

# /create-issue

Use the Bash tool to call `gh issue create` with the title and body.
```

**Why bad?** Deterministic API call with known parameters.

**Better**: CLI command calling `gh` directly

### ❌ Anti-Pattern 4: Duplicate Logic

```python
# BAD: Reimplementing agent logic in Python
def create_implementation_plan(requirements: str) -> str:
    # Trying to replicate what /erk:craft-plan does
    plan = f"## Objective\n{requirements}\n## Steps\n..."
    return plan
```

**Why bad?** Duplicates agent command logic, loses AI reasoning.

**Better**: Spawn `/erk:craft-plan` from CLI command (hybrid pattern)

## Migration Path

If you have an existing command in the wrong category:

### Agent → CLI Migration

1. Verify operation is truly deterministic
2. Implement Python logic with proper error handling
3. Add unit tests with fakes
4. Update documentation and routing
5. Remove agent command

### CLI → Agent Migration

1. Create agent command with clear instructions
2. Test with various inputs
3. Update documentation and routing
4. Archive CLI command (keep for reference)

### CLI → Hybrid Migration

1. Identify AI vs deterministic portions
2. Extract AI work into agent command
3. Update CLI to spawn agent for AI work
4. Keep CLI orchestration and cleanup

## Related Documentation

- [Claude CLI Integration](claude-cli-integration.md) - How to spawn Claude from Python
- [CLI Development Guide](../cli/index.md) - Python CLI command patterns
- [Commands Guide](../commands/index.md) - Agent command best practices
