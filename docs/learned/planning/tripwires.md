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

**CRITICAL: Before adding a new PR-dependent step to trigger-async-learn** → Read [Learn Without PR Context](learn-without-pr-context.md) first. Any new PR-dependent step must handle the None case from \_get_pr_for_plan_direct. The entire PR comment block is gated on pr_result not being None.

**CRITICAL: Before adding a new filtering step to preprocess_session.py** → Read [Session Preprocessing Architecture](session-preprocessing.md) first. There are TWO preprocessing implementations: the exec script (preprocess_session.py) and erk-shared (session_preprocessing.py). The exec script has the full filtering pipeline; erk-shared has only Stage 1 mechanical reduction. New filters go in the exec script. Read this doc first.

**CRITICAL: Before adding a new pipeline stage to trigger-async-learn** → Read [Learn Pipeline Workflow](learn-pipeline-workflow.md) first. New stages must be direct Python function calls, not subprocess invocations. The orchestrator uses tight coupling for performance. See the Direct-Call Architecture section in async-learn-local-preprocessing.md.

**CRITICAL: Before adding branch_name to plan-header at creation time** → Read [Branch Name Inference](branch-name-inference.md) first. branch_name is intentionally omitted at creation because the branch doesn't exist yet. The plan-save → branch-create → impl-signal lifecycle requires this gap. See the temporal gap section below.

**CRITICAL: Before adding erk-consolidated label to a single-issue replan** → Read [Consolidation Labels](consolidation-labels.md) first. Only multi-plan consolidation gets the erk-consolidated label. Single-issue replans are updates, not consolidations.

**CRITICAL: Before adding new agents to learn workflow** → Read [Learn Workflow](learn-workflow.md) first. Document input/output format and test file passing. Learn workflow uses stateless agents with file-based composition.

**CRITICAL: Before adding subprocess calls to trigger-async-learn** → Read [Async Learn Local Preprocessing](async-learn-local-preprocessing.md) first. This command uses direct Python function calls, not subprocess invocations. This is intentional — see the direct-call architecture section below.

**CRITICAL: Before after plan-implement execution completes** → Read [Plan Lifecycle](lifecycle.md) first. Always clean .worker-impl/ with `git rm -rf .worker-impl/` and commit. Transient artifacts cause CI formatter failures (Prettier).

**CRITICAL: Before analyzing sessions larger than 100k characters** → Read [Scratch Storage](scratch-storage.md) first. Use `erk exec preprocess-session` first. Achieves ~99% token reduction (e.g., 6.2M -> 67k chars). Critical for fitting large sessions in agent context windows.

**CRITICAL: Before assigning opus to a mechanical extraction agent** → Read [Multi-Tier Agent Orchestration](agent-orchestration.md) first. Model escalation: haiku/sonnet for extraction and rule-based work, opus only for creative authoring. See the model escalation decision table.

**CRITICAL: Before assuming branch_name is always present in plan-header metadata** → Read [PR Discovery Strategies for Plans](pr-discovery.md) first. branch_name is null until Phase 2 (plan submit). Check the plan metadata field lifecycle in lifecycle.md.

**CRITICAL: Before assuming plan content is in the issue body** → Read [Plan Content Extraction Fallback](metadata-block-fallback.md) first. Schema v2 stores plan content in the FIRST COMMENT, not the issue body. The body contains only the plan-header metadata block. See extract_plan_from_comment() for the extraction logic.

**CRITICAL: Before automatically removing .impl/ folder** → Read [.worker-impl/ vs .impl/ Cleanup Discipline](worktree-cleanup.md) first. NEVER auto-delete .impl/. It belongs to the user for plan-vs-implementation review. Only .worker-impl/ is auto-cleaned.

**CRITICAL: Before blocking implementation on review PR feedback** → Read [PR-Based Plan Review Workflow](pr-review-workflow.md) first. Review PRs are advisory and non-blocking. Implementation can proceed regardless of review PR state.

