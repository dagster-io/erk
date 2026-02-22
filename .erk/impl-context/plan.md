# Documentation Plan: Eliminate erk:prepare command and documentation

## Context

PR #7805 successfully removed the `/erk:prepare` slash command and `PREPARE_SLASH_COMMAND` constant from the erk codebase, consolidating worktree preparation into the existing `erk br create --for-plan` workflow. The PR was correctly implemented on its branch and squash-merged to master.

The primary learning from this PR is not about the implementation itself, but about documentation hygiene: four documentation files in `docs/learned/` still contain phantom references to the deleted `/erk:prepare` command. These stale references would cause agents to attempt executing non-existent commands, wasting time and creating confusion. The replacement workflow (`erk br create --for-plan`) is already extensively documented, so this is purely a cleanup task.

This learn plan focuses on removing stale documentation references and adding a tripwire to prevent future phantom command references in documentation. No new documentation creation is needed.

## Raw Materials

PR #7805

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 4     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 1     |
| Potential tripwires (score2-3) | 1     |

## Stale Documentation Cleanup

Existing docs with phantom references requiring immediate action:

### 1. agent-commands.md - Remove /erk:prepare example

**Location:** `docs/learned/claude-code/agent-commands.md`
**Action:** DELETE_STALE_ENTRY
**Source:** [PR #7805]

**Cleanup Instructions:**

Remove `/erk:prepare` from the example list of conversation-context extraction patterns. Keep other valid command examples like `/erk:plan-submit`, `/erk:pr-address-remote`. This is a targeted deletion - remove only the reference to the non-existent command.

### 2. next-steps-output.md - Remove PREPARE_SLASH_COMMAND documentation

**Location:** `docs/learned/planning/next-steps-output.md`
**Action:** DELETE_STALE_ENTRY
**Source:** [PR #7805]

**Cleanup Instructions:**

Remove documentation of the `PREPARE_SLASH_COMMAND` constant which no longer exists in the codebase. Remove "Prepare worktree: /erk:prepare" from next-steps output examples. Update any format examples to show the simplified output without the prepare reference. The constant was removed from `packages/erk-shared/src/erk_shared/output/next_steps.py`.

### 3. command-boundaries.md - Remove /erk:prepare delegation example

**Location:** `docs/learned/architecture/command-boundaries.md`
**Action:** DELETE_STALE_ENTRY
**Source:** [PR #7805]

**Cleanup Instructions:**

Remove the `/erk:prepare` row from the agent-delegating-to-CLI table. Keep other valid examples of command delegation patterns. If the row removal leaves a gap in the table's illustrative examples, consider whether another valid command could serve as a replacement example, but do not invent new examples - only use existing, documented commands.

### 4. command-organization.md - Remove prepare from top-level list

**Location:** `docs/learned/cli/command-organization.md`
**Action:** DELETE_STALE_ENTRY
**Source:** [PR #7805]

**Cleanup Instructions:**

Remove `prepare` from the top-level plan operations list. The document already extensively covers `erk br create --for-plan` as the official workflow for plan preparation. Clarify that plan commands are: `implement`, `checkout`, `sync` (but NOT `prepare`). The hidden `prepare_cwd_recovery_cmd` is an internal recovery mechanism and should not be documented as user-facing.

## Documentation Items

### HIGH Priority

All HIGH priority items are stale documentation cleanup actions listed above.

### MEDIUM Priority

#### 1. Pre-existing verbatim code blocks (Documentation Debt)

**Location:** `docs/learned/cli/command-organization.md`
**Action:** UPDATE (future work)
**Source:** [PR #7805 - audit-pr-docs bot comment]

This is pre-existing documentation debt, not introduced by PR #7805. The file contains 2 verbatim code blocks (import patterns, add_command registration) with HIGH drift risk. Future work should convert these to conceptual descriptions with cross-references to code.

**Note:** This is a cleanup opportunity for future work, not part of the immediate PR #7805 learnings.

#### 2. Duplicative property tables in next-steps-output.md

**Location:** `docs/learned/planning/next-steps-output.md`
**Action:** UPDATE (future work)
**Source:** [PR #7805 - audit-pr-docs bot comment]

Pre-existing issue: duplicative property tables reproducing dataclass string templates. Future work should reference dataclass location instead of reproducing implementation details.

**Note:** Separate from the immediate stale reference cleanup.

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Verify command existence before documenting

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before referencing slash commands or CLI commands in documentation
**Warning:** VERIFY the command actually exists. Check `.claude/commands/` for slash commands, `src/erk/cli/` for CLI commands. DO NOT document commands that "should exist" or "will be created" - only document what exists NOW.
**Target doc:** `docs/learned/documentation/tripwires.md`

This tripwire is critical because documentation can reference deleted commands without obvious signals. There are no broken links, no grep failures in markdown - the phantom reference silently persists. When agents follow stale documentation, they attempt to execute non-existent commands, wasting time and creating confusion.

The pattern observed in PR #7805: the `/erk:prepare` command was removed from the codebase, but four documentation files continued referencing it. Without active verification, these phantom references accumulate silently.

**Prevention protocol:**
1. When documenting commands, verify the command file exists
2. When removing commands, grep `docs/learned/` for all references
3. Update or remove each reference as part of the deletion PR
4. Add command existence verification to documentation review checklists

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Verbatim code blocks in documentation

**Score:** 3/10 (Cross-cutting +2, Repeated pattern +1)
**Notes:** Identified by audit-pr-docs bot as a recurring pattern affecting multiple files. Did not meet threshold because: (1) not non-obvious - linters can detect it, (2) low destructive potential - causes drift over time rather than immediate failure. May warrant promotion if drift issues become more prevalent.

## Verification Commands

To verify cleanup completeness after updates:

```bash
# Should return 0 results after cleanup
rg --type=md "/erk:prepare" docs/learned/

# Should return 0 results after cleanup
rg --type=md "PREPARE_SLASH_COMMAND" docs/learned/

# Should return 0 results after cleanup (except hidden prepare_cwd_recovery_cmd)
rg --type=md "erk prepare" docs/learned/
```

## Success Criteria

- [ ] All 4 documentation files updated to remove phantom references
- [ ] Verification commands return 0 results
- [ ] Replacement workflow (`erk br create --for-plan`) remains documented
- [ ] No new documentation created (cleanup only)
- [ ] Tripwire added to prevent future phantom command references

## Anti-Patterns to Avoid

- Creating new documentation about the `/erk:prepare` removal
- Documenting "why this command was removed" historical context
- Adding deprecation notices (command is already deleted, not deprecated)
- Treating this as an implementation failure (it was not - PR correctly implemented all changes)

Simply delete the stale references and add the tripwire to prevent recurrence.
