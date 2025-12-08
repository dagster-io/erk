---
title: Kit CLI Push-Down Pattern
read_when:
  - "agent markdown files exceed 200 lines"
  - "slash commands contain embedded bash scripts"
  - "need to make agent logic testable"
  - "optimizing token usage in kit commands"
---

# Kit CLI Push-Down Pattern

When agent markdown files grow large (>200 lines) with embedded bash commands, push logic down to kit CLI commands for testability and token efficiency.

## Problem: Agent-Heavy Commands

Large agent markdown files with embedded bash:

```markdown
# git-branch-submitter.md (442 lines)

## Step 1: Check Authentication

Check if GitHub is authenticated:

bash
gh auth status || (echo "Not authenticated" && exit 1)

## Step 2: Stage and Push

bash
git add -A
git commit -m "..."
git push -u origin HEAD

## Step 3: Create PR

bash
pr_url=$(gh pr create --fill --json url -q '.url')
echo "$pr_url"

... (400 more lines of embedded bash)
```

**Problems**:

- **Untestable**: Bash embedded in markdown can't be unit tested
- **Token-heavy**: ~7,500-9,000 tokens per invocation
- **Unmaintainable**: Logic scattered across markdown prose
- **Error-prone**: No type safety, hard to debug

## Solution: Python-Backed Commands

Push logic to kit CLI commands:

```markdown
# pr-push.md (~60 lines)

## Execute PR Push

Run the preflight operation:

bash
erk pr push

The command handles:

- Authentication checks
- Staging and pushing changes
- PR creation
- Diff extraction for analysis

Result will be provided for the next phase.
```

**Benefits**:

- **Testable**: Full unit test coverage with fakes
- **Token-efficient**: ~2,000-2,500 tokens (67-75% reduction)
- **Maintainable**: Python code with type hints
- **Composable**: CLI commands can be called from other contexts

## Migration Steps

### 1. Identify Mechanical Operations

Extract operations that don't require AI:

✅ **Push to CLI**:

- Git operations (add, commit, push, diff)
- GitHub API calls (create PR, update PR, fetch data)
- Authentication checks
- File I/O (write diffs, read config)

❌ **Keep in Agent**:

- Diff analysis
- Commit message generation
- PR description generation
- Semantic decision-making

### 2. Create Kit CLI Commands or Main CLI Commands

**Kit CLI** (`pyproject.toml` entry point):

```toml
[project.entry-points."mykit.cli"]
pr-push = "mykit.commands.pr_push:pr_push"
pr-finalize = "mykit.commands.pr_push:finalize"
```

**Main CLI** (erk core):

```python
@click.command("pr-push")
@click.pass_obj
def pr_push(ctx: ErkContext, branch: str | None = None) -> None:
    """Push changes and create PR (preflight phase)."""
    result = run_preflight(ctx.git, ctx.github, branch or ctx.git.current_branch())
    click.echo(json.dumps(result.to_dict()))
```

### 3. Create Integration Package with Protocol + Types

Define interfaces for operations:

```python
# erk_shared/integrations/git_pr/__init__.py

from typing import Protocol
from dataclasses import dataclass
from pathlib import Path

class GitPrKit(Protocol):
    """Minimal dependencies for PR operations."""

    @property
    def git(self) -> Git: ...

    @property
    def github(self) -> GitHub: ...

@dataclass
class GitPreflightResult:
    """Result from PR push preflight."""
    pr_url: str
    diff_path: Path
    branch: str
    base_branch: str
```

**Key insight**: `ErkContext` satisfies `GitPrKit` via structural typing (no code changes needed).

### 4. Add Real/Fake Implementations

**Real operations** (`operations/preflight.py`):

```python
def run_preflight(git: Git, github: GitHub, branch: str) -> GitPreflightResult:
    """Execute preflight operations."""
    if not github.is_authenticated():
        raise GitPreflightError("GitHub auth required")

    git.push(branch)
    pr_url = github.create_pr(branch)
    diff = git.get_diff("main", branch)
    diff_path = _write_diff(diff)

    return GitPreflightResult(pr_url, diff_path, branch, "main")
```

**Fake implementations** (for tests):

