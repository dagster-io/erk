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

**creating a PR without draft=True in automated workflows** → Read [Draft PR Handling](draft-pr-handling.md) first. All automated erk PR creation uses draft mode. This gates CI costs and prevents premature review. See draft-pr-handling.md.

**editing commit-message-prompt.md in either location** → Read [Template Synchronization](template-synchronization.md) first. Update BOTH copies: .claude/skills/erk-diff-analysis/references/commit-message-prompt.md AND packages/erk-shared/src/erk_shared/gateway/gt/commit_message_prompt.md. CI enforces byte-equality.

**investigating an automated reviewer complaint** → Read [Automated Review Handling](automated-review-handling.md) first. Determine if the tool is the authority for that concern. For formatting, prettier is the authority — if prettier passes, dismiss the bot. For type errors, ty is the authority.

**silently catching exceptions in PR body updates** → Read [Stub PR Workflow Link](stub-pr-workflow-link.md) first. Use best-effort pattern: try/except with logger.warning(), not silent pass. See one_shot_dispatch.py for the canonical example.

**using GitHub API to fetch PR diffs** → Read [Large Diff PR Submission Recovery](large-diff-recovery.md) first. GitHub returns HTTP 406 for diffs exceeding ~20k lines. Use local git diff instead via get_diff_to_branch() for reliable extraction.

**using gh pr create directly in Python code** → Read [Git-Only PR Submission Path](pr-submission-workflow.md) first. The pipeline uses ctx.github.create_pr() (REST API gateway), not gh pr create. The command-level path uses gh CLI directly because it runs in shell context. See pr-submission-workflow.md.

**using gh pr ready instead of the gateway's mark_pr_ready method** → Read [Draft PR Handling](draft-pr-handling.md) first. mark_pr_ready uses REST API to preserve GraphQL quota. Don't shell out to gh pr ready directly.

**using issue number from .impl/issue.json in a checkout footer** → Read [PR Validation Rules](pr-validation-rules.md) first. Checkout footers require the PR number (from create_pr return value), NOT the issue number. Issue numbers go in `Closes` references. See pr-validation-rules.md.

**using raw gh pr view or gh pr create in Python code** → Read [PR Creation Decision Logic](pr-creation-patterns.md) first. Use the typed GitHub gateway (get_pr_for_branch, create_pr) instead of shelling out. The gateway returns PRDetails | PRNotFound for LBYL handling.

**working on branch after erk pr submit** → Read [Git-Only PR Submission Path](pr-submission-workflow.md) first. Squash-force-push causes branch divergence. Run `git pull --rebase` after erk pr submit before making further changes.

**writing checkout footer with issue number from .impl/issue.json** → Read [Checkout Footer Syntax](checkout-footer-syntax.md) first. Use PR number (from create_pr result), NOT issue number. The checkout command requires a PR number. Issue numbers in checkout footers cause erk pr check validation failures.

**writing gh pr checkout in a PR footer** → Read [Checkout Footer Syntax](checkout-footer-syntax.md) first. The checkout footer uses `erk pr checkout <number> --script`, NOT `gh pr checkout`. The footer format has changed.
