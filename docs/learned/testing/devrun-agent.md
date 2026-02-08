---
title: Devrun Agent - Read-Only Design
read_when:
  - "using the devrun agent"
  - "running CI checks via Task tool"
  - "writing prompts for devrun"
  - "understanding the parent-agent fix cycle"
tripwires:
  - action: "asking devrun agent to fix errors or make tests pass"
    warning: "Devrun is READ-ONLY. It runs commands and reports results. The parent agent must handle all fixes."
  - action: "running pytest, ty, ruff, prettier, make, or gt directly via Bash"
    warning: "Use Task(subagent_type='devrun') instead. A UserPromptSubmit hook enforces this on every turn."
last_audited: "2026-02-08"
audit_result: edited
---

# Devrun Agent - Read-Only Design

## Why Read-Only?

Devrun exists to enforce a strict separation between **observation** (running commands, parsing output) and **mutation** (editing files, fixing errors). This separation solves three problems that emerge when a single agent does both:

1. **Ambiguous failure attribution.** When an agent that can both run tests and edit files reports "fixed 3 of 5 failures," the parent doesn't know whether the fixes were correct, whether they introduced regressions, or whether it should continue iterating. Read-only devrun removes this ambiguity — every failure report is an unambiguous signal that the parent must act.

2. **Runaway fix loops.** An agent with both capabilities can enter a cycle of breaking and "fixing" code without the parent's knowledge. Devrun's lack of Write/Edit tools makes this structurally impossible — it can't even attempt a fix via Bash because its agent definition explicitly forbids file-writing Bash patterns (sed -i, output redirection, tee, etc.).

3. **Cost control.** Devrun uses the haiku model because it only needs to execute commands and parse structured output — no reasoning about code changes. This keeps CI iteration cheap. The parent agent (typically sonnet or opus) handles the expensive reasoning about what to fix.

## The Iteration Protocol

The parent agent owns the entire fix cycle. Devrun is invoked repeatedly as a stateless oracle:

1. Parent invokes devrun: "Run pytest and report results"
2. Devrun executes, parses output, returns structured failures
3. Parent reads failures, edits code using Write/Edit tools
4. Parent invokes devrun again: "Run pytest and report results"
5. Repeat until passing

**Why stateless matters:** Each devrun invocation starts fresh. It has no memory of previous runs, which means the parent must never phrase prompts that assume continuity (e.g., "run the remaining failures"). The parent maintains all iteration state.

## Enforcement Chain

Devrun's read-only constraint is enforced at three levels, creating defense in depth:

| Level | Mechanism | What it prevents |
|-------|-----------|-----------------|
| **Agent definition** | `tools: Read, Bash, Grep, Glob, Task` — no Write or Edit | Direct file modification via Claude tools |
| **Agent instructions** | Explicit FORBIDDEN Bash patterns list | File modification via Bash workarounds (sed -i, tee, etc.) |
| **Per-prompt hook** | UserPromptSubmit reminder on every turn | Parent agent running pytest/ty/ruff directly instead of delegating |

<!-- Source: .claude/agents/devrun.md -->

The agent definition in `.claude/agents/devrun.md` contains the complete operational contract: command normalization rules, output parsing patterns per tool, reporting format, and the full list of forbidden Bash patterns.

<!-- Source: src/erk/cli/commands/exec/scripts/user_prompt_hook.py, build_devrun_reminder -->

The per-prompt hook (see `build_devrun_reminder()` in `src/erk/cli/commands/exec/scripts/user_prompt_hook.py`) emits the routing reminder on every user message, ensuring even the parent agent doesn't bypass devrun by running tools directly.

## Anti-Patterns

These are prompts that violate the read-only contract. Devrun will refuse them, but the parent agent shouldn't send them in the first place:

```
# WRONG — delegates fix responsibility
"Run make fast-ci and fix any issues"

# WRONG — expects iteration within devrun
"Keep running pytest until all tests pass"

# WRONG — assumes devrun tracks state across invocations
"Continue fixing the remaining test failures"
```

The correct prompt is always a variation of: **"Run [command] and report results."**

## Relationship to CI Commands

<!-- Source: .claude/commands/local/fast-ci.md -->
<!-- Source: .claude/commands/local/all-ci.md -->

The `/local:fast-ci` and `/local:all-ci` commands both delegate to devrun. They differ only in which tests they run (unit-only vs all including integration), but share the same delegation pattern and iteration protocol. The `ci-iteration` skill documents the complete CI iteration workflow that wraps devrun.

## Related Documentation

- `.claude/agents/devrun.md` — Complete operational contract (tool access, command normalization, reporting format)
- [Agent Delegation](../planning/agent-delegation.md) — The broader delegation pattern that devrun exemplifies
- [Context Injection Tiers](../architecture/context-injection-tiers.md) — How the devrun routing reminder fits into the three-tier enforcement system
