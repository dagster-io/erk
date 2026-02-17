# Plan: Complete howto/remote-execution.md

> **Replans:** #6126

## Context

`docs/howto/remote-execution.md` is a 43-line skeleton with 8 empty TODO sections. The document needs to be filled in as a practical how-to guide for running erk plan implementations remotely via GitHub Actions. The writing style should match `docs/howto/local-workflow.md` (step-by-step, conversational, practical).

## What Changed Since Original Plan

- The `plan-implement.yml` workflow name was already correct in the original plan
- `pr-checkout-sync.md` is fully written (145 lines) and available for cross-linking
- Investigation confirmed all 8 sections remain empty — no partial work exists
- Technical details are well-documented in `docs/learned/planning/lifecycle.md` (comprehensive lifecycle reference)

## Investigation Findings

### Corrections to Original Plan

- `--base` flag defaults to **current branch** (not trunk); falls back to trunk only on placeholder/unpushed branches
- Session gist upload uses `ERK_QUEUE_GH_PAT` (needs gist scope), not the default `GITHUB_TOKEN`
- Branch naming uses `P{issue_number}-` prefix (e.g., `P123-feature-01-15-1430`)
- Draft PR is created **locally** by `erk plan submit` (for correct commit attribution), not by GitHub Actions
- `submission-queued` comment uses `expected_workflow: plan-implement` (metadata name, not filename)

### Additional Details Discovered

- Concurrency control: one run per issue; resubmitting cancels the in-progress run
- CI trigger: workflow pushes empty commit to fire push-event CI (since `workflow_dispatch` doesn't trigger them)
- Merge conflict handling: `erk exec rebase-with-conflict-resolution` runs if push fails
- `.worker-impl/` (committed to branch) vs `.impl/` (gitignored, local only) distinction is important
- Model defaults to `claude-opus-4-6`, configurable via workflow input
- Three required secrets: `ERK_QUEUE_GH_PAT` (repo + gist scope), `ANTHROPIC_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`
- Multi-issue support: `erk plan submit 123 456 789` validates all then submits sequentially

## Implementation Steps

### 1. Fill all 8 sections of `docs/howto/remote-execution.md`

**File:** `docs/howto/remote-execution.md`

Write content for each section following the `local-workflow.md` style (conversational, step-oriented, practical). Keep the existing heading structure and See Also links.

**Section content:**

#### Section 1: Overview
- What remote execution is: running plan implementations in GitHub Actions instead of locally
- Why: sandboxed environment, parallel execution, overnight/batch work, keeps your machine free
- Quick mental model: `erk plan submit` sends your plan to a GitHub Actions runner that executes it with Claude

#### Section 2: Prerequisites
- GitHub Actions workflow `plan-implement.yml` must exist in the repo
- Three required repository secrets: `ERK_QUEUE_GH_PAT` (repo + gist scope), `ANTHROPIC_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`
- Note that `ERK_QUEUE_GH_PAT` is validated at workflow startup with a clear error if missing
- A saved erk-plan issue (from `/erk:plan-save` or `erk plan create`)

#### Section 3: Creating a Plan
- Brief: same as local workflow — plan mode, save to GitHub
- Link to `local-workflow.md` Steps 1-3 rather than duplicating
- Emphasize that the plan must be saved to a GitHub issue before submission

#### Section 4: Submitting for Remote Execution
- Command: `erk plan submit <issue-number>`
- Multi-issue: `erk plan submit 123 456 789` (validates all, submits sequentially)
- `--base <branch>` flag: defaults to current branch (for stacking), falls back to trunk on placeholder branches
- `--force` / `-f` flag: skip confirmation prompts
- What happens behind the scenes:
  1. Validates issue (erk-plan label, OPEN state, clean working directory)
  2. Creates branch with `P{issue}-` prefix (or reuses existing)
  3. Creates `.worker-impl/` folder with plan files, commits to branch
  4. Creates draft PR locally (for commit attribution)
  5. Dispatches `plan-implement.yml` workflow
  6. Prints the workflow run URL
- Branch reuse detection: prompts if existing `P{issue}-*` branches found

#### Section 5: Monitoring Execution
- The submit output prints the workflow run URL directly
- Alternative: `gh run list --workflow=plan-implement.yml | grep "{issue-number}:"`
- Run name format: `{issue_number}:{distinct_id}` (6-char base36)
- Concurrency: one run per issue; resubmitting cancels the in-progress run
- Observable states table (from lifecycle.md):
  - `submission-queued` comment → submitted
  - `workflow-started` comment → running
  - PR draft → implementing
  - PR ready for review → complete

#### Section 6: Reviewing the Result
- PR is automatically marked ready for review on success
- PR body contains AI-generated implementation summary + checkout instructions
- Session log is uploaded to a GitHub Gist (linked from plan issue's `plan-header` metadata)
- To review locally: `erk pr checkout <pr-number>` (links to pr-checkout-sync.md)
- If `no-changes` label applied: implementation found nothing to change — review the diagnostic PR

#### Section 7: Debugging Remote PRs
- `erk pr checkout <pr-number>` to get the code locally
- `erk pr sync --dangerous` to sync with remote updates
- `/erk:pr-address` to address review comments
- Resubmitting (`erk plan submit <issue>` again) cancels the current run and starts fresh
- Link to `pr-checkout-sync.md` for detailed checkout/sync workflow

#### Section 8: When to Use Remote vs Local
- Comparison table:

| Factor | Remote | Local |
|--------|--------|-------|
| Runs on | GitHub Actions (ubuntu) | Your machine |
| Parallel execution | Yes (one per issue) | No (blocks your session) |
| Session log | Gist (automatic) | Local only |
| Debug access | Via `erk pr checkout` | Immediate |
| Model | Configurable (default opus-4-6) | Interactive session |
| Best for | Parallel work, overnight, batch | Iterative, full control |

- Use remote when: multiple plans to run, want to keep working, overnight batch
- Use local when: need interactive debugging, want immediate feedback, iterating

### 2. Preserve existing See Also links

The current See Also section at the bottom is already correct — keep it as-is.

## Key References

- **Pattern to follow:** `docs/howto/local-workflow.md` (writing style, structure)
- **Technical reference:** `docs/learned/planning/lifecycle.md` (lifecycle details)
- **Cross-link target:** `docs/howto/pr-checkout-sync.md` (debugging remote PRs)
- **Submit command:** `src/erk/cli/commands/submit.py` (source of truth for submission flow)

## Verification

1. Read the completed document to verify all 8 TODO comments are replaced with content
2. Verify cross-links to `local-workflow.md` and `pr-checkout-sync.md` are correct
3. Run prettier formatting via devrun agent
4. Verify no technical inaccuracies by cross-referencing with `lifecycle.md`