---
title: Workflows Tripwires
read_when:
  - "working on workflows code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from workflows/*.md frontmatter -->

# Workflows Tripwires

Rules triggered by matching actions in code.

**assuming one-shot plan and implementation run in the same Claude session** → Read [One-Shot Workflow](one-shot-workflow.md) first. They run in separate sessions. The plan is written to `.impl/plan.md` and the implementer reads it fresh. No context carries over.

**loading erk-diff-analysis skill more than once per session** → Read [Skill-Based Commit Message Generation](commit-messages.md) first. Skills persist for the entire session. Check conversation history for 'erk-diff-analysis' before reloading.

**modifying one-shot branch naming convention** → Read [One-Shot Workflow](one-shot-workflow.md) first. Branch format is `oneshot-{slug}-{MM-DD-HHMM}` (no plan issue) or `P{N}-{slug}-{MM-DD-HHMM}` (when plan_issue_number is provided). The workflow and CLI both depend on these prefixes for identification.

**running gt sync without committing or stashing working tree changes** → Read [Git Sync State Preservation](git-sync-state-preservation.md) first. gt sync performs a rebase which can silently lose uncommitted changes. Always commit or stash before sync, and verify working tree state after.

**writing a commit message manually for multi-file changes** → Read [Skill-Based Commit Message Generation](commit-messages.md) first. Load the erk-diff-analysis skill first. It produces component-aware, strategically framed messages that become both the commit and PR body.
