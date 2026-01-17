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
    def prepare(self) -> str:
        return f"erk prepare {self.issue_number}"

    @property
    def submit(self) -> str:
        return f"erk plan submit {self.issue_number}"


# Slash commands (static, don't need issue number)
SUBMIT_SLASH_COMMAND = "/erk:plan-submit"
PREPARE_SLASH_COMMAND = "/erk:prepare"


def format_next_steps_plain(issue_number: int) -> str:
    """Format for CLI output (plain text)."""
    s = IssueNextSteps(issue_number)
    return f"""Next steps:

View Issue: {s.view}

In Claude Code:
  Prepare worktree: {PREPARE_SLASH_COMMAND}
  Submit to queue: {SUBMIT_SLASH_COMMAND}

OR exit Claude Code first, then run one of:
  Local: {s.prepare}
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

**Prepare worktree:**
```bash
{s.prepare}
```"""
