# Documentation Plan: Add "erk learn" option to land learn-check menu

## Context

This implementation added a 4th menu option to the learn-status check during `erk land` execution. Previously, when a plan branch had not been learned from, users were presented with 3 options: trigger async learn, continue without learning, or cancel. The new 4th option allows users to run `erk learn {plan_number}` manually in a separate terminal session, giving them the ability to interactively review and guide the learning process rather than using the automated async workflow.

The documentation matters because the implementation touched several patterns that future agents need to understand: menu expansion in Click-based CLIs, the relationship between IntRange validators and option counts, and importantly, diagnosing Graphite stack issues when empty branches block PR submission. The session encountered significant friction with Graphite stacks when an empty parent branch (from a previous failed worktree creation) blocked submission. This debugging cycle consumed substantial time and represents a common failure mode that should be documented to prevent future agents from repeating the investigation.

Key insights from this implementation include: the 4th menu option follows the existing SystemExit(0) pattern for user-initiated cancellation; the test uses monkeypatch with click.prompt to simulate user input; and the troubleshooting workflow for empty Graphite branches involves `gt info`, `gt ls`, and `gt upstack onto` commands to diagnose and bypass blocking branches.

## Raw Materials

https://gist.github.com/schrockn/0a8c1c799b930d36204b6874cbb965da

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 9     |
| Contradictions to resolve      | 1     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score2-3) | 4     |

## Contradiction Resolutions

### 1. Tripwire promotion status mismatch

**Existing doc:** `docs/learned/planning/tripwire-promotion-workflow.md`
**Conflict:** The doc describes tripwire promotion as part of the land pipeline, but git commit 6e5fbcc55 "Remove tripwire promotion from land execution pipeline (#6954)" was merged on the same day. The actual PR diff shows NO tripwire promotion code, only the menu option change.
**Resolution:** Verify whether tripwire-promotion-workflow.md still reflects current functionality. If tripwire promotion has been removed from the land pipeline, the doc needs updating to reflect that extraction and promotion is a separate concern from landing. The plan title appears to reference stale scope.

## Documentation Items

### HIGH Priority

#### 1. Empty branch blocking Graphite stack submission

**Location:** `docs/learned/erk/graphite-stack-troubleshooting.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Graphite Stack Troubleshooting
read_when:
  - "PR submission fails with 'no changes' error"
  - "Graphite stack has empty branches"
  - "debugging gt upstack onto failures"
tripwires:
  - action: "Before submitting PRs in Graphite stacks"
    warning: "Validate all ancestor branches have commits. Empty branches block entire stack. Use `gt info` to diagnose, `gt upstack onto` to fix."
---

# Graphite Stack Troubleshooting

## Empty Branch Blocking Submission

**Problem**: PR submission fails with "no changes" or similar error, even though your working branch has changes.

**Root cause**: An ancestor branch in the Graphite stack has no commits (empty branch). This commonly happens when a worktree creation fails partway through, leaving a branch that was created but never received commits.

## Diagnostic Workflow

**Step 1: Check parent branch status**

See `gt info --branch <parent>` in Graphite CLI documentation for checking branch metadata including commit status.

**Step 2: List stack structure**

Use `gt ls` to visualize the entire stack and identify which branches exist.

**Step 3: Identify empty branches**

For each ancestor, check if commits exist with `git log <parent>..HEAD`. If empty, that branch is blocking.

## Resolution: Skip Empty Branch

When an empty ancestor branch is identified, use `gt upstack onto` to re-parent your branch to a valid ancestor:

See `gt upstack onto <valid-ancestor>` in Graphite CLI documentation for re-parenting branches.

This removes the empty branch from your stack lineage, allowing submission to proceed.

## Prevention

Before running PR submission workflows, validate that the current branch and all ancestors have commits. A tripwire in planning/tripwires.md covers this check.

## Related

- [PR Submit Pipeline Architecture](../cli/pr-submit-pipeline.md)
- [Planning Tripwires](../planning/tripwires.md)
```

