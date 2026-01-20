---
title: Session Source Abstraction
read_when:
  - "working with learn workflow session handling"
  - "understanding local vs remote session origins"
  - "implementing session source processing"
  - "extending learn to handle remote artifacts"
---

# Session Source Abstraction

An abstraction for handling sessions from different origins (local vs remote artifacts) in the learn workflow.

## Key Insight

Session **files** are always local during processing (remote sessions get downloaded first). The abstraction tracks **where sessions came from**, not where they currently reside. This enables proper attribution and filtering in the learn workflow.

## Architecture

```
SessionSource (ABC)
├── LocalSessionSource   - Sessions from ~/.claude/projects/
└── RemoteSessionSource  - Sessions downloaded from GitHub Actions artifacts
```

### SessionSource ABC

All implementations provide:

| Property      | Type          | Description                                  |
| ------------- | ------------- | -------------------------------------------- |
| `source_type` | `str`         | Identifier: `"local"` or `"remote"`          |
| `session_id`  | `str`         | Claude Code session ID                       |
| `run_id`      | `str \| None` | GitHub Actions run ID (remote sessions only) |

### LocalSessionSource

Sessions found in `~/.claude/projects/` on the machine where learn is running:

- `source_type` returns `"local"`
- `run_id` returns `None`

### RemoteSessionSource

Sessions downloaded from GitHub Actions workflow artifacts:

- `source_type` returns `"remote"`
- `run_id` returns the GitHub Actions run ID

This is currently a forward-looking stub - actual artifact download functionality will be implemented in a future phase.

## Usage

Both implementations can be used polymorphically:

```python
from erk_shared.learn.extraction.session_source import (
    SessionSource,
    LocalSessionSource,
    RemoteSessionSource,
)

# Collect mixed sources
sources: list[SessionSource] = [
    LocalSessionSource(_session_id="local-123"),
    RemoteSessionSource(_session_id="remote-456", _run_id="run-789"),
]

# Process uniformly
for source in sources:
    print(f"Processing {source.source_type} session: {source.session_id}")
    if source.run_id:
        print(f"  From run: {source.run_id}")
```

## Related Fields

Plan issues track session sources via plan-header fields:

| Field                         | Description                                  |
| ----------------------------- | -------------------------------------------- |
| `last_local_impl_session`     | Session ID from local implementation         |
| `last_remote_impl_session_id` | Session ID from remote (GitHub Actions) impl |
| `last_remote_impl_run_id`     | Run ID for fetching remote session artifacts |

See [Plan Schema Reference](../planning/plan-schema.md) for complete field documentation.

## Implementation Reference

- **Source file:** `packages/erk-shared/src/erk_shared/learn/extraction/session_source.py`
- **Tests:** `packages/erk-shared/tests/unit/learn/extraction/test_session_source.py`
