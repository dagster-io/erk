---
title: Command-Agent Delegation
read_when:
  - "delegating to agents from commands"
  - "implementing command-agent pattern"
  - "workflow orchestration"
---

# Command-Agent Delegation Pattern

## Pattern Overview

For architectural context and pattern rationale (WHAT and WHY), see:
[Agent-Delegating Commands Pattern](../developer/agentic-engineering-patterns/agent-delegating-commands.md)

This guide focuses on HOW to implement the pattern with step-by-step technical instructions.

## Overview

**Command-agent delegation** is an architectural pattern where slash commands serve as lightweight entry points that delegate complete workflows to specialized agents. The command defines _what_ needs to happen (prerequisites, high-level flow), while the agent implements _how_ it happens (orchestration, error handling, result reporting).

**Benefits:**

- **Separation of concerns**: Commands are user-facing contracts; agents are implementation details
- **Maintainability**: Complex logic lives in one place (agent), not scattered across commands
- **Reusability**: Multiple commands can delegate to the same agent
- **Testability**: Agents can be tested independently of command invocation
- **Cost efficiency**: Agents can use appropriate models (haiku for orchestration, sonnet for analysis)

## When to Delegate

Use this decision framework to determine if delegation is appropriate:

### ✅ Good Candidates for Delegation

- **Multi-step workflows** - Command orchestrates 3+ distinct steps
- **Complex error handling** - Command needs extensive error formatting and recovery guidance
- **State management** - Command tracks progress across multiple operations
- **Tool orchestration** - Command coordinates multiple CLI tools or APIs
- **Repeated patterns** - Multiple commands share similar workflow logic

### ❌ Poor Candidates for Delegation

- **Simple wrappers** - Command just calls a single tool with pass-through arguments
- **Pure routing** - Command only selects between other commands or agents
- **Configuration** - Command just reads/writes config (minimal logic)
- **Status display** - Command only queries and formats existing state

### Decision Tree

```
Does command orchestrate 3+ steps?
├─ YES → Consider delegation
└─ NO → Is error handling extensive (>50 lines)?
    ├─ YES → Consider delegation
    └─ NO → Does it manage complex state?
        ├─ YES → Consider delegation
        └─ NO → Keep command inline (no delegation needed)
```

**Examples:**

| Scenario                                                        | Delegate? | Rationale                                                       |
| --------------------------------------------------------------- | --------- | --------------------------------------------------------------- |
| Run pytest with specialized output parsing                      | ✅ Yes    | Complex parsing, multiple tools (devrun agent)                  |
| Create worktree with validation, JSON parsing, formatted output | ✅ Yes    | Multi-step workflow with error handling (planned-wt-creator)    |
| Submit branch: stage, diff analysis, commit, PR creation        | ✅ Yes    | Complex orchestration with git + GitHub CLI (git-pr-push-agent) |
| Run single git command with no processing                       | ❌ No     | Simple wrapper, no orchestration needed                         |
| Display help text or documentation                              | ❌ No     | No workflow, just content display                               |

## Delegation Patterns

### Pattern 1: Simple Tool Delegation

**When to use:** Command needs specialized parsing or formatting of tool output.

**Example:** `/fast-ci` and `/all-ci` → `devrun` agent

**Characteristics:**

- Agent wraps a single category of tools (pytest, pyright, ruff, etc.)
- Provides specialized output parsing
- Formats results consistently
- Commands share agent but may pass different parameters
- Iterative error fixing
- Cost efficiency with lighter model

**Command structure:**

```markdown
---
description: Run fast CI checks iteratively
---

# /fast-ci

Run fast CI checks iteratively (unit tests + pyright) until all pass.

## Implementation

Delegates to the devrun agent:

Task(
subagent_type="devrun",
description="Run fast CI checks",
prompt="Run unit tests with pytest, then run pyright. Fix any failures iteratively."
)
```

**Agent responsibilities:**

- Parse tool-specific output formats
- Extract failures and provide context
- Format results for user consumption
- Iterate until success or max attempts

### Pattern 2: Workflow Orchestration

**When to use:** Command manages a multi-step workflow with dependencies between steps.

**Examples:**

- `/erk:git-pr-push` → `git-pr-push-agent` agent
- `/erk:create-wt-from-plan-file` → `planned-wt-creator` agent

**Characteristics:**

- Agent coordinates multiple tools in sequence
- Each step may depend on previous step's output
- Complex error handling at each step
- Rich user feedback throughout workflow
- Typically uses haiku model for cost efficiency

**Command structure:**

