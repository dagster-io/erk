"""Plan next steps formatting - single source of truth."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PrNextSteps:
    """Canonical commands for plan operations."""

    pr_number: int
    url: str

    @property
    def view(self) -> str:
        return self.url

    @property
    def dispatch(self) -> str:
        return f"erk pr dispatch {self.pr_number}"

    @property
    def checkout(self) -> str:
        return f"erk br co --for-plan {self.pr_number}"

    @property
    def checkout_new_slot(self) -> str:
        return f"erk br co --new-slot --for-plan {self.pr_number}"

    @property
    def dispatch_slash_command(self) -> str:
        return DISPATCH_SLASH_COMMAND

    @property
    def implement_current_wt(self) -> str:
        return f"erk br co --for-plan {self.pr_number} && erk implement"

    @property
    def implement_current_wt_dangerous(self) -> str:
        return f"erk br co --for-plan {self.pr_number} && erk implement -d"

    @property
    def implement_new_wt(self) -> str:
        return (
            f'source "$(erk br co --new-slot --for-plan {self.pr_number} --script)"'
            " && erk implement"
        )

    @property
    def implement_new_wt_dangerous(self) -> str:
        return (
            f'source "$(erk br co --new-slot --for-plan {self.pr_number} --script)"'
            " && erk implement -d"
        )


# Slash commands (static, don't need plan number)
DISPATCH_SLASH_COMMAND = "/erk:pr-dispatch"
CHECKOUT_SLASH_COMMAND = "/erk:prepare"


def format_pr_next_steps_plain(pr_number: int, *, url: str) -> str:
    """Format for CLI output (plain text)."""
    s = PrNextSteps(pr_number=pr_number, url=url)
    return f"""Implement PR #{pr_number}:
  In current wt:    {s.implement_current_wt}
    (dangerously):  {s.implement_current_wt_dangerous}
  In new wt:        {s.implement_new_wt}
    (dangerously):  {s.implement_new_wt_dangerous}

Checkout PR #{pr_number}:
  In current wt:  {s.checkout}
  In new wt:      {s.checkout_new_slot}

Dispatch PR #{pr_number}:
  CLI command:    {s.dispatch}
  Slash command:  {s.dispatch_slash_command}"""


def format_next_steps_markdown(pr_number: int, *, url: str) -> str:
    """Format for PR body (markdown)."""
    s = PrNextSteps(pr_number=pr_number, url=url)
    return f"""## Execution Commands

**Dispatch to Erk Queue:**
```bash
{s.dispatch}
```

---

### Local Execution

**Checkout PR branch:**
```bash
{s.checkout}
```"""
