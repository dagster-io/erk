---
title: Agent Orchestration Safety Patterns
read_when:
  - "launching subagents that produce large outputs"
  - "using Write tool before launching dependent agents"
  - "designing agent-to-agent data handoff"
tripwires:
  - action: "launching subagents that produce outputs > 1KB"
    warning: "Use Write tool for agent outputs. Bash heredocs fail silently above 10KB."
  - action: "launching dependent agents that read from files written by Write tool"
    warning: "Verify file existence with ls before launching dependent agents."
---

# Agent Orchestration Safety Patterns

When orchestrating multiple agents that pass data between them, two failure modes cause silent data loss. These patterns prevent both.

## Bash Heredoc Output Truncation

Bash tool output is truncated when it exceeds ~10KB. This means agents that produce large outputs (analysis results, extracted documentation, synthesized plans) will silently lose data if the output is captured via Bash heredoc or echo.

**Symptom**: Downstream agent receives partial data with no error indication.

**Pattern**: Use the Write tool for any agent output expected to exceed 1KB:

1. Agent writes output to a scratch file using Write tool
2. Parent agent verifies the file exists
3. Dependent agent receives the file path, not inline content

**Scratch storage location**: `.erk/scratch/<session-id>/` for session-scoped data.

See `scratch-storage.md` for the canonical scratch storage pattern.

## Write Tool File Existence Validation

The Write tool can silently fail if the target directory doesn't exist. When a dependent agent expects to read a file that was written by a prior step, always verify before launching.

**Pattern**: After writing a file with Write tool, run `ls <path>` to confirm it exists before passing the path to a dependent agent.

**Why not just check in the dependent agent?** By the time the dependent agent fails, context has been spent on agent setup. Fail-fast at the orchestration layer saves tokens and provides clearer error messages.

## Safe Agent Output Handoff (Combined Pattern)

For workflows where Agent A produces output consumed by Agent B:

1. Agent A writes output to `.erk/scratch/<session-id>/<step-name>.md` using Write tool
2. Orchestrator verifies file with `ls` (Bash tool)
3. Orchestrator launches Agent B with the file path as an argument

This three-step pattern is used in the learn workflow where parallel analysis agents write results that feed into sequential synthesis agents.

## Reference

- Learn workflow implementation: `src/erk/cli/commands/exec/scripts/` (learn-related scripts)
- Scratch storage: [Scratch Storage](scratch-storage.md)
