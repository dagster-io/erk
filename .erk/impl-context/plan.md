# Plan: Create `/erk:pr-list` Slash Command

## Context

The existing `erk pr list` CLI command renders a Rich table at 200-char width with many columns (pr, stage, sts, created, obj, loc, branch, run-id, run, author, chks, cmts). This is optimized for wide terminals, not Claude Code's narrower output. The user wants a Claude Code terminal-friendly rendering of open PRs as a slash command.

## Approach

Follow the `objective-list.md` pattern: use `gh pr list` with `--json` to fetch structured PR data, then have Claude render a compact markdown table. This is simpler and more reliable than calling `erk pr list` and trying to parse Rich markup.

## File to Create

**`.claude/commands/erk/pr-list.md`**

### Structure

```yaml
---
description: List open PRs in Claude Code terminal format
context: fork
agent: general-purpose
model: haiku
---
```

### Agent Instructions

**Step 1: Fetch open PRs** using `gh pr list`:
```bash
gh pr list --state open --json number,title,headRefName,isDraft,reviewDecision,statusCheckRollup,createdAt,author,labels --limit 30
```

**Step 2: Format as markdown table** with these columns (selected for Claude Code readability):

| #    | Title               | Branch        | Status | Checks | Created |
| ---- | ------------------- | ------------- | ------ | ------ | ------- |
| #123 | Add feature X       | feat/add-x    | Draft  | 3/3    | 2d ago  |
| #456 | Fix login bug       | fix/login     | Review | 2/5    | 1w ago  |

- **Status**: Draft / Open / Approved / Changes Requested
- **Checks**: passing/total counts from `statusCheckRollup`
- **Created**: relative time

**Step 3: Suggest next steps** (follow `objective-list.md` pattern):
- `gh pr view <number>` — View PR details
- `gh pr checkout <number>` — Check out the PR locally

## Conventions Followed

- Kebab-case filename: `pr-list.md`
- `context: fork` for isolated execution
- `model: haiku` for fast, cheap rendering (same as `objective-list.md`)
- Uses `gh` CLI directly (no Rich/Python dependency)
- Markdown table output (Claude Code native rendering)

## Verification

1. Run `/erk:pr-list` in Claude Code
2. Confirm table renders cleanly in the terminal
3. Confirm clickable PR numbers and useful status info
