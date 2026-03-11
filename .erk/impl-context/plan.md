# Switch all remote dispatch workflows to Sonnet 4.6

## Context

All 7 Claude-invoking workflows currently default to `claude-opus-4-6`. Additionally, `.erk/config.toml` overrides plan-implement to `claude-opus-4-5`. Switching everything to `claude-sonnet-4-6` for cost/speed optimization.

## Changes

### 1. Workflow YAML defaults (`claude-opus-4-6` → `claude-sonnet-4-6`)

Each file has a `default: "claude-opus-4-6"` line to change:

- `.github/workflows/one-shot.yml` (line 31)
- `.github/workflows/plan-implement.yml` (line 35 + line 81 — dual default for workflow_dispatch and workflow_call)
- `.github/workflows/pr-address.yml` (line 19)
- `.github/workflows/pr-rebase.yml` (line 32)
- `.github/workflows/pr-rewrite.yml` (line 27)
- `.github/workflows/consolidate-learn-plans.yml` (line 27)
- `.github/workflows/learn.yml` (line 71 — hard-coded `--model claude-opus-4-6` in bash)

### 2. Config override (`.erk/config.toml`)

Line 15: `model_name = "claude-opus-4-5"` → `model_name = "claude-sonnet-4-6"`

### 3. Policy doc update (`docs/learned/ci/workflow-model-policy.md`)

Update the policy to reflect `claude-sonnet-4-6` as the new standard default across all workflows and tripwire text.

## Verification

- `grep -r "claude-opus" .github/workflows/` should return no results
- `grep "model_name" .erk/config.toml` should show `claude-sonnet-4-6`
