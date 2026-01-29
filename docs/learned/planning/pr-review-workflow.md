---
title: PR-Based Plan Review Workflow
category: planning
read_when: Reviewing plans collaboratively before implementation
---

# PR-Based Plan Review Workflow

## Overview

Alternative to immediate implementation: submit plans as temporary PRs for collaborative review.

## When to Use

- Plan is complex and needs multiple stakeholders to review
- Significant architectural decision requires team input
- Want feedback on approach before implementation

## Workflow Steps

1. Create plan via plan mode or `/erk:objective-next-plan`
2. Save to GitHub with `/erk:plan-save`
3. Run: `erk exec plan-submit-for-review <issue-number>`
4. Create temporary PR with plan content using returned data
5. Review and discuss in PR UI
6. Incorporate feedback into plan
7. Delete temporary PR branch
8. Implement plan normally via `erk plan submit`

## Command Reference

| Command                                      | Purpose                             |
| -------------------------------------------- | ----------------------------------- |
| `erk exec plan-submit-for-review <issue>`    | Extract plan content from issue     |
| `erk exec plan-create-review-branch <issue>` | Create review branch with plan file |

## Difference from Direct Implementation

- **Direct:** `erk plan submit` creates branch, PR, implements automatically
- **Review:** `erk exec plan-submit-for-review` returns data for manual review PR creation
