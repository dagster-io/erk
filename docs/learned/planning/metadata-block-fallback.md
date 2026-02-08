---
title: Plan Content Extraction Fallback
read_when:
  - "extracting plan content from GitHub issue comments"
  - "debugging 'no plan content found' errors in replan or plan-implement"
  - "working with older erk-plan issues that lack metadata blocks"
tripwires:
  - action: "assuming plan content is in the issue body"
    warning: "Schema v2 stores plan content in the FIRST COMMENT, not the issue body. The body contains only the plan-header metadata block. See extract_plan_from_comment() for the extraction logic."
  - action: "checking only one location when extracting plan content"
    warning: "Always check both the first comment (plan-body metadata block) and the issue body before reporting 'no plan content found'. The replan command documents this explicitly in Step 4a."
---

# Plan Content Extraction Fallback

Plan issues use a two-location storage design with backward-compatible fallback. Understanding why content lives where it does prevents agents from looking in the wrong place and reporting false "no content" errors.

## Why Two Locations Exist

Schema v2 plan issues split content across two GitHub API objects for a deliberate reason: **fast querying vs. full content**.

| Location      | What it stores                                                | Why                                                                                                                        |
| ------------- | ------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Issue body    | `plan-header` metadata block (YAML)                           | Compact structured data for batch queries — worktree name, dispatch status, timestamps. Never contains plan text.          |
| First comment | `plan-body` metadata block (plan markdown inside `<details>`) | Full plan content. Separating it from the body means listing/filtering issues doesn't require downloading large plan text. |

<!-- Source: erk_shared/gateway/github/plan_issues.py, create_plan_issue -->

The `create_plan_issue()` function in `erk_shared/gateway/github/plan_issues.py` orchestrates this: it creates the issue with a metadata-only body, then explicitly adds the first comment with the plan content. The comment is not auto-created by GitHub — erk creates it via `add_comment()` and records the `plan_comment_id` back into the issue body for direct lookup.

## The Fallback Chain

<!-- Source: erk_shared/gateway/github/metadata/plan_header.py, extract_plan_from_comment -->

`extract_plan_from_comment()` in `plan_header.py` implements a two-format fallback within the first comment:

1. **New format (primary)**: Look for `<!-- erk:metadata-block:plan-body -->` markers, then extract content from the `<details>` block inside
2. **Old format (fallback)**: Look for `<!-- erk:plan-content -->` / `<!-- /erk:plan-content -->` markers

The replan command (`/erk:replan`, Step 4a) adds an additional layer: if no plan content is found in the first comment at all, check the issue body directly. This handles legacy issues that predate the body/comment split entirely.

## Three Eras of Plan Issues

The fallback exists because the plan storage format evolved through three eras:

| Era                       | Storage location    | Markers                                                  | Example             |
| ------------------------- | ------------------- | -------------------------------------------------------- | ------------------- |
| **Pre-metadata**          | Issue body directly | None (raw markdown)                                      | Earliest issues     |
| **v1 metadata**           | First comment       | `<!-- erk:plan-content -->`                              | Transitional format |
| **v2 metadata** (current) | First comment       | `<!-- erk:metadata-block:plan-body -->` with `<details>` | All new issues      |

Each extraction layer handles one transition, and together they cover the full history.

## Anti-Patterns

**Only checking one location and failing immediately** — The most common agent mistake. An agent fetches the issue body, sees YAML metadata instead of plan content, and reports "no plan found." The plan is in the first comment, not the body.

**Assuming `plan_comment_id` is always set** — Older issues may not have this field in the plan-header. When it's missing, fall back to fetching the first comment via the GitHub API (e.g., `gh issue view --comments`).

**Ignoring the `<details>` wrapper** — The plan-body block wraps content in a `<details open>` tag for GitHub rendering. Extracting the raw block body without stripping the `<details>` wrapper will include HTML tags in the plan text.

## Related Documentation

- `/erk:replan` command — Step 4a documents the full fallback chain agents should follow
