---
description: Where different types of validation belong in the codebase
read_when:
  - adding format validation
  - deciding where to enforce constraints
  - validation logic placement
last_audited: "2026-02-16 00:00 PT"
audit_result: new
---

# Validation Layer Placement

## Principle

Validation belongs at the **data layer** (operations modules), not at command or presentation layers.

## Why

Data layer validation ensures all code paths enforce constraints, regardless of entry point (CLI, API, programmatic).

## Example

<!-- Source: src/erk/agent_docs/operations.py, validate_agent_doc_frontmatter -->

See `LAST_AUDITED_PATTERN` validation in `validate_agent_doc_frontmatter()` in `src/erk/agent_docs/operations.py` - validates format in the data layer, not in CLI commands.

## Layer Responsibilities

- **Data layer** (operations.py): Format validation, constraint enforcement
- **Command layer** (CLI): User input parsing, error display
- **Presentation layer** (TUI): Display formatting, user interaction

## Anti-Pattern

Validating in CLI command and forgetting the constraint when data is modified programmatically.