**CRITICAL: Before calling commands that depend on `.impl/issue.json` metadata** → Read [Plan Lifecycle](lifecycle.md) first. Verify metadata file exists in worktree; if missing, operations silently return empty values.

**CRITICAL: Before calling preprocess_session functions from trigger_async_learn** → Read [Session Preprocessing Architecture](session-preprocessing.md) first. trigger_async_learn duplicates the exec script's filtering pipeline as \_preprocess_session_direct(). If you change the exec script's pipeline, update the direct function too.

**CRITICAL: Before capturing subagent output inline when it may exceed 1KB** → Read [Agent Orchestration Safety Patterns](agent-orchestration-safety.md) first. Bash tool truncates output at ~10KB with no error. Use Write tool to save agent output to scratch storage, then pass the file path to dependent agents.

**CRITICAL: Before changing branch naming convention (P{issue}- prefix)** → Read [Branch Name Inference](branch-name-inference.md) first. The P{issue}- prefix is a cross-cutting contract used by both branch creation (naming.generate_issue_branch_name) and PR recovery (get_pr_for_plan). Changing the prefix format requires updating both sides.

**CRITICAL: Before changing how sessions are classified as planning vs impl** → Read [Learn Pipeline Workflow](learn-pipeline-workflow.md) first. Classification uses planning_session_id from GitHub metadata. The resulting prefix (planning- vs impl-) propagates into XML filenames and is used by downstream learn agents to weight insights differently.

**CRITICAL: Before checking only one location when extracting plan content** → Read [Plan Content Extraction Fallback](metadata-block-fallback.md) first. Always check both the first comment (plan-body metadata block) and the issue body before reporting 'no plan content found'. The replan command documents this explicitly in Step 4a.

**CRITICAL: Before closing a plan issue without verifying all items were addressed** → Read [Complete File Inventory Protocol](complete-inventory-protocol.md) first. Compare the file inventory against the plan's items before closing. Silent omissions are the most common failure mode.

**CRITICAL: Before consolidating issues that already have erk-consolidated label** → Read [Consolidation Labels](consolidation-labels.md) first. Filter out erk-consolidated issues before consolidation. These are outputs of previous consolidation and should not be re-consolidated.

**CRITICAL: Before constructing a PR footer manually instead of using build_pr_body_footer()** → Read [PR Submission Patterns](pr-submission-patterns.md) first. The footer format includes checkout commands and closing references with specific patterns. Use the builder function to ensure validation passes.

**CRITICAL: Before creating a PR without first checking if one already exists for the branch** → Read [PR Submission Patterns](pr-submission-patterns.md) first. The submit pipeline is idempotent — it checks for existing PRs before creating. If building PR creation outside the pipeline, replicate this check to prevent duplicates.

**CRITICAL: Before creating a learn plan without setting learned_from_issue** → Read [Learn Plans vs. Implementation Plans](learn-vs-implementation-plans.md) first. Learn plans MUST set learned_from_issue to their parent implementation plan's issue number. Without it, base branch auto-detection fails and the learn plan lands on trunk instead of stacking on the parent.

**CRITICAL: Before creating a new plan-generating command without a pre-plan gathering step** → Read [Context Preservation Prompting Patterns](context-preservation-prompting.md) first. Without explicit context materialization before EnterPlanMode, agents produce sparse plans. Apply the two-phase pattern from this document.

**CRITICAL: Before creating erk-learn plan for an issue that already has erk-learn label** → Read [Learn Plan Validation](learn-plan-validation.md) first. Validate target issue has erk-plan label, NOT erk-learn. Learn plans analyze implementation plans, not other learn plans (cycle prevention).

**CRITICAL: Before creating temp files for AI workflows** → Read [Scratch Storage](scratch-storage.md) first. Use worktree-scoped scratch storage for session-specific data.

**CRITICAL: Before designing multi-agent pipelines where child agents return results via TaskOutput** → Read [Token Optimization Patterns](token-optimization-patterns.md) first. Add output size guidance to agent definitions (word count targets, table-preferred format, capped entries) to prevent context bloat when outputs accumulate in parent context.

