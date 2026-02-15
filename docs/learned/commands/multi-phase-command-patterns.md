---
title: Multi-Phase Command Patterns
read_when:
  - "writing multi-phase commands that use subagent isolation"
  - "creating commands that run in both interactive and CI contexts"
  - "debugging commands where only the first phase executes"
tripwires:
  - action: "writing multi-phase commands that use subagent isolation"
    warning: "Multi-phase commands can terminate prematurely if subagent isolation fails in the target execution mode. When a skill invocation or Task call returns empty/early due to isolation failure, the parent context may receive a terminal instruction (e.g., 'Output ONLY JSON') and stop before executing remaining phases. Test with `claude --print` and verify ALL phases execute."
  - action: "committing commands invoked by GitHub Actions workflows without testing in --print mode"
    warning: "Features that work in interactive mode may fail in --print mode. context: fork is the most notable example — it creates isolation interactively but loads inline in --print mode. Test with `claude --print '/command args'` and verify all phases execute."
---

# Multi-Phase Command Patterns

## The Premature Termination Vulnerability

Multi-phase commands (commands that execute several sequential phases of work) are vulnerable to silent premature termination when subagent isolation fails.

**The mechanism:** When a phase invokes a skill via `context: fork` and isolation fails (e.g., in `--print` mode), the skill's terminal output instructions contaminate the parent context. The parent completes the first phase, outputs the requested data, and stops — abandoning all remaining phases.

**Why this is dangerous:**

- The workflow reports success (exit 0)
- No exceptions are thrown
- The session logs show clean completion
- Only expected artifacts (commits, resolved threads) reveal the failure

**Evidence:** PR #7096 — the pr-address 5-phase workflow terminated after Phase 1 classification, abandoning Phases 2-5.

## Prevention

1. **Test commands in target execution mode** (`claude --print` for CI workflows)
2. **Verify ALL phases execute**, not just Phase 1
3. **Use explicit Task delegation for CI contexts** (not `context: fork`)
4. **Check session logs** to verify subagent isolation occurred (separate session IDs)

See `docs/learned/architecture/task-context-isolation.md` for the Task delegation pattern and CI context constraints.

See `docs/learned/claude-code/context-fork-feature.md` for execution mode limitations of `context: fork`.

## Related Documentation

- [Task Context Isolation Pattern](../architecture/task-context-isolation.md) — CI constraints and Task delegation patterns
- [Context Fork Feature](../claude-code/context-fork-feature.md) — Execution mode limitations
- [Claude CLI Execution Modes](../architecture/claude-cli-execution-modes.md) — Behavioral differences between modes
