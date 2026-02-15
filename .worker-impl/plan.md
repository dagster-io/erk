# Documentation Plan: Fix pr-address remote workflow: classifier kills multi-phase execution

## Context

This implementation fixed a critical production reliability issue where the `pr-address` remote workflow would succeed (green checkmark in GitHub Actions) but produce no actual work - no commits, no resolved threads, no code changes. The root cause was subtle: the `context: fork` skill metadata doesn't create true subagent isolation when Claude runs in `--print` mode (used by CI/GitHub Actions workflows). Instead, the skill content loads inline, and its terminal instruction "Output ONLY the following JSON" contaminated the parent context, causing Claude to stop execution after the classification phase.

The fix replaced three skill invocations with explicit `Task` tool calls that guarantee subagent isolation in all execution modes. This surgical change (+17/-5 lines in a single file) makes the five-phase pr-address workflow reliable in CI contexts. However, without documentation, this pattern will recur in other commands that use `context: fork` skills in workflows.

Documentation matters here because the failure mode is exceptionally deceptive: the workflow reports success, no exceptions are thrown, and the session logs show a clean completion. Only by checking for expected artifacts (commits, resolved threads) or examining session IDs in logs would an engineer discover the problem. The debugging workflow, the root cause analysis, and the Task tool pattern for CI-safe isolation all deserve documentation to prevent future teams from rediscovering this the hard way.

## Raw Materials

https://gist.github.com/schrockn/3a8490425e475d020fff2861a0558b99

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 11    |
| Contradictions to resolve      | 2     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score 2-3)| 2     |

## Documentation Items

### HIGH Priority

#### 1. context: fork fails in --print mode tripwire

