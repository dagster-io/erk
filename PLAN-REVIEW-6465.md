# Plan: Add `erk exec update-roadmap-step` command

## Goal

Create an `erk exec update-roadmap-step` command that atomically updates a step's PR cell in an objective's roadmap table. This replaces the ad-hoc Python scripting that was needed in `plan-save` (fetch body → string replace → write body) with a single CLI call.

## Usage

```bash
# Set PR reference for a step
erk exec update-roadmap-step 6423 --step 1.3 --pr "plan #6464"

# Mark step as done with PR
erk exec update-roadmap-step 6423 --step 1.3 --pr "#6500"

# Clear PR reference
erk exec update-roadmap-step 6423 --step 1.3 --pr ""
```

## Output

```json
{
  "success": true,
  "issue_number": 6423,
  "step_id": "1.3",
  "previous_pr": null,
  "new_pr": "plan #6464",
  "url": "https://github.com/..."
}
```

## Files to Create

| File | Purpose |
|------|---------|
| `src/erk/cli/commands/exec/scripts/update_roadmap_step.py` | The Click command |
| `tests/unit/cli/commands/exec/scripts/test_update_roadmap_step.py` | Unit tests |

## Files to Modify

| File | Changes |
|------|---------|
| `src/erk/cli/commands/exec/group.py` | Import and register the new command |

## Implementation

### 1. Command: `update_roadmap_step.py`

Follow the standard exec script pattern:

- `@click.command(name="update-roadmap-step")`
- Args: `ISSUE_NUMBER` (int)
- Options: `--step` (required, str), `--pr` (required, str)
- Use `@click.pass_context` + `require_issues(ctx)` + `require_repo_root(ctx)`

Logic:
1. Fetch issue body via `github.get_issue(repo_root, issue_number)`
2. Parse roadmap with `parse_roadmap(body)` from `objective_roadmap_shared`
3. Find the step matching `--step` across all phases
4. If step not found → error exit
5. Perform string replacement on the raw body to update just the PR cell in the matching table row
6. Write updated body via `github.update_issue_body(repo_root, issue_number, BodyText(content=updated_body))`
7. Output JSON result

**String replacement approach**: Use regex to find the table row matching the step ID and replace the PR cell. The row format is `| <step_id> | <description> | <status> | <pr> |`. Replace the entire row with the same content but updated PR cell and status set to `-` (let status inference handle it).

Specifically:
- Build a regex from the step ID: `^\|\\s*{re.escape(step_id)}\\s*\|(.+?)\|(.+?)\|(.+?)\|$`
- Replace the last two cells (status → `-`, pr → new value)
- This preserves the description cell exactly

### 2. Registration in `group.py`

Add import and `exec_group.add_command(update_roadmap_step, name="update-roadmap-step")`.

### 3. Tests: `test_update_roadmap_step.py`

Use `CliRunner` + `ErkContext.for_test(github_issues=FakeGitHubIssues(...))` pattern.

Test cases:
- **Success**: Update a pending step with `plan #123` → verify body updated, JSON output correct
- **Success**: Update a step that already has a PR → verify previous_pr in output
- **Step not found**: Step ID doesn't exist → exit code 1, error message
- **Issue not found**: Issue doesn't exist → exit code 1, error message
- **No roadmap**: Issue has no roadmap table → exit code 1, error message
- **Clear PR**: Set `--pr ""` → clears the cell

Each test creates a `FakeGitHubIssues` with an `IssueInfo` containing a realistic roadmap body, invokes the command, and asserts both the JSON output and the updated body content.

### 4. Update `objective-next-plan` skill

After the command exists, update `.claude/skills/objective/commands/objective-next-plan.md` Step 3.5 to replace the inline Python with:

```bash
erk exec update-roadmap-step <objective-issue> --step <step_id> --pr "plan #<issue_number>"
```

## Verification

1. Run unit tests: `uv run pytest tests/unit/cli/commands/exec/scripts/test_update_roadmap_step.py -v`
2. Run type checker on the new file
3. Manual test against a real objective (e.g., `erk exec update-roadmap-step 6423 --step 1.4 --pr "plan #9999"` then verify with `erk exec get-issue-body 6423`)