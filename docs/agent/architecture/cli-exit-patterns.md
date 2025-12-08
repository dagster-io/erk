---
title: CLI Exit Patterns
read_when:
  - "writing kit CLI commands"
  - "handling errors in CLI commands"
  - "choosing between JSON and styled output"
  - "understanding exit code conventions"
---

# CLI Exit Patterns

Two distinct error handling patterns exist for CLI commands depending on the consumer.

## erk CLI Pattern (Human Consumer)

**Location**: `src/erk/cli/ensure.py`

- **Output**: Styled text with red "Error:" prefix
- **Exit code**: 1 on error
- **Consumer**: Human users in terminal

```python
from erk.cli.ensure import Ensure

# Type-narrowing methods that exit on error
branch = Ensure.branch(result)      # str | BranchDetectionFailed -> str
pr = Ensure.pr(result)              # PRDetails | NoPRForBranch -> PRDetails
comments = Ensure.comments(result)  # list | GitHubAPIFailed -> list
Ensure.void_op(result)              # None | GitHubAPIFailed -> None
```

## Kit CLI Pattern (Agent Consumer)

**Location**: `packages/dot-agent-kit/src/dot_agent_kit/cli_result.py`

- **Output**: JSON with `success`, `error_type`, `message` fields
- **Exit code**: 0 even on error (supports `|| true` shell patterns)
- **Consumer**: AI agents parsing JSON output

```python
from dot_agent_kit.cli_result import exit_with_error
from dot_agent_kit.non_ideal_state import GitHubChecks, BranchDetectionFailed

result = GitHubChecks.branch(get_current_branch(ctx))
if isinstance(result, BranchDetectionFailed):
    exit_with_error(result.error_type, result.message)
branch = result  # Type narrowed
```

## Decision Guide

| Aspect | erk CLI | Kit CLI |
|--------|---------|---------|
| Consumer | Human | AI Agent |
| Output format | Styled text | JSON |
| Exit code on error | 1 | 0 |
| Error handling | `Ensure.X()` | `isinstance() + exit_with_error()` |
| Package | `src/erk/` | `packages/dot-agent-kit/` |

## Why Kit CLI Exits with Code 0

Kit commands are invoked by agents that parse JSON output. Using exit code 0:
- Allows `|| true` patterns without losing error info
- Error details are in JSON, not exit code
- Prevents shell script failures on expected errors
