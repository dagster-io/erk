---
title: Objective View JSON Schema
read_when:
  - "using erk objective view --json-output"
  - "consuming structured objective data programmatically"
  - "understanding the graph output format"
---

# Objective View JSON Schema

Complete schema for the `erk objective view --json-output` command.

## Output Format

<!-- Source: src/erk/cli/commands/objective/view_cmd.py:125-156 -->

```json
{
  "issue_number": 6423,
  "phases": [
    {
      "number": 1,
      "suffix": "",
      "name": "Foundation",
      "nodes": [
        {
          "id": "1.1",
          "description": "Add user model",
          "status": "done",
          "plan": "#6464",
          "pr": "#6500"
        }
      ]
    }
  ],
  "graph": {
    "nodes": [
      {
        "id": "1.1",
        "description": "Add user model",
        "status": "done",
        "plan": "#6464",
        "pr": "#6500",
        "depends_on": []
      }
    ],
    "unblocked": ["2.1"],
    "next_node": "2.1",
    "is_complete": false
  },
  "summary": {
    "total_nodes": 5,
    "pending": 2,
    "planning": 0,
    "done": 2,
    "in_progress": 1,
    "blocked": 0,
    "skipped": 0
  }
}
```

## Top-Level Fields

| Field          | Type   | Description                     |
| -------------- | ------ | ------------------------------- |
| `issue_number` | int    | GitHub issue number             |
| `phases`       | array  | Roadmap phases with nodes       |
| `graph`        | object | Dependency graph representation |
| `summary`      | object | Status counts from graph nodes  |

## Graph Fields

| Field         | Type           | Description                                   |
| ------------- | -------------- | --------------------------------------------- |
| `nodes`       | array          | All nodes with `depends_on` edges             |
| `unblocked`   | array[string]  | Node IDs whose dependencies are all satisfied |
| `next_node`   | string \| null | First unblocked pending node, or null if none |
| `is_complete` | bool           | Whether all nodes are in terminal state       |

## Summary Fields

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py:134-148 -->

| Field         | Type | Description                     |
| ------------- | ---- | ------------------------------- |
| `total_nodes` | int  | Total number of roadmap nodes   |
| `pending`     | int  | Nodes with status `pending`     |
| `planning`    | int  | Nodes with status `planning`    |
| `done`        | int  | Nodes with status `done`        |
| `in_progress` | int  | Nodes with status `in_progress` |
| `blocked`     | int  | Nodes with status `blocked`     |
| `skipped`     | int  | Nodes with status `skipped`     |

## Related Documentation

- [Objective Commands](../cli/objective-commands.md) — CLI command reference
- [Dependency Graph Architecture](dependency-graph.md) — Graph types and traversal
- [Roadmap Status System](roadmap-status-system.md) — Status resolution rules
