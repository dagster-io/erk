# Documentation Extraction: NonIdealState and Error Handling Patterns

## Objective

Document the NonIdealState pattern and associated error handling architecture introduced for handling operations that can fail gracefully without throwing exceptions.

## Source Information

- **Session IDs analyzed**: e3979d54-4167-452b-80a7-a7054b18bd0b
- **Branch**: 2720-extend-pr-address-to-inclu-12-08-0722

---

## Documentation Items

### 1. NonIdealState Pattern (Category B - Teaching Gap)

**Location**: `docs/agent/architecture/non-ideal-state.md`
**Action**: Create new document
**Priority**: High

**Content**:

```markdown
---
title: NonIdealState Pattern
read_when:
  - "handling operations that can fail gracefully"
  - "returning errors without throwing exceptions"
  - "type narrowing for error handling"
  - "working with GitHubChecks class"
---

# NonIdealState Pattern

Pattern for handling operations that can fail gracefully by returning `T | NonIdealState` instead of throwing exceptions.

## Overview

The NonIdealState pattern separates **error detection** from **error handling**:

- Operations return `T | NonIdealState` (never throw)
- Callers inspect results and decide how to handle errors
- Type narrowing works naturally with `isinstance()` checks

## Core Types

**Location**: `packages/erk-shared/src/erk_shared/non_ideal_state.py`

\`\`\`python
from typing import Protocol, runtime_checkable

@runtime_checkable
class NonIdealState(Protocol):
    """Marker interface for non-ideal states."""
    @property
    def error_type(self) -> str: ...
    
    @property
    def message(self) -> str: ...
\`\`\`

**Concrete implementations**:
- `BranchDetectionFailed` - Branch could not be detected
- `NoPRForBranch` - No PR exists for the specified branch
- `PRNotFoundError` - PR with specified number does not exist
- `GitHubAPIFailed` - GitHub API call failed

## Usage Pattern

\`\`\`python
from erk_shared.non_ideal_state import NonIdealState, BranchDetectionFailed

# Function returns T | NonIdealState
result = GitHubChecks.branch(get_current_branch())

# Check and handle error
if isinstance(result, BranchDetectionFailed):
    # Handle error case
    ...
branch = result  # Type narrowed to str
\`\`\`

## Integration with Ensure Class

For erk CLI commands, use `Ensure` methods for type narrowing with styled error output:

\`\`\`python
from erk.cli.ensure import Ensure
from erk_shared.non_ideal_state import GitHubChecks

# Exits with styled error + code 1 if NonIdealState
branch = Ensure.branch(GitHubChecks.branch(raw_branch))
pr = Ensure.pr(GitHubChecks.pr_for_branch(github, repo_root, branch))
\`\`\`

## When to Use

- Operations that can fail due to external state (GitHub API, git state)
- When callers need flexibility in how to handle errors
- When you want type narrowing to work naturally

## When NOT to Use

- Programming errors (use exceptions)
- Validation that should fail fast (use `Ensure.invariant()`)
- Simple boolean checks
```

---

### 2. Kit CLI vs erk CLI Exit Patterns (Category B - Teaching Gap)

**Location**: `docs/agent/architecture/cli-exit-patterns.md`
**Action**: Create new document
**Priority**: High

**Content**:

```markdown
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

\`\`\`python
from erk.cli.ensure import Ensure

# Type-narrowing methods that exit on error
branch = Ensure.branch(result)      # str | BranchDetectionFailed -> str
pr = Ensure.pr(result)              # PRDetails | NoPRForBranch -> PRDetails
comments = Ensure.comments(result)  # list | GitHubAPIFailed -> list
Ensure.void_op(result)              # None | GitHubAPIFailed -> None
\`\`\`

## Kit CLI Pattern (Agent Consumer)

**Location**: `packages/dot-agent-kit/src/dot_agent_kit/cli_result.py`

- **Output**: JSON with `success`, `error_type`, `message` fields
- **Exit code**: 0 even on error (supports `|| true` shell patterns)
- **Consumer**: AI agents parsing JSON output

\`\`\`python
from dot_agent_kit.cli_result import exit_with_error
from dot_agent_kit.non_ideal_state import GitHubChecks, BranchDetectionFailed

result = GitHubChecks.branch(get_current_branch(ctx))
if isinstance(result, BranchDetectionFailed):
    exit_with_error(result.error_type, result.message)
branch = result  # Type narrowed
\`\`\`

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
```

