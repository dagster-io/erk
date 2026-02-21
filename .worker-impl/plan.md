# Plan: Create `/local:objective-reevaluate` Skill

## Context

When objectives have long lifespans, their prose drifts from reality. We just manually fixed issue #7390 where `inspect` references persisted after the command was merged into `view`. This required: finding the stale references across both the issue body YAML and the rendered objective-body comment, making text replacements, and pushing updates via the GitHub API. There's no skill for this today — the closest analog is `/local:check-relevance` (which assesses whether a *plan or PR* is superseded) and `/erk:objective-update-with-landed-pr` (which reconciles prose *after landing a specific PR*). Neither covers a general "audit this objective against the current codebase" workflow.

## What the Skill Does

A slash command `/local:objective-reevaluate <issue-number>` that audits an open objective against the current codebase state and proposes updates. It covers:

1. **Stale references** — renamed commands, moved files, deleted modules mentioned in node descriptions, Key Files, or Implementation Context
2. **Already-done work** — pending nodes whose work was accomplished via other PRs or incidental changes
3. **Outdated prose** — Design Decisions or Implementation Context that no longer match reality
4. **Node relevance** — whether remaining pending nodes still make sense

## Implementation

### File to create

`.claude/commands/local/objective-reevaluate.md`

### Skill structure (follows `check-relevance` phased pattern)

**Phase 1: Fetch Objective Context**
- Run `erk exec objective-fetch-context --objective <NUMBER>` to get full objective data
- Parse roadmap phases, node statuses, dependency graph
- Extract the objective-body comment (comment ID from `objective-header` metadata)

**Phase 2: Extract Auditable References**
- From node descriptions: file paths, command names, function names, class names
- From Implementation Context section: key files list, architecture descriptions
- From Design Decisions section: technology choices, pattern references
- Build a checklist of concrete assertions to verify

**Phase 3: Verify Against Codebase**
- For each file path reference: check existence via Glob
- For each command/function/class name: search via Grep
- For each pending node: run check-relevance-style search (is this work already done?)
- For stale command references (like `inspect` → `view`): check if the referenced CLI command exists

**Phase 4: Build Findings Report**
- Present a structured findings table:

```
| Location | Reference | Status | Finding |
|----------|-----------|--------|---------|
| Node 1.4 description | `inspect` command | STALE | Command merged into `view` (PR #7385) |
| Key Files | `inspect_cmd.py` | STALE | File deleted, now `view_cmd.py` |
| Node 2.3 | pending | STILL RELEVANT | No evidence of implementation |
```

- Categorize findings: STALE (needs update), DONE (node completed elsewhere), CURRENT (no action), UNCLEAR (needs human review)

**Phase 5: Propose Updates**
- For STALE references: propose specific text replacements
- For DONE nodes: propose status change to `done` with evidence
- For outdated prose: propose revised text
- Present all proposals for user review

**Phase 6: Execute Updates (with confirmation)**
- Use AskUserQuestion to let user approve/reject/modify proposals
- Apply approved changes:
  - Issue body YAML updates via `erk exec update-objective-node` (for node status changes)
  - Full body text updates via `erk exec update-issue-body` (for prose/reference fixes)
  - Objective-body comment updates via `gh api` PATCH (for rendered content fixes)
- Post an action comment summarizing what was reconciled

### Key design decisions

- **Skill, not CLI command**: This is judgment-heavy work (interpreting whether a reference is stale) — perfect for an agent skill, not a deterministic CLI tool
- **Always requires confirmation**: Never auto-mutate; always present findings and get user approval
- **Covers both surfaces**: Updates both the issue body (YAML metadata) AND the objective-body comment (rendered prose) — this was the exact gap we hit manually
- **Reuses existing exec scripts**: `objective-fetch-context`, `update-objective-node`, `update-issue-body`, `objective-post-action-comment`

## Files to modify/create

| File | Action |
|------|--------|
| `.claude/commands/local/objective-reevaluate.md` | **Create** — the skill itself |

## Verification

1. Run `/local:objective-reevaluate 7390` and confirm it detects any remaining stale references
2. Run against another open objective to verify it handles clean objectives gracefully (reports "no issues found")
3. Verify the action comment is posted correctly after applying fixes