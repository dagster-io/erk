---
title: Planning Tripwires
read_when:
  - "working on planning code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from planning/*.md frontmatter -->

# Planning Tripwires

Rules triggered by matching actions in code.

**adding <code> inside <summary> elements in PR bodies** → Read [Planned PR Lifecycle](planned-pr-lifecycle.md) first. Graphite doesn't render <code> inside <summary> — use plain text instead. GitHub renders it but Graphite does not. The correct format is <summary>original-plan</summary> not <summary><code>original-plan</code></summary>.

**adding Closes #N to a planned PR footer** → Read [Planned PR Lifecycle](planned-pr-lifecycle.md) first. Planned PR IS the plan. Self-referential close would close the plan itself. Use issue_number=None for github-draft-pr backend.

**adding a new PR-dependent step to trigger-async-learn** → Read [Learn Without PR Context](learn-without-pr-context.md) first. Any new PR-dependent step must handle the None case from \_get_pr_for_plan_direct. The entire PR comment block is gated on pr_result not being None.

**adding a new filtering step to preprocess_session.py** → Read [Session Preprocessing Architecture](session-preprocessing.md) first. There are TWO preprocessing implementations: the exec script (preprocess_session.py) and erk-shared (session_preprocessing.py). The exec script has the full filtering pipeline; erk-shared has only Stage 1 mechanical reduction. New filters go in the exec script. Read this doc first.

**adding a new pipeline stage to trigger-async-learn** → Read [Learn Pipeline Workflow](learn-pipeline-workflow.md) first. New stages must be direct Python function calls, not subprocess invocations. The orchestrator uses tight coupling for performance. See the Direct-Call Architecture section in async-learn-local-preprocessing.md.

**adding a new setup path to plan-implement without routing through Step 2d** → Read [Impl-Context Staging Directory](impl-context.md) first. Impl-context cleanup routing: all code paths that set up an implementation context must route through Step 2d in plan-implement.md, which is the single convergence point for .erk/impl-context/ cleanup. Adding a new setup path that bypasses Step 2d will silently skip cleanup, leaving .erk/impl-context/ files in the final PR diff.

**adding branch_name to plan-header at creation time** → Read [Branch Name Inference](branch-name-inference.md) first. branch_name is intentionally omitted at creation because the branch doesn't exist yet. The plan-save → branch-create → impl-signal lifecycle requires this gap. See the temporal gap section below.

**adding dry-run support to one-shot commands** → Read [One-Shot Workflow](one-shot-workflow.md) first. One-shot dry-run mode must NOT create skeleton issues

**adding erk-consolidated label to a single-issue replan** → Read [Consolidation Labels](consolidation-labels.md) first. Only multi-plan consolidation gets the erk-consolidated label. Single-issue replans are updates, not consolidations.

**adding footer before PR creation** → Read [Planned PR Lifecycle](planned-pr-lifecycle.md) first. PR footer needs the PR number, which isn't known until after create_pr returns. Add footer AFTER PR creation.

**adding new agents to learn workflow** → Read [Learn Workflow](learn-workflow.md) first. Document input/output format and test file passing. Learn workflow uses stateless agents with file-based composition.

**adding post-dispatch operations without matching dispatch_cmd.py pattern** → Read [One-Shot Workflow](one-shot-workflow.md) first. dispatch_one_shot() and \_dispatch_planned_pr_plan() in dispatch_cmd.py must stay synchronized. Both use write_dispatch_metadata() + create_submission_queued_block(). Changes to one must be mirrored in the other.

**adding redundant branch-location guards to learn status checks** → Read [Remote Branch Learn Support](remote-branch-learn.md) first. Learn status checking in land_pipeline.py:341 requires is_current_branch or worktree_path is not None. Remote branches (is_current_branch=False, worktree_path=None) are not prompted for learn — this is intentional since remote sessions are handled via async-learn branches.

**adding subprocess calls to trigger-async-learn** → Read [Async Learn Local Preprocessing](async-learn-local-preprocessing.md) first. This command uses direct Python function calls, not subprocess invocations. This is intentional — see the direct-call architecture section below.

**after plan-implement execution completes** → Read [Plan Lifecycle](lifecycle.md) first. Always clean .erk/impl-context/ with `git rm -rf .erk/impl-context/` and commit. Transient artifacts cause CI formatter failures (Prettier).

