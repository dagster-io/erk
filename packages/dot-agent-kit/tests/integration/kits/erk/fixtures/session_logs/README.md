# Session Log Test Fixtures

Realistic JSONL session log fixtures for integration testing.

## Directory Structure

```
session_logs/
├── project_alpha/           # Project with single session, single slug
│   └── session-aaa.jsonl
├── project_beta/            # Project with multiple sessions
│   ├── session-bbb.jsonl    # Has slug "beta-plan-one"
│   └── session-ccc.jsonl    # Has slug "beta-plan-two"
├── project_gamma/           # Project with session containing multiple slugs
│   └── session-ddd.jsonl    # Has "gamma-first" then "gamma-second"
├── project_delta/           # Project with no slugs (no plan mode used)
│   └── session-eee.jsonl
└── project_epsilon/         # Project with agent files (should be skipped)
    ├── session-fff.jsonl
    └── agent-12345678.jsonl # Should be ignored
```

## JSONL Format

Each line is a JSON object with these key fields:

- `sessionId`: UUID identifying the session
- `type`: Entry type (user, assistant, tool_result, file-history-snapshot)
- `slug`: (Optional) Plan mode identifier, maps to ~/.claude/plans/{slug}.md

## Usage

These fixtures are used by `test_session_plan_extractor_integration.py` to test:

- Finding project directories by session ID
- Extracting slugs from session logs
- Handling multiple sessions/projects
- Skipping agent files
