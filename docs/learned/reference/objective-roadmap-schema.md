---
title: Objective Roadmap Schema Reference
read_when:
  - "writing or parsing roadmap YAML frontmatter"
  - "validating roadmap step data"
  - "extending the roadmap schema"
tripwires:
  - action: "adding new fields to the roadmap schema without updating validate_roadmap_frontmatter()"
    warning: "New fields must be validated in validate_roadmap_frontmatter() in objective_roadmap_frontmatter.py. Extra fields are preserved but unknown required fields will cause validation failures."
---

# Objective Roadmap Schema Reference

Formal specification for the YAML frontmatter schema used in objective roadmap metadata blocks.

## Schema Version 1

The current and only schema version.

```yaml
---
schema_version: "1"
steps:
  - id: "1.1"
    description: "Implement user authentication"
    status: "done"
    pr: "#123"
  - id: "1.2"
    description: "Add login page"
    status: "in_progress"
    pr: "plan #456"
  - id: "2.1"
    description: "Write integration tests"
    status: "pending"
    pr: null
---
```

## Field Definitions

### Top-Level Fields

| Field            | Type   | Required | Description                  |
| ---------------- | ------ | -------- | ---------------------------- |
| `schema_version` | string | Yes      | Must be `"1"`                |
| `steps`          | list   | Yes      | Ordered list of step objects |

### Step Fields

| Field         | Type           | Required | Description                               |
| ------------- | -------------- | -------- | ----------------------------------------- |
| `id`          | string         | Yes      | Step identifier (e.g., `"1.1"`, `"2A.3"`) |
| `description` | string         | Yes      | Human-readable step description           |
| `status`      | string         | Yes      | Current step status                       |
| `pr`          | string or null | No       | PR or plan reference                      |

## Valid Status Values

| Status        | Meaning               |
| ------------- | --------------------- |
| `pending`     | Not started           |
| `done`        | Completed, PR merged  |
| `in_progress` | Work underway         |
| `blocked`     | Blocked by dependency |
| `skipped`     | Intentionally skipped |

## Valid PR Formats

| Format      | Meaning                                            | Example             |
| ----------- | -------------------------------------------------- | ------------------- |
| `null`      | No PR associated                                   | `pr: null` or `pr:` |
| `#NNN`      | Merged/open PR number                              | `pr: "#123"`        |
| `plan #NNN` | Plan issue number (work planned but not yet in PR) | `pr: "plan #456"`   |

## Step ID Convention

Step IDs encode phase membership via prefix:

- `"1.1"`, `"1.2"` -> Phase 1
- `"2A.1"`, `"2A.2"` -> Phase 2A (sub-phase)
- `"3.1"` -> Phase 3

The part before the last `.` is the phase identifier. The part after is the step number within the phase. Phase identifiers match the regex `^\d+[A-Z]?$`.

## Forward Compatibility

Extra fields in step objects are silently ignored by the parser. This allows adding optional fields in future schema versions without breaking existing parsers. The serializer, however, only writes known fields (`id`, `description`, `status`, `pr`).

## Validation

<!-- Source: src/erk/cli/commands/exec/scripts/objective_roadmap_frontmatter.py, validate_roadmap_frontmatter -->

Validation is performed by `validate_roadmap_frontmatter()` in `objective_roadmap_frontmatter.py`. It returns `(steps, errors)` where:

- If validation succeeds: `steps` is a `list[RoadmapStep]`, `errors` is empty
- If validation fails: `steps` is `None`, `errors` contains descriptive messages

Validation checks:

1. `schema_version` field exists and equals `"1"`
2. `steps` field exists and is a list
3. Each step is a mapping with required fields (`id`, `description`, `status`)
4. All field values have correct types (strings, optional string for `pr`)

## Related Documentation

- [Objective Roadmap Frontmatter](../objectives/objective-roadmap-frontmatter.md) - Architecture and parsing flow
- [Roadmap Format Versioning](../objectives/roadmap-format-versioning.md) - Version migration strategy
- [Metadata Blocks Reference](../architecture/metadata-blocks.md) - Block format and parsing
