"""Issue and draft PR next steps formatting - single source of truth."""

from dataclasses import dataclass


@dataclass(frozen=True)
class IssueNextSteps:
    """Canonical commands for issue operations."""

    issue_number: int

    @property
    def view(self) -> str:
        return f"gh issue view {self.issue_number} --web"

    @property
    def prepare(self) -> str:
        return f"erk br co --for-plan {self.issue_number}"

    @property
    def submit(self) -> str:
        return f"erk plan submit {self.issue_number}"

    @property
    def prepare_and_implement(self) -> str:
        return (
            f'source "$(erk br co --for-plan {self.issue_number} --script)"'
            " && erk implement --dangerous"
        )

    @property
    def prepare_new_slot(self) -> str:
        return f"erk br co --new-slot --for-plan {self.issue_number}"

    @property
    def prepare_new_slot_and_implement(self) -> str:
        return (
            f'source "$(erk br co --new-slot --for-plan {self.issue_number} --script)"'
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

    @property
    def prepare(self) -> str:
        return f"erk br co --for-plan {self.pr_number}"

    @property
    def prepare_and_implement(self) -> str:
        return (
            f'source "$(erk br co --for-plan {self.pr_number} --script)"'
            " && erk implement --dangerous"
        )

    @property
    def prepare_new_slot(self) -> str:
        return f"erk br co --new-slot --for-plan {self.pr_number}"

    @property
    def prepare_new_slot_and_implement(self) -> str:
        return (
            f'source "$(erk br co --new-slot --for-plan {self.pr_number} --script)"'
            " && erk implement --dangerous"
        )


# Slash commands (static, don't need issue number)
SUBMIT_SLASH_COMMAND = "/erk:plan-submit"
PREPARE_SLASH_COMMAND = "/erk:prepare"


def format_next_steps_plain(issue_number: int) -> str:
    """Format for CLI output (plain text)."""
    s = IssueNextSteps(issue_number)
    return f"""Next steps:

View Issue: {s.view}

In Claude Code:
  Submit to queue: {SUBMIT_SLASH_COMMAND}

OR exit Claude Code first, then run one of:
  Local: {s.prepare}
  Implement: {s.prepare_and_implement}
  Submit to Queue: {s.submit}"""


def format_draft_pr_next_steps_plain(pr_number: int, *, branch_name: str) -> str:
    """Format for CLI output (plain text) for draft PR plans."""
    s = DraftPRNextSteps(pr_number=pr_number, branch_name=branch_name)
    return f"""Next steps:

View PR: {s.view}

In Claude Code:
  Submit to queue: {SUBMIT_SLASH_COMMAND}

OR exit Claude Code first, then run one of:
  Local: {s.prepare}
  Implement: {s.prepare_and_implement}
  Submit to Queue: {s.submit}"""


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

**Checkout plan branch:**
```bash
{s.prepare}
```"""
