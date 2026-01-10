---
description: Audit open erk-plan issues for staleness and validity
---

# /local:audit-plans

Audits open erk-plan issues to identify stale, orphaned, or completed plans that may need attention or closing.

## Usage

```bash
/local:audit-plans           # Oldest 20 plans
/local:audit-plans --all     # All open plans
```

---

## Agent Instructions

### Phase 1: List Open Plans

Fetch all open erk-plan issues, sorted oldest first:

```bash
gh issue list --repo dagster-io/erk --label "erk-plan" --state open --limit 100 \
  --json number,title,createdAt,labels --jq 'sort_by(.createdAt)'
```

Report:

- Total count of open plans
- Date range (oldest to newest)

If `$ARGUMENTS` does not contain `--all`, limit analysis to the oldest 20 plans.

### Phase 2: Gather Details (per plan)

For each plan, extract metadata and analyze status:

**2.1 Get issue body:**

```bash
gh issue view <NUMBER> --json body --jq '.body'
```

**2.2 Parse plan-header metadata:**

Look for the `<plan-header>` block in the issue body containing YAML:

```yaml
plan_comment_id: 3710772890 # Where to fetch plan body
last_local_impl_at: "..." # Local implementation timestamp
last_local_impl_event: ended # "started" or "ended"
last_remote_impl_at: "..." # Remote implementation timestamp
objective_issue: 4227 # Linked objective (check if closed)
```

**2.3 Check linked objective (if exists):**

If `objective_issue` is present, check its state:

```bash
gh issue view <OBJECTIVE_NUMBER> --json state,title
```

**2.4 Get plan content (optional, for deeper analysis):**

If needed, fetch the plan body from the comment:

```bash
gh api repos/dagster-io/erk/issues/comments/<PLAN_COMMENT_ID> --jq '.body'
```

### Phase 3: Classify Each Plan

Apply these classification rules:

| Category        | Signal                                       | Meaning                                       |
| --------------- | -------------------------------------------- | --------------------------------------------- |
| **Likely Done** | `last_*_impl_event: ended`                   | Implementation completed - verify in codebase |
| **Orphaned**    | `objective_issue` points to CLOSED objective | Parent objective changed/completed            |
| **Abandoned**   | `last_*_impl_event: started` only (no ended) | Implementation started but not finished       |
| **Stale**       | No impl timestamps + >7 days old             | Never attempted, possibly obsolete            |
| **Active**      | Recent creation or recent impl activity      | Still in progress                             |

### Phase 4: Present Report

Group plans by category and present in tables:

```markdown
## Likely Done (X plans)

Plans where implementation completed. Verify and close if work was merged.

| Issue | Title         | Implemented  | Age     |
| ----- | ------------- | ------------ | ------- |
| #1234 | Add feature X | local: Dec 5 | 14 days |

## Orphaned (X plans)

Plans linked to closed objectives. The approach may have changed.

| Issue | Title       | Objective | Objective Status |
| ----- | ----------- | --------- | ---------------- |
| #1235 | Implement Y | #4227     | CLOSED           |

## Abandoned (X plans)

Plans where implementation started but never finished.

| Issue | Title      | Started | Age     |
| ----- | ---------- | ------- | ------- |
| #1236 | Refactor Z | Dec 1   | 21 days |

## Stale (X plans)

Plans never attempted, possibly obsolete.

| Issue | Title    | Created | Age     |
| ----- | -------- | ------- | ------- |
| #1237 | Old idea | Nov 15  | 45 days |

## Active (X plans)

Recent plans or plans with recent activity.

| Issue | Title        | Created/Updated |
| ----- | ------------ | --------------- |
| #1238 | Current work | Dec 8           |
```

### Phase 5: Recommendations

After presenting the report:

1. **Do NOT auto-close any issues** - present findings for human decision
2. Ask the user what actions to take using AskUserQuestion:
   - "Close all Likely Done plans"
   - "Close all Orphaned plans"
   - "Review specific plans individually"
   - "No action needed"

### Phase 6: Execute Actions (if requested)

If user selects plans to close:

```bash
gh issue close <NUMBER> --comment "Closing via plan audit: <reason>"
```

Report results and any failures.

---

## Key Data Structures

### Plan Header Schema

The `<plan-header>` block in issue body contains:

```yaml
schema_version: "1"
plan_comment_id: 3710772890 # Comment ID containing actual plan
last_local_impl_at: "2024-12-05T..."
last_local_impl_event: ended # "started" or "ended"
last_remote_impl_at: "2024-12-06T..."
objective_issue: 4227 # Optional: linked objective
```

### Classification Priority

1. **Orphaned** takes precedence (objective closed = context changed)
2. **Likely Done** if ended event exists
3. **Abandoned** if started but not ended
4. **Stale** if no impl timestamps and old
5. **Active** otherwise

---

## Error Handling

- If GitHub API rate limited, report and stop
- If plan-header parsing fails, note in report and continue
- If objective lookup fails, note in report and continue