```markdown
---
description: Create worktree from existing plan file on disk
---

# /erk:create-wt-from-plan-file

Create a erk worktree from an existing plan file on disk.

## What This Command Does

Delegates the complete worktree creation workflow to the `planned-wt-creator` agent, which handles:

1. Auto-detect most recent plan file at repository root
2. Validate plan file (exists, readable, not empty)
3. Run `erk create --from-plan-file` with JSON output
4. Display plan location and next steps

## Implementation

Task(
subagent_type="planned-wt-creator",
description="Create worktree from plan",
prompt="Execute the complete planned worktree creation workflow"
)
```

**Agent responsibilities:**

- Execute workflow steps in order
- Parse outputs from each step
- Handle errors at each boundary
- Format final results for user

### Pattern 3: Shared Workflow Documentation

**When to use:** Multiple commands delegate to the same agent or share workflow logic.

**Example:** `/fast-ci` and `/all-ci` both reference `.claude/docs/ci-iteration.md`

**Characteristics:**

- Workflow documentation lives in `.claude/docs/`
- Commands reference shared doc with `@` syntax
- Single source of truth for workflow details
- Reduces duplication across commands
- Agent implements shared workflow

**Shared doc pattern:**

```markdown
# CI Iteration Workflow

This document describes the iterative CI workflow used by /fast-ci and /all-ci commands.

## Workflow Steps

1. Run specified CI checks
2. Capture failures
3. If failures: analyze and suggest fixes
4. Retry until success or max attempts
5. Report final status

## Agent Invocation

Both commands delegate to devrun agent:

- /fast-ci: "Run pytest tests/ && pyright"
- /all-ci: "Run make all-ci"
```

## Implementation Guide

Follow these steps to implement command-agent delegation:

### Step 1: Create Agent File

**Location:** `.claude/agents/<category>/<agent-name>.md`

**Frontmatter requirements:**

```yaml
---
name: agent-name # Used in Task subagent_type
description: One-line summary # Shows in kit registry
model: haiku | sonnet | opus # Model selection (see below)
color: blue | green | red | cyan # UI color coding
tools: Read, Bash, Task # Available tools
---
```

**Content structure:**

```markdown
You are a specialized agent for [purpose]. You orchestrate [high-level workflow].

**Philosophy**: [Why this agent exists, design principles]

## Your Core Responsibilities

1. [Responsibility 1]
2. [Responsibility 2]
   ...

## Complete Workflow

### Step 1: [First Step Name]

[Detailed instructions for step 1]

**Error handling:**

- Error case 1 → formatted error message
- Error case 2 → formatted error message

### Step 2: [Second Step Name]

[Detailed instructions for step 2]

...

## Best Practices

- [Practice 1]
- [Practice 2]

## Quality Standards

Before completing your work, verify:
✅ [Success criterion 1]
✅ [Success criterion 2]
```

### Step 2: Define Agent Workflow Steps

Break the workflow into clear, sequential steps:

1. **Input validation** - Check prerequisites and inputs
2. **Orchestration** - Execute operations in order
3. **Output formatting** - Present results to user
4. **Error handling** - Format errors with context and guidance

Each step should include:

- Clear instructions for the agent
- Expected inputs and outputs
- Error scenarios with formatted error templates
- Success criteria

### Step 3: Implement Error Handling

All errors must follow a consistent template:

```
❌ Error: [Brief description in 5-10 words]

Details: [Specific error message, relevant context, diagnostic info]

Suggested action:
  1. [Concrete step to resolve]
  2. [Alternative approach]
  3. [Fallback option]
```

**Error handling principles:**

- Catch errors at each step boundary
- Provide diagnostic context
- Suggest 1-3 concrete actions
- Never let raw exceptions reach the user

### Step 4: Update Command to Delegation-Only

**Target:** <50 lines total

**Structure:**

````markdown
---
description: One-line summary
---

# /command-name

Brief description of what command does.

## Usage

```bash
/command-name [optional-arg]
```
````

## What This Command Does

Delegates to the `agent-name` agent, which handles:

1. [High-level step 1]
2. [High-level step 2]
   ...

## Prerequisites

- [Prerequisite 1]
- [Prerequisite 2]

## Implementation

When this command is invoked, delegate to the agent:

```
Task(
    subagent_type="agent-name",
    description="Brief task description",
    prompt="Execute the complete [workflow name] workflow"
)
```

The agent handles all workflow orchestration, error handling, and result reporting.

````

### Step 5: Add to Kit Registry (if bundled)

If the agent is part of a kit (not project-specific), update the kit registry:

**File:** `.erk/kits/<kit-name>/registry-entry.md`

