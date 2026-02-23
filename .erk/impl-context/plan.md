# Fix: `/local:objective-reevaluate` fails on startup

## Context

Every invocation of `/local:objective-reevaluate` fails immediately because Phase 1 calls `erk exec objective-fetch-context --objective <N>`, which auto-discovers the current branch, tries to resolve it to a plan, and fails with `"No plan found for branch 'master'"`. This script is designed for post-landing/closed-plan workflows that always have plan+PR+branch context. Reevaluation only needs the objective issue itself.

## Approach

Update the skill's Phase 1 to use `get-issue-body` instead of `objective-fetch-context`. No new exec scripts needed — the LLM executing the skill can parse roadmap tables and metadata directly from the raw issue body text.

## Changes

**File:** `.claude/commands/local/objective-reevaluate.md`

### Phase 1 update

Replace the `objective-fetch-context` call and its field references with:

```bash
erk exec get-issue-body <NUMBER>
```

Adjust parsed fields:
- `objective.body` → `body`
- `objective.title` → `title`
- `objective.state` → `state`
- `objective.labels` → `labels`
- Remove `roadmap.phases` from the "Parse the JSON output to get" list

Add explicit note: **Do NOT use `objective-fetch-context`** — it requires plan/branch/PR context and fails on master.

### Phase 2 update

The skill says "From roadmap node descriptions" — this already implies the LLM reads the body text. Add a note that the roadmap is parsed directly from the issue body (which contains markdown tables + YAML metadata blocks), not from a pre-parsed `roadmap.phases` field.

## Verification

1. Run `/local:objective-reevaluate 7978` from master — should no longer fail at startup
2. Confirm it successfully fetches the objective and proceeds to Phase 2
