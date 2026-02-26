# Documentation Plan: Update CHANGELOG.md Unreleased section with 100 commits

## Context

This session executed a routine administrative task: synchronizing CHANGELOG.md with 100 commits across the erk repository. The workflow demonstrates erk's plan mode behavior where `/local:changelog-update` delegates commit categorization to a subagent, then the ExitPlanMode hook intercepts to offer a save-or-implement decision point.

While the changelog update itself is self-documenting and requires no additional documentation, the session revealed a valuable cross-cutting pattern: handling large JSON outputs from Task agents. The categorizer agent returned 55KB of structured JSON, and the session shows multiple failed attempts (cat, grep, head, Read) before discovering that persisted tool output requires Python JSON parsing directly on the file path. This pattern applies to any command using Task agents with large output expectations.

The session also surfaced clarification opportunities for plan mode documentation: which commands require branch+PR context versus plan-mode compatible commands, and how the ExitPlanMode hook interacts with workflow skills. These are refinements to existing docs rather than new documentation needs.

## Raw Materials

PR #8316

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 3 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score>=4) | 1 |
| Potential tripwires (score 2-3) | 2 |

## Documentation Items

### HIGH Priority

#### 1. Large subagent output handling pattern

**Location:** `docs/learned/planning/subagent-output-handling.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - launching Task agent expecting JSON output
  - tool result shows persisted-output marker
  - handling large subagent returns
---

# Handling Large Subagent Output

When Task agents return large outputs (typically >20KB), Claude Code persists the result to a file rather than displaying inline.

## Recognition

Look for the `<persisted-output>` marker in tool_result:

```
<persisted-output>
File: /path/to/.erk/scratch/sessions/.../tool-output.json
Preview: [first 500 chars]
</persisted-output>
```

## Correct Pattern

When you see `<persisted-output>`:

1. **Do NOT** attempt Read, cat, grep, or head on the file
2. **Do** use Python to parse the JSON file directly
3. Extract the specific data you need from the parsed structure

## Why This Matters

The session that discovered this pattern wasted 3-4 attempts trying standard file reading approaches:
- `cat file.json | grep pattern` - output truncated
- `Read file.json` - too large for inline display
- `head -100 file.json` - missed needed data

All failed because the persisted output is structured JSON meant for programmatic access.

## Example

See `packages/erk-dev/src/erk_dev/commands/changelog_commits/command.py` for a command that produces large JSON output requiring this handling pattern.
```

---

### MEDIUM Priority

#### 1. Plan mode command compatibility guidance

**Location:** `docs/learned/planning/plan-mode-restrictions.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add a new section to existing plan-mode-restrictions.md:

```markdown
## Command Context Requirements

Commands vary in their context requirements. Before invoking, understand whether a command:

### Requires branch + PR context

These commands operate on "current branch's PR" and will fail in plan mode or on trunk:
- `/erk:pr-address` - needs active PR to fetch review comments
- `/erk:pr-preview-address` - same as pr-address
- `erk pr submit` - needs branch with unpushed commits

### Plan-mode compatible

These commands work without a PR context:
- `/erk:plan-save` - creates new PR from plan
- `/local:changelog-update` - works on any branch
- `/erk:objective-plan` - creates plans from objectives

### Context validation

When authoring commands that launch expensive subagents:
- Validate context requirements before delegation
- Return structured error JSON if requirements not met
- Include guidance on correct invocation in error message
```

---

#### 2. Changelog workflow + plan mode interaction

**Location:** `docs/learned/planning/plan-mode-workflows.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - working with skills that invoke ExitPlanMode
  - understanding plan mode hook interaction
  - changelog update workflow
---

# Plan Mode Workflow Coordination

Skills that invoke ExitPlanMode undergo hook interception before completing.

## The Pattern

1. Skill executes (e.g., `/local:changelog-update`)
2. Skill delegates to subagent for processing (e.g., commit categorization)
3. Agent writes plan to file and calls ExitPlanMode
4. **Hook intercepts** - displays plan contents and offers decision:
   - Create plan PR (recommended on trunk)
   - Implement directly
   - View/edit plan
5. User choice determines next action

## Why Hook Prompts After Agent Shows Proposal

The agent displays a proposal, then the hook displays the same plan contents. This apparent duplication serves a purpose:
- Agent's display is informational (showing what was generated)
- Hook's display is actionable (offering save/implement decision)
- Hook provides trunk-safety warning that agent doesn't

## Important Behaviors

- Skills should NOT assume immediate implementation after ExitPlanMode
- Hook stdout becomes Claude's context for next action
- After `/erk:plan-save`, agent should STOP (not call ExitPlanMode again)

## Example Flow

See `.claude/commands/local/changelog-update.md` for the complete workflow specification and `.claude/hooks/exit-plan-mode-hook.md` for hook behavior.
```

---

### LOW Priority

None.

## Contradiction Resolutions

None found. All existing documentation is consistent with session behavior.

## Stale Documentation Cleanup

None found. All referenced artifacts verified to exist:
- `.claude/commands/local/changelog-update.md`
- `.claude/agents/changelog/commit-categorizer.md`
- `packages/erk-dev/src/erk_dev/commands/changelog_commits/command.py`

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Repeated attempts to read large tool output

**What happened:** Agent tried cat, grep, head, and Read to extract data from 55KB JSON file
**Root cause:** Standard file reading approaches fail or truncate when tool output is persisted to a file due to size
**Prevention:** Recognize `<persisted-output>` marker immediately; use Python JSON parsing on the persisted file path
**Recommendation:** TRIPWIRE - this is cross-cutting and non-obvious

### 2. pr-address invoked without PR context

**What happened:** User ran `/erk:pr-address` on master branch without specifying `--pr` flag
**Root cause:** Command expects branch with associated PR; user had just saved a plan PR but was still on master
**Prevention:** Command correctly returned structured error; documentation could clarify context requirements
**Recommendation:** ADD_TO_DOC - include in plan mode command compatibility section

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Large subagent output handling

**Score:** 4/10 (criteria: Cross-cutting +2, Repeated pattern +1, Non-obvious +1)
**Trigger:** Before launching Task agent with large output expectations, or when tool result shows `<persisted-output>` marker
**Warning:** Check for `<persisted-output>` marker in tool_result. If present, use Python JSON parsing directly on the persisted file path. Skip Read/cat/grep attempts - they will fail or truncate.
**Target doc:** `docs/learned/planning/tripwires.md`

This is tripwire-worthy because:
- It applies to any command using Task agent with JSON output, not just changelog workflows
- The session shows 3-4 failed attempts before the agent found the working approach
- Agent training suggests Read and grep for file access, but persisted-output requires a fundamentally different pattern
- Without this guidance, future agents will waste context on the same failed approaches

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Command context validation before subagent launch

**Score:** 3/10 (criteria: Cross-cutting +2, Non-obvious +1)
**Notes:** The pr-address command launched the classifier subagent before validating PR existence. The expensive operation failed due to missing context. However, the error handling was correct and the failure was recoverable. Not promoted to tripwire because: (1) the command did return a proper structured error, (2) the cost is one subagent invocation, not catastrophic, (3) fixing this is a code improvement, not a documentation need.

### 2. Plan mode workflow coordination

**Score:** 2/10 (criteria: Cross-cutting +2)
**Notes:** Skills that invoke ExitPlanMode should not assume immediate implementation due to hook interception. However, this is by-design behavior, not an error pattern. The hook exists precisely to intercept and offer decisions. Score too low for tripwire status because it's working as intended - no harm occurs, just a UX pattern to understand.
