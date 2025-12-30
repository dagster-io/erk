---
erk:
  kit: erk
---

# Extract Agent Docs - Plan Workflow

Shared extraction plan workflow for `/erk:extract-agent-docs` and `/erk:extract-agent-docs-from-log` commands.

## Step 6: Format Plan Content

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

Extract the session ID from the `SESSION_CONTEXT` hook reminder in your context, then run the kit CLI command with the plan content directly:

```bash
erk exec create-extraction-plan \
    --plan-content="<the formatted plan content>" \
    --session-id="<session-id>" \
    --extraction-session-ids="<session-id>"
```

The command automatically:

1. Writes the plan to `.erk/scratch/<session-id>/extraction-plan-*.md`
2. Creates a GitHub issue with `erk-plan` + `erk-extraction` labels
3. Sets `plan_type: extraction` in the plan-header metadata
4. Includes `source_plan_issues` and `extraction_session_ids` for tracking

Parse the JSON result to get `issue_number` and `issue_url`.

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
    erk plan submit [issue_number]
```