---

### 3. GitHubChecks Class (Category B - Teaching Gap)

**Location**: `docs/agent/architecture/github-checks-pattern.md`
**Action**: Create new document  
**Priority**: Medium

**Content**:

```markdown
---
title: GitHubChecks Pattern
read_when:
  - "calling GitHub API in kit commands"
  - "handling GitHub operation failures"
  - "using NonIdealState with GitHub operations"
---

# GitHubChecks Pattern

Static class that wraps GitHub operations to return `T | NonIdealState` instead of throwing.

## Location

`packages/dot-agent-kit/src/dot_agent_kit/non_ideal_state.py`

## Available Methods

\`\`\`python
class GitHubChecks:
    @staticmethod
    def branch(branch: str | None) -> str | BranchDetectionFailed:
        """Check if branch was detected."""
    
    @staticmethod
    def pr_for_branch(github, repo_root, branch) -> PRDetails | NoPRForBranch:
        """Look up PR for branch."""
    
    @staticmethod
    def pr_by_number(github, repo_root, pr_number) -> PRDetails | PRNotFoundError:
        """Look up PR by number."""
    
    @staticmethod
    def add_reaction(github_issues, repo_root, comment_id, reaction) -> None | GitHubAPIFailed:
        """Add reaction to a comment."""
    
    @staticmethod
    def issue_comments(github_issues, repo_root, issue_number) -> list | GitHubAPIFailed:
        """Get issue/PR discussion comments."""
\`\`\`

## Usage in Kit Commands

\`\`\`python
from dot_agent_kit.cli_result import exit_with_error
from dot_agent_kit.non_ideal_state import (
    GitHubChecks, BranchDetectionFailed, NoPRForBranch
)

# Chain of checks with early exit on error
branch_result = GitHubChecks.branch(get_current_branch(ctx))
if isinstance(branch_result, BranchDetectionFailed):
    exit_with_error(branch_result.error_type, branch_result.message)
branch = branch_result

pr_result = GitHubChecks.pr_for_branch(github, repo_root, branch)
if isinstance(pr_result, NoPRForBranch):
    exit_with_error(pr_result.error_type, pr_result.message)
pr_details = pr_result
\`\`\`

## Design Principles

1. **Never throws** - All errors returned as NonIdealState
2. **Thin wrapper** - Minimal logic, just error type conversion
3. **Composable** - Results can be chained with isinstance checks
```

---

### 4. Update docs/agent/index.md (Category B - Teaching Gap)

**Location**: `docs/agent/index.md`
**Action**: Update (add entries for new docs)
**Priority**: Low

Add to architecture section:
- `non-ideal-state.md` - "handling operations that can fail gracefully"
- `cli-exit-patterns.md` - "writing kit CLI commands", "choosing between JSON and styled output"
- `github-checks-pattern.md` - "calling GitHub API in kit commands"

---

### 5. Update Glossary (Category B - Teaching Gap)

**Location**: `docs/agent/glossary.md`
**Action**: Update (add term)
**Priority**: Low

Add entry:

```markdown
### NonIdealState

A Protocol interface for representing operation failures without throwing exceptions.

**Pattern**: Functions return \`T | NonIdealState\` allowing callers to inspect results and decide how to handle errors.

**Key types**: \`BranchDetectionFailed\`, \`NoPRForBranch\`, \`PRNotFoundError\`, \`GitHubAPIFailed\`

**Usage**:
- Kit CLI: Check with \`isinstance()\`, exit with \`exit_with_error()\`
- Erk CLI: Use \`Ensure.X()\` methods for type narrowing

**Files**: \`erk_shared/non_ideal_state.py\`, \`dot_agent_kit/non_ideal_state.py\`
```