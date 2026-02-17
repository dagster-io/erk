---
title: Cornerstone Enforcement in Learn Pipeline
last_audited: "2026-02-17 00:00 PT"
audit_result: clean
read_when:
  - "understanding SHOULD_BE_CODE filtering"
  - "working on learn pipeline classification"
  - "documentation items being classified as code"
  - "understanding cornerstone test rules"
tripwires:
  - action: "classifying a single-artifact API reference as NEW_DOC"
    warning: "Apply the three-rule SHOULD_BE_CODE test first. Single-artifact knowledge belongs in code (types, docstrings, or comments), not docs/learned/."
---

# Cornerstone Enforcement in Learn Pipeline

The learn pipeline filters documentation proposals through a cornerstone test to prevent single-artifact knowledge from polluting `docs/learned/`. Items that fail the test are classified as `SHOULD_BE_CODE` and redirected to code changes instead of documentation.

## Problem

The learn pipeline generates documentation proposals from session analysis. Without filtering, many proposals describe knowledge that attaches to a single code artifact: one function's behavior, one class's API, one enum's values. These belong as docstrings, type annotations, or code comments — not cross-cutting documentation.

Before cornerstone enforcement, the pipeline was only checking one of four levels in the knowledge placement hierarchy. This led to documentation sprawl with single-artifact API references filling `docs/learned/`.

## The Three-Rule SHOULD_BE_CODE Test

Implemented in `.claude/agents/learn/documentation-gap-identifier.md`:

| Rule | Knowledge Type                                                                         | Code Placement                        |
| ---- | -------------------------------------------------------------------------------------- | ------------------------------------- |
| 1    | **Enumerable catalog** (error types, status values, config keys, option sets)          | Literal type, Enum, or typed constant |
| 2    | **Single-artifact API reference** (method tables, signatures for one class/ABC/module) | Docstrings on that artifact           |
| 3    | **Single-location insight** (behavior of one function or code block)                   | Code comment at that location         |

**Decision boundary:** "Does this knowledge attach to a single code artifact?" If yes, classify as `SHOULD_BE_CODE`.

If the insight spans multiple files or connects systems, it belongs in `docs/learned/`.

## CODE_CHANGE Action Type

Items classified as `SHOULD_BE_CODE` in the gap analysis are mapped to `CODE_CHANGE` action type in the plan synthesizer (`.claude/agents/learn/plan-synthesizer.md`).

A `CODE_CHANGE` item specifies:

- What code change is needed (type artifact, docstring, or comment)
- Where in the source code it belongs
- No markdown documentation content is generated

This ensures the learn pipeline output directs agents to modify code rather than create unnecessary documentation.

## Classification Categories

The full classification set in the gap identifier:

| Classification    | When to Use                                               |
| ----------------- | --------------------------------------------------------- |
| NEW_DOC           | New cross-cutting topic not covered by existing docs      |
| UPDATE_EXISTING   | Existing doc covers related topic, needs update           |
| UPDATE_REFERENCES | Existing doc valid but has phantom file paths             |
| DELETE_STALE      | Existing doc describes artifacts that no longer exist     |
| TRIPWIRE          | Cross-cutting concern that applies broadly                |
| SHOULD_BE_CODE    | Knowledge belonging in code (types, docstrings, comments) |
| SKIP              | Already documented or doesn't need documentation          |

## Output Statistics

The gap identifier includes a "Cornerstone redirects (SHOULD_BE_CODE)" count in its output statistics, making it visible how many items were filtered by the cornerstone test.

## Related Documentation

- [Learn Workflow](learn-workflow.md) - Complete learn pipeline workflow
- [Conventions](../conventions.md) - Naming and coding conventions
