---
title: Roadmap Step Inference
read_when:
  - "understanding how roadmap steps are parsed"
  - "working with objective step detection"
  - "debugging step inference issues"
---

# Roadmap Step Inference

This document describes how erk determines the next actionable step from an objective's roadmap table.

## Overview

Rather than using regex-based parsing, erk uses Claude Haiku to analyze objective roadmaps. This LLM-based approach is more flexible and handles edge cases in markdown formatting.

## PR Column Format

Objective roadmaps use a specific format in the PR column:

| Column Value | Meaning                        | Step Status |
| ------------ | ------------------------------ | ----------- |
| (empty)      | Step is pending                | PENDING     |
| `#XXXX`      | Step completed (PR merged)     | DONE        |
| `plan #XXXX` | Plan in progress for this step | IN_PROGRESS |

## Status Column Override

The Status column overrides PR column inference:

| Status Column | Effect                               |
| ------------- | ------------------------------------ |
| `blocked`     | Step is blocked regardless of PR col |
| `skipped`     | Step is skipped regardless of PR col |
| (empty)       | Use PR column to determine status    |

**Critical**: Always check Status column first. Ignoring it causes data loss.

## Inference Rules

The LLM follows these rules to find the next actionable step:

1. Find all steps in the roadmap
2. For each step, determine its status from PR and Status columns
3. Find the FIRST step where:
   - Previous step (if any) is DONE
   - This step is PENDING (not done, blocked, skipped, or in-progress)
4. Return that step, or indicate no step available

## Response Format

The inference returns structured fields:

| Field         | Type   | Description                           |
| ------------- | ------ | ------------------------------------- |
| `NEXT_STEP`   | yes/no | Whether an actionable step was found  |
| `STEP_ID`     | string | Step identifier (e.g., "1.1", "2A.1") |
| `DESCRIPTION` | string | Human-readable step description       |
| `PHASE`       | string | Phase name (e.g., "Phase 1: Setup")   |
| `REASON`      | string | Why this step was chosen              |

## Cost Model

- Uses Haiku model: ~$0.001 per inference
- Designed for automated workflows where many objectives are processed

## Error Handling

The inference can fail due to:

- LLM rate limits or API errors
- Malformed objective body (no roadmap table)
- Network issues

On failure, returns `InferenceError` with descriptive message.

## Implementation Reference

See `infer_next_step()` in `packages/erk-shared/src/erk_shared/objectives/next_step_inference.py`.

## Related Documentation

- [Objectives Index](index.md) - Package overview and key types
- [Glossary: Objectives System](../glossary.md#objectives-system) - Terminology definitions
