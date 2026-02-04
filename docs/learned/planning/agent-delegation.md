---
title: Command-Agent Delegation
read_when:
  - "delegating to agents from commands"
  - "implementing command-agent pattern"
  - "workflow orchestration"
tripwires:
  - action: "using background agents without waiting for completion before dependent operations"
    warning: "Use TaskOutput with block=true to wait for all background agents to complete. Without synchronization, dependent agents may read incomplete outputs or missing files."
last_audited: "2026-02-04 14:09 PT"
audit_result: edited
---

# Command-Agent Delegation Pattern

## Pattern Overview

This guide covers the command-agent delegation pattern: when to use it, how to implement it, and common pitfalls to avoid.

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

| Scenario                                                        | Delegate? | Rationale                                                                        |
| --------------------------------------------------------------- | --------- | -------------------------------------------------------------------------------- |
| Run pytest with specialized output parsing                      | ✅ Yes    | Complex parsing, multiple tools (devrun agent)                                   |
| Create worktree with validation, JSON parsing, formatted output | ✅ Yes    | Multi-step workflow with error handling (planned-wt-creator)                     |
| Submit branch: stage, diff analysis, commit, PR creation        | ❌ No     | Consolidated into inline command (sequential workflow, no complex orchestration) |
| Run single git command with no processing                       | ❌ No     | Simple wrapper, no orchestration needed                                          |
| Display help text or documentation                              | ❌ No     | No workflow, just content display                                                |

## Delegation Patterns

### Pattern 1: Simple Tool Delegation

**When to use:** Command needs specialized parsing or formatting of tool output.

**Example:** `/fast-ci` and `/all-ci` → `devrun` agent

**Characteristics:**

- Agent wraps a single category of tools (pytest, ty, ruff, etc.)
- Provides specialized output parsing
- Formats results consistently
- Commands share agent but may pass different parameters
- Iterative error fixing
- Cost efficiency with lighter model

**Command structure:** See `.claude/commands/local/fast-ci.md`

**Agent responsibilities:**

- Parse tool-specific output formats
- Extract failures and provide context
- Format results for user consumption
- Iterate until success or max attempts

### Pattern 2: Workflow Orchestration

**When to use:** Command manages a multi-step workflow with dependencies between steps.

**Examples:**

- `/erk:create-wt-from-plan-file` → `planned-wt-creator` agent

**Characteristics:**

- Agent coordinates multiple tools in sequence
- Each step may depend on previous step's output
- Complex error handling at each step
- Rich user feedback throughout workflow
- Typically uses haiku model for cost efficiency

**Command structure:** See historical reference in `packages/erk-kits/src/erk_kits/data/kits/erk/commands/erk/create-wt-from-plan-file.md` (deprecated)

**Agent responsibilities:**

- Execute workflow steps in order
- Parse outputs from each step
- Handle errors at each boundary
- Format final results for user

### Pattern 3: Shared Workflow Skills

**When to use:** Multiple commands delegate to the same agent or share workflow logic.

**Example:** `/fast-ci` and `/all-ci` both reference `.claude/skills/ci-iteration/SKILL.md`

**Characteristics:**

- Workflow documentation lives in skills (`.claude/skills/`)
- Commands reference shared skill with `@` syntax
- Single source of truth for workflow details
- Reduces duplication across commands
- Agent implements shared workflow

**Shared skill pattern:** See `.claude/skills/ci-iteration/SKILL.md` for workflow documentation shared across commands.

## Implementation Guide

Follow these steps to implement command-agent delegation:

### Step 1: Create Agent File

**Location:** `.claude/agents/<category>/<agent-name>.md`

**Frontmatter requirements:** See existing agent files (`.claude/agents/devrun.md`) for required fields: name, description, model, color, tools.

**Content structure:** Include philosophy, core responsibilities, workflow steps with error handling, best practices, and quality standards. See `.claude/agents/devrun.md` for reference structure.

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

See `.claude/commands/local/fast-ci.md` for the canonical delegation pattern: frontmatter with description, what the command does, prerequisites, and a single Task tool invocation to the agent.

### Step 5: Add to Kit Registry (if bundled)

If the agent is part of a kit (not project-specific), update the kit registry:

**File:** `.erk/kits/<kit-name>/registry-entry.md`

Add agent documentation:

```markdown
### Agents

- **agent-name** - [Description]. Use Task tool with `subagent_type="agent-name"`.
```

## Agent Specifications

See existing agent files for frontmatter requirements (name, description, model, color, tools). Model selection: default to `haiku` for orchestration, use `sonnet` for analysis/reasoning, avoid `opus` unless necessary.

### Multi-Tier Agent Orchestration

For complex workflows requiring multiple agents, use a tiered orchestration pattern:

```
Parallel Tier (independent extraction, run simultaneously)
  ├─ Agent A (haiku) - Extract patterns from source A
  ├─ Agent B (haiku) - Extract patterns from source B
  └─ Agent C (haiku) - Extract patterns from source C

Sequential Tier 1 (depends on Parallel Tier)
  └─ Agent D (haiku) - Synthesize and deduplicate

Sequential Tier 2 (depends on Sequential Tier 1)
  └─ Agent E (opus) - Creative authoring, quality-critical output
```

**Key principles:**

1. **Parallel extraction**: Independent agents run simultaneously via `run_in_background: true`
2. **Sequential synthesis**: Dependent agents wait for inputs before launching
3. **Model escalation**: Use cheaper models (haiku) for mechanical tasks, expensive models (opus) for creative/quality-critical tasks
4. **File-based composition**: Agents write to scratch storage; subsequent agents read from those paths