---

#### 2. 4th menu option in land learn-check flow

**Location:** `docs/learned/cli/learn-plan-land-flow.md`
**Action:** UPDATE
**Source:** [PR #6956]

**Draft Content:**

```markdown
## Learn Status Menu Options

The `check_learn_status()` step presents a four-choice menu when landing a plan branch that has not been learned from. See `_prompt_async_learn_and_continue()` in `src/erk/cli/commands/land_cmd.py`.

**Option 4: Run erk learn manually**

Added in PR #6956. When selected:
- Prints to stderr: "Run this command to learn from the plan:"
- Prints to stderr: "  erk learn {plan_number}"
- Exits with SystemExit(0) (same pattern as cancel)

This option is useful when users want an interactive learn session rather than async, but do not want to type the plan number manually.

**Implementation note**: The IntRange validator must match the option count. When option 4 was added, IntRange changed from (1, 3) to (1, 4).
```

---

#### 3. Stack validation before PR submit

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl]

**Draft Content:**

```markdown
**CRITICAL: Before running `erk:pr-submit` or PR submission workflows** -> Read [Graphite Stack Troubleshooting](../erk/graphite-stack-troubleshooting.md) first. Check `git log <parent>..HEAD` shows at least 1 commit. If empty, investigate stack structure with `gt info` and `gt ls`.
```

---

### MEDIUM Priority

#### 4. Click IntRange validation pattern

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl]

**Draft Content:**

```markdown
**CRITICAL: Before adding options to Click interactive menus** -> Always update IntRange validator to match new option count (e.g., IntRange(1, 3) -> IntRange(1, 4)). Failure causes runtime validation errors when users select the new option.
```

---

#### 5. Menu option expansion pattern

**Location:** `docs/learned/cli/learn-plan-land-flow.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Adding Menu Options to Interactive Prompts

When adding a new option to Click interactive menus (like the learn-status prompt), follow this checklist:

1. **Update display text**: Add the new option line with appropriate numbering
2. **Update IntRange validator**: Extend the range to include the new option number
3. **Add choice handler**: Add `elif choice == N:` block with the new behavior
4. **Update docstring**: Change "three choices" to "four choices" etc.
5. **Add test**: Verify the new option behavior with monkeypatch

See `_prompt_async_learn_and_continue()` in `src/erk/cli/commands/land_cmd.py` for reference implementation.
```

---

#### 6. Fast mode API limitations

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl]

**Draft Content:**

```markdown
**CRITICAL: When PR submission fails with 'Fast mode not available via API'** -> Report to user that manual `/fast` toggle is required. Do not retry automatically. This is a Claude Code API limitation, not an erk bug.
```

---

