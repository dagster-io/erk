Change the draft PR "Next steps" output so that the `erk br co` command uses the branch name instead of the PR number.

## Current behavior

When a plan is saved as a draft PR, the "Outside Claude Code" next steps show:

```
Local: erk br co 7646 && erk implement --dangerous
```

## Desired behavior

```
Local: erk br co <branch_name> && erk implement --dangerous
```

Where `<branch_name>` is the actual git branch name of the draft PR (e.g., `sc/my-feature-branch`).

## Files to change

### 1. `packages/erk-shared/src/erk_shared/output/next_steps.py`

- Add a `branch_name: str` field to the `DraftPRNextSteps` frozen dataclass
- Update the `checkout_and_implement` property to use `self.branch_name` instead of `self.pr_number`
- Update `format_draft_pr_next_steps_plain` to accept `branch_name: str` parameter and pass it to `DraftPRNextSteps`

### 2. All callers of `format_draft_pr_next_steps_plain` and `DraftPRNextSteps`

Find all callers and update them to pass the branch name. The branch name should already be available in the JSON output from `plan-save` and `plan-update-issue` commands (the `branch_name` field).

### 3. `.claude/commands/erk/plan-save.md`

In the "Step 4: Display Results" section, change the draft PR next steps template from:

```
Local: erk br co <issue_number> && erk implement --dangerous
```

to:

```
Local: erk br co <branch_name> && erk implement --dangerous
```

where `<branch_name>` comes from the JSON output's `branch_name` field.

### 4. Any other skills/commands that display the same next steps

Search for other `.claude/commands/` or `.claude/skills/` files that show `erk br co <issue_number>` in draft PR context and update them similarly.

## Notes

- The `erk plan-save` and `erk plan-update-issue` commands already return `branch_name` in their JSON output, so the data is available.
- The `erk plan submit` command should continue to use the PR number (not branch name) since that's an erk CLI command that takes issue numbers.
- Only the `erk br co` command should switch to branch name, since that's how users naturally think about checking out branches.

