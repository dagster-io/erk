---
title: Error Detection Patterns for Subprocess Failures
last_audited: "2026-02-13 00:00 PT"
audit_result: clean
read_when:
  - "classifying errors from subprocess stderr output"
  - "detecting specific failure modes from external tool output"
  - "adding new SubmitError error_type based on error text"
---

# Error Detection Patterns for Subprocess Failures

## The Problem: Unstructured Error Output

External tools (Graphite, git, gh) communicate failures through exit codes and stderr text, not structured error types. When erk needs to distinguish between failure modes -- for example, "restack required" vs "generic submit failure" -- it must parse the error text.

## Keyword Detection Pattern

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, _graphite_first_flow -->

The keyword detection pattern extracts error text from an exception and checks for known substrings using case-insensitive matching. See `_graphite_first_flow()` in `src/erk/cli/commands/pr/submit_pipeline.py` for the reference implementation.

**When to use:** The external tool doesn't provide structured error codes, and a specific keyword reliably indicates a distinct failure mode.

**Trade-offs:**

- String matching is brittle if the tool changes its error messages
- Acceptable when the keyword is stable and appears in the tool's own documentation or UI
- Case-insensitive matching (`.lower()`) adds robustness

**Decision criteria for adding a new keyword detection:**

1. The keyword appears reliably in the tool's error output for this specific failure mode
2. The failure mode requires different user remediation than the generic case
3. No structured alternative exists (exit codes, JSON output, etc.)

## Existing Keyword Detections

| Keyword                             | Tool                   | Error Type                  | Source          |
| ----------------------------------- | ---------------------- | --------------------------- | --------------- |
| `"restack"`                         | Graphite (`gt submit`) | `graphite_restack_required` | PR #6885        |
| `"non-fast-forward"` / `"rejected"` | git push               | `branch_diverged`           | Submit pipeline |

## Anti-Pattern: Over-Parsing

Don't parse error text when a structured alternative exists. For example, git commands can return specific exit codes, and `gh` supports `--json` output. Keyword detection is the last resort, not the first choice.

## Related Patterns

- [CLI Error Handling Anti-Patterns](error-handling-antipatterns.md) - When to use UserFacingCliError vs RuntimeError
- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md) - Structured error types
- [PR Submit Pipeline](pr-submit-pipeline.md) - Full pipeline architecture
