---
description: Preview PR review feedback and planned actions
---

# /erk:pr-preview-address

## Description

Fetches unresolved PR review comments and discussion comments from the current branch's PR, then displays a summary showing what actions would be taken if `/erk:pr-address` were run. This is a preview-only command that makes no changes.

## Usage

```bash
/erk:pr-preview-address
/erk:pr-preview-address --all    # Include resolved threads
```

## Agent Instructions

> **IMPORTANT: This is a READ-ONLY preview command.**
>
> Do NOT make any code changes, resolve any threads, reply to any comments, or create any commits.

### Phase 1: Delegate to Task for Context Isolation

Use the Task tool to fetch and classify PR feedback. This isolates the raw JSON from the main context, returning only a human-readable summary.

**Determine flags**: If `--all` was specified in the command, include `--include-resolved` in the fetch command.

```
Task(
  subagent_type: "general-purpose",
  model: "sonnet",
  description: "Fetch PR feedback preview",
  prompt: |
    Fetch and classify PR review feedback for the current branch's PR.

    ## Steps
    1. Get the current branch: `git rev-parse --abbrev-ref HEAD`
    2. Get the PR number for this branch: `gh pr view --json number -q .number`
    3. Run: `erk exec get-pr-review-comments [--include-resolved if --all flag]`
    4. Run: `erk exec get-pr-discussion-comments`
    5. Parse and classify the JSON outputs

    ## Classification

    > See `pr-operations` skill for the **Comment Classification Model**.

    Determine complexity and proposed action for each:
    - **Code change**: Requires modification to source files
    - **Doc update**: Requires documentation changes
    - **Already resolved**: Issue appears already addressed
    - **Question to answer**: Needs a reply
    - **No action**: Acknowledgment, no change needed
    - **Investigate**: Requires codebase exploration

    ## Output Format

    ### Summary
    [Human-readable paragraph: PR number, PR title, actionable count, informational count]

    ### PR Feedback Table
    | # | Type | Location | Summary | Complexity | Proposed Action |
    |---|------|----------|---------|------------|-----------------|
    | 1 | Review | foo.py:42 | "Use LBYL pattern" | Local fix | Code change |
    ...

    ### Execution Plan Preview
    Show how `/erk:pr-address` would group these items into batches:
    - Batch 1: Local Fixes
    - Batch 2: Single-File Changes
    - Batch 3: Cross-Cutting Changes
    - Batch 4: Complex Changes

    ### Statistics
    - Total feedback items: N
    - Review threads: N (N unresolved, N resolved)
    - Discussion comments: N
    - Estimated batches: N
    - Auto-proceed batches (simple): N
    - User confirmation batches (complex): N

    If no comments found, output: "No unresolved review comments or discussion comments on PR #NNN."

    ## Important
    - This is a PREVIEW only - do NOT make any changes
    - Do NOT resolve threads, reply to comments, or create commits
    - Just report what would happen if /erk:pr-address were run
)
```

### Phase 2: Display Results

Display the Task's output to the user. The summary is already formatted for human consumption.

Add a footer:

```
To address these comments, run: /erk:pr-address
```

### Phase 3: Exit (NO ACTIONS)

**CRITICAL**: This is a preview-only command. Do NOT:

- Make any code changes
- Resolve any threads
- Reply to any comments
- Create any commits
- Push anything to remote
- Run any CI commands

Simply display the summary and exit.

## Error Handling

**No PR for branch:** Display error and suggest creating a PR with `gt create` or `gh pr create`

**GitHub API error:** Display error and suggest checking `gh auth status` and repository access