**CRITICAL: Before editing plan content only in the PR branch without syncing** → Read [PR-Based Plan Review Workflow](pr-review-workflow.md) first. Plan content lives in two places (PR branch + issue comment). Edit the local file, then sync to the issue with `erk exec plan-update-from-feedback`. See plan-file-sync-pattern.md.

**CRITICAL: Before entering Plan Mode in replan or consolidation workflow** → Read [Context Preservation in Replan Workflow](context-preservation-in-replan.md) first. Gather investigation context FIRST (Step 6a). Enter plan mode only after collecting file paths, evidence, and discoveries. Sparse plans are destructive to downstream implementation.

**CRITICAL: Before estimating effort for a plan without checking actual files changed** → Read [Complete File Inventory Protocol](complete-inventory-protocol.md) first. Run a file inventory first. Plans that skip inventory systematically undercount configuration, test, and documentation changes.

**CRITICAL: Before fetching N large documents into parent agent context** → Read [Token Optimization Patterns](token-optimization-patterns.md) first. Delegate content fetching to child agents. Parent receives only analysis summaries, not raw content. Achieves O(1) parent context instead of O(n). See token-optimization-patterns.md.

**CRITICAL: Before gathering sessions for preprocessing** → Read [Learn Workflow](learn-workflow.md) first. Sessions >100k characters MUST be preprocessed first. Use erk exec preprocess-session for ~99% token reduction.

**CRITICAL: Before grepping only for the error message text** → Read [Source Investigation Over Trial-and-Error](debugging-patterns.md) first. Also grep for function names extracted from the error (e.g., 'checkout_footer' from 'Missing checkout footer'). Validator function names are more stable search targets than error message strings.

**CRITICAL: Before implementing PR body generation with checkout footers** → Read [Plan Lifecycle](lifecycle.md) first. HTML `<details>` tags will fail `has_checkout_footer_for_pr()` validation. Use plain text backtick format: `` `gh pr checkout <number>` ``

**CRITICAL: Before implementing custom PR/plan relevance assessment logic** → Read [Plan Lifecycle](lifecycle.md) first. Reference `/local:check-relevance` verdict classification system first. Use SUPERSEDED (80%+ overlap), PARTIALLY_IMPLEMENTED (30-80% overlap), DIFFERENT_APPROACH, STILL_RELEVANT, NEEDS_REVIEW categories for consistency.

**CRITICAL: Before including impl-signal or plan-save-to-issue in a Task tool sub-agent prompt** → Read [Sub-Agent Context Limitations](sub-agent-context-limitations.md) first. Sub-agents cannot access ${CLAUDE_SESSION_ID}. Session-dependent commands must run in the root agent context. See sub-agent-context-limitations.md.

**CRITICAL: Before launching a dependent agent that reads a file written by a prior agent** → Read [Agent Orchestration Safety Patterns](agent-orchestration-safety.md) first. Verify the file exists (ls) before launching. Write tool silently fails if the parent directory is missing, and the dependent agent wastes its entire context discovering the file isn't there.

**CRITICAL: Before making a third trial-and-error attempt at a validation fix** → Read [Source Investigation Over Trial-and-Error](debugging-patterns.md) first. After 2 failed attempts, stop guessing. Grep for the validator function and read the source to understand the exact requirement.

**CRITICAL: Before manually creating an erk-plan issue with gh issue create** → Read [Plan Lifecycle](lifecycle.md) first. Use `erk exec plan-save-to-issue --plan-file <path>` instead. Manual creation requires complex metadata block format (see Metadata Block Reference section).

**CRITICAL: Before manually setting the base branch for a learn plan submission** → Read [Learn Plans vs. Implementation Plans](learn-vs-implementation-plans.md) first. Learn plan base branch is auto-detected from learned_from_issue → parent branch. Only use --base to override if the parent branch is missing from the remote.

**CRITICAL: Before merging a plan review PR** → Read [PR-Based Plan Review Workflow](pr-review-workflow.md) first. Plan review PRs are NEVER merged. They exist only for inline review comments. Close without merging when review is complete.

