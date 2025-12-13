# Plan: Use GitHub's Native Branch-to-Issue Linking

Replace custom branch naming with `gh issue develop` across all commands.

## Summary

**Current state:** Custom `derive_branch_name_with_date()` creates branches like `my-feature-25-11-29-1430`

**Proposed state:** Use `gh issue develop 123` which creates `123-my-feature` with native GitHub linking

**Benefits:**
- Branch appears in issue sidebar under "Development"
- Automatic PR-to-issue linking
- Delete ~200 lines of custom branch naming code
- Consistent with GitHub conventions

## Scope

- **Commands:** submit, implement, wt create --from-issue
- **Migration:** Document only (old branches remain as-is)
- **Submit behavior:** Keeps local branch/PR creation, uses `gh issue develop` for branch name

---

## Implementation

### Step 1: Create IssueDevelopment ABC

Create new abstraction for issue-linked branch operations.

**New file:** `packages/erk-shared/src/erk_shared/github/issue_development.py`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DevelopmentBranch:
    """Result of creating an issue-linked development branch."""
    branch_name: str
    issue_number: int
    already_existed: bool


class IssueDevelopment(ABC):
    """Abstract interface for issue-linked branch operations."""

    @abstractmethod
    def create_development_branch(
        self,
        repo_root: Path,
        issue_number: int,
        *,
        base_branch: str | None = None,
    ) -> DevelopmentBranch:
        """Create a development branch linked to an issue via gh issue develop."""
        ...

    @abstractmethod
    def get_linked_branch(
        self,
        repo_root: Path,
        issue_number: int
    ) -> str | None:
        """Get existing development branch for an issue."""
        ...
```

### Step 2: Implement Real and Fake

**New file:** `src/erk/core/github/issue_development_real.py`

```python
class RealIssueDevelopment(IssueDevelopment):
    def create_development_branch(self, repo_root, issue_number, *, base_branch=None):
        # Check for existing linked branch first
        existing = self.get_linked_branch(repo_root, issue_number)
        if existing:
            return DevelopmentBranch(existing, issue_number, already_existed=True)

        # Create via gh issue develop
        cmd = ["gh", "issue", "develop", str(issue_number)]
        if base_branch:
            cmd.extend(["--base", base_branch])

        result = run_subprocess_with_context(cmd, cwd=repo_root, ...)
        branch_name = result.stdout.strip()

        return DevelopmentBranch(branch_name, issue_number, already_existed=False)

    def get_linked_branch(self, repo_root, issue_number):
        cmd = ["gh", "issue", "develop", "--list", str(issue_number)]
        # Parse output to get branch name
        ...
```

**New file:** `tests/fakes/fake_issue_development.py`

```python
@dataclass
class FakeIssueDevelopment(IssueDevelopment):
    existing_branches: dict[int, str] = field(default_factory=dict)
    _created_branches: list[tuple[int, str]] = field(default_factory=list)

    @property
    def created_branches(self) -> list[tuple[int, str]]:
        return list(self._created_branches)

    def create_development_branch(self, repo_root, issue_number, *, base_branch=None):
        if issue_number in self.existing_branches:
            return DevelopmentBranch(
                self.existing_branches[issue_number], issue_number, already_existed=True
            )
        branch_name = f"{issue_number}-issue-branch"
        self._created_branches.append((issue_number, branch_name))
        self.existing_branches[issue_number] = branch_name
        return DevelopmentBranch(branch_name, issue_number, already_existed=False)
```

### Step 3: Add to ErkContext

**Modify:** `src/erk/core/context.py`

```python
@dataclass(frozen=True)
class ErkContext:
    # ... existing fields ...
    issue_development: IssueDevelopment  # NEW
```

Update context factory to inject dependency.

### Step 4: Update submit.py

**Modify:** `src/erk/cli/commands/submit.py`

Replace:
```python
from erk_shared.naming import derive_branch_name_with_date
...
branch_name = derive_branch_name_with_date(issue.title)
```

With:
```python
dev_branch = ctx.issue_development.create_development_branch(
    repo.root,
    issue_number,
    base_branch=trunk_branch,
)
branch_name = dev_branch.branch_name

if dev_branch.already_existed:
    # Branch exists, check for PR
    ...
else:
    # New branch, proceed with checkout and commit
    ctx.git.checkout_branch(repo.root, branch_name)
```

Keep the rest of the PR creation logic intact.

### Step 5: Update implement.py

**Modify:** `src/erk/cli/commands/implement.py`

In `_implement_from_issue()`, replace branch derivation:
```python
# OLD:
# name = ensure_unique_worktree_name_with_date(plan_source.base_name, ...)

# NEW:
dev_branch = ctx.issue_development.create_development_branch(
    repo.root,
    int(issue_number),
)
branch = dev_branch.branch_name
name = sanitize_worktree_name(branch)
```

### Step 6: Update wt create --from-issue

**Modify:** `src/erk/cli/commands/wt/create_cmd.py`

In the `--from-issue` flow:
```python
# When from_issue is set:
dev_branch = ctx.issue_development.create_development_branch(
    repo.root,
    int(issue_number_parsed),
)
branch = dev_branch.branch_name
name = sanitize_worktree_name(branch)
```

**Keep existing ad-hoc flows unchanged** for:
- `erk wt create <name>` (no issue)
- `erk wt create --from-plan <file>`
- `erk wt create --from-branch <branch>`

### Step 7: Delete Unused Code

**Delete from** `packages/erk-shared/src/erk_shared/naming.py`:
- `derive_branch_name_from_title()` (lines 405-448)
- `derive_branch_name_with_date()` (lines 451-474)
- `WORKTREE_DATE_SUFFIX_FORMAT` constant (line 19)
- `ensure_unique_worktree_name_with_date()` (lines 308-344)

**Delete file:** `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/derive_branch_name.py`

**Delete tests:**
- `test_derive_branch_name_*` in `tests/core/utils/test_naming.py`
- `test_ensure_unique_worktree_name_with_date` in same file

### Step 8: Update Documentation

Document the naming change in release notes or CHANGELOG:
- Old branches: `my-feature-25-11-29-1430`
- New branches: `123-my-feature`
- Existing worktrees unaffected

---

## Files to Modify

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/github/issue_development.py` | **NEW** - IssueDevelopment ABC |
| `src/erk/core/github/issue_development_real.py` | **NEW** - Real implementation |
| `tests/fakes/fake_issue_development.py` | **NEW** - Fake for testing |
| `src/erk/core/context.py` | Add `issue_development` field |
| `src/erk/cli/commands/submit.py` | Use `issue_development.create_development_branch()` |
| `src/erk/cli/commands/implement.py` | Use `issue_development` for issue mode |
| `src/erk/cli/commands/wt/create_cmd.py` | Use `issue_development` for --from-issue |
| `packages/erk-shared/src/erk_shared/naming.py` | Delete unused functions |
| `packages/dot-agent-kit/.../derive_branch_name.py` | **DELETE** |
| `tests/core/utils/test_naming.py` | Delete obsolete tests |
| `tests/commands/test_submit.py` | Update to use FakeIssueDevelopment |
| `tests/commands/test_implement.py` | Update to use FakeIssueDevelopment |

---

## Implementation Order

1. Create `IssueDevelopment` ABC and implementations (non-breaking)
2. Add to `ErkContext` (non-breaking)
3. Update `submit.py` to use new interface
4. Update `implement.py` to use new interface
5. Update `wt create --from-issue` to use new interface
6. Delete unused code and tests
7. Update tests
8. Document naming change