**analyzing sessions larger than 100k characters** → Read [Scratch Storage](scratch-storage.md) first. Use `erk exec preprocess-session` first. Achieves ~99% token reduction (e.g., 6.2M -> 67k chars). Critical for fitting large sessions in agent context windows.

**assigning opus to a mechanical extraction agent** → Read [Multi-Tier Agent Orchestration](agent-orchestration.md) first. Model escalation: haiku/sonnet for extraction and rule-based work, opus only for creative authoring. See the model escalation decision table.

**assuming branch names always follow the P-prefix format** → Read [Branch Plan Resolution](branch-plan-resolution.md) first. Branch resolution supports multiple formats (P-prefix, objective). Use resolve_plan_id_for_branch() rather than manual parsing. See branch-plan-resolution.md.

**assuming branch_name is always present in plan-header metadata** → Read [PR Discovery Strategies for Plans](pr-discovery.md) first. branch_name is null until Phase 2 (pr dispatch). Check the plan metadata field lifecycle in lifecycle.md.

**assuming plan content is in the issue body** → Read [Plan Content Extraction Fallback](metadata-block-fallback.md) first. Schema v2 stores plan content in the FIRST COMMENT, not the issue body. The body contains only the plan-header metadata block. See extract_plan_from_comment() for the extraction logic.

**assuming remote sessions skip local preprocessing** → Read [Async Learn Local Preprocessing](async-learn-local-preprocessing.md) first. Since PR #6974, remote sessions go through the same \_preprocess_session_direct() pipeline as local sessions. They are downloaded first, then preprocessed identically.

**automatically removing .impl/ folder** → Read [.erk/impl-context/ vs .impl/ Cleanup Discipline](worktree-cleanup.md) first. NEVER auto-delete .impl/. It belongs to the user for plan-vs-implementation review. Only .erk/impl-context/ is auto-cleaned.

**backfilling labels on existing issues without considering updated_at side effects** → Read [Plan Label Assignment Scheme](label-scheme.md) first. GitHub label operations change the issue's updated_at timestamp. This affects sort order in list views and may confuse users.

**calling `create_impl_context()` without checking `impl_context_exists()` first** → Read [Impl-Context Staging Directory](impl-context.md) first. Both submit paths use LBYL: `if impl_context_exists(): remove_impl_context()` before creating. Stale .erk/impl-context/ from a prior failed submission causes errors.

**calling commands that depend on `.impl/plan-ref.json` metadata** → Read [Plan Lifecycle](lifecycle.md) first. Verify metadata file exists in worktree; if missing, operations silently return empty values. read_plan_ref() tries plan-ref.json first, falls back to legacy issue.json.

**calling gh issue view with a plan_id from PlannedPRBackend** → Read [Plan ID Semantics](plan-id-semantics.md) first. For planned-PR plans, plan_id is a PR number, not an issue number. Use gh pr view instead. Check provider type before assuming plan_id semantics.

**calling preprocess_session functions from trigger_async_learn** → Read [Session Preprocessing Architecture](session-preprocessing.md) first. trigger_async_learn duplicates the exec script's filtering pipeline as \_preprocess_session_direct(). If you change the exec script's pipeline, update the direct function too.

**calling update_metadata() on PlanBackend** → Read [PlanBackend Migration Guide](plan-backend-migration.md) first. Always check isinstance(result, PlanNotFound) before calling update_metadata()

**calling update_metadata() on PlannedPRBackend without verifying plan exists** → Read [Planned PR Backend](planned-pr-backend.md) first. PlannedPRBackend.update_metadata() raises PlanHeaderNotFoundError if the header block is absent. Read operations (get_plan) return None gracefully. Always check plan existence before writing metadata.

**capturing subagent output inline when it may exceed 1KB** → Read [Agent Orchestration Safety Patterns](agent-orchestration-safety.md) first. Bash tool truncates output at ~10KB with no error. Use Write tool to save agent output to scratch storage, then pass the file path to dependent agents.

**catching PlanHeaderNotFoundError** → Read [PlanBackend Migration Guide](plan-backend-migration.md) first. PlanHeaderNotFoundError is an exception; PlanNotFound is a result type - use LBYL for the latter

