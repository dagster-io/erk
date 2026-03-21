---
title: PR Feedback Classification Architecture
read_when:
  - "working with PR review feedback classification"
  - "debugging why review comments are not being classified correctly"
  - "understanding the two-stage classify-then-summarize pipeline"
  - "adding new classification rules to classify-pr-feedback"
tripwires:
  - action: "doing bot detection or state interpretation in the LLM skill"
    warning: "Mechanical classification (bot detection, APPROVED/CHANGES_REQUESTED state, restructuring detection) belongs in the CLI stage (classify-pr-feedback). The LLM skill only handles action summaries, complexity, and ambiguous cases."
  - action: "putting restructuring analysis (renamed files) in the LLM skill"
    warning: "Restructuring detection uses `git diff -M -C` in the CLI stage. The LLM receives a pre-built RestructuredFile list, not raw diff output."
---

# PR Feedback Classification Architecture

## Two-Stage Pipeline

PR feedback classification uses a two-stage pipeline: mechanical (CLI) then semantic (LLM skill).

### Stage 1: CLI (`classify-pr-feedback` exec command)

**Source**: `src/erk/cli/commands/exec/scripts/classify_pr_feedback.py` (493 lines)

**Registered**: `exec/group.py:202` as `classify-pr-feedback`

Performs deterministic classification:

| Task                        | Implementation                                                                |
| --------------------------- | ----------------------------------------------------------------------------- |
| Bot detection               | `[bot]` suffix check on review author login                                   |
| State interpretation        | `APPROVED` → informational, `CHANGES_REQUESTED` → actionable                  |
| Restructuring analysis      | `git diff -M -C` detects renamed/moved/copied files → `RestructuredFile` list |
| Pre-existing issue flagging | Candidate identification for "already existed" comments                       |

Output: JSON with mechanically classified feedback (intermediate format for LLM)

### Stage 2: LLM (pr-feedback-classifier skill)

**Source**: `.claude/skills/pr-feedback-classifier/`

Handles semantic tasks:

- `action_summary`: Brief description of what needs to change
- Complexity estimation (simple/moderate/complex)
- Ambiguous review classification (when state alone is insufficient)
- Batch construction for PR address workflow

## Data Flow

```
GitHub API (reviews, threads, comments)
    ↓ erk exec classify-pr-feedback
JSON output (mechanically classified)
    ↓ pr-feedback-classifier skill
Batched output → pr-address workflow
```

## Key Output Types

Frozen dataclasses in `classify_pr_feedback.py`:

- `RestructuredFile` — renamed/copied/moved file with old and new paths
- Review thread classification with resolved/active state
- Discussion comment classification with bot flag

## Related Documentation

- [PR Address Command](../cli/pr-address.md) — Consumer of the classification pipeline
