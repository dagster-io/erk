---
description: Create a plan from a one-shot instruction, save it as a GitHub issue, and write results to .impl/ (used by CI workflow)
---

# One-Shot Plan

You are running autonomously in a CI workflow. Your job is to read an instruction, explore the codebase, create a detailed implementation plan, and save it as a GitHub issue.

**Important:** You are ONLY planning, not implementing. The plan must be self-contained — a separate Claude session will implement it with no access to your exploration context.

## Step 1: Read the Instruction

Read `.impl/task.md` to understand what you need to do.

## Step 2: Read Objective Context (if present)

If the `$OBJECTIVE_ISSUE` environment variable is set (non-empty), this plan is for a specific step of an objective. Use `erk exec check-objective $OBJECTIVE_ISSUE` to fetch the full objective context (title, roadmap, progress). The `$STEP_ID` environment variable contains the specific roadmap step ID being planned. Incorporate the objective context into your planning — understand the broader goal and how this step fits into it.

## Step 3: Load Context

Read `AGENTS.md` to understand the project conventions. Follow its documentation-first discovery process: scan `docs/learned/index.md`, grep `docs/learned/` for relevant docs, and load skills as directed by AGENTS.md routing rules.

## Step 4: Explore the Codebase

Use Explore agents and Grep/Glob to understand the relevant areas of the codebase:

- Search for files, patterns, and existing implementations related to the instruction
- Identify which files need to be created or modified
- Understand existing architecture and patterns
- Find relevant tests and test patterns

## Step 5: Write the Plan

Write a comprehensive implementation plan to `.impl/plan.md`.

The plan MUST be self-contained for a separate Claude session to implement. Include:

- **Context**: What problem this solves and why
- **Changes**: Specific files to create/modify with detailed descriptions of what to change
- **Implementation details**: Code patterns to follow, key decisions, edge cases
- **Files NOT changing**: Clarify what's out of scope
- **Verification**: How to verify the implementation works

Follow the planning conventions in `docs/learned/planning/` if available.

## Step 6: Save Plan to GitHub Issue

Check the `$PLAN_ISSUE_NUMBER` environment variable:

**If `$PLAN_ISSUE_NUMBER` is set (non-empty):** A skeleton plan issue was pre-created at dispatch time. Update it with the real plan content:

```bash
erk exec plan-update-issue --issue-number $PLAN_ISSUE_NUMBER --plan-path .impl/plan.md --format json
```

Parse the JSON output. If `success` is not `true`, stop and report the error. Otherwise, use `$PLAN_ISSUE_NUMBER` as the `issue_number`. To get the `title`, extract the first `# ` heading from `.impl/plan.md`.

**If `$PLAN_ISSUE_NUMBER` is not set (empty):** Fall back to creating a new issue (backwards compatible for direct `erk one-shot` calls without pre-created skeleton):

```bash
erk exec plan-save-to-issue --plan-file .impl/plan.md --format json --created-from-workflow-run-url "$WORKFLOW_RUN_URL"
```

If the `WORKFLOW_RUN_URL` environment variable is not set, omit the `--created-from-workflow-run-url` flag.

If the `$OBJECTIVE_ISSUE` environment variable is set (non-empty), add `--objective-issue $OBJECTIVE_ISSUE` to the command above to link the plan to its parent objective.

Parse the JSON output. If `success` is not `true`, stop and report the error. Otherwise, extract `issue_number` and `title` from the output.

## Step 7: Write Plan Result

Write the plan result to `.impl/plan-result.json` with the following format:

```json
{"issue_number": <num>, "title": "<title>"}
```

Use the `issue_number` and `title` extracted from the Step 6 output.

## Important Notes

- This is planning only — do NOT implement any code changes
- Your outputs are `.impl/plan.md` and `.impl/plan-result.json`
- The plan must be detailed enough for another agent to implement without additional context
- Keep the plan focused on the instruction
- Never modify CHANGELOG.md