**changing branch naming convention (plnd/ prefix)** → Read [Branch Name Inference](branch-name-inference.md) first. The plnd/ prefix (planned-PR) is a cross-cutting contract used by branch creation, extraction functions, and PR recovery. Changing the prefix format requires updating all consumers. The legacy P{issue}- prefix has been fully removed.

**changing how sessions are classified as planning vs impl** → Read [Learn Pipeline Workflow](learn-pipeline-workflow.md) first. Classification uses planning_session_id from GitHub metadata. The resulting prefix (planning- vs impl-) propagates into XML filenames and is used by downstream learn agents to weight insights differently.

**checking erk exec plan-save --format json output for empty result** → Read [Planned PR Backend](planned-pr-backend.md) first. Empty stdout does not mean failure. The duplicate-detection path writes JSON to stderr, not stdout. Always capture both streams with 2>&1 or check for empty stdout and retry with stderr capture.

**checking only one location when extracting plan content** → Read [Plan Content Extraction Fallback](metadata-block-fallback.md) first. Always check both the first comment (plan-body metadata block) and the issue body before reporting 'no plan content found'. The replan command documents this explicitly in Step 4a.

**classifying a single-artifact API reference as NEW_DOC** → Read [Cornerstone Enforcement in Learn Pipeline](cornerstone-enforcement.md) first. Apply the three-rule SHOULD_BE_CODE test first. Single-artifact knowledge belongs in code (types, docstrings, or comments), not docs/learned/.

**closing a plan issue without verifying all items were addressed** → Read [Complete File Inventory Protocol](complete-inventory-protocol.md) first. Compare the file inventory against the plan's items before closing. Silent omissions are the most common failure mode.

**committing to planned-PR plan branches after checkout without pulling remote** → Read [Planned PR Branch Sync](planned-pr-branch-sync.md) first. Both setup_impl_from_pr.py and submit.py use the same three-step sync: fetch_branch -> checkout/create_tracking -> pull_rebase. Skipping pull_rebase causes non-fast-forward push failures.

**consolidating issues that already have erk-consolidated label** → Read [Consolidation Labels](consolidation-labels.md) first. Filter out erk-consolidated issues before consolidation. These are outputs of previous consolidation and should not be re-consolidated.

**constructing a PR footer manually instead of using build_pr_body_footer()** → Read [PR Submission Patterns](pr-submission-patterns.md) first. The footer format includes checkout commands and closing references with specific patterns. Use the builder function to ensure validation passes.

**creating a PR without first checking if one already exists for the branch** → Read [PR Submission Patterns](pr-submission-patterns.md) first. The dispatch pipeline is idempotent — it checks for existing PRs before creating. If building PR creation outside the pipeline, replicate this check to prevent duplicates.

**creating a learn plan without setting learned_from_issue** → Read [Learn Plans vs. Implementation Plans](learn-vs-implementation-plans.md) first. Learn plans MUST set learned_from_issue to their parent implementation plan's issue number. Without it, base branch auto-detection fails and the learn plan lands on trunk instead of stacking on the parent.

**creating a new branch for a planned-PR plan** → Read [Planned PR Branch Sync](planned-pr-branch-sync.md) first. Planned PR plans already have a branch created during plan-save. Reuse the existing branch, don't create a new one.

**creating a new plan-generating command without a pre-plan gathering step** → Read [Context Preservation Prompting Patterns](context-preservation-prompting.md) first. Without explicit context materialization before EnterPlanMode, agents produce sparse plans. Apply the two-phase pattern from this document.

**creating erk-learn plan for an issue that already has erk-learn label** → Read [Learn Plan Validation](learn-plan-validation.md) first. Validate target issue has erk-plan label, NOT erk-learn. Learn plans analyze implementation plans, not other learn plans (cycle prevention).

**creating temp files for AI workflows** → Read [Scratch Storage](scratch-storage.md) first. Use worktree-scoped scratch storage for session-specific data.

**delegating batch file renames from a plan** → Read [Plan Lifecycle](lifecycle.md) first. Verify each file path exists before delegating. Wrong paths cause silent coverage gaps in rename operations.

**delegating judgment steps to Haiku subagents** → Read [Command-Agent Delegation](agent-delegation.md) first. Prose reconciliation, design analysis, and architectural comparison need Opus-level reasoning. Delegating to a Haiku subagent loses quality. Also avoid delegating steps that require direct user interaction.

