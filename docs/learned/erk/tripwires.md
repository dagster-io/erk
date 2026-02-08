---
title: Erk Tripwires
read_when:
  - "working on erk code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from erk/*.md frontmatter -->

# Erk Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before constructing a checkout footer string manually** → Read [PR Checkout Footer Validation Pattern](pr-commands.md) first. Use build_pr_body_footer() from the gateway layer. Manual construction risks format drift from the validator regex.

**CRITICAL: Before creating a placeholder branch with ctx.branch_manager.create_branch()** → Read [Placeholder Branches](placeholder-branches.md) first. Placeholder branches must bypass BranchManager. Use ctx.git.branch.create_branch() to avoid Graphite tracking. See branch-manager-decision-tree.md for the full decision framework.

**CRITICAL: Before deleting a placeholder branch with ctx.branch_manager.delete_branch()** → Read [Placeholder Branches](placeholder-branches.md) first. Placeholder branch deletion must also bypass BranchManager. Use ctx.git.branch.delete_branch() directly.

**CRITICAL: Before using `gh codespace create` to create a codespace** → Read [Codespace Machine Types](codespace-machine-types.md) first. The machines endpoint returns HTTP 500 for this repo. Use `POST /user/codespaces` REST API directly. See the workaround section below.

**CRITICAL: Before using issue number in checkout footer instead of PR number** → Read [PR Checkout Footer Validation Pattern](pr-commands.md) first. Checkout footer requires the PR number (from gh pr create output), NOT the plan issue number from .impl/issue.json.