Add agent documentation:
```markdown
### Agents

- **agent-name** - [Description]. Use Task tool with `subagent_type="agent-name"`.
````

## Agent Specifications

### Frontmatter Requirements

All agents must include frontmatter with these fields:

```yaml
name: agent-name # REQUIRED: Used in Task subagent_type parameter
description: Summary # REQUIRED: One-line purpose (shown in registry)
model: haiku # REQUIRED: Model selection (see below)
color: blue # REQUIRED: UI color (blue, green, red, cyan, yellow)
tools: Read, Bash, Task # REQUIRED: Available tools (comma-separated)
```

**Field constraints:**

- `name`: Must be unique across all agents (kit + project), kebab-case
- `description`: One sentence, no period at end
- `model`: Must be one of: haiku, sonnet, opus
- `color`: Must be one of: blue, green, red, cyan, yellow, magenta
- `tools`: Comma-separated list from available tools

### Model Selection

Choose the appropriate model based on agent's cognitive requirements:

| Model      | Cost        | Speed       | Use Cases                                                                                                       |
| ---------- | ----------- | ----------- | --------------------------------------------------------------------------------------------------------------- |
| **haiku**  | 💰 Low      | ⚡⚡⚡ Fast | • Workflow orchestration<br>• Tool invocation<br>• JSON parsing<br>• Simple formatting<br>• Iterative execution |
| **sonnet** | 💰💰 Medium | ⚡⚡ Medium | • Complex analysis<br>• Code review<br>• Diff analysis<br>• Decision-making<br>• Pattern matching               |
| **opus**   | 💰💰💰 High | ⚡ Slower   | • Highly complex reasoning<br>• Novel problem solving<br>• Multi-step planning<br>• Rare, specialized tasks     |

**Guidelines:**

- **Default to haiku** for orchestration and tool coordination
- **Use sonnet** when analysis or reasoning is primary task
- **Avoid opus** unless absolutely necessary (cost implications)

**Examples:**

- `devrun` (haiku) - Runs tools, parses output, iterates
- `git-pr-push-agent` (haiku) - Orchestrates git/gh operations
- `planned-wt-creator` (haiku) - Detects files, validates, creates worktree
- Code review agent (sonnet) - Analyzes code quality and patterns

### Tools Available

Agents can specify which tools they need:

| Tool        | Purpose                                      |
| ----------- | -------------------------------------------- |
| `Read`      | Read files from filesystem                   |
| `Write`     | Write files to filesystem                    |
| `Edit`      | Edit existing files                          |
| `Bash`      | Execute shell commands                       |
| `Task`      | Delegate to other agents or run kit commands |
| `Glob`      | Find files by pattern                        |
| `Grep`      | Search file contents                         |
| `WebFetch`  | Fetch web content                            |
| `WebSearch` | Search the web                               |

**Principle:** Only request tools the agent will actually use. Fewer tools = clearer scope.

## Examples from Codebase

### Example 1: /fast-ci → devrun

**Pattern:** Simple tool delegation

**Command:** `.claude/commands/fast-ci.md` (minimal)

```markdown
Delegates to devrun agent to run pytest and pyright iteratively.
```

**Agent:** `.claude/agents/devrun.md`

- Specializes in running development tools
- Parses tool-specific output formats
- Iterates until success or max attempts
- Used by multiple commands (/fast-ci, /all-ci)

**Key insight:** One agent serves multiple commands by accepting different tool invocations.

### Example 2: /erk:git-pr-push → git-pr-push-agent

**Pattern:** Workflow orchestration

**Command:** `.claude/commands/erk/git-pr-push.md`

```markdown
Delegates the complete git-based PR push workflow to the `git-pr-push-agent` agent.
```

**Agent:** `.claude/agents/erk/git-pr-push-agent.md`

- Check uncommitted changes and stage/commit
- Analyze diff and generate commit message
- Push branch and create/update PR
- Comprehensive error handling at each step

**Key insight:** Agent coordinates multiple steps with dependencies, handling errors at each boundary.

### Example 3: /erk:create-wt-from-plan-file → planned-wt-creator

⚠️ **Note:** This command is now deprecated. The recommended workflow is to use `erk implement <issue>` instead, which creates worktrees directly from GitHub issues. This example is preserved for architectural reference.

**Pattern:** Workflow orchestration

**Command:** `packages/erk-kits/src/erk_kits/data/kits/erk/commands/erk/create-wt-from-plan-file.md` (42 lines)

- Reduced from 338 lines (87% reduction)
- All orchestration moved to agent

**Agent:** `.claude/agents/erk/planned-wt-creator.md`

- Plan file detection and validation
- Worktree creation via erk CLI
- JSON output parsing
- Next steps display

**Key insight:** Delegation enables massive simplification of command while maintaining all functionality.

## Anti-Patterns

### ❌ Don't: Run Tools Directly When Agent Exists

```markdown
# ❌ WRONG: Command runs pytest directly

/fast-ci:
bash: pytest tests/

# ✅ CORRECT: Command delegates to devrun agent

/fast-ci:
Task(subagent_type="devrun", prompt="Run pytest tests/")
```

**Why:** Bypasses specialized parsing and error handling in agent.

### ❌ Don't: Embed Orchestration in Command Files

```markdown
# ❌ WRONG: 338 lines of orchestration in command

