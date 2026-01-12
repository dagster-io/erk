# Plan: Add Fake Instantiation Patterns to fake-driven-testing Skill

## Problem

When authoring tests, agents assume fake APIs instead of reading them, leading to:
- Using methods that don't exist (e.g., `fake_issues.add_issue()`)
- Missing factory methods like `for_test()`
- Wrong constructor arguments

## Solution

Add a dedicated "Fake Instantiation Patterns" section to the fake-driven-testing skill with concrete examples for commonly used fakes.

## Files to Modify

1. `.claude/skills/fake-driven-testing/references/quick-reference.md` - Add new section

## Implementation

### Add to quick-reference.md

Add a new section **"Fake Instantiation Patterns"** after the existing "Common Test Patterns" section:

```markdown
## Fake Instantiation Patterns

**RULE: Before using a Fake* class, read its constructor signature or check for `for_test()` method.**

### FakeGitHubIssues

Constructor injection only - NO mutation methods like `add_issue()`.

```python
from erk_shared.github.issues import FakeGitHubIssues
from tests.test_utils.github_helpers import create_test_issue

# Empty fake
fake_issues = FakeGitHubIssues()

# With pre-configured issues (use create_test_issue helper)
fake_issues = FakeGitHubIssues(
    issues={123: create_test_issue(123, "Title", "Body")}
)

# With labels
fake_issues = FakeGitHubIssues(labels={"erk-plan", "ai-generated"})

# Assertions use mutation tracking properties
assert len(fake_issues.added_comments) == 1
assert fake_issues.created_issues[0][0] == "Expected Title"
```

### FakeClaudeInstallation

Use `for_test()` factory method - constructor requires all params.

```python
from erk_shared.learn.extraction.claude_installation.fake import (
    FakeClaudeInstallation,
    FakeProject,
    FakeSessionData,
)

# Simple - use for_test() with defaults
fake_claude = FakeClaudeInstallation.for_test()

# With settings
fake_claude = FakeClaudeInstallation.for_test(
    settings={"statusLine": {"type": "command"}}
)

# With session data
fake_claude = FakeClaudeInstallation.for_test(
    projects={
        tmp_path: FakeProject(
            sessions={
                "session-id": FakeSessionData(
                    content='{"type": "user"}\n',
                    size_bytes=1024,
                    modified_at=time.time(),
                )
            }
        )
    }
)
```

### FakeGit

Constructor injection with path-keyed dicts.

```python
from erk_shared.git.fake import FakeGit

# Minimal setup
fake_git = FakeGit()

# With branch state
fake_git = FakeGit(
    current_branches={cwd: "feature-branch"},
    trunk_branches={cwd: "master"},
    local_branches={cwd: ["master", "feature-branch"]},
)

# Assertions use mutation tracking
assert fake_git.checked_out_branches[-1] == (cwd, "new-branch")
assert len(fake_git.created_branches) == 1
```

### ErkContext.for_test()

Use for CLI command tests with dependency injection.

```python
from erk_shared.context import ErkContext

ctx = ErkContext.for_test(
    git=fake_git,
    github_issues=fake_issues,
    cwd=tmp_path,
    repo_root=tmp_path,
)

result = runner.invoke(my_command, ["arg"], obj=ctx)
```
```

## Why quick-reference.md?

- It's the "quick lookup" document agents consult first
- Existing "Common Test Patterns" section sets precedent for code examples
- patterns.md covers implementation patterns (how to BUILD fakes), not usage

## Verification

1. Run `/local:fast-ci` to ensure no formatting issues
2. Load the fake-driven-testing skill and verify the new section appears
3. Manual review: examples should be copy-paste ready