**Location:** `docs/learned/claude-code/tripwires.md` (new file)
**Action:** CREATE
**Source:** [Impl], [PR #7096]

**Draft Content:**

```markdown
---
title: Claude Code Tripwires
read-when:
  - working with Claude Code configuration or settings
  - writing commands that use context: fork metadata
  - creating skills with terminal output instructions
---

# Claude Code Tripwires

## context: fork Does Not Isolate in --print Mode

**Trigger:** Before invoking skills with `context: fork` in commands that run via `claude --print` in CI

**Warning:** The `context: fork` metadata does NOT create subagent isolation in `--print` mode (used by GitHub Actions workflows). The skill content loads inline in the parent context. If the skill has terminal output instructions (e.g., "Output ONLY JSON"), those instructions will contaminate the parent and cause it to stop execution prematurely.

**Solution:** Use explicit Task tool delegation instead. See `task-for-ci-isolation` in `docs/learned/architecture/task-context-isolation.md` for the pattern.

**Evidence:** PR #7096 fixed pr-address workflow that was terminating after Phase 1 classification despite reporting success in GitHub Actions.
```

---

#### 2. Update context-fork-feature.md with execution mode limitations

**Location:** `docs/learned/claude-code/context-fork-feature.md`
**Action:** UPDATE
**Source:** [Impl], [PR #7096]

**Draft Content:**

Add a new section "Execution Mode Limitations" explaining:

```markdown
## Execution Mode Limitations

### context: fork Behavior by Execution Mode

| Mode | Fork Creates Isolation? | Behavior |
|------|------------------------|----------|
| Interactive (`/command`) | Yes | True subagent with separate session ID |
| Non-interactive (`claude --print`) | **No** | Content loads inline, instructions contaminate parent |

### The Problem in CI Contexts

When commands run via `claude --print` in GitHub Actions workflows, `context: fork` does not create true subagent isolation. The skill content loads directly into the parent context. If the skill contains terminal output instructions like "Output ONLY JSON", those instructions become the parent's instructions, causing it to:

1. Output the structured data as requested
2. Stop execution immediately (following the "only" directive)
3. Abandon remaining workflow phases

This failure mode is deceptive: the workflow reports success (exit 0), but no actual work is done.

### Prevention

For commands that run in CI/workflows, use explicit Task tool delegation instead of relying on `context: fork`. See `docs/learned/architecture/task-context-isolation.md` for the pattern.

The original `context: fork` recommendation ("Prefer context: fork for fetch-and-classify patterns") remains valid **in interactive mode**. Use Task delegation for CI/workflow contexts.
```

---

#### 3. Add CI Context Constraints section to task-context-isolation.md

**Location:** `docs/learned/architecture/task-context-isolation.md`
**Action:** UPDATE
**Source:** [Impl], [PR #7096]

**Draft Content:**

Add a new section "CI Context Constraints" covering Task as the required (not optional) isolation mechanism:

```markdown
## CI Context Constraints

### Task Tool as Required Isolation Mechanism

In `--print` mode (used by GitHub Actions workflows), `context: fork` does not create true subagent isolation. The Task tool is the **required** pattern for commands that need isolation in CI contexts.

**When Task is Required (not optional)**:
- Command runs via `claude --print` in workflows
- Skill has terminal output instructions that could contaminate parent
- Multi-phase workflows where isolation failure would abandon remaining phases

**Task Delegation Pattern for Skills:**

See the implementation in `.claude/commands/erk/pr-address.md`, grep for "Task tool" to find the Phase 1 and Phase 4 classification patterns. The pattern:

1. Use `Task(subagent_type: "general-purpose", ...)`
2. In the prompt, instruct the agent to "Load and follow the skill instructions in .claude/skills/SKILLNAME/SKILL.md"
3. Pass through any arguments
4. Request the complete output as the final message

This creates genuine subagent isolation regardless of execution mode.

### Why This Matters

The pr-address workflow has 5 phases. Without proper isolation, the classifier's "Output ONLY JSON" instruction causes the parent to stop after Phase 1, abandoning batch changes, commits, thread resolution, and verification. The workflow reports success but produces no work.
```

---

#### 4. Multi-phase execution vulnerability tripwire

**Location:** `docs/learned/commands/tripwires.md`
**Action:** UPDATE
**Source:** [Impl], [PR #7096]

**Draft Content:**

Add to existing tripwires file:

```markdown
## Multi-Phase Command Isolation Vulnerability

**Trigger:** Before writing multi-phase commands that use subagent isolation

**Warning:** Multi-phase commands can terminate prematurely if subagent isolation fails in the target execution mode. When a skill invocation or Task call returns empty/early due to isolation failure, the parent context may receive a terminal instruction (e.g., "Output ONLY JSON") and stop before executing remaining phases.

**Prevention:**
1. Test commands in target execution mode (`claude --print` for CI workflows)
2. Verify ALL phases execute, not just Phase 1
3. Use explicit Task delegation for CI contexts (not `context: fork`)
4. Check session logs to verify subagent isolation occurred (separate session IDs)

**Evidence:** PR #7096 - pr-address 5-phase workflow terminated after Phase 1 classification, abandoning Phases 2-5.
```

---

#### 5. CI workflow verification patterns

**Location:** `docs/learned/ci/workflow-verification-patterns.md` (new file)
**Action:** CREATE
**Source:** [Impl], [PR #7096]

**Draft Content:**

```markdown
---
title: CI Workflow Verification Patterns
read-when:
  - debugging GitHub Actions workflows that "succeeded but did nothing"
  - verifying remote Claude workflows actually completed work
  - investigating why commits or changes didn't appear after workflow success
tripwires: 1
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
- Each phase typically has multiple tool calls - very short sessions indicate failure

### 4. Compare with Known-Working Workflows

When debugging a failing workflow:
1. Find a similar workflow that works (e.g., plan-implement, one-shot)
2. Compare invocation patterns (--print flag, arguments, etc.)
3. Identify what differs in the failing workflow
4. This helped isolate that --print flag itself wasn't the problem in PR #7096

## Tripwire

**After GitHub Actions workflow reports success, before assuming work was done:**
Verify expected artifacts exist (commits, changes, resolved threads). Don't trust exit code alone.
```

---

#### 6. Clarify context-dependent fork recommendation

**Location:** `docs/learned/architecture/task-context-isolation.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Update the existing recommendation (approximately line 38) from:

"Prefer `context: fork` for fetch-and-classify patterns"

To:

"Prefer `context: fork` for fetch-and-classify patterns **in interactive mode**. For commands that run via `claude --print` in CI/workflows, use explicit Task delegation instead - `context: fork` does not create isolation in non-interactive mode."

---

### MEDIUM Priority

#### 7. Claude CLI execution modes reference

**Location:** `docs/learned/architecture/claude-cli-execution-modes.md` (new file)
**Action:** CREATE
**Source:** [Impl], [PR #7096]

**Draft Content:**

```markdown
---
title: Claude CLI Execution Modes
read-when:
  - writing commands that run in both interactive and CI contexts
  - debugging commands that work locally but fail in GitHub Actions
  - understanding --print mode behavioral differences
tripwires: 0
---

# Claude CLI Execution Modes

## Overview

Claude CLI has two primary execution modes with different behavioral characteristics.

## Mode Comparison

| Feature | Interactive Mode | `--print` Mode (CI) |
|---------|-----------------|---------------------|
| Invocation | `/command` or `claude` | `claude --print "/command"` |
| Used by | Local development | GitHub Actions workflows |
| Stdin interaction | Yes | No |
| `context: fork` isolation | Yes | **No** (loads inline) |
| Task tool isolation | Yes | Yes |
| Multi-turn tool use | Yes | Yes |

## The Critical Difference: Subagent Isolation

The most significant behavioral difference affects subagent creation:

**context: fork**:
- Interactive: Creates separate agent context with own session ID
- `--print`: Loads skill content inline, contaminating parent context

**Task tool**:
- Interactive: Creates separate agent context
- `--print`: Creates separate agent context (works identically)

## Testing Commands for Both Modes

Commands destined for CI workflows should be tested in both modes:

```bash
# Interactive test
/your-command args

# CI simulation
claude --print "/your-command args"
```

Verify:
1. All phases execute (not just first phase)
2. Expected artifacts are produced
3. Session logs show separate session IDs for subagent work

## When to Use Task Tool

Use explicit Task tool delegation (not `context: fork`) when:
- Command will run via `--print` in CI
- Skill has terminal output instructions
- Multi-phase workflow where isolation failure would be catastrophic
- You need guaranteed isolation regardless of execution mode

See `.claude/commands/erk/pr-address.md` for an implementation example (grep for "Task tool").
```

---

#### 8. Remote workflow debugging techniques

**Location:** `docs/learned/ci/debugging-remote-workflows.md` (new file)
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Debugging Remote Workflows
read-when:
  - remote workflow succeeded but produced no changes
  - investigating why a GitHub Actions Claude workflow failed silently
  - debugging multi-phase command execution in CI
tripwires: 0
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
```

---

#### 9. Update pr-address-workflows.md with implementation notes

**Location:** `docs/learned/erk/pr-address-workflows.md`
**Action:** UPDATE
**Source:** [PR #7096]

**Draft Content:**

Add a section "Remote Workflow Implementation Notes":

```markdown
## Remote Workflow Implementation Notes

### Classifier Isolation

The remote workflow uses `claude --print` for non-interactive execution. Due to `context: fork` limitations in this mode (see `docs/learned/claude-code/context-fork-feature.md`), the pr-feedback-classifier MUST be invoked via explicit Task tool delegation, not skill invocation.

See `.claude/commands/erk/pr-address.md`, grep for "Phase 1: Classify Feedback" to find the Task tool pattern. The same pattern is used in Phase 4 verification.

This ensures all 5 phases execute reliably:
1. Classify Feedback (via Task tool)
2. Batch Changes
3. Commit and Push
4. Final Verification (via Task tool)
5. Summary

### Why This Matters

Without proper isolation, the classifier's "Output ONLY JSON" instruction would contaminate the parent context, causing the workflow to terminate after Phase 1 with no commits, no resolved threads, and a deceptive "success" status.
```

---

#### 10. Terminal instruction contamination failure mode

**Location:** `docs/learned/architecture/task-context-isolation.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add a section explaining the contamination failure mode:

```markdown
## Terminal Instruction Contamination

### The Failure Mode

When `context: fork` fails to create isolation (e.g., in `--print` mode), skill instructions become parent instructions. Skills with terminal output instructions are particularly dangerous:

**Example problematic skill instruction:**
"Output ONLY the following JSON (no prose, no markdown, no code fences)"

**What happens when fork fails:**
1. Skill content loads inline into parent context
2. "Output ONLY JSON" becomes the parent's instruction
3. Parent outputs the structured data
4. Parent stops execution (following the "only" directive)
5. Remaining workflow phases are abandoned
6. Workflow exits with success status (no errors occurred)

### Diagnosis

**Symptoms:**
- Workflow reports success but produces no commits/changes
- Session has very few turns (only first phase completes)
- Final output is JSON (from what should have been a subagent)
- All tool calls share the same session ID (no fork occurred)

**Prevention:**
- Use Task tool for guaranteed isolation in CI contexts
- Test commands with `claude --print` before committing
- Verify subagent isolation by checking session IDs in logs
```

---

#### 11. Test multi-mode commands before CI deployment tripwire

**Location:** `docs/learned/commands/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add to existing tripwires:

```markdown
## Test Commands in Target Execution Mode

**Trigger:** Before committing commands invoked by GitHub Actions workflows

**Warning:** Features that work in interactive mode may fail in `--print` mode. `context: fork` is the most notable example - it creates isolation interactively but loads inline in `--print` mode.

**Prevention:**
1. Test locally with `claude --print '/command args'`
2. Verify all phases execute, not just first phase
3. Check that expected artifacts are produced
4. If isolation is needed, use explicit Task tool delegation
```

---

## Contradiction Resolutions

### 1. context: fork recommendation for reusable patterns

**Existing doc:** `docs/learned/claude-code/context-fork-feature.md`
**Also:** `docs/learned/architecture/task-context-isolation.md`
**Conflict:** Both documents recommend `context: fork` for reusable patterns, but new insight reveals it fails in `--print` mode

**Resolution:** This is NOT a true contradiction - it's context-dependent correctness. Both recommendations are valid in their contexts:
- `context: fork` works correctly in INTERACTIVE mode
- `context: fork` FAILS in `--print` mode (CI contexts)

**Action:** Add "Execution Mode Limitations" subsections to both docs clarifying when each recommendation applies. Do NOT delete or merge - preserve both recommendations with execution context clarification.

### 2. Stale phantom references

**Document:** `docs/learned/architecture/task-context-isolation.md`
**Phantom ref:** `/erk:pr-preview-address` (command does not exist)

**Document:** `docs/learned/claude-code/context-fork-feature.md`
**Phantom refs:** `.claude/commands/local/audit-doc.md`, `audit-scan.md` (commands do not exist)

**Resolution:** UPDATE_REFERENCES - remove phantom command references. Core pattern documentation in both files remains valid and accurate.

## Stale Documentation Cleanup

### 1. task-context-isolation.md phantom reference

**Location:** `docs/learned/architecture/task-context-isolation.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `/erk:pr-preview-address`
**Cleanup Instructions:** Search for and remove reference to the non-existent `/erk:pr-preview-address` command. The surrounding technical content about Task context isolation remains accurate.

### 2. context-fork-feature.md phantom references

**Location:** `docs/learned/claude-code/context-fork-feature.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `.claude/commands/local/audit-doc.md`, `audit-scan.md`
**Cleanup Instructions:** Search for and remove references to these non-existent command files. The feature explanation and usage guidance remains accurate.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Skill Fork Failure in Non-Interactive Mode

**What happened:** The pr-address remote workflow reported success but made no commits. Investigation revealed the pr-feedback-classifier skill's `context: fork` didn't create isolation in `--print` mode, causing the "Output ONLY JSON" instruction to contaminate the parent context and terminate execution after Phase 1.

**Root cause:** `context: fork` is a declarative mechanism that doesn't function identically across execution modes. In `--print` mode, the skill content loads inline rather than creating a true subagent.

**Prevention:** For commands that run in CI via `--print`, use explicit Task tool delegation instead of relying on `context: fork`. Test commands with `claude --print` before committing.

**Recommendation:** TRIPWIRE - This is the highest-value prevention item (score 8/10).

### 2. Trusting GitHub Actions Success Status

**What happened:** Initial investigation assumed the green checkmark meant success. The user had to correct the agent: "i don't see the commit and the pr threads are unresolved."

**Root cause:** GitHub Actions reports success based on exit code (0), not whether the workflow produced expected outputs. Claude sessions can exit cleanly without completing intended work.

**Prevention:** Always verify expected artifacts (commits, file changes, resolved threads) rather than trusting job status alone.

**Recommendation:** TRIPWIRE - CI verification pattern deserves a tripwire (score 5/10).

### 3. Multi-Phase Workflow Vulnerability

**What happened:** A 5-phase workflow silently terminated after Phase 1 with no indication of failure.

**Root cause:** When subagent isolation fails and terminal instructions contaminate the parent, the parent completes "successfully" but abandons remaining phases.

**Prevention:** Test multi-phase commands in target execution mode. Verify all phases execute, not just the first.

**Recommendation:** TRIPWIRE - Multi-phase command authors need this warning (score 6/10).

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. context: fork --print mode failure

**Score:** 8/10 (criteria: Non-obvious +2, Cross-cutting +2, Destructive potential +2, Silent failure +2)
**Trigger:** Before invoking skills with `context: fork` in commands that run via `claude --print` in CI
**Warning:** `context: fork` metadata does NOT create subagent isolation in `--print` mode. The skill content loads inline. If the skill has terminal output instructions, those contaminate the parent and cause premature termination. Use explicit Task tool delegation instead.
**Target doc:** `docs/learned/claude-code/tripwires.md` (new)

This is the most critical tripwire candidate. The failure is completely silent - workflow reports success, no exceptions are thrown, and without checking actual outputs, the problem is invisible. The pattern affects ALL commands that invoke forked skills in CI contexts.

### 2. Multi-phase command premature termination

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before writing multi-phase commands that use subagent isolation
**Warning:** Multi-phase commands can terminate prematurely if subagent isolation fails. The parent receives terminal instructions from the failed fork and stops before executing remaining phases. Test with `claude --print` and verify ALL phases execute.
**Target doc:** `docs/learned/commands/tripwires.md`

This affects ANY multi-phase command (not just pr-address). The pr-address fix is one instance, but without a tripwire, the pattern will recur.

### 3. GitHub Actions false success verification

**Score:** 5/10 (criteria: Non-obvious +2, Silent failure +2, Repeated pattern +1)
**Trigger:** After GitHub Actions workflow reports success, before assuming work was done
**Warning:** GitHub Actions success (exit 0) does NOT guarantee expected outputs. Verify commits, file changes, and thread states exist. Check session logs for actual outputs vs just completion.
**Target doc:** `docs/learned/ci/workflow-verification-patterns.md` (new) or `docs/learned/ci/tripwires.md`

This is a general CI debugging principle that applies beyond the specific fork issue.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Testing commands in both execution modes

**Score:** 3/10 (criteria: Non-obvious +2, External tool quirk +1)
**Notes:** Could be elevated to full tripwire if more CI failures occur due to mode differences. Currently lower priority because it's subsumed by the more specific `context: fork` tripwire.

### 2. Session ID tracking for isolation verification

**Score:** 3/10 (criteria: Non-obvious +2, External tool quirk +1)
**Notes:** Useful debugging technique but narrow scope - only relevant when diagnosing isolation failures specifically. Good to mention in debugging docs but not tripwire-worthy on its own.