**CRITICAL: Before modifying learn command to add/remove/reorder agents** → Read [Learn Workflow](learn-workflow.md) first. Verify tier placement before assigning model. Parallel extraction uses haiku, sequential synthesis may need opus for quality-critical output.

**CRITICAL: Before modifying marker deletion behavior in exit-plan-mode hook** → Read [Session-Based Plan Deduplication](session-deduplication.md) first. Reusable markers (plan-saved) must persist; one-time markers (implement-now, objective-context) are consumed. Deleting reusable markers breaks state machines and enables retry loops that create duplicates.

**CRITICAL: Before modifying the gist upload content format** → Read [Learn Pipeline Workflow](learn-pipeline-workflow.md) first. The download side (download-learn-materials) parses delimiters to split content back into files. Changes to the upload format must be mirrored in the download parser. See gist-materials-interchange.md.

**CRITICAL: Before moving gateway files without git mv** → Read [Gateway Consolidation Checklist](gateway-consolidation-checklist.md) first. Always use git mv to preserve file history. Plain mv + git add loses blame history, making future archaeology harder.

**CRITICAL: Before passing ${CLAUDE_SESSION_ID} to a sub-agent via the prompt string** → Read [Sub-Agent Context Limitations](sub-agent-context-limitations.md) first. String substitution of ${CLAUDE_SESSION_ID} happens at the root agent level. By the time the sub-agent runs the bash command, the variable is not in its environment. The root agent must resolve the value and pass it as a literal.

**CRITICAL: Before passing session content to an analysis agent** → Read [Session Preprocessing Architecture](session-preprocessing.md) first. Raw JSONL sessions can be 6+ million characters. Always preprocess first. The learn workflow validates preprocessed output exists before spawning agents.

**CRITICAL: Before preprocessing remote sessions locally** → Read [Async Learn Local Preprocessing](async-learn-local-preprocessing.md) first. Remote sessions are already preprocessed. Only local sessions (source_type == 'local') go through local preprocessing.

**CRITICAL: Before prompting an agent to 'include findings in the plan' without structuring them first** → Read [Context Preservation Prompting Patterns](context-preservation-prompting.md) first. Unstructured prompts don't work — agents summarize at too high a level. Use the four-category gathering step instead.

**CRITICAL: Before reading learn_plan_issue or learn_status** → Read [Learn Plan Metadata Preservation](learn-plan-metadata-fields.md) first. Verify field came through full pipeline. If null, check if filtered out earlier. Use gateway abstractions; never hand-construct Plan objects.

**CRITICAL: Before relying on agent instructions as the sole enforcement for a critical operation** → Read [Workflow Reliability Patterns](reliability-patterns.md) first. Agent behavior is non-deterministic. Critical operations need a deterministic workflow step as the final safety net.

**CRITICAL: Before removing .worker-impl/ during implementation (before CI passes)** → Read [.worker-impl/ vs .impl/ Cleanup Discipline](worktree-cleanup.md) first. The folder is load-bearing during implementation — Claude reads from it (via copy to .impl/). Only remove after implementation succeeds and CI passes.

**CRITICAL: Before renaming gateway files during a move without checking for non-standard naming** → Read [Gateway Consolidation Checklist](gateway-consolidation-checklist.md) first. Source files that don't follow standard naming (e.g., executor.py instead of abc.py) must be renamed to abc.py/real.py/fake.py during the move. The gateway directory convention requires standard file names.

**CRITICAL: Before reusing existing worktrees for remote implementation** → Read [Remote Implementation Idempotency](remote-implementation-idempotency.md) first. Check if worktree already has a branch before creating new one. Reusing worktrees without checking causes PR orphaning.

**CRITICAL: Before running /erk:learn in CI** → Read [Learn Workflow](learn-workflow.md) first. CI mode skips interactive prompts and auto-proceeds. Check CI/GITHUB_ACTIONS env vars. See CI Environment Behavior section.