```python
class FakeGit:
    def __init__(self) -> None:
        self.methods_called: dict[str, bool] = {}

    def push(self, branch: str) -> None:
        self.methods_called["push"] = True

class FakeGitHub:
    def create_pr(self, branch: str) -> str:
        self.methods_called["create_pr"] = True
        return "https://github.com/org/repo/pull/123"
```

### 5. Update Slash Command to Delegate to CLI

**Before (agent-heavy)**:

```markdown
## Step 1: Auth Check

bash
gh auth status
```

**After (Python-backed)**:

```markdown
## Execute Preflight

bash
result=$(erk pr push --json)
pr_url=$(echo "$result" | jq -r '.pr_url')
diff_path=$(echo "$result" | jq -r '.diff_path')

Now analyze the diff at `$diff_path`...
```

Or even simpler with two-phase pattern:

```markdown
Run preflight:

bash
erk pr push

The PR has been created. Generate metadata based on the diff.
```

### 6. Remove Old Agent from kit.yaml

After migration, remove the old agent:

```yaml
# kit.yaml - BEFORE
artifacts:
  agents:
    - agents/git-branch-submitter.md

# kit.yaml - AFTER
artifacts:
  agents: []
  # Removed git-branch-submitter.md
```

**Don't forget**: Remove the symlink from `.claude/agents/` directory. The `test_no_broken_symlinks_in_claude_directory` integration test will fail if orphaned symlinks remain.

## Before/After Comparison

### Before: Agent-Heavy (git-branch-submitter)

```markdown
# agents/git-branch-submitter.md (442 lines)

## Step 1: Auth Check

bash
if ! gh auth status 2>/dev/null; then
echo "Error: GitHub not authenticated"
exit 1
fi

## Step 2: Check Dirty State

bash
if ! git diff-index --quiet HEAD --; then
echo "Error: Uncommitted changes"
exit 1
fi

## Step 3: Push Branch

bash
git push -u origin HEAD

## Step 4: Create PR

bash
pr_url=$(gh pr create --fill --json url -q '.url')
if [ -z "$pr_url" ]; then
echo "Error: PR creation failed"
exit 1
fi

## Step 5: Get Diff

bash
diff=$(git diff main...HEAD)
echo "$diff" > /tmp/pr-diff.txt

## Step 6: Analyze Diff

[... 200 lines of analysis logic ...]

## Step 7: Generate Title/Body

[... 200 lines of generation logic ...]
```

**Issues**:

- 442 lines
- 7,500-9,000 tokens
- No tests
- Hard to maintain

### After: Python-Backed (pr-push)

**Command file** (60 lines):

```markdown
# commands/pr-push.md (~60 lines)

Run preflight to push changes and create PR:

bash
erk pr push

Generate commit message and PR metadata based on the diff.

After generation, finalize:

bash
erk pr finalize --title "$title" --body "$body"
```

**Python implementation** (testable):

```python
# erk_shared/integrations/git_pr/operations/preflight.py

def run_preflight(git: Git, github: GitHub, branch: str) -> GitPreflightResult:
    """Execute all preflight operations."""
    if not github.is_authenticated():
        raise GitPreflightError("GitHub auth required")

    if git.has_uncommitted_changes():
        raise GitPreflightError("Uncommitted changes")

    git.push(branch)
    pr_url = github.create_pr(branch)
    diff = git.get_diff("main", branch)
    diff_path = _write_diff(diff)

    return GitPreflightResult(pr_url, diff_path, branch, "main")
```

**Tests**:

```python
# tests/unit/integrations/git_pr/test_preflight.py

def test_run_preflight():
    fake_git = FakeGit()
    fake_gh = FakeGitHub()

    result = run_preflight(fake_git, fake_gh, "feature")

    assert result.pr_url.startswith("https://github.com")
    assert fake_git.methods_called["push"]
    assert fake_gh.methods_called["create_pr"]
```

**Results**:

- ~60 lines markdown
- 2,000-2,500 tokens (67-75% reduction)
- Full test coverage
- Easy to maintain

## When to Use This Pattern

**Use kit CLI push-down when**:

- Agent markdown exceeds ~200 lines
- Contains embedded bash scripts
- Logic is mechanical (not semantic)
- Want to test the operations
- Token usage is a concern

