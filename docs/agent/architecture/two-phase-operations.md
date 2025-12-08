---
title: Two-Phase Operation Pattern
read_when:
  - "implementing slash commands that combine mechanical operations with AI analysis"
  - "separating Python operations from AI-powered workflows"
  - "designing CLI commands for git or PR operations"
  - "optimizing token usage in agent workflows"
---

# Two-Phase Operation Pattern

The two-phase operation pattern separates mechanical Python operations from AI-powered analysis, creating testable, token-efficient workflows.

## Architecture

```
Slash Command → Preflight (Python) → AI Analysis → Finalize (Python)
```

### Phase 1: Preflight (Python)

Mechanical operations handled entirely in Python:

- Auth checks (GitHub token, git config)
- Staging changes (git add)
- Pushing branches
- PR creation
- Diff extraction

**Returns**: Structured result (e.g., `GitPreflightResult`) with all data AI needs

**Events**: Yields `ProgressEvent` for status updates, `CompletionEvent` with result

**Errors**: Typed error classes (e.g., `GitPreflightError`)

### Phase 2: AI Analysis

Only semantic work requiring LLM:

- Diff analysis
- Commit message generation
- PR title/body generation

**Input**: Receives diff file path and metadata from preflight

**Pattern**: Uses `CommitMessageGenerator` or similar for AI invocation

### Phase 3: Finalize (Python)

Apply AI-generated content:

- Update PR metadata with AI-generated title/body
- Add footer generation
- Add issue closing references
- Clean up temp files

## Benefits

### Testability

All Python operations testable with `FakeGit`/`FakeGitHub`:

```python
def test_pr_push_preflight():
    fake_git = FakeGit()
    fake_gh = FakeGitHub()

    result = run_preflight(fake_git, fake_gh, branch="feature")

    assert result.pr_url == "https://github.com/org/repo/pull/123"
    assert fake_git.push_called
    assert fake_gh.create_pr_called
```

### Token Efficiency

Agent only loaded for semantic work:

- **Before (agent-heavy)**: ~7,500-9,000 tokens per invocation
- **After (two-phase)**: ~2,000-2,500 tokens for AI phase only

Preflight and finalize run without agent context.

### Consistency

Same pattern works for both git-only and Graphite flows:

- Git flow: `erk pr push` → preflight → AI → finalize
- Graphite flow: `erk gt pr submit` → preflight → AI → finalize

## Implementation Structure

### Preflight Function

```python
def run_preflight(
    git: Git,
    github: GitHub,
    branch: str
) -> GitPreflightResult:
    """Execute all mechanical operations before AI analysis."""
    # Auth checks
    if not github.is_authenticated():
        raise GitPreflightError("GitHub auth required")

    # Push branch
    git.push(branch)

    # Create PR
    pr_url = github.create_pr(branch)

    # Extract diff
    diff = git.get_diff("main", branch)
    diff_path = write_diff_to_temp(diff)

    return GitPreflightResult(
        pr_url=pr_url,
        diff_path=diff_path,
        branch=branch
    )
```

### AI Analysis Integration

```python
def generate_pr_metadata(result: GitPreflightResult) -> PRMetadata:
    """Use AI to generate PR title and body from diff."""
    generator = CommitMessageGenerator()

    with open(result.diff_path, encoding="utf-8") as f:
        diff_content = f.read()

    return generator.generate_pr_metadata(
        diff=diff_content,
        branch=result.branch
    )
```

### Finalize Function

```python
def finalize_pr(
    github: GitHub,
    pr_url: str,
    metadata: PRMetadata,
    issue_number: int | None
) -> None:
    """Apply AI-generated metadata to PR."""
    # Update PR
    github.update_pr(
        pr_url,
        title=metadata.title,
        body=format_pr_body(metadata.body, issue_number)
    )

    # Cleanup
    cleanup_temp_files()
```

## Example Implementations

### Git-Only Flow

Located in `erk_shared/integrations/git_pr/operations/`:

- `preflight.py` - Auth, push, PR creation, diff extraction
- `finalize.py` - Update PR metadata, cleanup

Slash command: `.claude/commands/git-pr-push.md`

### Graphite Flow

Located in `erk_shared/integrations/gt/operations/`:

- `preflight.py` - Graphite-specific preflight (stack-aware)
- `finalize.py` - Graphite-specific finalize (updates stack)

Slash command: `.claude/commands/gt-pr-submit.md`

## Design Principles

### Keep Preflight Pure Python

No AI calls in preflight - only mechanical operations:

✅ **Correct**: Git commands, API calls, file operations

❌ **Wrong**: Commit message generation, diff analysis

### Return Complete Context

Preflight result must contain everything AI needs:

```python
@dataclass
class GitPreflightResult:
    pr_url: str
    diff_path: Path  # AI reads this
    branch: str
    base_branch: str
    commit_count: int
```

AI phase should NOT call git/GitHub APIs directly.

### Handle Errors in Preflight

Fail fast on mechanical issues before invoking AI:

```python
def run_preflight(...) -> GitPreflightResult:
    if not git.has_staged_changes():
        raise GitPreflightError("No staged changes")

    if not github.is_authenticated():
        raise GitPreflightError("GitHub auth required")

    # ... continue with operations
```

### Emit Progress Events

Keep user informed during long operations:

```python
yield ProgressEvent("Pushing branch...")
git.push(branch)

yield ProgressEvent("Creating PR...")
pr_url = github.create_pr(branch)

yield CompletionEvent(GitPreflightResult(...))
```

## When to Use Two-Phase Pattern

**Use when**:

- Slash command needs both mechanical operations AND AI analysis
- Operations are slow (network calls, git operations)
- Want to test mechanical parts without AI
- Token usage is a concern

**Don't use when**:

- Pure Python operations (no AI needed)
- Pure AI operations (no mechanical work)
- Simple operations not worth splitting

## Testing Strategy

### Test Preflight with Fakes

```python
def test_preflight_creates_pr():
    fake_git = FakeGit()
    fake_gh = FakeGitHub()

    result = run_preflight(fake_git, fake_gh, branch="feature")

    assert result.pr_url.startswith("https://github.com")
    assert fake_git.methods_called["push"]
    assert fake_gh.methods_called["create_pr"]
```

### Test Finalize with Fakes

```python
def test_finalize_updates_pr():
    fake_gh = FakeGitHub()
    metadata = PRMetadata(title="feat: new", body="description")

    finalize_pr(fake_gh, pr_url="...", metadata=metadata, issue_number=123)

    assert fake_gh.methods_called["update_pr"]
    assert "Closes #123" in fake_gh.last_pr_body
```

### Integration Test (Optional)

```python
def test_full_workflow_integration():
    # Uses real git/GitHub in test environment
    result = run_preflight(real_git, real_gh, branch="test")
    metadata = generate_pr_metadata(result)
    finalize_pr(real_gh, result.pr_url, metadata, None)

    # Verify PR exists with correct metadata
    pr = real_gh.get_pr(result.pr_url)
    assert pr.title == metadata.title
```

## Related Topics

- [Kit CLI Push-Down Pattern](../kits/kit-cli-push-down.md) - When to move agent logic to Python
- [Protocol Satisfaction](protocol-vs-abc.md) - Using Protocols for operation dependencies
- [Subprocess Wrappers](subprocess-wrappers.md) - Safe git command execution
