# Plan: Changelog Update in Plan Cycle

## Overview

Add guidance to `/local:changelog-update` for running changelog updates through the full erk plan cycle (GitHub issue + branch + PR).

## Approach

Modify the existing command to detect plan mode and behave differently:

**Normal mode (current):** Analyze → Propose → Approve → Update (all in one session)

**Plan mode (new):** Analyze → Write proposal to plan file → Exit plan mode → User runs `/erk:plan-implement`

## Changes to `.claude/commands/local/changelog-update.md`

### 1. Add Plan Mode Section at Top

Add a new section after the Usage section explaining the plan cycle workflow:

```markdown
## Plan Cycle Workflow

To run changelog updates through the full plan cycle (GitHub issue + branch + PR):

1. Enter plan mode first
2. Run `/local:changelog-update`
3. Review the proposal written to the plan file
4. Exit plan mode
5. Choose "Implement now" when prompted
```

### 2. Add Plan Mode Detection in Agent Instructions

Add a new phase between "Get Commits" and "Analyze and Categorize":

```markdown
### Phase 2b: Check for Plan Mode

If plan mode is active (check for "Plan mode is active" in system reminders):
1. Continue with Phase 3 (Analyze and Categorize)
2. In Phase 4, write the proposal to the plan file (from "Plan File Info:" in system reminders) instead of displaying it
3. Skip Phases 5-6 (let /erk:plan-implement handle the update)
4. Call ExitPlanMode when done
```

### 3. Modify Phase 4 for Plan Mode

Update Phase 4 to handle both modes:

```markdown
### Phase 4: Present Proposal

**If NOT in plan mode:** Present the proposal as currently documented and wait for approval.

**If in plan mode:** Write the proposal to the plan file in this format:

```markdown
# Plan: Changelog Update

## Overview

Update CHANGELOG.md with commits since v{version} ({n} commits total).

## Proposed Entries

### Added ({count})
1. `{hash}` - {description}
   - *Reasoning:* {why}

### Changed ({count})
...

### Filtered Out ({count})
...

## Update Details

- **As of marker:** Will be set to `{head_commit}`
- **Section order:** {categories with entries}

## Execution Steps

1. Present proposal for review (awaiting approval)
2. After approval, add "As of `{hash}`" marker to Unreleased section
3. Add entries under appropriate category headers
4. Preserve any existing entries in Unreleased section
```

Then call ExitPlanMode. The /erk:plan-implement workflow will handle saving to GitHub and implementation.
```

## File to Modify

- `.claude/commands/local/changelog-update.md`

## Implementation Notes

- The plan file format matches what I just used for issue #4232 - it worked well
- The "Execution Steps" section in the plan provides guidance for the implementing agent
- This integrates naturally with the existing exit-plan-mode hook flow