**designing output routing for a multi-agent workflow** → Read [Agent Output Routing Strategies](agent-output-routing-strategies.md) first. Choose between embedded-prompt routing (in orchestrator Task prompts) and agent-file routing (in agent definitions). See this doc for the decision framework.

**detecting plan backend by checking backend type directly** → Read [Planned PR Branch Sync](planned-pr-branch-sync.md) first. Use github.get_pr() + pr_result.head_ref_name to discover the plan branch. There is only one backend (planned-PR).

**editing plan body content in plan creation, replan, or one-shot dispatch** → Read [One-Shot Workflow](one-shot-workflow.md) first. One-shot metadata block preservation: the metadata block in the plan body (HTML comment with erk:metadata-block markers) must survive all edits. Never strip or overwrite HTML comment blocks that contain erk:metadata-block markers.

**entering Plan Mode in replan or consolidation workflow** → Read [Context Preservation in Replan Workflow](context-preservation-in-replan.md) first. Gather investigation context FIRST (Step 6a). Enter plan mode only after collecting file paths, evidence, and discoveries. Sparse plans are destructive to downstream implementation.

**estimating effort for a plan without checking actual files changed** → Read [Complete File Inventory Protocol](complete-inventory-protocol.md) first. Run a file inventory first. Plans that skip inventory systematically undercount configuration, test, and documentation changes.

**fetching N large documents into parent agent context** → Read [Token Optimization Patterns](token-optimization-patterns.md) first. Delegate content fetching to child agents. Parent receives only analysis summaries, not raw content. Achieves O(1) parent context instead of O(n). See token-optimization-patterns.md.

**gathering sessions for preprocessing** → Read [Learn Workflow](learn-workflow.md) first. Sessions >100k characters MUST be preprocessed first. Use erk exec preprocess-session for ~99% token reduction.

**grepping only for the error message text** → Read [Source Investigation Over Trial-and-Error](debugging-patterns.md) first. Also grep for function names extracted from the error (e.g., 'checkout_footer' from 'Missing checkout footer'). Validator function names are more stable search targets than error message strings.

**hardcoding next-steps command strings instead of using the dataclass properties** → Read [Next Steps Output Formatting](next-steps-output.md) first. Use IssueNextSteps or PlannedPRNextSteps dataclasses from erk_shared.output.next_steps. They are the single source of truth for command formatting.

**implementing PR body generation with checkout footers** → Read [Plan Lifecycle](lifecycle.md) first. HTML `<details>` tags will fail `has_checkout_footer_for_pr()` validation. Use plain text backtick format: `` `gh pr checkout <number>` ``

**implementing custom PR/plan relevance assessment logic** → Read [Plan Lifecycle](lifecycle.md) first. Reference `/local:check-relevance` verdict classification system first. Use SUPERSEDED (80%+ overlap), PARTIALLY_IMPLEMENTED (30-80% overlap), DIFFERENT_APPROACH, STILL_RELEVANT, NEEDS_REVIEW categories for consistency.

**implementing planned-PR plan without syncing with remote** → Read [Planned PR Branch Sync](planned-pr-branch-sync.md) first. Before implementing a planned-PR plan, always sync with remote: fetch_branch -> checkout/create_tracking -> pull_rebase

**importing functions directly from plan_header.py** → Read [Plan Header Privatization](plan-header-privatization.md) first. plan_header.py functions are being privatized. Use PlanBackend methods instead for metadata operations.

**including impl-signal or plan-save in a Task tool sub-agent prompt** → Read [Sub-Agent Context Limitations](sub-agent-context-limitations.md) first. Sub-agents cannot access ${CLAUDE_SESSION_ID}. Session-dependent commands must run in the root agent context. See sub-agent-context-limitations.md.

**launching a dependent agent that reads a file written by a prior agent** → Read [Agent Orchestration Safety Patterns](agent-orchestration-safety.md) first. Verify the file exists (ls) before launching. Write tool silently fails if the parent directory is missing, and the dependent agent wastes its entire context discovering the file isn't there.

**launching parallel agents that return results inline instead of writing to files** → Read [Parallel Agent Orchestration for Bulk Operations](parallel-audit-pattern.md) first. Parallel agents must write results via Write tool to .erk/scratch/ files. Inline results can be truncated or lost. The parent agent reads files after completion.