#### 7. Click prompt testing pattern

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [PR #6956]

**Draft Content:**

```markdown
## Testing Interactive Click Prompts

When testing commands that use `click.prompt()` for user input, use monkeypatch to control the return value:

**Pattern**: See `test_check_learn_status_and_prompt_manual_learn_prints_command_and_exits` in `tests/unit/cli/commands/land/test_learn_status.py` for a complete example.

Key techniques:
- Use `monkeypatch.setattr("click.prompt", lambda **kwargs: 4)` to simulate user selecting option 4
- Capture output with `capsys` fixture to verify printed messages
- Check for `SystemExit` with `pytest.raises(SystemExit)` for cancel/exit behaviors
- Combine with FakeConsole and FakeGitHubIssues for full test isolation
```

---

#### 8. WIP commit handling in plan execution

**Location:** `docs/learned/planning/plan-execution-patterns.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Plan Execution Patterns
read_when:
  - "implementing plans in worktrees"
  - "handling WIP commits during implementation"
---

# Plan Execution Patterns

## WIP Commit Handling

When changes are pre-committed as "WIP" (work in progress), agents should work with the existing commit structure rather than amending.

**Why**: The git safety protocol restricts commit --amend to specific scenarios:
1. User explicitly requested amend
2. Adding edits from pre-commit hook

**Anti-pattern**: Amending a WIP commit made by another process or earlier in the session without checking authorship.

**Correct pattern**: Treat WIP commits as valid starting points. Add new commits on top or create fixup commits if cleanup is needed later.

See git safety protocol in CLAUDE.md for complete rules.
```

---

### LOW Priority

#### 9. Script-aware output pattern reinforcement

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE (enhance existing)
**Source:** [Impl]

**Draft Content:**

```markdown
**Example**: Interactive CLI options that print commands for users to run should use `user_output()` (stderr) to avoid interfering with script capture. The 4th learn-status menu option prints the erk learn command to stderr so it displays to users but does not pollute stdout for scripts that might capture command output.
```

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Empty Graphite branch blocking PR submission

**What happened:** After creating a worktree that failed partway through, the agent attempted to submit a PR but encountered "no changes" errors. The actual working branch had changes, but a parent branch in the Graphite stack was empty.
**Root cause:** Worktree creation left behind an empty branch when it failed after branch creation but before committing changes.
**Prevention:** Before PR submission, validate all ancestor branches have commits using `git log <parent>..HEAD`.
**Recommendation:** TRIPWIRE (score: 6)

### 2. Fast mode API limitation during PR submission

**What happened:** PR submission workflow failed with "Fast mode not available via API" error.
**Root cause:** Claude Code's fast mode cannot be toggled programmatically through the API.
**Prevention:** When this error occurs, inform the user that manual `/fast` toggle is required. Do not retry automatically.
**Recommendation:** TRIPWIRE (score: 3)

### 3. IntRange validator mismatch after adding menu option

**What happened:** If IntRange is not updated when adding a menu option, selecting the new option causes a validation error.
**Root cause:** Click's IntRange validator rejects values outside the specified range.
**Prevention:** Always update IntRange bounds when adding menu options.
**Recommendation:** ADD_TO_DOC (score: 3, borderline tripwire)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Empty branch blocking Graphite stack submission

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before submitting PRs in Graphite stacks
**Warning:** Validate all ancestor branches have commits. Empty branches block entire stack. Use `gt info` to diagnose, `gt upstack onto` to fix.
**Target doc:** `docs/learned/planning/tripwires.md`

This is tripwire-worthy because empty branches are a non-obvious failure mode. The error message ("no changes") does not indicate the root cause (empty ancestor). Without this tripwire, agents waste significant time debugging stack structure when a simple `git log` check would identify the problem immediately. The pattern affects any Graphite stack workflow, making it cross-cutting.

### 2. Stack validation before PR submit

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** Before running `erk:pr-submit` or PR submission workflows
**Warning:** Check `git log <parent>..HEAD` shows at least 1 commit. If empty, investigate stack structure with `gt info` and `gt ls`.
**Target doc:** `docs/learned/planning/tripwires.md`

This generalizes the empty branch tripwire to all PR submission contexts. The pre-submission validation prevents the more expensive debugging cycle that occurs after submission fails.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Click IntRange validation when adding menu options

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)
**Notes:** Specific to interactive CLI prompts. While the error is clear when it occurs (validation error), the fix requires understanding Click's IntRange behavior. Promotion warranted if this pattern appears in more CLI commands.

### 2. Fast mode API limitations

**Score:** 3/10 (criteria: Non-obvious +2, External tool quirk +1)
**Notes:** Specific to Claude Code API context. Cannot be fixed by the agent. Promotion depends on how frequently this error is encountered in workflows.

### 3. Testing interactive prompts with Click

**Score:** 2/10 (criteria: Non-obvious +2)
**Notes:** Standard testing pattern but the monkeypatch approach for click.prompt is not immediately obvious. Covered by example in testing docs rather than tripwire.

### 4. WIP commit handling in git safety protocol

**Score:** 2/10 (criteria: Non-obvious +2)
**Notes:** Edge case of existing git safety rules. Clarification rather than new constraint. The git safety protocol already covers amend restrictions; this documents when NOT to amend.