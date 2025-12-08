---
title: Two-Phase Operation Architecture
read_when:
  - "implementing CLI operations with AI generation"
  - "adding new submit or land workflows"
  - "understanding preflight/finalize pattern"
---

# Two-Phase Operation Architecture

Erk's PR submission and landing workflows follow a **Preflight → AI → Finalize** pattern that separates destructive git operations from AI-powered content generation.

## Architecture Overview

```
┌─────────────┐       ┌──────────────┐       ┌────────────┐
│  Preflight  │  -->  │      AI      │  -->  │  Finalize  │
│   (Python)  │       │  (Delegate)  │       │  (Python)  │
└─────────────┘       └──────────────┘       └────────────┘
     Phase 1              Phase 2               Phase 3
```

### Phase 1: Preflight (Python)

**Purpose**: Execute all destructive git/GitHub operations before AI generation

**Operations**:
- Authentication checks (Graphite + GitHub)
- Squash commits if needed
- Submit branch (push to remote, create PR)
- Extract diff for AI analysis
- Rebase stack
- Merge PR (for land operations)

**Key Principle**: All mutations happen in this phase. If preflight succeeds, the PR/branch is already in its target state. AI generation is just adding metadata.

**Output**:
- PR number
- Diff file path
- Repository metadata (root, branch names, commit messages)
- Error details (if preflight fails)

### Phase 2: AI Generation (Delegated)

**Purpose**: Generate PR title and body from diff

**Input**:
- Diff file from preflight
- Repository context (branch names, commit messages)

**Output**:
- PR title (first line of commit message)
- PR body (remaining lines of commit message)

**Implementation**: Delegated to `CommitMessageGenerator` which uses the Claude CLI.

### Phase 3: Finalize (Python)

**Purpose**: Apply AI-generated metadata to the PR

**Operations**:
- Update PR title via GitHub API
- Update PR body via GitHub API
- Add labels (e.g., `erk-skip-extraction` for extraction plans)
- Clean up temporary files (diff files)

**Key Principle**: This phase is idempotent. If it fails, the PR exists and can be manually updated.

**Output**:
- PR URL (GitHub)
- Graphite URL (if available)
- Success/failure status

## Phase Responsibilities

| Phase      | Mutations | Idempotent | Can Fail Safely? |
| ---------- | --------- | ---------- | ---------------- |
| Preflight  | Yes       | No         | No - abort early |
| AI         | No        | Yes        | Yes - retry      |
| Finalize   | Yes       | Yes        | Yes - manual fix |

### Why Separate Phases?

1. **Fail Fast**: Preflight validates all preconditions (auth, no conflicts, commits exist) before making changes
2. **AI Isolation**: AI generation can't corrupt git state or create orphaned PRs
3. **Testability**: Python functions accept Result types, no subprocess calls in AI phase
4. **Token Efficiency**: AI generation happens in Python, not bash-heavy agent code
5. **Reliability**: If AI fails, PR still exists (just missing description)

## Implementation Examples

### PR Submit (`erk pr submit`)

**File**: `src/erk/cli/commands/pr/submit_cmd.py`

```python
# Phase 1: Preflight
preflight_result = _run_preflight(ctx, cwd, session_id, debug)
if isinstance(preflight_result, PreAnalysisError):
    raise click.ClickException(preflight_result.message)

# Phase 2: Generate
msg_result = _run_commit_message_generation(
    msg_gen,
    diff_file=Path(preflight_result.diff_file),
    repo_root=Path(preflight_result.repo_root),
    current_branch=preflight_result.current_branch,
    parent_branch=preflight_result.parent_branch,
)

# Phase 3: Finalize
finalize_result = _run_finalize(
    ctx,
    cwd,
    pr_number=preflight_result.pr_number,
    title=msg_result.title,
    body=msg_result.body,
    diff_file=preflight_result.diff_file,
)
```

### PR Land (`erk pr land`)

**File**: `src/erk/cli/commands/pr/land_cmd.py`

