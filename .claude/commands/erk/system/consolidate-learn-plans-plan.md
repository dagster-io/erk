---
description: CI-only skill for autonomous learn plan consolidation (used by consolidate-learn-plans workflow)
---

# Consolidate Learn Plans (CI)

You are running autonomously in a CI workflow. Your job is to query all open erk-learn plans, consolidate them into a single implementation-ready documentation plan, and output the results.

**Important:** This is the autonomous CI version. No user interaction (no AskUserQuestion). If there are no plans, output a sentinel and exit cleanly.

## Step 1: Load Context

Read `AGENTS.md` to understand the project conventions. Follow its documentation-first discovery process: scan `docs/learned/index.md`, grep `docs/learned/` for relevant docs.

## Step 2: Query Open erk-learn Plans

Fetch all open plans with the `erk-learn` label:

```bash
gh api repos/${GITHUB_REPOSITORY:-dagster-io/erk}/issues \
  -X GET \
  --paginate \
  -f labels=erk-learn \
  -f state=open \
  -f per_page=100 \
  --jq '.[] | {number, title, created_at, labels: [.labels[].name]}'
```

## Step 3: Filter Out Already-Consolidated Plans

Filter out any plans that have the `erk-consolidated` label. These were created by a previous consolidation and should not be re-consolidated.

Store the filtered list of plan numbers.

## Step 4: Handle Zero Plans

If zero plans remain after filtering:

1. Write sentinel result file:

```bash
cat > .erk/impl-context/plan-result.json <<'EOF'
{"plan_number": 0, "has_plans": false, "title": "No learn plans to consolidate"}
EOF
```

2. Exit cleanly (exit code 0). The workflow will detect `has_plans=false` and close the PR automatically.

## Step 5: Fetch Plan Bodies

For each remaining plan, fetch the full body:

```bash
erk exec get-plan-info <N> --include-body
```

Collect the title, body, and any metadata from each plan.

## Step 6: Investigate Codebase Against Plan Items

Launch Explore agents (via Task tool with `subagent_type: Explore`) to investigate the codebase for each major documentation topic mentioned in the plans.

For each exploration, check:

- Does the documentation already exist in `docs/learned/`?
- What is the current state of the code being documented?
- Are there related docs that should be updated rather than creating new ones?

**Wait for ALL agents to complete** (use `timeout: 600000` with TaskOutput) before proceeding.

## Step 7: Write Implementation Plan

Write a concrete implementation plan to `.erk/impl-context/plan.md`. This is NOT a "plan plan" — it must contain **concrete file create/edit steps** for `docs/learned/`.

For each documentation item, specify:

- **Target file path**: Exact path in `docs/learned/` hierarchy
- **Action**: Create new file or edit existing file
- **Content outline**: Section headings and key content to include
- **Source references**: Which plan items and code locations inform this content
- **Verification**: How to confirm the documentation is accurate

Include a phase for updating `docs/learned/index.md` if new files are created.

The plan must be self-contained — a separate Claude session will implement it.

## Step 8: Save Plan Metadata

Generate a 2-3 sentence summary of the plan. Then update the plan:

Check the `$PR_NUMBER` environment variable. If set:

```bash
erk exec plan-update --plan-number $PR_NUMBER --plan-path .erk/impl-context/plan.md --format json --summary="${PLAN_SUMMARY}"
```

Parse the JSON output. If `success` is `true`, use `$PR_NUMBER` as the plan number.

## Step 9: Write Plan Result

Write the result file:

```json
{"plan_number": <num>, "title": "<title>", "has_plans": true}
```

To `.erk/impl-context/plan-result.json`.

## Step 10: Close Original Learn Plans

For each original learn plan (from Step 3), close it with a cross-reference comment and add the `erk-consolidated` label:

```bash
# Add consolidated label
gh api repos/${GITHUB_REPOSITORY:-dagster-io/erk}/issues/<number>/labels \
  -X POST \
  -f "labels[]=erk-consolidated"

# Add cross-reference comment
gh issue comment <number> --body "Consolidated into #<new_plan_number>. See consolidated plan for implementation details."

# Close the plan
gh issue close <number>
```

If any plan is a PR (not an issue), use `gh pr close` instead.

## Important Notes

- This runs in CI — no user interaction, no AskUserQuestion
- Output files: `.erk/impl-context/plan.md` and `.erk/impl-context/plan-result.json`
- The sentinel `has_plans: false` in plan-result.json tells the workflow to skip implementation
- Never modify CHANGELOG.md
- Focus on `docs/learned/` documentation, not code changes
