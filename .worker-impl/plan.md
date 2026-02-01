# Plan: Create `/local:interview` Command

## Summary

Create a new slash command at `.claude/commands/local/interview.md` that interviews the user in-depth using `AskUserQuestion`, then returns a structured summary to the conversation context oriented toward creating a plan or objective.

## Design

**Pattern**: Agent Delegation (Context → Interview → Summarize → Recommend)

**Key design decisions:**

1. **No side effects** — the command only reads code and asks questions. It produces conversation output, not files. This means it works identically standalone or mid-plan-mode.
2. **Goal-oriented output** — the summary is framed as input to plan/objective creation, with a specific recommendation on which path to take based on interview findings.
3. **Scope question is part of the interview** — during the interview itself, ask whether this is plan-sized or objective-sized work. Don't treat it as a separate routing step.
4. **`allowed-tools` restriction** — `AskUserQuestion, Read, Glob, Grep` only. No Write, no Bash, no EnterPlanMode. This forces the command to stay in interview mode.

**Output format**: A structured summary block in the conversation containing:
- Context, requirements (must/nice/out-of-scope), behavior, edge cases, design decisions, constraints, acceptance criteria, open questions
- A clear recommendation: "This is plan-sized" or "This is objective-sized" with reasoning
- Specific next step: "Enter plan mode" or "Run `/erk:objective-create`"

## File to Create

`.claude/commands/local/interview.md`

## Command Structure

```
---
description: Interview user in-depth to gather requirements for a plan or objective
argument-hint: [topic or feature description]
allowed-tools: AskUserQuestion, Read, Glob, Grep
---
```

**Phases:**
1. **Explore codebase** — read relevant files based on `$ARGUMENTS` before asking anything
2. **Interview rounds** — 4-8 rounds of AskUserQuestion, 1-4 questions per round, with between-round summaries and additional code reading as needed
3. **Scope determination** — as part of a late interview round, ask whether this is single-PR (plan) or multi-PR (objective) work
4. **Structured summary** — output the interview summary to conversation context with a recommended next step

## Verification

- Invoke `/local:interview some feature` from a fresh session — confirm it interviews and produces summary
- Invoke `/local:interview` from within plan mode — confirm it works (read-only tools + AskUserQuestion are available in plan mode)
- Confirm the output summary is useful as input to plan mode or `/erk:objective-create`