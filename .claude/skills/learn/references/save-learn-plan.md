# Save Learn Plan

Validate the synthesized plan content, save to GitHub issue, and store tripwire candidates.

## Step 1: Validate Plan Content

```bash
cat .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/learn-plan.md | erk exec validate-plan-content
```

Parse the JSON output:

- If `valid: false` → Skip saving, return `completed_no_plan` status
- If `valid: true` → Continue with save below

## Step 2: Save to GitHub Issue

**If plan is valid**, save it as a GitHub issue:

```bash
erk exec plan-save-to-issue \
    --plan-type learn \
    --plan-file .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/learn-plan.md \
    --session-id="${CLAUDE_SESSION_ID}" \
    --format json
```

**Additional flags (append as needed):**

- `--learned-from-issue <parent-issue-number>` — When learning from a parent plan (used by `/erk:learn`)
- `--created-from-workflow-run-url "$WORKFLOW_RUN_URL"` — When running in GitHub Actions (enables backlink)

Parse the JSON output to get `issue_number` (the new learn plan issue).

Display the result:

```
Learn plan saved to GitHub issue #<issue_number>
```

## Step 3: Store Tripwire Candidates

**If plan was valid and saved**, store structured tripwire candidates as a metadata comment:

```bash
erk exec store-tripwire-candidates \
    --issue <new-learn-plan-issue-number> \
    --candidates-file .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/tripwire-candidates.json
```

This stores the tripwire candidates as a machine-readable metadata block comment on the learn plan issue, enabling `erk land` to read them directly without regex parsing.

Parse the JSON output. If `count` is 0, no comment was added (no candidates found by the extractor). This is normal and not an error.
