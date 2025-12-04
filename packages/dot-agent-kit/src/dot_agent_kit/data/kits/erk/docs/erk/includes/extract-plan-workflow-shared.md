# Extract Agent Docs - Plan Workflow

Shared extraction plan workflow for `/erk:extract-agent-docs` and `/erk:extract-agent-docs-from-log` commands.

## Step 6: Format as Extraction Plan

Format the selected suggestions as an implementation plan in markdown:

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

## Step 7: Create Extraction Plan Issue

**CRITICAL: Use the kit CLI command.** Do NOT manually create a GitHub issue with `gh issue create` - this will result in incorrect metadata format.

Run the kit CLI command to create the extraction plan issue:

```bash
echo "<plan_content>" | dot-agent run erk create-extraction-plan --source-plan-issues="" --extraction-session-ids="<session-id>"
```

Pass the plan content via stdin. The command will:

1. Create a GitHub issue with `erk-plan` + `erk-extraction` labels
2. Create the issue body with a `plan-header` metadata block containing `schema_version`, `created_at`, `created_by`, `plan_type: extraction`, etc.
3. Add the plan content as a **first comment** wrapped in a `plan-body` metadata block

**Expected issue structure:**

- **Issue body**: Only contains `plan-header` metadata block (compact, for fast querying)
- **First comment**: Contains `plan-body` metadata block with the full implementation plan

This matches the schema version 2 format used by standard plan issues. See [issue #2066](https://github.com/dagster-io/erk/issues/2066) for an example of the correct format.

## Step 8: Output Next Steps

After issue creation, display:

```
✅ Extraction plan created: #<issue_number>
   URL: <issue_url>

**Next steps:**
1. Review the plan in GitHub
2. Create a worktree: `erk implement <issue_number>` or `erk wt create --from-plan <issue_number>`
3. Implement the documentation changes
4. When done, run: `erk plan extraction complete <issue_number>`
   This will mark the source plans as docs-extracted
```