/erk:create-wt-from-plan-file:

## Step 1: Detect plan file

[50 lines of instructions]

## Step 2: Validate plan

[50 lines of instructions]
...

# ✅ CORRECT: Command delegates to agent

/erk:create-wt-from-plan-file:
Task(subagent_type="planned-wt-creator", prompt="...")
```

**Why:** Commands become hard to maintain and test. Duplication across similar commands.

### ❌ Don't: Duplicate Error Handling Across Commands

```markdown
# ❌ WRONG: Each command duplicates error templates

/command-1: [200 lines with error handling]
/command-2: [200 lines with same error handling]

# ✅ CORRECT: Agent handles errors once

Agent: [Complete error handling]
/command-1: Task(subagent_type="agent")
/command-2: Task(subagent_type="agent")
```

**Why:** Inconsistent error messages, harder to update error handling.

### ❌ Don't: Mix Delegation and Inline Logic

```markdown
# ❌ WRONG: Command partially delegates

/command:
[30 lines of inline logic]
Task(subagent_type="agent", ...)
[30 lines more inline logic]

# ✅ CORRECT: Full delegation

/command:
Task(subagent_type="agent", prompt="Execute complete workflow")
```

**Why:** Unclear separation of concerns, harder to test and maintain.

## Delegation vs Inline: Quick Reference

| Characteristic      | Inline Command             | Delegated Command               |
| ------------------- | -------------------------- | ------------------------------- |
| **Lines of code**   | 100-500+                   | <50                             |
| **Error handling**  | Embedded in command        | In agent                        |
| **Orchestration**   | Step-by-step in command    | In agent                        |
| **Reusability**     | Copy-paste across commands | One agent, multiple commands    |
| **Testing**         | Test command invocation    | Test agent independently        |
| **Model selection** | Uses main session model    | Agent chooses appropriate model |
| **Maintenance**     | Update multiple commands   | Update one agent                |

## Agent Discovery

### Finding Available Agents

**Method 3: Check AGENTS.md**
Checklist table links to delegation pattern documentation.

### Using Agents in Commands

**Task tool invocation:**

```python
Task(
    subagent_type="agent-name",  # Must match agent's "name" in frontmatter
    description="Brief description",  # Shown in UI progress
    prompt="Detailed instructions for agent"  # Agent receives this
)
```

**Parameters:**

- `subagent_type` (required): Agent name from frontmatter
- `description` (required): Short task description (3-5 words)
- `prompt` (required): Complete instructions for agent
- `model` (optional): Override agent's default model

## Quality Standards

### Command Quality Standards

Commands using delegation must meet these standards:

✅ **Line count**: <50 lines total (including frontmatter)
✅ **Prerequisites section**: Clear list of requirements
✅ **Single delegation**: One Task tool invocation, no inline logic
✅ **Reference agent**: Point to agent for implementation details
✅ **User-facing**: Focus on "what" not "how"

### Agent Quality Standards

Agents must meet these standards:

✅ **Comprehensive error handling**: Formatted error for every failure mode
✅ **Self-contained workflow**: No external dependencies on command logic
✅ **Clear step structure**: Sequential steps with clear boundaries
✅ **Best practices section**: Guidance for agent execution
✅ **Quality checklist**: Success criteria before completion
✅ **Model appropriate**: Use haiku for orchestration, sonnet for analysis

## Progressive Disclosure

Documentation follows a progressive disclosure model:

1. **Quick reference** - AGENTS.md checklist entry
   - One line: "Creating command that orchestrates workflow → command-agent-delegation.md"

2. **Pattern documentation** - This document (docs/agent/planning/agent-delegation.md)
   - Complete patterns, examples, anti-patterns

3. **Implementation examples** - Actual commands and agents in codebase
   - `/fast-ci` → `devrun` (simple delegation)
   - `/erk:git-pr-push` → `git-pr-push-agent` (workflow orchestration)
   - `/erk:create-wt-from-plan-file` → `planned-wt-creator` (workflow orchestration)

**Navigation:**

- `AGENTS.md` → Quick lookup during coding
- `docs/agent/guide.md` → Navigation hub to all documentation
- This doc → Complete delegation pattern reference

## Summary

**When to delegate:**

- Multi-step workflows (3+ steps)
- Complex error handling needed
- State management across operations
- Tool orchestration required

**How to delegate:**

1. Create agent with frontmatter and workflow steps
2. Implement comprehensive error handling
3. Update command to delegation-only (<50 lines)
4. Add agent to kit registry if bundled

**Key principles:**

- Commands define _what_ (user contract)
- Agents implement _how_ (orchestration, error handling)
- One agent can serve multiple commands
- Use appropriate model (haiku for orchestration)
- Follow progressive disclosure (checklist → docs → implementation)
