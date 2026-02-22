---
title: One-Shot Workflow
read_when:
  - "using erk one-shot command"
  - "understanding one-shot remote execution"
  - "debugging one-shot workflow failures"
  - "working with one-shot.yml"
tripwires:
  - action: "modifying one-shot branch naming convention"
    warning: "Branch format is `oneshot-{slug}-{MM-DD-HHMM}` (no plan issue) or `P{N}-{slug}-{MM-DD-HHMM}` (when plan_issue_number is provided). The workflow and CLI both depend on these prefixes for identification."
  - action: "assuming one-shot plan and implementation run in the same Claude session"
    warning: "They run in separate sessions. The plan is written to `.impl/plan.md` and the implementer reads it fresh. No context carries over."
---

# One-Shot Workflow

This document has been consolidated into [planning/one-shot-workflow.md](../planning/one-shot-workflow.md), which contains the complete reference including skeleton plan pattern, objective integration, registration details, and source code references.

See [planning/one-shot-workflow.md](../planning/one-shot-workflow.md) for all content.