**making a third trial-and-error attempt at a validation fix** → Read [Source Investigation Over Trial-and-Error](debugging-patterns.md) first. After 2 failed attempts, stop guessing. Grep for the validator function and read the source to understand the exact requirement.

**making objective-update-after-land exit non-zero** → Read [Objective Update After Land](objective-update-after-land.md) first. This script uses fail-open design. Failures must not block landing. See objective-update-after-land.md.

**manually creating an erk-plan issue with gh issue create** → Read [Plan Lifecycle](lifecycle.md) first. Use `erk exec plan-save --plan-file <path>` instead. Manual creation requires complex metadata block format (see Metadata Block Reference section).

**manually setting the base branch for a learn plan submission** → Read [Learn Plans vs. Implementation Plans](learn-vs-implementation-plans.md) first. Learn plan base branch is auto-detected from learned_from_issue → parent branch. Only use --base to override if the parent branch is missing from the remote.

**marking a planned-PR plan as 'implementation complete' and referencing itself as the implementing PR** → Read [Planned PR Lifecycle](planned-pr-lifecycle.md) first. Self-referential close prevention: when a planned PR IS the plan, it cannot close itself. The plan's implementation-complete event cannot reference the plan PR as the implementing PR. One-shot dispatch guards against this — do not remove the guard.

**modifying learn command to add/remove/reorder agents** → Read [Learn Workflow](learn-workflow.md) first. Verify tier placement before assigning model. Parallel extraction uses haiku, sequential synthesis may need opus for quality-critical output.

**modifying marker deletion behavior in exit-plan-mode hook** → Read [Session-Based Plan Deduplication](session-deduplication.md) first. Reusable markers (plan-saved) must persist; one-time markers (implement-now, objective-context) are consumed. Deleting reusable markers breaks state machines and enables retry loops that create duplicates.

**modifying register-one-shot-plan exit behavior** → Read [One-Shot Workflow](one-shot-workflow.md) first. register-one-shot-plan uses best-effort: exit 0 if any operation succeeds

**modifying the gist upload content format** → Read [Learn Pipeline Workflow](learn-pipeline-workflow.md) first. The download side (download-learn-materials) parses delimiters to split content back into files. Changes to the upload format must be mirrored in the download parser. See gist-materials-interchange.md.

**moving gateway files without git mv** → Read [Gateway Consolidation Checklist](gateway-consolidation-checklist.md) first. Always use git mv to preserve file history. Plain mv + git add loses blame history, making future archaeology harder.

**parsing plan content without backward compatibility** → Read [Planned PR Lifecycle](planned-pr-lifecycle.md) first. extract_plan_content() handles both details-wrapped and old flat format. Always use it instead of manual parsing.

**passing ${CLAUDE_SESSION_ID} to a sub-agent via the prompt string** → Read [Sub-Agent Context Limitations](sub-agent-context-limitations.md) first. String substitution of ${CLAUDE_SESSION_ID} happens at the root agent level. By the time the sub-agent runs the bash command, the variable is not in its environment. The root agent must resolve the value and pass it as a literal.

**passing session content to an analysis agent** → Read [Session Preprocessing Architecture](session-preprocessing.md) first. Raw JSONL sessions can be 6+ million characters. Always preprocess first. The learn workflow validates preprocessed output exists before spawning agents.

**prompting an agent to 'include findings in the plan' without structuring them first** → Read [Context Preservation Prompting Patterns](context-preservation-prompting.md) first. Unstructured prompts don't work — agents summarize at too high a level. Use the four-category gathering step instead.

**pushing implementation commits after impl-context cleanup without git pull --rebase** → Read [Impl-Context Staging Directory](impl-context.md) first. After git rm + commit + push of .erk/impl-context/, the local branch may diverge from remote if other commits were pushed. Run git pull --rebase before pushing further implementation commits to avoid non-fast-forward push failures.

**querying plans using only the erk-planned-pr base label** → Read [Plan Label Assignment Scheme](label-scheme.md) first. Use type-specific labels (erk-plan, erk-learn) for queries. The base label erk-planned-pr is for identification, not filtering. See github-graphql-label-semantics.md for AND-logic issues.

