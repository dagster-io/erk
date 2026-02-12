---
title: Objective Reconciler Workflow
read_when:
  - understanding automated objective advancement
  - configuring objective reconciler GitHub Action
  - debugging objective reconciliation
tripwires:
  - action: "triggering objective reconciliation"
    warning: "The reconcile command launches Claude interactively—it does NOT perform autonomous batch processing. Review actual workflow implementation before assuming sweep behavior."
---

# Objective Reconciler Workflow

Why reconciliation exists: objectives track multi-PR goals with roadmap tables. When a PR lands, the objective's next pending step should get a plan. Manual creation doesn't scale; automatic reconciliation bridges objective roadmaps to plan generation.

## Two Reconciliation Modes

Erk provides two distinct workflows with different triggering and scope:

### Single-Objective Mode

**Workflow:** `objective-reconcile.yml`
**Trigger:** `erk launch objective-reconcile --objective <N>`

<!-- Source: .github/workflows/objective-reconcile.yml -->

See `.github/workflows/objective-reconcile.yml` for workflow structure. The workflow dispatches with `distinct_id` for run discovery.

The reconcile command (removed in PR #6736) launched Claude interactively with `/erk:objective-next-plan`.

**What actually happens:**

1. CLI validates objective exists and has `erk-objective` label
2. Launches Claude Code in plan mode with full codebase access
3. Claude executes the `/erk:objective-next-plan` command interactively
4. Agent creates plan through normal planning workflow

This is NOT autonomous batch processing—it's **human-in-the-loop plan creation via remote Claude session**.

### Sweep Mode (Disabled by Default)

**Workflow:** `objective-reconciler.yml` (plural)
**Trigger:** Manual dispatch or scheduled cron (currently commented out)

<!-- Source: .github/workflows/objective-reconciler.yml -->

See `.github/workflows/objective-reconciler.yml:15-17` for the disabled cron schedule. Uncomment to enable 15-minute reconciliation sweeps.

**Design intent:** Query all objectives with `auto-advance` label, reconcile each in sequence.

**Current state:** The workflow file exists but the `auto-advance` label is not used anywhere in the codebase. Grep finds zero references in `src/erk/` to this label. The sweep mode is infrastructure without implementation.

## Why Reconciliation Launches Claude Interactively

The `/erk:objective-next-plan` command requires context-dependent decisions:

1. **Step selection** — Multiple pending steps may exist; agent asks user which to plan
2. **Codebase exploration** — Agent needs to grep, read files, understand current architecture
3. **Plan quality** — Interactive planning produces better plans than templated generation

Autonomous batch reconciliation would require either:

- Pre-selecting the next step (which step? Linear progression ignores dependencies)
- Skipping exploration (plans lack context about current codebase state)
- Auto-approving plans (quality drops without review)

The interactive approach trades automation speed for plan quality.

## Concurrency Control

<!-- Source: .github/workflows/objective-reconcile.yml -->

Single-objective mode uses `group: reconcile-objective-${{ github.event.inputs.objective }}` to prevent concurrent reconciliation of the same objective. Different objectives can reconcile in parallel.

<!-- Source: .github/workflows/objective-reconciler.yml -->

Sweep mode uses `group: reconcile-objectives-sweep` with `cancel-in-progress: false` to serialize all sweeps globally. This prevents multiple sweeps from racing to create plans for the same objectives.

## Secret Requirements

Both workflows require:

| Secret                    | Purpose                              |
| ------------------------- | ------------------------------------ |
| `ERK_QUEUE_GH_PAT`        | GitHub token for issue operations    |
| `ANTHROPIC_API_KEY`       | Claude API access                    |
| `CLAUDE_CODE_OAUTH_TOKEN` | OAuth token for Claude Code sessions |

<!-- Source: .github/workflows/objective-reconciler.yml -->

See `.github/workflows/objective-reconciler.yml:41-48` for the setup action that consumes these secrets.

### Slash Command

The workflow launches Claude with `/erk:objective-next-plan` to create plans for pending objective steps.

## Cost Model Reality

The original document estimated ~$0.003 per objective. This is wrong for two reasons:

1. **Interactive sessions cost more** — Claude explores the codebase, reads multiple files, plans iteratively. A single reconciliation can consume 50K+ tokens depending on codebase complexity.

2. **No batching** — Each objective launches a separate Claude session. 10 objectives = 10 sessions = 10× the cost.

Actual cost per reconciliation: **$0.01-0.05** depending on codebase size and plan complexity.

Sweep mode running every 15 minutes (96 runs/day) with 5 active objectives = 480 sessions/day = **$4.80-24.00/day**. This is why the cron schedule is disabled by default.

## Label Dependency Gap

The workflows reference `auto-advance` label as the selector for sweep mode, but:

- No code creates this label
- No documentation explains when to apply it
- No validation prevents applying it to non-objectives

The label exists in workflow YAML but not in the label ontology. This is a **missing implementation piece**, not just documentation.

To enable sweep mode:

1. Define `auto-advance` label in GitHub repo settings
2. Document criteria for applying the label (all objectives? specific phases?)
3. Update objective creation workflow to optionally add the label
4. Test sweep mode with a single auto-advance objective before enabling cron

## Relationship to `erk launch` Command

<!-- Source: src/erk/cli/commands/launch_cmd.py, _trigger_objective_reconcile -->

The `erk launch objective-reconcile` command is a thin wrapper around GitHub's workflow dispatch API. See `_trigger_objective_reconcile()` in `src/erk/cli/commands/launch_cmd.py:160-191` for implementation.

The wrapper:

1. Validates objective exists
2. Builds workflow inputs (`objective`, `dry_run`)
3. Triggers workflow via GitHub API
4. Returns workflow run URL

No local reconciliation logic—purely a remote trigger.

## Dry-Run Mode

Both workflows support `--dry-run` flag, but it's **not implemented in the actual reconcile command**. The flag passes through to the workflow but has no effect because `reconcile_cmd.py` doesn't check for it.

To implement dry-run:

1. Add `--dry-run` flag to `reconcile_objectives()` CLI command
2. Pass flag to interactive agent config
3. Modify `/erk:objective-next-plan` to skip `EnterPlanMode` in dry-run
4. Print "DRY RUN: Would create plan for step X" instead

Currently, `--dry-run` is **documentation-driven fiction**.

## When to Use Which Mode

| Scenario                                         | Use                                              | Why                                               |
| ------------------------------------------------ | ------------------------------------------------ | ------------------------------------------------- |
| Manually create plan for specific objective step | `erk launch objective-reconcile --objective <N>` | Human reviews step selection and plan             |
| Want autonomous reconciliation                   | Don't use either mode                            | Not implemented; interactive sessions don't batch |
| Testing reconciliation workflow                  | Single-objective mode with `--dry-run`           | No-op currently; would need implementation        |

## Future Enhancement Path

To achieve true autonomous reconciliation:

1. **Step selection policy** — Define algorithm: next pending step, highest priority, unblocked dependencies
2. **Plan template system** — Generate plans from roadmap step descriptions without full exploration
3. **Quality gates** — Auto-approve simple plans, flag complex ones for review
4. **Cost controls** — Daily budget limits, max concurrent reconciliations
5. **Dry-run implementation** — Actually implement the flag

Until then, reconciliation is **interactive planning with GitHub Actions glue**, not autonomous sweep.

## Related Documentation

- [Objective Commands](../cli/objective-commands.md) — CLI interface for objective management
- [GitHub Actions Workflow Patterns](github-actions-workflow-patterns.md) — Workflow composition patterns
