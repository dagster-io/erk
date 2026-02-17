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

**adding a new step to the bootstrap sequence** → Read [Codespace Remote Execution Pattern](codespace-remote-execution.md) first. This affects ALL remote commands. The bootstrap runs on every SSH invocation, so added steps must be idempotent and fast.

**constructing a checkout footer string manually** → Read [PR Checkout Footer Validation Pattern](pr-commands.md) first. Use build_pr_body_footer() from the gateway layer. Manual construction risks format drift from the validator regex.

**creating a placeholder branch with ctx.branch_manager.create_branch()** → Read [Placeholder Branches](placeholder-branches.md) first. Placeholder branches must bypass BranchManager. Use ctx.git.branch.create_branch() to avoid Graphite tracking. See branch-manager-decision-tree.md for the full decision framework.

**deleting a placeholder branch with ctx.branch_manager.delete_branch()** → Read [Placeholder Branches](placeholder-branches.md) first. Placeholder branch deletion must also bypass BranchManager. Use ctx.git.branch.delete_branch() directly.

**duplicating git pull / uv sync / venv activation in a codespace command** → Read [Codespace Remote Execution Pattern](codespace-remote-execution.md) first. Use build_codespace_ssh_command() — bootstrap logic is centralized there. See composable-remote-commands.md for the five-step pattern.

**embedding single quotes in a remote erk command argument** → Read [Codespace Remote Execution Pattern](codespace-remote-execution.md) first. The bootstrap wraps the entire command in single quotes. Single quotes in arguments will break the shell string.

**removing the uv pip install --no-deps line from activation** → Read [Workspace Activation and Package Refresh](workspace-activation.md) first. This line refreshes workspace editable packages on every activation. Without it, worktrees may use stale versions of erk, erk-shared, or erk-statusline after switching branches.

**running gt sync without verifying clean working tree** → Read [Graphite Stack Troubleshooting](graphite-stack-troubleshooting.md) first. gt sync performs a rebase that can lose uncommitted changes. Commit or stash first. See docs/learned/workflows/git-sync-state-preservation.md

**using `gh codespace create` to create a codespace** → Read [Codespace Machine Types](codespace-machine-types.md) first. The machines endpoint returns HTTP 500 for this repo. Use `POST /user/codespaces` REST API directly. See the workaround section below.

**using issue number in checkout footer instead of PR number** → Read [PR Checkout Footer Validation Pattern](pr-commands.md) first. Checkout footer requires the PR number (from gh pr create output), NOT the plan issue number from .impl/issue.json.
