"""Issue next steps formatting - single source of truth."""

from dataclasses import dataclass


@dataclass(frozen=True)
class IssueNextSteps:
    """Canonical commands for issue operations."""

    issue_number: int

    @property
    def view(self) -> str:
        return f"gh issue view {self.issue_number} --web"

    @property
    def view_pr(self) -> str:
        return f"gh pr view {self.issue_number} --web"

    @property
    def prepare(self) -> str:
        return f"erk prepare {self.issue_number}"

    @property
    def submit(self) -> str:
        return f"erk plan submit {self.issue_number}"

    @property
    def prepare_and_implement(self) -> str:
        return f'source "$(erk prepare {self.issue_number} --script)" && erk implement --dangerous'


# Slash commands (static, don't need issue number)
SUBMIT_SLASH_COMMAND = "/erk:plan-submit"
PREPARE_SLASH_COMMAND = "/erk:prepare"


def format_next_steps_plain(issue_number: int) -> str:
    """Format for CLI output (plain text)."""
    steps = IssueNextSteps(issue_number)
    return f"""Next steps:

View Issue: {steps.view}

In Claude Code:
  Prepare worktree: {PREPARE_SLASH_COMMAND}
  Submit to queue: {SUBMIT_SLASH_COMMAND}

OR exit Claude Code first, then run one of:
  Local: {steps.prepare}
  Prepare+Implement: {steps.prepare_and_implement}
  Submit to Queue: {steps.submit}"""


def format_next_steps_draft_pr(plan_number: int) -> str:
    """Format next steps for draft PR backend (CLI output)."""
    steps = IssueNextSteps(plan_number)
    return f"""Next steps:

View PR: {steps.view_pr}

In Claude Code:
  Submit to queue: {SUBMIT_SLASH_COMMAND} — Submit plan for remote agent implementation

OR exit Claude Code first, then run one of:
  Local: {steps.prepare}
  Prepare+Implement: {steps.prepare_and_implement}
  Submit to Queue: {steps.submit}"""


def format_next_steps_markdown(issue_number: int) -> str:
    """Format for issue body (markdown)."""
    steps = IssueNextSteps(issue_number)
    return f"""## Execution Commands

**Submit to Erk Queue:**
```bash
{steps.submit}
```

---

### Local Execution

**Prepare worktree:**
```bash
{steps.prepare}
```"""
