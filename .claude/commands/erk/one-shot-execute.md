---
description: Execute a one-shot task autonomously (used by CI workflow)
---

# One-Shot Autonomous Execute

You are running autonomously in a CI workflow. Your job is to read an instruction, explore the codebase, plan, implement, and verify.

## Step 1: Read the Instruction

Read `.impl/task.md` to understand what you need to do.

## Step 2: Load Skills

Load the following skills:

- `dignified-python` — for Python coding standards
- `fake-driven-testing` — for test patterns

## Step 3: Explore the Codebase

Use Explore agents to understand the relevant areas of the codebase. Search for files, patterns, and existing implementations related to the instruction.

Read `AGENTS.md` and `docs/learned/index.md` to understand the project conventions. Search `docs/learned/` for relevant documentation before writing code.

## Step 4: Plan the Approach

Based on your exploration, decide:

- What files need to be created or modified
- What the implementation strategy is
- What tests are needed

## Step 5: Implement

Write the code changes, following project conventions:

- Load `dignified-python` skill for Python standards (LBYL, modern types, ABC interfaces)
- Load `fake-driven-testing` skill for test patterns
- Follow AGENTS.md standards
- Include tests for new functionality
- Use `devrun` agent for running pytest/ty/ruff/prettier/make (never direct Bash for these)

## Step 6: Run CI Checks

Use the `devrun` agent to run verification:

1. Run `make fast-ci` and report results
2. Fix any failures found
3. Repeat until CI passes

## Important Notes

- This is a one-shot execution — no issue tracking, no signal handling
- Keep changes focused on the instruction
- If the instruction is unclear, do your best interpretation
- Always include tests for code changes
- Never modify CHANGELOG.md
