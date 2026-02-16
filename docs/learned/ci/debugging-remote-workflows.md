---
title: Debugging Remote Workflows
read_when:
  - "remote workflow succeeded but produced no changes"
  - "investigating why a GitHub Actions Claude workflow failed silently"
  - "debugging multi-phase command execution in CI"
---

# Debugging Remote Workflows

## Investigation Workflow

When a remote workflow reports success but doesn't produce expected outputs:

### Step 1: Verify Actual Outputs

Before diving into logs, confirm the problem:

- Check for expected commits on the branch
- Check for expected file changes
- Check PR thread states
- Don't assume GitHub Actions green = success

### Step 2: Extract Session Logs

```bash
gh run view <run-id> --log
```

Save to file for easier analysis:

```bash
gh run view <run-id> --log > workflow.log
```

### Step 3: Count Message Turns

Search for turn indicators in the log:

- Very short turn counts (6-8 for a 5-phase workflow) indicate premature termination
- Compare with expected workflow length

### Step 4: Check Session IDs

If subagent isolation should have occurred:

- Look for session ID changes in logs
- Same session ID throughout = fork didn't work
- Different session IDs = subagent was created

### Step 5: Identify Termination Point

Find the last tool call or output:

- JSON output as final message often indicates terminal instruction contamination
- Look for what instruction caused the stop

### Step 6: Compare with Working Workflows

Find a similar workflow that works correctly:

- Compare invocation patterns
- Check for differences in skill loading or Task usage
- Eliminate common factors (like --print flag) as causes

## Common Failure Patterns

### Terminal Instruction Contamination

**Symptom:** Workflow outputs JSON and stops
**Cause:** Skill's "Output ONLY JSON" instruction loaded inline (fork failed)
**Solution:** Use Task tool for guaranteed isolation

### Multi-Phase Premature Termination

**Symptom:** Only Phase 1 completes, remaining phases abandoned
**Cause:** Subagent isolation failure causes parent to receive terminal instruction
**Solution:** Test with `claude --print` locally, use Task tool in CI commands

## Related Documentation

- [CI Workflow Verification Patterns](workflow-verification-patterns.md) — Verification checklists
- [Task Context Isolation Pattern](../architecture/task-context-isolation.md) — Terminal instruction contamination details
- [Claude CLI Execution Modes](../architecture/claude-cli-execution-modes.md) — Mode behavioral differences
