# Plan: Add visible AI-generated summary to plan PRs

## Context

When plan PRs are created via `/erk:plan-save`, the entire plan content is hidden inside a `<details><summary>original-plan</summary>` tag. This means you see nothing about the plan without clicking to expand it. We want a visible AI-generated summary above the collapsed plan so you can understand the plan at a glance.

## Target PR body (Stage 1)

```
This plan adds session preprocessing stats to the `erk land` output,
showing user turns, duration, and JSONL-to-XML compression ratios
alongside each discovered session.

<details>
<summary>original-plan</summary>

[full plan content]