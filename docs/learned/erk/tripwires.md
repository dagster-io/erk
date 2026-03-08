---
title: Erk Tripwires
read_when:
  - "working on erk code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from erk/*.md frontmatter -->

# Erk Tripwires

Rules triggered by matching actions in code.

**adding a new call site that passes same_worktree** → Read [Same-Worktree Navigation](same-worktree-navigation.md) first. Use target_path.resolve() == ctx.cwd.resolve() — not string comparison. See same-worktree-navigation.md.

**adding a new cleanup path in land_cmd.py without calling \_ensure_branch_not_checked_out()** → Read [Multi-Path Branch Cleanup in Land](four-path-cleanup.md) first. All cleanup paths must call \_ensure_branch_not_checked_out() before branch deletion. Git refuses to delete branches checked out in any worktree.

**adding a new step to the bootstrap sequence** → Read [Codespace Remote Execution Pattern](codespace-remote-execution.md) first. This affects ALL remote commands. The bootstrap runs on every SSH invocation, so added steps must be idempotent and fast.

**assuming dispatch_ref is project-level config** → Read [dispatch_ref Configuration](dispatch-ref-config.md) first. dispatch_ref is repo-level config (.erk/config.toml), overridable at local level (.erk/config.local.toml). It is not project-level.

**checking thread count without comparing to dash count** → Read [PR Feedback Classifier Schema](pr-feedback-classifier-schema.md) first. Thread count in classifier output must equal erk dash count. Missing threads are silently dropped.

**constructing a checkout footer string manually** → Read [PR Checkout Footer Validation Pattern](pr-commands.md) first. Use build_pr_body_footer() from the gateway layer. Manual construction risks format drift from the validator regex.

**constructing branch names manually** → Read [Branch Naming Conventions](branch-naming.md) first. Use generate_planned_pr_branch_name() for consistent objective ID encoding.

**creating a placeholder branch with ctx.branch_manager.create_branch()** → Read [Placeholder Branches](placeholder-branches.md) first. Placeholder branches must bypass BranchManager. Use ctx.git.branch.create_branch() to avoid Graphite tracking. See branch-manager-decision-tree.md for the full decision framework.

**deleting a placeholder branch with ctx.branch_manager.delete_branch()** → Read [Placeholder Branches](placeholder-branches.md) first. Placeholder branch deletion must also bypass BranchManager. Use ctx.git.branch.delete_branch() directly.

**deleting stub branches without untracking from Graphite first** → Read [Stub Branch Lifecycle](stub-branch-lifecycle.md) first. Stub branches tracked by Graphite pollute gt log output. Untrack with gt branch untrack before deletion.

**duplicating git pull / uv sync / venv activation in a codespace command** → Read [Codespace Remote Execution Pattern](codespace-remote-execution.md) first. Use build_codespace_ssh_command() — bootstrap logic is centralized there. See composable-remote-commands.md for the five-step pattern.

**editing .claude/ markdown without running prettier** → Read [PR Feedback Classifier Schema](pr-feedback-classifier-schema.md) first. Run `prettier --write <file>` immediately after editing .claude/ markdown. `make fast-ci` fails otherwise.

**embedding single quotes in a remote erk command argument** → Read [Codespace Remote Execution Pattern](codespace-remote-execution.md) first. The bootstrap wraps the entire command in single quotes. Single quotes in arguments will break the shell string.

**implementing branch deletion during automated cleanup** → Read [Branch Cleanup Guide](branch-cleanup.md) first. Use force=True (git branch -D) for post-merge cleanup. Non-force delete refuses squash-merged branches because the SHA differs.

**passing both --ref and --ref-current to a dispatch command** → Read [dispatch_ref Configuration](dispatch-ref-config.md) first. --ref and --ref-current are mutually exclusive. resolve_dispatch_ref() raises UsageError if both are provided.

**pushing to a branch that may have been updated remotely without checking for divergence** → Read [Graphite Divergence Detection](graphite-divergence-detection.md) first. The Graphite-first flow pre-checks for divergence before gt submit. Check with branch_exists_on_remote -> fetch_branch -> is_branch_diverged_from_remote.

**removing the uv pip install --no-deps line from activation** → Read [Workspace Activation and Package Refresh](workspace-activation.md) first. This line refreshes workspace editable packages on every activation. Without it, worktrees may use stale versions of erk, erk-shared, or erk-statusline after switching branches.

**resolving a review thread when the comment is a discussion comment (not a review thread)** → Read [PR Address Workflows](pr-address-workflows.md) first. Review threads and discussion comments use different GitHub APIs. resolve-review-threads only handles review threads. Discussion comments are resolved differently (or not at all).

**running gt commands without --no-interactive** → Read [Graphite Divergence Detection](graphite-divergence-detection.md) first. All gt commands MUST use --no-interactive. Without it, gt may prompt for input and hang indefinitely.

**running gt sync without verifying clean working tree** → Read [Graphite Stack Troubleshooting](graphite-stack-troubleshooting.md) first. gt sync performs a rebase that can lose uncommitted changes. Commit or stash first. See docs/learned/workflows/git-sync-state-preservation.md

**running raw git commands (checkout, branch) without gt track on a Graphite-managed branch** → Read [Graphite Divergence Detection](graphite-divergence-detection.md) first. Raw git commands (checkout, branch) without `gt track` cause Graphite's cache to diverge from actual branch state. Use BranchManager which handles Graphite tracking automatically, or call `gt track` after raw git operations.

**treating informational_count as including review threads** → Read [PR Feedback Classifier Schema](pr-feedback-classifier-schema.md) first. informational_count covers ONLY discussion comments, not review threads. All unresolved review threads must appear individually in actionable_threads.

**trying to extract plan number from branch name** → Read [Branch Naming Conventions](branch-naming.md) first. Plan numbers are NOT encoded in branch names. Use plan-ref.json as the sole source of truth.

**using `gh codespace create` to create a codespace** → Read [Codespace Machine Types](codespace-machine-types.md) first. The machines endpoint returns HTTP 500 for this repo. Use `POST /user/codespaces` REST API directly. See the workaround section below.

**using find_worktree_for_branch() alone for stack navigation** → Read [Worktree Branch Mismatch Handling](worktree-branch-mismatch.md) first. Always use find_worktree_for_branch_or_path() for stack navigation, not find_worktree_for_branch() alone. The path-based fallback handles cases where users ran manual git checkout in a worktree.

**using has_uncommitted_changes() to check slot reuse eligibility** → Read [Slot Pool Architecture](slot-pool-architecture.md) first. Untracked files are safe for branch switching — use get_file_status() and check only staged/modified files. has_uncommitted_changes() includes untracked files which would incorrectly block slot reuse.

**using issue number in checkout footer instead of PR number** → Read [PR Checkout Footer Validation Pattern](pr-commands.md) first. Checkout footer requires the PR number (from gh pr create output), NOT the plan number from .erk/impl-context/plan-ref.json.
