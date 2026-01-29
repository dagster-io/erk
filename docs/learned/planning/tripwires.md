---
title: Planning Tripwires
read_when:
  - "working on planning code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from planning/*.md frontmatter -->

# Planning Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before adding new agents to learn workflow** → Read [Learn Workflow](learn-workflow.md) first. Document input/output format and test file passing. Learn workflow uses stateless agents with file-based composition.

**CRITICAL: Before after plan-implement execution completes** → Read [Plan Lifecycle](lifecycle.md) first. Always clean .worker-impl/ with `git rm -rf .worker-impl/` and commit. Transient artifacts cause CI formatter failures (Prettier).

**CRITICAL: Before analyzing sessions larger than 100k characters** → Read [Scratch Storage](scratch-storage.md) first. Use `erk exec preprocess-session` first. Achieves ~99% token reduction (e.g., 6.2M -> 67k chars). Critical for fitting large sessions in agent context windows.

**CRITICAL: Before calling commands that depend on `.impl/issue.json` metadata** → Read [Plan Lifecycle](lifecycle.md) first. Verify metadata file exists in worktree; if missing, operations silently return empty values.

**CRITICAL: Before consolidating issues that already have erk-consolidated label** → Read [Consolidation Labels](consolidation-labels.md) first. Filter out erk-consolidated issues before consolidation. These are outputs of previous consolidation and should not be re-consolidated.

**CRITICAL: Before creating a review PR for a plan** → Read [PR-Based Plan Review Workflow](pr-review-workflow.md) first. Review PRs are draft PRs that are never merged. Use erk exec plan-create-review-pr.

**CRITICAL: Before creating erk-learn plan for an issue that already has erk-learn label** → Read [Learn Plan Validation](learn-plan-validation.md) first. Validate target issue has erk-plan label, NOT erk-learn. Learn plans analyze implementation plans, not other learn plans (cycle prevention).

**CRITICAL: Before creating temp files for AI workflows** → Read [Scratch Storage](scratch-storage.md) first. Use worktree-scoped scratch storage for session-specific data.

**CRITICAL: Before entering Plan Mode in replan or consolidation workflow** → Read [Context Preservation in Replan Workflow](context-preservation-in-replan.md) first. Gather investigation context FIRST (Step 6a). Enter plan mode only after collecting file paths, evidence, and discoveries. Sparse plans are destructive to downstream implementation.

**CRITICAL: Before gathering sessions for preprocessing** → Read [Learn Workflow](learn-workflow.md) first. Sessions >100k characters MUST be preprocessed first. Use erk exec preprocess-session for ~99% token reduction.

**CRITICAL: Before implementing PR body generation with checkout footers** → Read [Plan Lifecycle](lifecycle.md) first. HTML `<details>` tags will fail `has_checkout_footer_for_pr()` validation. Use plain text backtick format: `` `gh pr checkout <number>` ``

**CRITICAL: Before implementing custom PR/plan relevance assessment logic** → Read [Plan Lifecycle](lifecycle.md) first. Reference `/local:check-relevance` verdict classification system first. Use SUPERSEDED (80%+ overlap), PARTIALLY_IMPLEMENTED (30-80% overlap), DIFFERENT_APPROACH, STILL_RELEVANT, NEEDS_REVIEW categories for consistency.

**CRITICAL: Before launching dependent agents that read from files written by Write tool** → Read [Agent Orchestration Safety Patterns](agent-orchestration-safety.md) first. Verify file existence with ls before launching dependent agents.

**CRITICAL: Before launching subagents that produce outputs > 1KB** → Read [Agent Orchestration Safety Patterns](agent-orchestration-safety.md) first. Use Write tool for agent outputs. Bash heredocs fail silently above 10KB.

**CRITICAL: Before manually creating an erk-plan issue with gh issue create** → Read [Plan Lifecycle](lifecycle.md) first. Use `erk exec plan-save-to-issue --plan-file <path>` instead. Manual creation requires complex metadata block format (see Metadata Block Reference section).

**CRITICAL: Before manually creating plan review branches** → Read [PR-Based Plan Review Workflow](pr-review-workflow.md) first. Use plan-create-review-branch to ensure proper naming (plan-review-{issue}-{timestamp}).

**CRITICAL: Before modifying learn command to add/remove/reorder agents** → Read [Learn Workflow](learn-workflow.md) first. Verify tier placement before assigning model. Parallel extraction uses haiku, sequential synthesis may need opus for quality-critical output.

**CRITICAL: Before modifying marker deletion behavior in exit-plan-mode hook** → Read [Session-Based Plan Deduplication](session-deduplication.md) first. Reusable markers (plan-saved) must persist; one-time markers (implement-now, objective-context) are consumed. Deleting reusable markers breaks state machines and enables retry loops that create duplicates.

**CRITICAL: Before reading learn_plan_issue or learn_status** → Read [Learn Plan Metadata Preservation](learn-plan-metadata-fields.md) first. Verify field came through full pipeline. If null, check if filtered out earlier. Use gateway abstractions; never hand-construct Plan objects.

**CRITICAL: Before reusing existing worktrees for remote implementation** → Read [Remote Implementation Idempotency](remote-implementation-idempotency.md) first. Check if worktree already has a branch before creating new one. Reusing worktrees without checking causes PR orphaning.

**CRITICAL: Before running /erk:learn in CI** → Read [Learn Workflow](learn-workflow.md) first. CI mode skips interactive prompts and auto-proceeds. Check CI/GITHUB_ACTIONS env vars. See CI Environment Behavior section.

**CRITICAL: Before saving a plan with --objective-issue flag** → Read [Plan Lifecycle](lifecycle.md) first. Always verify the link was saved correctly with `erk exec get-plan-metadata <issue> objective_issue`. Silent failures can leave plans unlinked from their objectives.

**CRITICAL: Before using background agents without waiting for completion before dependent operations** → Read [Command-Agent Delegation](agent-delegation.md) first. Use TaskOutput with block=true to wait for all background agents to complete. Without synchronization, dependent agents may read incomplete outputs or missing files.

**CRITICAL: Before using session-scoped markers in exec scripts** → Read [Session-Based Plan Deduplication](session-deduplication.md) first. Session markers enable idempotency in command retries. Always write markers AFTER successful operation completion, never before. Use triple-check guard on marker read: file exists AND content is valid AND expected type (numeric for issue numbers).

**CRITICAL: Before writing to /tmp/** → Read [Scratch Storage](scratch-storage.md) first. AI workflow files belong in .erk/scratch/<session-id>/, NOT /tmp/.
