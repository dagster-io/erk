---
title: Tool Restriction Safety Pattern
read_when:
  - implementing slash commands with safety constraints, designing read-only commands, creating commands that work in plan mode
---

# Tool Restriction Safety Pattern

The `allowed-tools` frontmatter field restricts which tools a command can use, enabling safe read-only operations that work within plan mode or other restricted contexts.

## Pattern Purpose

**Problem**: Some commands should be safe to use in plan mode (before implementation) or in contexts where code modification would be inappropriate.

**Solution**: Use `allowed-tools` frontmatter to enforce tool restrictions at the command level.

## Frontmatter Syntax

```yaml
---
description: Command description here
allowed-tools: AskUserQuestion, Read, Glob, Grep
---
```

**Effect**: The command can ONLY use the listed tools. Any attempt to use other tools (Write, Edit, Bash with mutations, etc.) will fail.

## Use Case: /local:interview

**File**: `.claude/commands/local/interview.md`

**Frontmatter**:

```yaml
---
description: Interview user in-depth to gather requirements for a plan or objective
allowed-tools: AskUserQuestion, Read, Glob, Grep
---
```

**Purpose**: Gather requirements through conversation and codebase exploration WITHOUT writing code.

**Why tool restrictions**:

1. **Plan mode compatibility**: Can be used within plan mode to gather context before planning
2. **Read-only guarantee**: Cannot accidentally modify files or execute destructive commands
3. **Clear scope**: Interview agent asks questions and searches code, nothing more

### Workflow: Interview → Gather → Plan

```markdown
User: "I want to add authentication to the app"

Agent: "Let me interview you about this feature"

SlashCommand(command="/local:interview authentication feature")

[Interview agent launches with tool restrictions]

Interview Agent (with only Read, Glob, Grep, AskUserQuestion):

- Searches for existing auth patterns in codebase
- Asks user: "Do you prefer OAuth, JWT, or session-based auth?"
- Asks user: "Where should tokens be stored?"
- Documents requirements from conversation

[Interview completes, returns to main conversation]

Agent: "Now I'll create a plan incorporating your preferences"
[Enters plan mode with gathered context]
```

## Tool Categories

### Read-Only Tools (Safe for Restrictions)

| Tool              | Purpose                  | Why Safe         |
| ----------------- | ------------------------ | ---------------- |
| `Read`            | Read files               | No modifications |
| `Glob`            | Find files by pattern    | No modifications |
| `Grep`            | Search file contents     | No modifications |
| `AskUserQuestion` | Ask clarifying questions | No code changes  |

### Write Tools (Typically Excluded)

| Tool    | Purpose                | Why Excluded          |
| ------- | ---------------------- | --------------------- |
| `Write` | Create new files       | Modifies filesystem   |
| `Edit`  | Modify existing files  | Modifies filesystem   |
| `Bash`  | Execute shell commands | Can modify filesystem |
| `Task`  | Delegate to sub-agents | Sub-agents may write  |

### Conditional Tools

| Tool   | Purpose       | Usage Guidance                                                   |
| ------ | ------------- | ---------------------------------------------------------------- |
| `Bash` | Run commands  | Safe if read-only commands (ls, git status), unsafe if mutations |
| `Task` | Launch agents | Safe if sub-agents also have tool restrictions                   |

## Design Guidance

### When to Use Tool Restrictions

✅ **Good candidates:**

- Commands that gather information before action
- Commands used within plan mode
- Commands that help users make decisions
- Commands that explore codebase without modifying it

❌ **Poor candidates:**

- Commands that implement features
- Commands that create PRs or commits
- Commands that run CI or tests (may need Bash)

### Choosing Allowed Tools

**Minimal set principle**: Only allow tools the command absolutely needs.

**Example reasoning for /local:interview**:

- ✅ `AskUserQuestion` — Core purpose is asking questions
- ✅ `Read` — May need to show user code snippets
- ✅ `Glob` — Find files matching patterns (e.g., "show me all auth-related files")
- ✅ `Grep` — Search for existing patterns
- ❌ `Write` — Never creates files (interview only)
- ❌ `Edit` — Never modifies files
- ❌ `Bash` — No need for shell commands

## Implementation Pattern

**Command file structure with tool restrictions**:

````markdown
---
description: One-line command description
allowed-tools: AskUserQuestion, Read, Glob, Grep
---

# /command-name

Brief description of what this command does.

## Safety

This command uses tool restrictions to ensure read-only behavior:

- Can search codebase
- Can ask user questions
- Cannot modify files or execute shell commands

## Usage

```bash
/command-name [optional-args]
```
````

## Implementation

[Command logic here]

```

## Enforcement

Tool restrictions are enforced by the Claude Code runtime:

1. Command declares `allowed-tools` in frontmatter
2. Runtime parses frontmatter before execution
3. Any tool call outside allowed set fails with error
4. Error message indicates which tool was blocked

**Error example**:
```

Error: Tool 'Write' is not allowed by this command.
Allowed tools: AskUserQuestion, Read, Glob, Grep

````

## Related Patterns

### Agent Delegation with Tool Restrictions

Commands with tool restrictions can delegate to agents, but the agent inherits the restrictions:

```markdown
---
allowed-tools: Read, Glob, Grep, Task
---

# /restricted-command

Task(
    subagent_type="search-agent",
    description="Search codebase",
    prompt="Find all occurrences of pattern X"
)
````

The `search-agent` can ONLY use Read, Glob, Grep (inherited from command), even if the agent's own frontmatter lists more tools.

### Combining with Plan Mode

Tool restrictions make commands safe to use in plan mode:

```markdown
User: [In plan mode] "Before I finalize this plan, let me interview myself about the requirements"

/local:interview feature-requirements

[Interview completes without exiting plan mode]

User: "Now I'll incorporate those requirements into the plan"
```

## Related Documentation

- [Agent Delegation](../planning/agent-delegation.md) — How /local:interview delegates to an agent
- [Context Preservation Prompting](../planning/context-preservation-prompting.md) — Using interview to gather context before planning
- [Plan Mode Workflows](../planning/plan-mode-workflows.md) — Commands that work within plan mode
