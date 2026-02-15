---
description: Create a plan from a one-shot instruction and save as GitHub issue (used by CI workflow)
---

# One-Shot Plan

You are running autonomously in a CI workflow. Your job is to read an instruction, explore the codebase, create a detailed implementation plan, and save it as a GitHub issue.

**Important:** You are ONLY planning, not implementing. The plan must be self-contained — a separate Claude session will implement it with no access to your exploration context.

## Step 1: Read the Instruction

Read `.impl/task.md` to understand what you need to do.

## Step 2: Load Context

Read `AGENTS.md` to understand the project conventions. Follow its documentation-first discovery process: scan `docs/learned/index.md`, grep `docs/learned/` for relevant docs, and load skills as directed by AGENTS.md routing rules.

## Step 3: Explore the Codebase

Use Explore agents and Grep/Glob to understand the relevant areas of the codebase:

- Search for files, patterns, and existing implementations related to the instruction
- Identify which files need to be created or modified
- Understand existing architecture and patterns
- Find relevant tests and test patterns

## Step 4: Write the Plan

Write a comprehensive implementation plan to `.impl/plan.md`.

The plan MUST be self-contained for a separate Claude session to implement. Include:

- **Context**: What problem this solves and why
- **Changes**: Specific files to create/modify with detailed descriptions of what to change
- **Implementation details**: Code patterns to follow, key decisions, edge cases
- **Files NOT changing**: Clarify what's out of scope
- **Verification**: How to verify the implementation works

Follow the planning conventions in `docs/learned/planning/` if available.

## Step 5: Save Plan to GitHub Issue

Run the following command to save the plan as a GitHub issue:

```bash
erk exec plan-save-to-issue --plan-file .impl/plan.md --format json
```

Parse the JSON output. It will contain:

- `issue_number`: The created issue number
- `title`: The issue title

## Step 6: Write Plan Issue Reference

Parse the JSON output from Step 5 and write `{"issue_number": N, "title": "..."}` to `.impl/plan-issue.json` so the workflow can extract the values. Use the `issue_number` and `title` fields from the `plan-save-to-issue` output.

## Important Notes

- This is planning only — do NOT implement any code changes
- The plan must be detailed enough for another agent to implement without additional context
- Keep the plan focused on the instruction
- Never modify CHANGELOG.md
