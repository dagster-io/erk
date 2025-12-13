"""Issue next steps formatting - single source of truth."""

from dataclasses import dataclass


@dataclass
class IssueNextSteps:
    """Canonical commands for issue operations."""

    issue_number: int

    @property
    def view(self) -> str:
        return f"gh issue view {self.issue_number} --web"

    @property
    def implement(self) -> str:
        return f"erk implement {self.issue_number}"

    @property
    def implement_dangerous(self) -> str:
        return f"erk implement {self.issue_number} --dangerous"

    @property
    def implement_yolo(self) -> str:
        return f"erk implement {self.issue_number} --yolo"

    @property
    def submit(self) -> str:
        return f"erk submit {self.issue_number}"


# Slash command (static, doesn't need issue number)
SUBMIT_SLASH_COMMAND = "/erk:plan-submit"


def format_next_steps_plain(issue_number: int) -> str:
    """Format for CLI output (plain text)."""
    s = IssueNextSteps(issue_number)
    return f"""Next steps:

View Issue: {s.view}
Interactive: {s.implement}
Dangerous Interactive: {s.implement_dangerous}
Dangerous, Non-Interactive, Auto-Submit: {s.implement_yolo}
Submit to Queue: {s.submit}
  # Or use: {SUBMIT_SLASH_COMMAND}"""


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

**Standard mode (interactive):**
```bash
{s.implement}
```

**Yolo mode (fully automated, skips confirmation):**
```bash
{s.implement_yolo}
```

**Dangerous mode (auto-submit PR after implementation):**
```bash
{s.implement_dangerous}
```"""
