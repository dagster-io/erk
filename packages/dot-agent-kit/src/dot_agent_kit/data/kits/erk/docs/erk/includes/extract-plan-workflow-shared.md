# Extract Agent Docs - Plan Workflow

Shared extraction plan workflow for `/erk:extract-agent-docs` and `/erk:extract-agent-docs-from-log` commands.

## Step 6: Format and Write Plan to Scratch Directory

Format the selected suggestions as an implementation plan and write to the scratch directory:

```markdown
# Plan: Documentation Extraction from Session

## Objective

Extract documentation improvements identified from session analysis.

## Source Information

- **Source Plan Issues:** [List issue numbers if analyzing a plan session, or empty list]
- **Extraction Session IDs:** ["<session-id>"]

## Documentation Items

### Item 1: [Title from suggestion]

**Type:** [Agent Doc | Skill | Glossary entry | etc.]
**Location:** `[path]`
**Action:** [New doc | Update existing | Merge into]
**Priority:** [High | Medium | Low]

**Content:**
[The draft content from the suggestion]

### Item 2: [Title]

...
```

**Scratch directory location**: `{repo_root}/.erk/scratch/<session-id>/`

Extract the session ID from the `SESSION_CONTEXT` hook reminder in your context, then write the plan content to:

```
{repo_root}/.erk/scratch/<session-id>/extraction-plan.md
```

Use the Write tool to create this file. The scratch directory is worktree-local and session-scoped.

**NEVER use `/tmp/` for AI workflow files.** Always use the scratch directory.

## Step 7: Create Extraction Plan Issue

Run the kit CLI command to create the extraction plan issue:

```bash
dot-agent run erk create-extraction-plan \
    --plan-file="{repo_root}/.erk/scratch/<session-id>/extraction-plan.md" \
    --source-plan-issues="" \
    --extraction-session-ids="<session-id>"
```

Parse the JSON result to get `issue_number` and `issue_url`.

The command will:

1. Create a GitHub issue with `erk-plan` + `erk-extraction` labels
2. Set `plan_type: extraction` in the plan-header metadata
3. Include `source_plan_issues` and `extraction_session_ids` for tracking

## Step 7.5: Verify Issue Structure

Run the plan check command to validate the issue conforms to Schema v2:

```bash
erk plan check <issue_number>
```

This validates:

- plan-header metadata block present in issue body
- plan-header has required fields
- First comment exists
- plan-body content extractable from first comment

**If verification fails:** Display the check output and warn the user that the issue may need manual correction.

## Step 8: Output Next Steps

After issue creation and verification, display:

```
✅ Extraction plan created and saved to GitHub

**Issue:** [title]
           [issue_url]

**Next steps:**

View the plan:
    gh issue view [issue_number] --web

Implement the extraction:
    erk implement [issue_number]

Submit for remote implementation:
    erk submit [issue_number]
```