Similar three-phase structure:
1. **Preflight**: Merge PR, delete worktree
2. **AI**: Generate extraction plan markers
3. **Finalize**: Create pending-extraction issues

## When to Use This Pattern

**Use two-phase operations when**:
- Operation creates a PR or modifies GitHub state
- AI-generated content is involved
- Multiple git operations must happen atomically (before AI)

**Do NOT use for**:
- Simple read-only operations (status checks, listing)
- Operations with no AI generation
- Operations where git state doesn't change

## Benefits

### 1. Testability

Python functions accept Result types, enabling unit tests without subprocess mocking:

```python
def test_finalize_updates_pr():
    fake_github = FakeGitHub(...)
    result = execute_finalize(
        ops=fake_ops,
        cwd=Path("/tmp/repo"),
        pr_number=123,
        pr_title="Fix bug",
        pr_body="Description",
    )
    assert isinstance(result, FinalizeResult)
    assert fake_github.pr_updates[123]["title"] == "Fix bug"
```

### 2. Token Efficiency

AI generation happens in Python, not agent-orchestrated bash:
- No subprocess call overhead in agent prompts
- Direct integration with Claude CLI
- Structured error handling without parsing bash output

### 3. Reliability

If AI generation fails:
- PR still exists (created in preflight)
- User can manually edit PR description
- No orphaned branches or corrupted git state

## Related Patterns

### Result Pattern

Two-phase operations use frozen dataclasses for results:

```python
@dataclass
class PreflightResult:
    success: bool
    pr_number: int
    diff_file: str
    repo_root: str
    current_branch: str
    parent_branch: str
    commit_messages: list[str]

@dataclass
class PreAnalysisError:
    success: bool
    error_type: PreAnalysisErrorType
    message: str
    details: dict[str, Any]
```

See [Result Pattern Documentation](result-pattern.md) for details.

### Event Streaming

Phases use generators to yield progress events:

```python
def execute_preflight(
    ops: GtKit,
    cwd: Path,
    session_id: str,
) -> Generator[ProgressEvent | CompletionEvent[PreflightResult | PreAnalysisError]]:
    yield ProgressEvent(style="info", message="Checking authentication...")
    # ... operations ...
    yield CompletionEvent(result=PreflightResult(...))
```

## Refactoring Agent Code to Python

### Before (Agent-Orchestrated)

```bash
# Agent code in slash command
gt submit --restack
PR_NUMBER=$(gh pr view --json number -q .number)
diff_file=$(mktemp)
git diff > "$diff_file"
# ... more bash ...
```

**Problems**:
- Agent must orchestrate multiple subprocess calls
- High token cost (bash output in context)
- Hard to test (requires mocking subprocess)
- Error handling via string parsing

### After (Python Two-Phase)

```python
# Python code in CLI command
for event in execute_preflight(ctx, cwd, session_id):
    if isinstance(event, CompletionEvent):
        result = event.result

if isinstance(result, PreflightResult):
    # Continue to AI phase
    ...
```

**Benefits**:
- Python orchestrates subprocess calls
- Low token cost (structured Result types)
- Easy to test (FakeGit, FakeGitHub)
- LBYL error handling with type checking

## Implementation Checklist

When adding a new two-phase operation:

1. [ ] Define Result types (Success + Error dataclasses)
2. [ ] Implement preflight function (returns Generator with events)
3. [ ] Implement finalize function (returns Generator with events)
4. [ ] Add CLI command that orchestrates phases
5. [ ] Add unit tests with Fake implementations
6. [ ] Add integration tests (if feasible)
7. [ ] Document in slash command (if exposed to agents)

## Related Documentation

- [Result Pattern](result-pattern.md) - Frozen dataclass result types
- [Subprocess Wrappers](subprocess-wrappers.md) - Safe subprocess execution
- [Erk Architecture Patterns](erk-architecture.md) - Dependency injection, dry-run
- [Git PR Consolidation](submission-flows.md) - Comparison of Git vs Graphite flows