**Real-world example:** The learn workflow uses this exact pattern:

| Tier         | Agents                                                 | Model | Purpose                  |
| ------------ | ------------------------------------------------------ | ----- | ------------------------ |
| Parallel     | SessionAnalyzer, CodeDiffAnalyzer, ExistingDocsChecker | Haiku | Mechanical extraction    |
| Sequential 1 | DocumentationGapIdentifier                             | Haiku | Rule-based deduplication |
| Sequential 2 | PlanSynthesizer                                        | Opus  | Creative authoring       |

See [Learn Workflow](learn-workflow.md#agent-tier-architecture) for the complete implementation.

### Background Agent Synchronization

When spawning background agents that must complete before proceeding, use `TaskOutput` with `block: true` to synchronize.

**Critical requirement:** Commands or workflows that spawn background agents MUST wait for completion before performing dependent operations.

**Pattern:**

```python
# Step 1: Launch background agents
Task(
    subagent_type="session-analyzer",
    description="Analyze session",
    run_in_background=True
)  # Returns agent_id

Task(
    subagent_type="code-diff-analyzer",
    description="Analyze code diff",
    run_in_background=True
)  # Returns agent_id

# Step 2: CRITICAL - Wait for completion before using results
TaskOutput(task_id=agent_id_1, block=True)
TaskOutput(task_id=agent_id_2, block=True)

# Step 3: Now safe to use agent outputs
```

**Why this matters:**

The `/erk:replan` command consolidates multiple source plans using parallel agents. Step 4e explicitly requires:

> "Use TaskOutput with `block: true` to wait for all agents to complete. Do NOT proceed to Step 5 until ALL agents have finished."

Without this synchronization:

- Dependent agents may read incomplete outputs
- File-based composition fails with missing data
- Consolidated plans may be incomplete or corrupted

**Real-world failure mode:**

A replan workflow spawned 3 analysis agents in parallel, then immediately launched the synthesis agent. The synthesis agent found only 1 of 3 expected input files because the parallel agents hadn't finished writing yet.

**Reference:** See `/erk:replan` Step 4e for the canonical implementation of this pattern.

### Tools Available

Agents specify tools in frontmatter. **Principle:** Only request tools the agent will actually use. Fewer tools = clearer scope.

## Examples from Codebase

### Example 1: /fast-ci → devrun

**Pattern:** Simple tool delegation

Read `.claude/commands/local/fast-ci.md` and `.claude/agents/devrun.md` for implementation.

**Key insight:** One agent serves multiple commands by accepting different tool invocations.

### Example 1b: /local:interview → interview agent

**Pattern:** Agent delegation with tool restrictions for safety

Read `.claude/commands/local/interview.md` for implementation.

**Key insight:** Tool restrictions (`allowed-tools: AskUserQuestion, Read, Glob, Grep`) enforce read-only behavior, making the command safe to use within plan mode.

**Use case:** Gather detailed requirements through conversation before entering plan mode or as part of planning workflow.

### Example 2: /erk:create-wt-from-plan-file → planned-wt-creator

⚠️ **Note:** This command is now deprecated. The recommended workflow is to use `erk implement <issue>` instead. This example is preserved for architectural reference.

**Pattern:** Workflow orchestration - See `packages/erk-kits/src/erk_kits/data/kits/erk/commands/erk/create-wt-from-plan-file.md`

**Key insight:** Delegation enabled 87% reduction (338 → 42 lines) while maintaining all functionality.

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

## Context Reduction Pattern

**When to use:** Agent processes large input data using deterministic rules to produce compact output for main conversation.

**Problem:** Some operations require processing large volumes of data (e.g., 2000+ lines of commit JSON) that would consume excessive context if directly loaded into the main conversation.

**Solution:** Delegate to a specialized subagent that:

1. Loads and processes the large input data
2. Applies deterministic rules or analysis
3. Returns a compact, actionable proposal (50-100 lines)
4. Main conversation receives only the proposal, not the raw data

### Example: changelog-update → commit-categorizer

**Workflow:**

1. Main conversation calls `/local:changelog-update`
2. Command delegates to `commit-categorizer` agent
3. Agent fetches 2000+ lines of commit JSON via `erk-dev changelog-commits --json-output`
4. Agent categorizes commits using rules from agent definition
5. Agent returns compact proposal (50-100 lines) with STATUS header
6. Main conversation presents proposal to user, requests edits
7. Main conversation updates CHANGELOG.md directly

**Context reduction:** 95% (2000+ lines → 50-100 lines)

**Output format:**

```
STATUS: OK
HEAD_COMMIT: abc123
SINCE_COMMIT: def456
TOTAL_COMMITS: 42

---PROPOSAL---

Found 42 commits since last sync.

**Major Changes (2):**
1. `abc123` - New plan review workflow
   - Reasoning: Significant user-facing feature

**Added (5):**
1. `def456` - New TUI command
   ...

**Filtered Out (35):**
- `ghi789` - "Update tests" -> test-only change
...
```

**When to apply:**

- Large input data (1000+ lines)
- Deterministic rules or categorization logic
- Compact output required (summary, proposal, list)
- Main conversation needs actionable result, not raw data

**Reference:** `.claude/agents/changelog/commit-categorizer.md` for canonical implementation.

## Agent Discovery

### Finding Available Agents

Check AGENTS.md for agent checklist table linking to delegation pattern documentation.

### Using Agents in Commands

Use `Task(subagent_type="agent-name", description="Brief description", prompt="Detailed instructions")`. The `subagent_type` must match the agent's `name` in frontmatter.

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