**reading learn_plan_issue or learn_status** → Read [Learn Plan Metadata Preservation](learn-plan-metadata-fields.md) first. Verify field came through full pipeline. If null, check if filtered out earlier. Use gateway abstractions; never hand-construct Plan objects.

**reading parallel agent output without verifying files exist** → Read [Parallel Agent Orchestration for Bulk Operations](parallel-audit-pattern.md) first. Always verify output files exist (ls -la) before reading. Agent failures may produce empty or missing files.

**recovering a branch name from a PR number using UI or truncated display** → Read [Branch Name Inference](branch-name-inference.md) first. Use `gh pr view <pr-number> --json headRefName` to recover exact branch names. UI display may truncate long branch names.

**relying on agent instructions as the sole enforcement for a critical operation** → Read [Workflow Reliability Patterns](reliability-patterns.md) first. Agent behavior is non-deterministic. Critical operations need a deterministic workflow step as the final safety net.

**removing .erk/impl-context/ during implementation (before CI passes)** → Read [.erk/impl-context/ vs .impl/ Cleanup Discipline](worktree-cleanup.md) first. The folder is load-bearing during implementation — Claude reads from it (via copy to .impl/). Only remove after implementation succeeds and CI passes.

**removing git-tracked temporary directories in setup scripts** → Read [Impl-Context Staging Directory](impl-context.md) first. Defer deletion to the git cleanup phase (git rm + commit + push), not shutil.rmtree(). setup_impl_from_issue.py reads the files but deliberately does NOT delete them — see the comment at line 202. Deletion is handled by plan-implement.md Step 2d.

**renaming a lifecycle stage value** → Read [Plan Lifecycle](lifecycle.md) first. Update 3 locations: LifecycleStageValue type, valid_stages set, and color conditions in compute_lifecycle_display(). Missing any location causes silent validation failures or incorrect TUI colors.

**renaming gateway files during a move without checking for non-standard naming** → Read [Gateway Consolidation Checklist](gateway-consolidation-checklist.md) first. Source files that don't follow standard naming (e.g., executor.py instead of abc.py) must be renamed to abc.py/real.py/fake.py during the move. The gateway directory convention requires standard file names.

**reusing existing worktrees for remote implementation** → Read [Remote Implementation Idempotency](remote-implementation-idempotency.md) first. Check if worktree already has a branch before creating new one. Reusing worktrees without checking causes PR orphaning.

**reviewing a PR that contains .erk/impl-context/ files** → Read [Impl-Context Staging Directory](impl-context.md) first. Leave a PR comment telling the author to remove .erk/impl-context/. This is an erk tooling error — the directory should have been cleaned up before implementation. Run: git rm -rf .erk/impl-context/ && git commit -m 'Remove leaked impl-context'

**rewriting PR body without preserving metadata** → Read [Planned PR Lifecycle](planned-pr-lifecycle.md) first. Extract metadata prefix on every lifecycle transition via extract_metadata_prefix() to prevent metadata loss.

**running /erk:learn in CI** → Read [Learn Workflow](learn-workflow.md) first. CI mode skips interactive prompts and auto-proceeds. Check CI/GITHUB_ACTIONS env vars. See CI Environment Behavior section.

**running /erk:learn on an issue that already has the erk-learn label** → Read [Learn Plans vs. Implementation Plans](learn-vs-implementation-plans.md) first. Learn plans cannot generate additional learn plans — this creates documentation cycles. The learn command validates this upfront and rejects learn-on-learn.

**running sequential analysis that could be parallelized** → Read [Multi-Tier Agent Orchestration](agent-orchestration.md) first. If agents analyze independent data sources, run them in parallel. Only use sequential execution when one agent's output is another's input.

**saving a plan linked to an objective** → Read [Plan Lifecycle](lifecycle.md) first. Always verify the link was saved correctly with `erk exec get-plan-metadata <issue> objective_issue`. Silent failures can leave plans unlinked from their objectives.

**staging .erk/impl-context/ deletion without an immediate commit** → Read [.erk/impl-context/ vs .impl/ Cleanup Discipline](worktree-cleanup.md) first. A downstream `git reset --hard` will silently discard staged-only deletions. Always commit+push cleanup atomically. See reliability-patterns.md.

**staging git changes (git add/git rm) without an immediate commit before a git reset --hard** → Read [Workflow Reliability Patterns](reliability-patterns.md) first. git reset --hard silently discards staged changes. Commit and push cleanup BEFORE any reset step.

