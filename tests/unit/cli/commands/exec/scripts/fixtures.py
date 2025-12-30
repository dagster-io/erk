"""Test fixtures for session log preprocessing tests.

Contains real JSONL entry samples extracted from actual Claude Code session logs.
"""

# File history snapshot entry (should be filtered out)
JSONL_FILE_HISTORY_SNAPSHOT = """{
  "type": "file-history-snapshot",
  "messageId": "msg_123",
  "parentUuid": "parent_456",
  "sessionId": "session_789",
  "snapshot": {"trackedFileBackups": {}, "timestamp": "2025-11-20T00:00:00Z"},
  "isSnapshotUpdate": false,
  "timestamp": "2025-11-20T00:00:00.000Z",
  "gitBranch": "test-branch",
  "cwd": "/test/dir",
  "userType": "user",
  "isSidechain": false
}"""

# User message with string content
JSONL_USER_MESSAGE_STRING = """{
  "type": "user",
  "message": {"role": "user", "content": "Hello, how are you?"},
  "parentUuid": "parent_123",
  "sessionId": "session_456",
  "gitBranch": "test-branch",
  "cwd": "/test/dir",
  "timestamp": "2025-11-20T00:00:00.000Z",
  "userType": "user",
  "isSidechain": false
}"""

# User message with structured content
JSONL_USER_MESSAGE_STRUCTURED = """{
  "type": "user",
  "message": {
    "role": "user",
    "content": [{"type": "text", "text": "Let me test <special> & chars"}]
  },
  "parentUuid": "parent_789",
  "sessionId": "session_abc",
  "gitBranch": "test-branch",
  "cwd": "/test/dir",
  "timestamp": "2025-11-20T00:00:00.000Z"
}"""

# Assistant message with text only
JSONL_ASSISTANT_TEXT = """{
  "type": "assistant",
  "message": {
    "role": "assistant",
    "content": [{"type": "text", "text": "I'll help you with that."}],
    "usage": {"input_tokens": 100, "output_tokens": 50}
  },
  "parentUuid": "parent_def",
  "sessionId": "session_ghi",
  "gitBranch": "test-branch",
  "cwd": "/test/dir",
  "timestamp": "2025-11-20T00:00:00.000Z"
}"""

# Assistant message with tool use
JSONL_ASSISTANT_TOOL_USE = """{
  "type": "assistant",
  "message": {
    "role": "assistant",
    "content": [
      {
        "type": "tool_use",
        "id": "toolu_abc123",
        "name": "Read",
        "input": {"file_path": "/test/file.py"}
      }
    ],
    "usage": {"input_tokens": 200, "output_tokens": 30}
  },
  "parentUuid": "parent_jkl",
  "sessionId": "session_mno",
  "gitBranch": "test-branch",
  "timestamp": "2025-11-20T00:00:00.000Z"
}"""

# Duplicate assistant message (for deduplication testing)
JSONL_DUPLICATE_ASSISTANT_TEXT = """{
  "type": "assistant",
  "message": {
    "role": "assistant",
    "content": [{"type": "text", "text": "I'll help you with that."}]
  },
  "sessionId": "session_pqr"
}"""

# Duplicate assistant message with tool_use (should keep tool_use, drop text)
JSONL_DUPLICATE_ASSISTANT_WITH_TOOL = """{
  "type": "assistant",
  "message": {
    "role": "assistant",
    "content": [
      {"type": "text", "text": "I'll help you with that."},
      {
        "type": "tool_use",
        "id": "toolu_xyz789",
        "name": "Edit",
        "input": {"file_path": "/test/edit.py"}
      }
    ]
  },
  "sessionId": "session_stu"
}"""

# Tool result
JSONL_TOOL_RESULT = """{
  "type": "tool_result",
  "message": {
    "role": "user",
    "content": [
      {
        "type": "tool_result",
        "tool_use_id": "toolu_abc123",
        "content": "File contents:\\n     1→def hello():\\n     2→    print('Hello')"
      }
    ],
    "tool_use_id": "toolu_abc123"
  },
  "sessionId": "session_vwx"
}"""

# Expected XML outputs
EXPECTED_XML_USER_STRING = """  <user>Hello, how are you?</user>"""

EXPECTED_XML_USER_STRUCTURED = """  <user>Let me test &lt;special&gt; &amp; chars</user>"""

EXPECTED_XML_ASSISTANT_TEXT = """  <assistant>I'll help you with that.</assistant>"""

EXPECTED_XML_TOOL_USE = """  <tool_use name="Read" id="toolu_abc123">
    <param name="file_path">/test/file.py</param>
  </tool_use>"""

EXPECTED_XML_TOOL_RESULT = """  <tool_result tool="toolu_abc123">
File contents:
     1→def hello():
     2→    print('Hello')
  </tool_result>"""


# Slug-based fixtures for plan extraction testing

# Session entry with a slug field (indicates plan mode was entered)
JSONL_SESSION_WITH_SLUG = """{
  "type": "assistant",
  "slug": "joyful-munching-hammock",
  "message": {"role": "assistant", "content": [{"type": "text", "text": "I'll help you."}]},
  "parentUuid": "parent_123",
  "sessionId": "session_456",
  "gitBranch": "test-branch",
  "cwd": "/test/dir",
  "timestamp": "2025-11-23T10:00:00.000Z"
}"""

# Session entry without slug field (no plan mode)
JSONL_SESSION_WITHOUT_SLUG = """{
  "type": "assistant",
  "message": {"role": "assistant", "content": [{"type": "text", "text": "I'll help you."}]},
  "parentUuid": "parent_789",
  "sessionId": "session_abc",
  "gitBranch": "test-branch",
  "cwd": "/test/dir",
  "timestamp": "2025-11-23T11:00:00.000Z"
}"""

# Sample plan content for testing
SAMPLE_PLAN_CONTENT = """# Test Feature

## Problem Statement

This is a test plan for unit testing.

## Implementation Steps

1. Step one
2. Step two
3. Step three

## Files to Modify

- `src/module.py`
- `tests/test_module.py`
"""


def create_session_file(path, entries: list[str]) -> None:
    """Write JSONL entries to a session file.

    JSONL format requires each JSON object on a single line with no internal newlines.
    This function parses each entry and writes it as compact single-line JSON.

    Args:
        path: Path object or string path to write to
        entries: List of JSONL entry strings to write (can be pretty-printed)
    """
    import json
    from pathlib import Path

    file_path = Path(path)
    with open(file_path, "w", encoding="utf-8") as f:
        for entry in entries:
            # Parse JSON and write back as compact single-line
            data = json.loads(entry)
            f.write(json.dumps(data) + "\n")


def create_session_entry(session_id: str, slug: str | None = None) -> str:
    """Create a minimal JSONL session entry for testing.

    Args:
        session_id: The session ID for the entry
        slug: Optional slug field (indicates plan mode)

    Returns:
        JSON string for the entry
    """
    import json

    entry = {
        "type": "assistant",
        "message": {"role": "assistant", "content": [{"type": "text", "text": "Test"}]},
        "sessionId": session_id,
        "timestamp": "2025-11-23T10:00:00.000Z",
    }
    if slug:
        entry["slug"] = slug
    return json.dumps(entry)
