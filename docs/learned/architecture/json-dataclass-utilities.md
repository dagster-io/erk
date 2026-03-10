---
title: JSON-Dataclass Utilities
read_when:
  - "serializing dataclasses to JSON"
  - "parsing JSON into dataclasses"
  - "working with agentclick JSON utilities"
tripwires: []
---

# JSON-Dataclass Utilities

## Overview

Shared utilities for converting between JSON and frozen dataclasses, consolidated in the `erk_shared.agentclick` package.

## Location

`packages/erk-shared/src/erk_shared/agentclick/dataclass_json.py`

## Key Utilities

- `python_type_to_json_schema()` — Maps Python type annotations to JSON Schema (handles Literal, tuple, list, dict, Union, primitives)
- Schema generation for frozen dataclasses
- Error schema constant for consistent error response format

## Related Modules

- `erk_shared.agentclick.json_command` — `@json_command` decorator for JSON-output Click commands
- `erk_shared.agentclick.machine_command` — `@machine_command` decorator for machine-readable output
- `erk_shared.agentclick.json_schema` — JSON Schema generation from dataclass types
- `erk_shared.agentclick.machine_schema` — Machine schema generation

## Usage Pattern

Import from `erk_shared.agentclick`, not from individual packages:

```python
from erk_shared.agentclick.dataclass_json import python_type_to_json_schema
```

## Rationale

Consolidation eliminated duplicate JSON/dataclass conversion logic that existed across multiple packages. The `@json_command` and `@machine_command` decorators both share the same underlying dataclass-to-JSON mapping.
