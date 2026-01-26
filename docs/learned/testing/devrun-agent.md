---
title: Devrun Agent - Read-Only Design
read_when:
  - "using the devrun agent"
  - "running CI checks via Task tool"
  - "debugging devrun agent failures"
  - "writing prompts for devrun"
tripwires:
  - action: "asking devrun agent to fix errors or make tests pass"
    warning: "Devrun is READ-ONLY. It runs commands and reports results. The parent agent must handle all fixes."
---

# Devrun Agent - Read-Only Design

The `devrun` agent is a specialized Task subagent for running development CLI tools (pytest, ty, ruff, prettier, make, gt). Its critical constraint: **it never modifies files**.

## Core Principle: Read-Only Execution

The devrun agent:

- **Runs** commands (pytest, ty, ruff, prettier, make, gt)
- **Parses** output to extract errors and failures
- **Reports** results back to the parent agent

The devrun agent **never**:

- Edits files
- Fixes errors
- Makes tests pass
- Modifies code

## Forbidden Prompt Patterns

These prompts violate the read-only contract:

❌ **"Run pytest and fix any errors that arise"**
❌ **"Make the tests pass"**
❌ **"Run ruff and address the issues"**
❌ **"Fix the type errors found by ty"**
❌ **"Run CI iteratively until it passes"**

These prompts imply the agent should modify files, which devrun cannot do.

## Required Prompt Patterns

Use these patterns instead:

✅ **"Run pytest and report results"**
✅ **"Execute ruff check and parse output"**
✅ **"Run ty and report any type errors"**
✅ **"Execute make fast-ci and report failures"**

The key words are "report" and "parse" - devrun observes and reports back.

## Iteration Workflow

When CI checks fail, use this pattern:

### Parent Agent Loop

```
1. Parent: "Run pytest and report results" → devrun agent
2. Devrun: Reports 3 test failures with details
3. Parent: Reads devrun output, identifies issues
4. Parent: Fixes code using Edit/Write tools
5. Parent: "Run pytest again and report results" → devrun agent
6. Devrun: Reports 1 test failure remaining
7. Parent: Fixes remaining issue
8. Parent: "Run pytest and report results" → devrun agent
9. Devrun: Reports all tests passing
```

**Key insight:** The parent agent drives the iteration loop. Devrun is stateless and read-only.

## Why This Design?

### Separation of Concerns

- **Devrun**: Command execution and output parsing (stateless)
- **Parent**: Code changes and iteration logic (stateful)

### Tool Access Boundaries

The devrun agent has access to:

- Read tool (for reading files to understand errors)
- Bash tool (for running commands)
- Grep/Glob tools (for searching code)
- Task tool (for spawning sub-agents if needed)

The devrun agent does NOT have access to:

- Edit tool
- Write tool
- TodoWrite tool (parent manages todos)

### Clear Failure Attribution

When devrun reports failures, it's unambiguous that the parent must act:

- ✅ **Clear**: "Devrun reports 3 type errors, parent must fix them"
- ❌ **Unclear**: "Devrun agent fixed some issues but got stuck"

## Common Mistakes

### Mistake 1: Delegating Fix Responsibility

**Wrong:**

```
Parent: "Run make fast-ci and fix any issues"
Devrun: [Attempts to fix, violates read-only contract]
```

**Correct:**

```
Parent: "Run make fast-ci and report results"
Devrun: "Found 3 issues: [details]"
Parent: [Fixes issues with Edit tool]
Parent: "Run make fast-ci again and report results"
```

### Mistake 2: Asking for Iterative Fixing

**Wrong:**

```
Parent: "Keep running pytest until all tests pass"
```

**Correct:**

```
Parent: "Run pytest and report results"
Devrun: [Reports failures]
Parent: [Analyzes, fixes]
Parent: "Run pytest again and report results"
[Repeat until passing]
```

### Mistake 3: Expecting Devrun to Track State

**Wrong:**

```
Parent: "Continue fixing the remaining test failures"
Devrun: [Doesn't know what "remaining" means - stateless]
```

**Correct:**

```
Parent: [Maintains state of which tests failed]
Parent: [Fixes specific tests]
Parent: "Run pytest and report results"
```

## Example Interaction

**Correct usage:**

```
Parent Agent: I need to verify the CI checks pass. Let me use the devrun agent.

[Spawns devrun agent]

Parent → Devrun: "Run `make fast-ci` and report all failures"

Devrun → Parent: "Command failed with exit code 1. Found issues:
- pytest: 2 failures in test_foo.py
- ruff: 1 unused import in src/bar.py
- ty: 1 type error in src/baz.py"

Parent: [Reads devrun output]
Parent: Let me fix the unused import first.
[Uses Edit tool to fix src/bar.py]

Parent → Devrun: "Run `make fast-ci` again and report results"

Devrun → Parent: "Command still failing:
- pytest: 2 failures in test_foo.py
- ty: 1 type error in src/baz.py"

[Parent continues fixing until devrun reports success]
```

## When to Use Devrun

Use devrun agent when:

- Running pytest, ty, ruff, prettier, make, gt commands
- You need structured output parsing
- You want to isolate command execution from code modification
- You're implementing CI verification workflows

Don't use devrun when:

- You need to modify files (use parent agent's Edit/Write tools)
- Running one-off bash commands (use Bash tool directly)
- The command is not a development tool (use Bash tool)

## Related Documentation

- [Subprocess Testing](subprocess-testing.md) - Testing patterns for process execution
- [CI Runner Gateway](../architecture/gateway-inventory.md#cirunner-gatewayci_runner) - CIRunner abstraction
- [AGENTS.md](../../../AGENTS.md) - Devrun agent routing rules
