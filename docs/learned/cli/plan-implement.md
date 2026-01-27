---
title: Plan-Implement Workflow
read_when:
  - "understanding the /erk:plan-implement command"
  - "implementing plans from GitHub issues"
  - "working with .impl/ folders"
  - "debugging plan execution failures"
---

# Plan-Implement Workflow

The `/erk:plan-implement` command orchestrates the complete workflow from plan to PR. Understanding its 4-phase execution pattern helps debug failures and understand timing.

## Execution Phases

### Phase 1: Setup (10-30 seconds)

**Actions:**

- Fetch plan from GitHub issue or file
- Create feature branch (stacked or from trunk)
- Initialize `.impl/` folder with plan content
- Validate plan structure

**Key Files Created:**

- `.impl/plan.md` - The immutable implementation plan
- `.impl/issue.json` - Issue metadata (if from GitHub)

**Common Failures:**

- Issue not found or inaccessible
- Branch already exists
- Invalid plan structure

### Phase 2: Implementation (varies)

**Actions:**

- Read plan and load related documentation
- Execute each phase sequentially
- Write code and tests together
- Mark phases complete in TodoWrite

**Timing:** Depends on plan complexity (5 minutes to 2+ hours)

**Critical Discipline:** `.impl/plan.md` is immutable - NEVER edit during implementation

### Phase 3: CI Verification (2-10 minutes)

**Actions:**

- Run CI checks iteratively (pytest, ty, ruff, prettier)
- Fix failures and re-run
- Continue until all checks pass

**Hook Integration:** If `.erk/prompt-hooks/post-plan-implement-ci.md` exists, follow its instructions instead of AGENTS.md defaults.

### Phase 4: PR Creation and Cleanup (10-20 seconds)

**Actions:**

- Create or update PR with `gh pr create --fill`
- Validate PR rules with `erk pr check`
- Clean up `.worker-impl/` if present (remote execution artifact)

**Critical Guardrail:** `.impl/` folder is NEVER deleted - preserved for user review

## Cleanup Discipline

### Always Clean Up

`.worker-impl/` - Transient working directory from remote execution:

```bash
if [ -d .worker-impl/ ]; then
  git rm -rf .worker-impl/
  git commit -m "Remove .worker-impl/ after implementation"
  git push
fi
```

### Never Clean Up

`.impl/` - Permanent plan reference preserved for:

- User review of what was planned vs implemented
- Plan reuse and iteration
- Session association for learn workflow

## Remote vs Local Execution

| Execution Mode            | .worker-impl/ Present | .impl/ Present | Session Upload                |
| ------------------------- | --------------------- | -------------- | ----------------------------- |
| Local agent               | No                    | Yes            | Via `erk exec upload-session` |
| Remote agent              | Yes                   | Yes            | Automatic via erk-remote      |
| Plan mode → implement now | No                    | Yes            | Via `erk exec upload-session` |

## Session Upload for Async Learn

Local implementations upload session to enable `erk learn --async`:

```bash
# After Phase 4, before cleanup
eval "$(erk exec capture-session-info)"
ISSUE_NUMBER=$(jq -r '.issue_number // empty' .impl/issue.json 2>/dev/null || echo "")

if [ -n "$SESSION_ID" ] && [ -n "$SESSION_FILE" ] && [ -n "$ISSUE_NUMBER" ]; then
  erk exec upload-session \
    --session-file "$SESSION_FILE" \
    --session-id "$SESSION_ID" \
    --source local \
    --issue-number "$ISSUE_NUMBER" || true
fi
```

This stores the session in a gist linked to the issue.

## Common Patterns

### Skipping to Implementation

If `.impl/` already exists and is valid, setup phase is skipped:

```bash
erk exec impl-init --json
# {"valid": true, ...}
# → Skip directly to Phase 2
```

### Stacked Branches

When implementing from a feature branch, new branch is stacked:

```bash
# On feature-a branch
/erk:plan-implement 123
# Creates feature-b stacked on feature-a
```

### File-Based Plans

Plans from markdown files skip GitHub issue tracking:

```bash
/erk:plan-implement ./my-plan.md
# has_issue_tracking: false
# No PR linking to issue
```

## Related Documentation

- [Plan Lifecycle](../planning/lifecycle.md) - Plan states and transitions
- [Session Management](session-management.md) - Session ID availability and uploads
- [PR Discovery](../planning/pr-discovery.md) - Fallback strategies when branch_name missing
