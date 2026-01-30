---
title: Roadmap Parser API Reference
read_when:
  - "calling parse_roadmap(), compute_summary(), serialize_phases(), or find_next_step()"
  - "working with RoadmapStep or RoadmapPhase dataclasses"
  - "building new features on top of the roadmap parser"
tripwires:
  - action: "creating a new roadmap data type without using frozen dataclass"
    warning: "RoadmapStep and RoadmapPhase are frozen dataclasses. New roadmap types must follow this pattern."
---

# Roadmap Parser API Reference

Code-level API reference for `objective_roadmap_shared.py` — the shared parser used by both `objective-roadmap-check` and `objective-roadmap-update`.

## Data Types

### RoadmapStep

```python
@dataclass(frozen=True)
class RoadmapStep:
    step_id: str          # e.g., "1.1", "2.3"
    description: str      # Step description text
    status: str           # "pending", "done", "in_progress", "blocked", "skipped"
    pr: str | None        # PR reference (e.g., "#123", "plan #456") or None
```

### RoadmapPhase

```python
@dataclass(frozen=True)
class RoadmapPhase:
    number: int           # Phase number (1, 2, 3, ...)
    name: str             # Phase name from header
    steps: list[RoadmapStep]
```

## Functions

### parse_roadmap

```python
def parse_roadmap(body: str) -> tuple[list[RoadmapPhase], list[str]]
```

Parses an objective issue body into structured phases and steps.

- **Input**: Raw markdown body of an objective issue
- **Returns**: `(phases, warnings)` — list of phases and list of validation warning strings
- **Parsing**: Regex-based, not LLM-based
  - Phase headers: `### Phase N: Name` pattern
  - Table rows: `| step_id | description | status | pr |` pattern
  - Status inference from status + PR columns (see [Roadmap Parser](roadmap-parser.md))

### compute_summary

```python
def compute_summary(phases: list[RoadmapPhase]) -> dict[str, int]
```

Counts steps by status across all phases.

- **Returns**: `{"total_steps": N, "pending": N, "done": N, "in_progress": N, "blocked": N, "skipped": N}`

### serialize_phases

```python
def serialize_phases(phases: list[RoadmapPhase]) -> list[dict[str, object]]
```

Converts phases to JSON-serializable dicts for CLI output.

### find_next_step

```python
def find_next_step(phases: list[RoadmapPhase]) -> dict[str, str] | None
```

Finds the first step with `"pending"` status, traversing phases in order.

- **Returns**: `{"id": "1.2", "description": "...", "phase": "Phase Name"}` or `None` if no pending steps

## Source Location

`src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py` (205 lines)

## Related Documentation

- [Roadmap Parser](roadmap-parser.md) — Usage guide and CLI syntax
- [Roadmap Mutation Semantics](../architecture/roadmap-mutation-semantics.md) — How updates interact with inference
