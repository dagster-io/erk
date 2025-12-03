# Extract Agent Docs - Plan Workflow

Shared extraction plan workflow for `/erk:extract-agent-docs` and `/erk:extract-agent-docs-from-log` commands.

## Step 6: Format as Extraction Plan

Format the selected suggestions as an implementation plan:

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

Run the kit CLI command to create the extraction plan issue:

```bash
dot-agent run erk create-extraction-plan --source-plan-issues="" --extraction-session-ids="<session-id>"
```

Pass the plan content via stdin. The command will:

1. Create a GitHub issue with `erk-plan` + `erk-extraction` labels
2. Set `plan_type: extraction` in the plan-header metadata
3. Include `source_plan_issues` and `extraction_session_ids` for tracking

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