**CRITICAL: Before running /erk:learn on an issue that already has the erk-learn label** → Read [Learn Plans vs. Implementation Plans](learn-vs-implementation-plans.md) first. Learn plans cannot generate additional learn plans — this creates documentation cycles. The learn command validates this upfront and rejects learn-on-learn.

**CRITICAL: Before running sequential analysis that could be parallelized** → Read [Multi-Tier Agent Orchestration](agent-orchestration.md) first. If agents analyze independent data sources, run them in parallel. Only use sequential execution when one agent's output is another's input.

**CRITICAL: Before saving a plan with --objective-issue flag** → Read [Plan Lifecycle](lifecycle.md) first. Always verify the link was saved correctly with `erk exec get-plan-metadata <issue> objective_issue`. Silent failures can leave plans unlinked from their objectives.

**CRITICAL: Before staging .worker-impl/ deletion without an immediate commit** → Read [.worker-impl/ vs .impl/ Cleanup Discipline](worktree-cleanup.md) first. A downstream `git reset --hard` will silently discard staged-only deletions. Always commit+push cleanup atomically. See reliability-patterns.md.

**CRITICAL: Before staging git changes (git add/git rm) without an immediate commit before a git reset --hard** → Read [Workflow Reliability Patterns](reliability-patterns.md) first. git reset --hard silently discards staged changes. Commit and push cleanup BEFORE any reset step.

**CRITICAL: Before treating missing PR as an error in the learn pipeline** → Read [Learn Without PR Context](learn-without-pr-context.md) first. No-PR is a valid workflow state, not an error. The learn pipeline must degrade gracefully — sessions alone provide sufficient material for insight extraction.

**CRITICAL: Before updating imports one file at a time during gateway consolidation** → Read [Gateway Consolidation Checklist](gateway-consolidation-checklist.md) first. Use LibCST for systematic import updates. Manual editing misses call sites and creates partial migration states. See docs/learned/refactoring/libcst-systematic-imports.md.

**CRITICAL: Before using background agents without waiting for completion before dependent operations** → Read [Command-Agent Delegation](agent-delegation.md) first. Use TaskOutput with block=true to wait for all background agents to complete. Without synchronization, dependent agents may read incomplete outputs or missing files.

**CRITICAL: Before using issue number from .impl/issue.json in a checkout footer** → Read [PR Submission Patterns](pr-submission-patterns.md) first. Checkout footers require the PR number, not the issue number. The issue is the plan; the PR is the implementation. See the PR Number vs Issue Number section.

**CRITICAL: Before using issue timeline API as the primary PR lookup path** → Read [PR Discovery Strategies for Plans](pr-discovery.md) first. The primary path is branch_name from plan-header → get_pr_for_branch(). Timeline API is a separate strategy for when branch_name is unavailable.

**CRITICAL: Before using opus/sonnet for mechanical data fetching or formatting tasks** → Read [Token Optimization Patterns](token-optimization-patterns.md) first. Use haiku for mechanical work (fetch, parse, format). Reserve expensive models for synthesis and reasoning.

**CRITICAL: Before using session-scoped markers in exec scripts** → Read [Session-Based Plan Deduplication](session-deduplication.md) first. Session markers enable idempotency in command retries. Always write markers AFTER successful operation completion, never before. Use triple-check guard on marker read: file exists AND content is valid AND expected type (numeric for issue numbers).

**CRITICAL: Before writing a plan step that says 'update X' without a file path** → Read [Context Preservation Patterns](context-preservation-patterns.md) first. Generic references force re-discovery. Include the full path, line numbers, and evidence. See the five dimensions below.

**CRITICAL: Before writing to /tmp/** → Read [Scratch Storage](scratch-storage.md) first. AI workflow files belong in .erk/scratch/<session-id>/, NOT /tmp/.

**CRITICAL: Before writing verification criteria like 'documentation is complete'** → Read [Context Preservation Patterns](context-preservation-patterns.md) first. Vague verification is unverifiable. Criteria must be testable with grep, file inspection, or running code.
