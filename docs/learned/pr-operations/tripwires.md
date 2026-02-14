---
title: Pr Operations Tripwires
read_when:
  - "working on pr-operations code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from pr-operations/*.md frontmatter -->

# Pr Operations Tripwires

Rules triggered by matching actions in code.

**adding Closes reference in a PR body update instead of initial creation** → Read [PR Validation Rules](pr-validation-rules.md) first. GitHub sets willCloseTarget at PR creation time. The Closes reference must be in the initial create_pr body, not a subsequent update. See checkout-footer-syntax.md.

**adding git-only PR logic to a new location** → Read [Git-Only PR Submission Path](pr-submission-workflow.md) first. Two git-only paths already exist (command-level and pipeline-level). Understand why both exist before adding a third. See pr-submission-workflow.md.

**adding plan HTML to the pr_body variable instead of pr_body_for_github** → Read [Plan Embedding in PR Body](plan-embedding-in-pr.md) first. Plan embedding uses <details> HTML which must never enter git commit messages. Append only to pr_body_for_github. See pr-body-formatting.md for the two-target pattern.

**calling create_pr without first checking get_pr_for_branch** → Read [PR Creation Decision Logic](pr-creation-patterns.md) first. Always LBYL-check for an existing PR before creating. Duplicate PRs cause confusion and orphaned state. See pr-creation-patterns.md.

**completing pr-address without updating PR body/title** → Read [PR Submit Workflow Phases](pr-submit-phases.md) first. Phase 5 (erk pr update-description) must run after addressing review comments. Skipping leaves PR body stale, which breaks objective-update-with-landed-pr accuracy.

**creating a PR without draft=True in automated workflows** → Read [Draft PR Handling](draft-pr-handling.md) first. All automated erk PR creation uses draft mode. This gates CI costs and prevents premature review. See draft-pr-handling.md.

**editing commit-message-prompt.md in either location** → Read [Template Synchronization](template-synchronization.md) first. Update BOTH copies: .claude/skills/erk-diff-analysis/references/commit-message-prompt.md AND packages/erk-shared/src/erk_shared/gateway/gt/commit_message_prompt.md. CI enforces byte-equality.

**using gh pr create directly in Python code** → Read [Git-Only PR Submission Path](pr-submission-workflow.md) first. The pipeline uses ctx.github.create_pr() (REST API gateway), not gh pr create. The command-level path uses gh CLI directly because it runs in shell context. See pr-submission-workflow.md.

**using gh pr ready instead of the gateway's mark_pr_ready method** → Read [Draft PR Handling](draft-pr-handling.md) first. mark_pr_ready uses REST API to preserve GraphQL quota. Don't shell out to gh pr ready directly.

**using issue number from .impl/issue.json in a checkout footer** → Read [PR Validation Rules](pr-validation-rules.md) first. Checkout footers require the PR number (from create_pr return value), NOT the issue number. Issue numbers go in `Closes` references. See pr-validation-rules.md.

**using raw gh pr view or gh pr create in Python code** → Read [PR Creation Decision Logic](pr-creation-patterns.md) first. Use the typed GitHub gateway (get_pr_for_branch, create_pr) instead of shelling out. The gateway returns PRDetails | PRNotFound for LBYL handling.

**writing checkout footer with issue number from .impl/issue.json** → Read [Checkout Footer Syntax](checkout-footer-syntax.md) first. Use PR number (from create_pr result), NOT issue number. The checkout command requires a PR number. Issue numbers in checkout footers cause erk pr check validation failures.

**writing gh pr checkout in a PR footer** → Read [Checkout Footer Syntax](checkout-footer-syntax.md) first. The checkout footer uses `erk pr checkout <number> --script`, NOT `gh pr checkout`. The footer format has changed.
