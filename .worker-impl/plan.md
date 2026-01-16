# Plan: Phase 1 - Session Source Abstraction

**Part of Objective #4991, Steps 1.1-1.4**

Refactor the learn workflow to support multiple session sources through a unified abstraction, preparing for remote artifact support in Phase 2.

## Goal

After this phase:
1. Plan-header has fields to track remote implementation (`remote_impl_run_id`, `remote_impl_session_id`)
2. `SessionSource` ABC exists with `LocalSessionSource` implementation
3. `get-learn-sessions` returns session source metadata alongside existing fields
4. Learn skill continues working identically (backwards compatible)

## Implementation

### Step 1.1: Add Plan Header Fields

**Files to modify:**
- `packages/erk-shared/src/erk_shared/github/metadata/schemas.py`
- `packages/erk-shared/src/erk_shared/github/metadata/plan_header.py`
- `packages/erk-shared/tests/unit/github/test_metadata_schemas.py`
- `packages/erk-shared/tests/unit/github/test_plan_header.py`

**Changes:**

1. Add constants to `schemas.py`:
   ```python
   LAST_REMOTE_IMPL_RUN_ID: Literal["last_remote_impl_run_id"] = "last_remote_impl_run_id"
   LAST_REMOTE_IMPL_SESSION_ID: Literal["last_remote_impl_session_id"] = "last_remote_impl_session_id"
   ```

2. Update `PlanHeaderFieldName` Literal union with new fields

3. Add to `PlanHeaderSchema.optional_fields` and validation

4. Update `create_plan_header_block()` and `format_plan_header_body()` signatures

5. Add extraction functions:
   - `extract_plan_header_remote_impl_run_id(issue_body) -> str | None`
   - `extract_plan_header_remote_impl_session_id(issue_body) -> str | None`

6. Add update function:
   - `update_plan_header_remote_impl_event(issue_body, run_id, session_id, remote_impl_at) -> str`

### Step 1.2: Create SessionSource Abstraction

**New files:**
```
packages/erk-shared/src/erk_shared/sessions/source/
├── __init__.py       # Re-exports
├── abc.py            # SessionSource ABC, SessionSourceInfo, SessionSourceError
├── local.py          # LocalSessionSource implementation
└── fake.py           # FakeSessionSource for testing
```

**abc.py design:**
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class SessionSourceInfo:
    """Serializable metadata about a session source."""
    session_id: str
    source_type: Literal["local", "remote_artifact"]
    location: str  # path for local, artifact reference for remote

@dataclass(frozen=True)
class SessionSourceError(Exception):
    """Error retrieving session content."""
    session_id: str
    source_type: str
    message: str

class SessionSource(ABC):
    """Abstract source of session content (lazy evaluation)."""

    @property
    @abstractmethod
    def session_id(self) -> str: ...

    @property
    @abstractmethod
    def source_type(self) -> Literal["local", "remote_artifact"]: ...

    @abstractmethod
    def get_content(self) -> str:
        """Fetch and return raw JSONL content."""
        ...

    @abstractmethod
    def get_info(self) -> SessionSourceInfo:
        """Return lightweight metadata (no content fetch)."""
        ...
```

**local.py:**
```python
@dataclass(frozen=True)
class LocalSessionSource(SessionSource):
    _session_id: str
    _path: Path

    # Implementation reads file on get_content(), raises SessionSourceError if missing
```

**fake.py:**
```python
@dataclass(frozen=True)
class FakeSessionSource(SessionSource):
    _session_id: str
    _source_type: Literal["local", "remote_artifact"]
    _content: str
    _location: str
```

**Tests:**
- `packages/erk-shared/tests/unit/sessions/source/test_local.py`
- `packages/erk-shared/tests/unit/sessions/source/test_fake.py`

### Step 1.3: Update get-learn-sessions Output

**Files to modify:**
- `src/erk/cli/commands/exec/scripts/get_learn_sessions.py`
- `tests/unit/cli/commands/exec/scripts/test_get_learn_sessions.py`

**Changes to output JSON (backwards compatible):**
```json
{
  "success": true,
  "issue_number": 123,
  // Existing fields remain unchanged
  "session_paths": [...],
  "readable_session_ids": [...],
  // NEW fields
  "session_sources": [
    {
      "session_id": "abc-123",
      "source_type": "local",
      "location": "/path/to/session.jsonl"
    }
  ],
  "remote_impl_run_id": null,
  "remote_impl_session_id": null
}
```

**Implementation:**
1. Add `session_sources` field to `GetLearnSessionsResult`
2. Add `remote_impl_run_id` and `remote_impl_session_id` fields
3. Build `LocalSessionSource` objects in `_discover_sessions()`
4. Serialize via `SessionSourceInfo` dataclass

### Step 1.4: Update Learn Skill Documentation

**File to modify:**
- `.claude/commands/erk/learn.md`

**Minimal changes for Phase 1:**
1. Document new `session_sources` field in Step 1
2. Note `remote_impl_run_id`/`remote_impl_session_id` for Phase 2
3. Continue using `session_paths` directly (existing behavior)

## Verification

1. **Unit tests pass:** Run `make fast-ci` for all new and modified code
2. **Backwards compatibility:** Existing learn workflow works identically
3. **Schema validation:** Plan header with new fields validates correctly
4. **Manual test:** Run `erk exec get-learn-sessions <issue>` and verify:
   - Existing fields (`session_paths`, `readable_session_ids`) unchanged
   - New `session_sources` array present with correct structure
   - New `remote_impl_run_id`/`remote_impl_session_id` fields present (null for now)

## Skills to Load

- `dignified-python` - for LBYL, frozen dataclasses, modern types
- `fake-driven-testing` - for test placement and fake patterns

## Related Files

- `packages/erk-shared/src/erk_shared/sessions/discovery.py` - existing session discovery
- `packages/erk-shared/src/erk_shared/learn/extraction/claude_installation/abc.py` - ABC pattern reference
- `packages/erk-shared/tests/unit/github/test_plan_header.py` - test pattern reference