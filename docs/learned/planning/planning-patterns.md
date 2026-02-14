---
title: Planning Patterns
last_audited: "2026-02-11"
audit_result: clean
read_when:
  - "preparing to enter plan mode"
  - "optimizing plan creation workflow"
  - "delegating tasks during planning"
---

# Planning Patterns

Patterns for effective plan creation and context management.

## Pre-Plan Context Gathering

**Pattern**: Gather ALL necessary context BEFORE entering plan mode.

### Why This Matters

Plan mode is for plan _creation_, not exploration. Entering plan mode early and then doing extensive file reading, API calls, and exploration wastes the focused planning context on data gathering.

### The Pattern

1. Parse objective and extract step details
2. Load all relevant documentation (migration guides, API references, prior PRs)
3. Read target files and analyze patterns
4. Enter plan mode with complete context
5. Write plan immediately without further exploration

### Parallel Context Gathering

Use parallel tool calls to load context simultaneously:

- Task agent for structured data (JSON parsing, issue fetching)
- File reads for documentation and source code
- Bash commands for git history and status

### Anti-pattern

Entering plan mode first, then spending multiple turns reading files, fetching issues, and exploring the codebase. This fragments the planning session with mechanical work.

## Task Agent for Structured Data

Delegate structured data parsing to the Task agent to keep the main conversation focused on planning logic:

- Fetch and parse issue body
- Validate labels and metadata
- Run JSON commands and format results
- Parse and format structured data

This separation keeps the main conversation clean and planning-focused.

## Plan-First Exploration Workflow

A structured approach to exploration before planning:

### Exploration Phase

1. **Search `docs/learned/`** for existing documentation matching the task
2. **Launch Explore agents** in parallel for independent questions about the codebase
3. **Read source files** referenced in documentation to verify accuracy
4. **Synthesize findings** into a mental model of what needs to change

### Structured Exploration Prompts

Categorize exploration prompts by their purpose:

| Category     | Example Prompt                               |
| ------------ | -------------------------------------------- |
| Architecture | "What is the gateway layer structure for X?" |
| Patterns     | "How are similar features implemented?"      |
| Testing      | "What test fixtures exist for this area?"    |
| Dependencies | "What other code depends on this module?"    |

### Transition to Planning

Enter plan mode only when exploration is complete. The plan should be writable in a single focused pass without needing additional file reads or searches.

## Related Documentation

- [Plan Lifecycle](lifecycle.md) - Complete lifecycle from creation through merge
- [Planning Workflow](workflow.md) - `.impl/` folder structure and commands
- [Exploration Strategies](exploration-strategies.md) - Two-stage Explore-then-Plan workflow