**Don't use when**:

- Agent is small (<100 lines)
- Operations require AI analysis
- One-off workflows not worth engineering

## Token Efficiency Comparison

| Approach        | Lines | Tokens      | Testable | Maintainable |
| --------------- | ----- | ----------- | -------- | ------------ |
| Agent-heavy     | 442   | 7,500-9k    | ❌       | ❌           |
| Python-backed   | 60    | 2,000-2.5k  | ✅       | ✅           |
| **Improvement** | -86%  | **-67-75%** | ✅       | ✅           |

## Design Principles

### Keep Agents Thin

Agents should orchestrate, not implement:

✅ **Agent role**: "Run preflight, then analyze diff, then finalize"

❌ **Not agent role**: Implementing git commands, API calls, error handling

### Push Logic to Python

If it can be tested, it should be in Python:

✅ **Python**: Authentication, git operations, API calls, file I/O

❌ **Agent markdown**: Semantic analysis, commit message generation

### Use JSON for Data Exchange

CLI commands return JSON for agent consumption:

```bash
result=$(erk pr push --json)
pr_url=$(echo "$result" | jq -r '.pr_url')
```

This enables type-safe data passing.

### Two-Phase Pattern

Separate mechanical operations from AI work:

1. **Preflight** (Python): Push, create PR, extract diff
2. **AI phase** (Agent): Analyze diff, generate metadata
3. **Finalize** (Python): Apply metadata, cleanup

See [Two-Phase Operation Pattern](../architecture/two-phase-operations.md) for details.

## Testing Strategy

### Unit Tests for Operations

```python
def test_preflight_validates_auth():
    fake_git = FakeGit()
    fake_gh = FakeGitHub(authenticated=False)

    with pytest.raises(GitPreflightError, match="auth required"):
        run_preflight(fake_git, fake_gh, "feature")
```

### Unit Tests for CLI Commands

```python
def test_pr_push_command(cli_runner, fake_context):
    result = cli_runner.invoke(pr_push, obj=fake_context)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert "pr_url" in output
```

### Integration Tests (Optional)

```python
def test_full_pr_workflow():
    # Uses real git/GitHub in test env
    run_preflight(real_git, real_gh, "test-branch")
    # Verify PR exists
```

## Migration Checklist

When migrating an agent-heavy command:

- [ ] Identify mechanical operations (auth, push, API calls)
- [ ] Create Protocol interface for dependencies
- [ ] Implement operations in Python (operations/ package)
- [ ] Add real implementations with error handling
- [ ] Add fake implementations for testing
- [ ] Write unit tests for all operations
- [ ] Create CLI commands (kit or main CLI)
- [ ] Update slash command to delegate to CLI
- [ ] Remove old agent markdown
- [ ] Remove agent entry from kit.yaml
- [ ] Remove symlink from .claude/agents/
- [ ] Verify `test_no_broken_symlinks_in_claude_directory` passes

## Example Implementations

### Git PR Push (git-only flow)

- **Integration**: `erk_shared/integrations/git_pr/`
- **Operations**: `erk_shared/integrations/git_pr/operations/`
- **CLI Command**: `erk_shared/cli/commands/pr_commands.py`
- **Slash Command**: `.claude/commands/git-pr-push.md`
- **Tests**: `tests/unit/integrations/git_pr/`

### Graphite PR Submit (stack-aware flow)

- **Integration**: `erk_shared/integrations/gt/`
- **Operations**: `erk_shared/integrations/gt/operations/`
- **Kit CLI**: `dot-agent-kit/.agent/kits/graphite-kit/src/commands/`
- **Slash Command**: `.claude/commands/gt-pr-submit.md`
- **Tests**: `dot-agent-kit/.agent/kits/graphite-kit/tests/`

## Related Topics

- [Two-Phase Operation Pattern](../architecture/two-phase-operations.md) - Architectural pattern for preflight/AI/finalize
- [Protocol Satisfaction](../architecture/protocol-vs-abc.md) - Using Protocols for minimal dependencies
- [Kit Artifact Management](dev/artifact-management.md) - Managing kit agents and symlinks
