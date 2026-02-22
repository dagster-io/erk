---
title: FakeGit Branch Divergence Testing
read_when:
  - "testing branch divergence scenarios"
  - "configuring FakeGit for force-push tests"
  - "writing tests that involve ahead/behind commit counts"
tripwires:
  - action: "testing divergence without setting branch_divergence in FakeGit"
    warning: "FakeGit.is_branch_diverged_from_remote() returns from the branch_divergence dict. Missing entries return default (not diverged). Set explicit divergence state for each test scenario."
---

# FakeGit Branch Divergence Testing

## BranchDivergence Type

Defined in `packages/erk-shared/src/erk_shared/gateway/git/abc.py`:

```python
class BranchDivergence(NamedTuple):
    is_diverged: bool
    ahead: int
    behind: int
```

## FakeGit Configuration

Constructor injection via dict with `(repo_path, branch_name, remote_name)` keys:

```python
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.git.abc import BranchDivergence

fake_git = FakeGit(
    branch_divergence={
        (tmp_path, "feature", "origin"): BranchDivergence(
            is_diverged=True,
            ahead=3,
            behind=2,
        )
    },
)
```

## Common Scenarios

| Scenario                 | is_diverged | ahead | behind | Real-world meaning                      |
| ------------------------ | ----------- | ----- | ------ | --------------------------------------- |
| Fresh branch, not pushed | False       | 1     | 0      | Local commits, no remote                |
| Up to date               | False       | 0     | 0      | Synced with remote                      |
| Plan impl (typical)      | True        | 3     | 2      | Worker commits diverged from scaffold   |
| Remote-only updates      | False       | 0     | 3      | Remote has new commits, local is behind |
| True divergence          | True        | 1     | 3      | Both sides have independent commits     |

## Test Pattern

From `tests/unit/cli/commands/pr/submit_pipeline/test_core_submit_flow.py`:

```python
def test_no_commits_ahead_returns_error(tmp_path: Path) -> None:
    fake_git = FakeGit(
        commits_ahead={(tmp_path, "main"): 0},
        branch_divergence={
            (tmp_path, "feature", "origin"): BranchDivergence(
                is_diverged=False, ahead=0, behind=0,
            )
        },
    )
    ctx = context_for_test(git=fake_git, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = _core_submit_flow(ctx, state)

    assert isinstance(result, SubmitError)
    assert result.error_type == "no_commits"
```

## Related Configuration

FakeGit also accepts `commits_ahead` for parent-relative commit counts — separate from divergence:

```python
FakeGit(
    commits_ahead={(tmp_path, "main"): 5},       # 5 commits ahead of main
    branch_divergence={...},                       # divergence from remote tracking
)
```

## Related Documentation

- [Testing Reference](testing.md) — Overall test architecture
- [Derived Flags Pattern](../architecture/derived-flags.md) — How divergence detection feeds into effective_force
