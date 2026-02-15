---
title: CI Workflow Verification Patterns
read_when:
  - "debugging GitHub Actions workflows that succeeded but did nothing"
  - "verifying remote Claude workflows actually completed work"
  - "investigating why commits or changes didn't appear after workflow success"
tripwires:
  - action: "assuming work was done after GitHub Actions workflow reports success"
    warning: "GitHub Actions success (exit 0) does NOT guarantee expected outputs. Verify commits, file changes, and thread states exist. Don't trust exit code alone."
---

# CI Workflow Verification Patterns

## The False Success Problem

GitHub Actions job success (green checkmark, exit code 0) does NOT guarantee the workflow produced expected outputs. A Claude session can complete without errors but fail to:

- Make code changes
- Create commits
- Push to branches
- Resolve threads

This happens when:

- Subagent isolation fails and terminal instructions contaminate parent
- Workflow exits cleanly but before completing intended work
- Tool calls succeed but don't produce expected artifacts

## Verification Pattern

### 1. Check for Expected Artifacts

Don't trust the status badge alone. Verify:

- **Commits**: `git log` on the branch shows new commits
- **File changes**: Expected files were modified
- **Thread resolution**: PR threads are actually resolved
- **PR state**: Expected labels, status, or checks appear

### 2. Examine Session Logs

Extract and analyze the actual session:

```bash
gh run view <run-id> --log
```

Search for:

- Actual tool call outputs (not just tool call starts)
- JSON outputs that might indicate premature termination
- Message count to identify where execution stopped

### 3. Count Message Turns

Compare turn count with expected workflow length:

- If workflow has 5 phases but only 6-8 turns, something stopped early
- Each phase typically has multiple tool calls — very short sessions indicate failure

### 4. Compare with Known-Working Workflows

When debugging a failing workflow:

1. Find a similar workflow that works (e.g., plan-implement, one-shot)
2. Compare invocation patterns (--print flag, arguments, etc.)
3. Identify what differs in the failing workflow
4. This helped isolate that the --print flag itself wasn't the problem in PR #7096

## Related Documentation

- [Debugging Remote Workflows](debugging-remote-workflows.md) — Step-by-step investigation workflow
- [Task Context Isolation Pattern](../architecture/task-context-isolation.md) — CI context constraints
- [Context Fork Feature](../claude-code/context-fork-feature.md) — Execution mode limitations