**treating missing PR as an error in the learn pipeline** → Read [Learn Without PR Context](learn-without-pr-context.md) first. No-PR is a valid workflow state, not an error. The learn pipeline must degrade gracefully — sessions alone provide sufficient material for insight extraction.

**updating imports one file at a time during gateway consolidation** → Read [Gateway Consolidation Checklist](gateway-consolidation-checklist.md) first. Use LibCST for systematic import updates. Manual editing misses call sites and creates partial migration states. See docs/learned/refactoring/libcst-systematic-imports.md.

**using 'steps' instead of 'nodes' in new plan metadata code** → Read [Schema V3 Migration](schema-v3-migration.md) first. Schema v3 uses 'nodes' (not 'steps'). The parser accepts both for backward compatibility but the renderer always emits v3. See schema-v3-migration.md.

**using `extract_metadata_prefix` or `extract_plan_content` without validating separator context** → Read [Planned PR Lifecycle](planned-pr-lifecycle.md) first. The content separator `\n\n---\n\n` can accidentally form from 'Remotely executed' notes + footer delimiter. extract_metadata_prefix() validates via `<!-- erk:metadata-block:` marker in the prefix. Never skip this validation.

**using background agents without waiting for completion before dependent operations** → Read [Command-Agent Delegation](agent-delegation.md) first. Use TaskOutput with block=true to wait for all background agents to complete. Without synchronization, dependent agents may read incomplete outputs or missing files.

**using gh issue view on a plan ID without checking plan backend type** → Read [Planned PR Backend](planned-pr-backend.md) first. Planned PR plan IDs are PR numbers. Using gh issue view on a planned-PR plan produces a confusing 404. Route to gh pr view based on backend type.

**using issue number from .impl/plan-ref.json in a checkout footer** → Read [PR Submission Patterns](pr-submission-patterns.md) first. Checkout footers require the PR number, not the issue number. The issue is the plan; the PR is the implementation. See the PR Number vs Issue Number section.

**using issue timeline API as the primary PR lookup path** → Read [PR Discovery Strategies for Plans](pr-discovery.md) first. The primary path is branch_name from plan-header → get_pr_for_branch(). Timeline API is a separate strategy for when branch_name is unavailable.

**using opus/sonnet for mechanical data fetching or formatting tasks** → Read [Token Optimization Patterns](token-optimization-patterns.md) first. Use haiku for mechanical work (fetch, parse, format). Reserve expensive models for synthesis and reasoning.

**using session-scoped markers in exec scripts** → Read [Session-Based Plan Deduplication](session-deduplication.md) first. Session markers enable idempotency in command retries. Always write markers AFTER successful operation completion, never before. Use triple-check guard on marker read: file exists AND content is valid AND expected type (numeric for issue numbers).

**validating plan_id in exec scripts without checking provider type** → Read [Planned PR Backend](planned-pr-backend.md) first. Planned PR plan_id IS the PR number (not an issue number). Check provider type before assuming plan_id semantics. Issue-based plans use issue numbers; planned-PR plans use PR numbers.

**writing a plan step that says 'update X' without a file path** → Read [Context Preservation Patterns](context-preservation-patterns.md) first. Generic references force re-discovery. Include the full path, line numbers, and evidence. See the five dimensions below.

**writing lifecycle_stage value other than 'impl' in a write point** → Read [Lifecycle Stage Consolidation](lifecycle-stage-consolidation.md) first. All lifecycle write points must use 'impl', never the legacy values 'implementing' or 'implemented'. Schema validation accepts legacy values for backwards compatibility only.

**writing post-dispatch operations without try/except guards** → Read [One-Shot Workflow](one-shot-workflow.md) first. Post-dispatch operations (metadata write, queued comment) are best-effort. Wrap in try/except with user-visible warnings. See write_dispatch_metadata() and create_submission_queued_block() in one_shot_dispatch.py.

**writing to /tmp/** → Read [Scratch Storage](scratch-storage.md) first. AI workflow files belong in .erk/scratch/<session-id>/, NOT /tmp/.

**writing verification criteria like 'documentation is complete'** → Read [Context Preservation Patterns](context-preservation-patterns.md) first. Vague verification is unverifiable. Criteria must be testable with grep, file inspection, or running code.
