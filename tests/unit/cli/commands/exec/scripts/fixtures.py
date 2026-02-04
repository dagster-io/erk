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


# Assistant message with thinking block
JSONL_ASSISTANT_WITH_THINKING = """{
  "type": "assistant",
  "message": {
    "role": "assistant",
    "content": [
      {"type": "thinking", "thinking": "Let me analyze this carefully before responding."},
      {"type": "text", "text": "Here is my response."}
    ],
    "model": "claude-opus-4-5-20251101"
  },
  "parentUuid": "parent_thinking",
  "sessionId": "session_thinking",
  "gitBranch": "test-branch",
  "timestamp": "2025-11-20T00:00:00.000Z"
}"""

# Summary entry
JSONL_SUMMARY_ENTRY = """{
  "type": "summary",
  "summary": "User requested feature implementation. Assistant created plan and began execution.",
  "sessionId": "session_summary",
  "timestamp": "2025-11-20T00:00:00.000Z"
}"""

# System entry with turn_duration subtype
JSONL_SYSTEM_ENTRY = """{
  "type": "system",
  "subtype": "turn_duration",
  "durationMs": 1234,
  "sessionId": "session_system",
  "timestamp": "2025-11-20T00:00:00.000Z"
}"""

# Assistant message with usage metadata
JSONL_ASSISTANT_WITH_USAGE = """{
  "type": "assistant",
  "message": {
    "role": "assistant",
    "content": [{"type": "text", "text": "Response with usage tracking."}],
    "usage": {"input_tokens": 150, "output_tokens": 75},
    "model": "claude-sonnet-4-5"
  },
  "parentUuid": "parent_usage",
  "sessionId": "session_usage",
  "gitBranch": "test-branch",
  "timestamp": "2025-11-20T00:00:00.000Z"
}"""

# Expected XML for thinking block
EXPECTED_XML_THINKING = (
    """  <thinking>Let me analyze this carefully before responding.</thinking>"""
)

# Expected XML for summary entry
EXPECTED_XML_SUMMARY = (
    """  <summary>User requested feature implementation. """
    """Assistant created plan and began execution.</summary>"""
)

# Expected XML for system entry
EXPECTED_XML_SYSTEM = """  <system subtype="turn_duration" duration_ms="1234" />"""

# Expected XML for usage metadata
EXPECTED_XML_USAGE = """  <usage input_tokens="150" output_tokens="75" />"""
