"""Issue and draft PR next steps formatting - single source of truth."""

from dataclasses import dataclass


@dataclass(frozen=True)
class IssueNextSteps:
    """Canonical commands for issue operations."""

    issue_number: int
    url: str

    @property
    def view(self) -> str:
        return self.url

    @property
    def checkout(self) -> str:
        return f"erk br co --for-plan {self.issue_number}"

    @property
    def submit(self) -> str:
        return f"erk plan submit {self.issue_number}"

    @property
    def checkout_and_implement(self) -> str:
        return (
            f'source "$(erk br co --for-plan {self.issue_number} --script)"'
            " && erk implement --dangerous"
        )

    @property
    def checkout_new_slot(self) -> str:
        return f"erk br co --new-slot --for-plan {self.issue_number}"

    @property
    def checkout_new_slot_and_implement(self) -> str:
        return (
            f'source "$(erk br co --new-slot --for-plan {self.issue_number} --script)"'
            " && erk implement --dangerous"
        )


@dataclass(frozen=True)
class DraftPRNextSteps:
    """Canonical commands for draft PR operations."""

    pr_number: int
    branch_name: str
    url: str

    @property
    def view(self) -> str:
        return self.url

    @property
    def submit(self) -> str:
        return f"erk plan submit {self.pr_number}"

    @property
    def checkout_branch_and_implement(self) -> str:
        return f'source "$(erk br co {self.branch_name} --script)" && erk implement --dangerous'

    @property
    def checkout(self) -> str:
        return f"erk br co --for-plan {self.pr_number}"

    @property
    def checkout_and_implement(self) -> str:
        return (
            f'source "$(erk br co --for-plan {self.pr_number} --script)"'
            " && erk implement --dangerous"
        )

    @property
    def checkout_new_slot(self) -> str:
        return f"erk br co --new-slot --for-plan {self.pr_number}"

    @property
    def checkout_new_slot_and_implement(self) -> str:
        return (
            f'source "$(erk br co --new-slot --for-plan {self.pr_number} --script)"'
            " && erk implement --dangerous"
        )


# Slash commands (static, don't need issue number)
SUBMIT_SLASH_COMMAND = "/erk:plan-submit"
CHECKOUT_SLASH_COMMAND = "/erk:prepare"


def format_next_steps_plain(issue_number: int, *, url: str) -> str:
    """Format for CLI output (plain text)."""
    s = IssueNextSteps(issue_number, url=url)
    return f"""Next steps:

View Issue: {s.view}

In Claude Code:
  Submit to queue: {SUBMIT_SLASH_COMMAND}

OR exit Claude Code first, then run one of:
  Checkout: {s.checkout}
  Implement: {s.checkout_and_implement}
  Submit to Queue: {s.submit}"""


def format_draft_pr_next_steps_plain(pr_number: int, *, branch_name: str, url: str) -> str:
    """Format for CLI output (plain text) for draft PR plans."""
    s = DraftPRNextSteps(pr_number=pr_number, branch_name=branch_name, url=url)
    return f"""Next steps:

View PR: {s.view}

In Claude Code:
  Submit to queue: {SUBMIT_SLASH_COMMAND}

OR exit Claude Code first, then run one of:
  Checkout: {s.checkout}
  Implement: {s.checkout_new_slot_and_implement}
  Submit to Queue: {s.submit}"""


def format_next_steps_markdown(issue_number: int, *, url: str) -> str:
    """Format for issue body (markdown)."""
    s = IssueNextSteps(issue_number, url=url)
    return f"""## Execution Commands

**Submit to Erk Queue:**
```bash
{s.submit}
```

---

### Local Execution

**Checkout plan branch:**
```bash
{s.checkout}
```"""
