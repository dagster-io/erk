# Plan: Complete howto/remote-execution.md

> **Replans:** #4896
> **Objective:** #4284 (User-Facing Documentation Restructure, Step 2B.1)

## What Changed Since Original Plan

- **Workflow renamed**: `erk-impl.yml` → `plan-implement.yml` (Jan 26, 2026)
- **pr-checkout-sync.md is now complete**: Can link directly for debugging section (was skeleton in original plan)
- **`--force` flag added**: For TUI support, deletes existing branches without prompting

## Investigation Findings

### Corrections to Original Plan

1. **Workflow name**: Reference `plan-implement.yml`, not `erk-impl.yml`
2. **Multi-issue support**: `erk plan submit` accepts multiple issue numbers: `erk plan submit 123 456 789`
3. **New flags**: `--base <branch>` and `-f/--force` available

### Additional Details Discovered

- Branch reuse detection prompts user for existing local branches (--force overrides)
- Session capture uploads to gist automatically
- `distinct_id` enables run discovery for monitoring
- No-changes scenarios handled gracefully with clear messaging

## Remaining Gaps

The entire document is a skeleton with TODO comments. All 8 sections need content:

1. Overview
2. Prerequisites
3. Creating a Plan
4. Submitting for Remote Execution
5. Monitoring Execution
6. Reviewing the Result
7. Debugging Remote PRs
8. When to Use Remote vs Local

## Implementation Steps

### Phase 1: Write Document Content

Replace all TODO sections in `docs/howto/remote-execution.md` following the `local-workflow.md` pattern (~80-100 lines).

**Section-by-section:**

1. **Overview** (~3-4 sentences)
   - What remote execution is: submit plans to GitHub Actions for automated implementation
   - When to use it: parallel execution, sandboxed environment, hands-off operation
   - Quick contrast with local workflow

2. **Prerequisites** (brief list)
   - GitHub Actions enabled on repository
   - Required secrets: `ERK_QUEUE_GH_PAT`, `CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_API_KEY`
   - Plan already saved to GitHub (link to local-workflow steps 1-3)

3. **Creating a Plan** (brief, ~2 sentences + link)
   - Reference local-workflow.md steps 1-3 (same process)
   - Note: stop at "Save to GitHub" option

4. **Submitting for Remote Execution** (main section, ~10 lines)
   - Command: `erk plan submit <issue-number>` (note: supports multiple issues)
   - Flags: `--base` for base branch, `-f/--force` to delete existing branches
   - What happens: creates branch, draft PR, triggers `plan-implement.yml` workflow
   - Example output

5. **Monitoring Execution** (~6-8 lines)
   - Where to watch: GitHub Actions tab, or link in issue comment
   - Run discovery via `distinct_id`
   - What you'll see: workflow progress, Claude implementing

6. **Reviewing the Result** (~6-8 lines)
   - PR marked ready for review when complete
   - PR body contains implementation summary
   - Session log uploaded to gist for debugging
   - Normal PR review process applies

7. **Debugging Remote PRs** (~4-6 lines)
   - Use `erk pr checkout` to iterate locally
   - Link to pr-checkout-sync.md for complete guide (now available)

8. **When to Use Remote vs Local** (comparison table)
   - Similar format to local-workflow.md table
   - Cover: where it runs, when to use, trade-offs

### Files to Modify

- `docs/howto/remote-execution.md` - Replace skeleton content

## Verification

1. Read completed document to verify structure matches local-workflow.md pattern
2. Confirm all TODO comments removed
3. Verify relative links are correct (`local-workflow.md`, `pr-checkout-sync.md`)
4. Check document length: target ~80-120 lines (similar to local-workflow.md's 84 lines)
5. Read `docs/learned/planning/lifecycle.md` for accuracy verification of technical details

## Related Documentation

- **Model:** `docs/howto/local-workflow.md` - pattern to follow
- **Technical reference:** `docs/learned/planning/lifecycle.md` - for accurate command descriptions
- **Debugging guide:** `docs/howto/pr-checkout-sync.md` - now complete, link in debugging section
- **Workflow file:** `.github/workflows/plan-implement.yml` - renamed from erk-impl.yml