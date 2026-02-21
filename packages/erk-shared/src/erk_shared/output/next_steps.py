"""Issue and draft PR next steps formatting - single source of truth."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WorktreeContext:
    """Context about whether the user is in a pool slot."""

    is_in_slot: bool
    slot_name: str | None


@dataclass(frozen=True)
class IssueNextSteps:
    """Canonical commands for issue operations."""

    issue_number: int

    @property
    def view(self) -> str:
        return f"gh issue view {self.issue_number} --web"

    @property
    def prepare(self) -> str:
        return f"erk br create --for-plan {self.issue_number}"

    @property
    def submit(self) -> str:
        return f"erk plan submit {self.issue_number}"

    @property
    def prepare_and_implement(self) -> str:
        return (
            f'source "$(erk br create --for-plan {self.issue_number} --script)"'
            " && erk implement --dangerous"
        )


@dataclass(frozen=True)
class DraftPRNextSteps:
    """Canonical commands for draft PR operations."""

    pr_number: int
    branch_name: str

    @property
    def view(self) -> str:
        return f"gh pr view {self.pr_number} --web"

    @property
    def submit(self) -> str:
        return f"erk plan submit {self.pr_number}"

    @property
    def checkout_and_implement(self) -> str:
        return f'source "$(erk br co {self.branch_name} --script)" && erk implement --dangerous'


# Slash commands (static, don't need issue number)
SUBMIT_SLASH_COMMAND = "/erk:plan-submit"
PREPARE_SLASH_COMMAND = "/erk:prepare"


def format_next_steps_plain(issue_number: int, *, worktree_context: WorktreeContext | None) -> str:
    """Format for CLI output (plain text)."""
    s = IssueNextSteps(issue_number)

    if worktree_context is not None and worktree_context.is_in_slot:
        return f"""Next steps:

View Issue: {s.view}

In Claude Code:
  Prepare (stacks in current worktree): {PREPARE_SLASH_COMMAND}
  Submit to queue: {SUBMIT_SLASH_COMMAND}

OR exit Claude Code first, then run one of:
  Stack here: {s.prepare}
  Stack+Implement: {s.prepare_and_implement}
  Submit to Queue: {s.submit}

Advanced — new worktree (run from root worktree):
  {s.prepare}"""

    return f"""Next steps:

View Issue: {s.view}

In Claude Code:
  Prepare worktree: {PREPARE_SLASH_COMMAND}
  Submit to queue: {SUBMIT_SLASH_COMMAND}

OR exit Claude Code first, then run one of:
  Local: {s.prepare}
  Prepare+Implement: {s.prepare_and_implement}
  Submit to Queue: {s.submit}"""


def format_draft_pr_next_steps_plain(
    pr_number: int, *, branch_name: str, worktree_context: WorktreeContext | None
) -> str:
    """Format for CLI output (plain text) for draft PR plans."""
    s = DraftPRNextSteps(pr_number=pr_number, branch_name=branch_name)

    if worktree_context is not None and worktree_context.is_in_slot:
        return f"""Next steps:

View PR: {s.view}

In Claude Code:
  Submit to queue: {SUBMIT_SLASH_COMMAND}

Outside Claude Code:
  Stack here: {s.checkout_and_implement}
  Submit to queue: {s.submit}

Advanced — new worktree (run from root worktree):
  {s.checkout_and_implement}"""

    return f"""Next steps:

View PR: {s.view}

In Claude Code:
  Submit to queue: {SUBMIT_SLASH_COMMAND}

Outside Claude Code:
  Local: {s.checkout_and_implement}
  Submit to queue: {s.submit}"""


def format_next_steps_markdown(issue_number: int) -> str:
    """Format for issue body (markdown)."""
    s = IssueNextSteps(issue_number)
    return f"""## Execution Commands

**Submit to Erk Queue:**
```bash
{s.submit}
```

---

### Local Execution

**Create branch from plan:**
```bash
{s.prepare}
```"""
