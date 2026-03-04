"""Plan next steps formatting - single source of truth."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanNextSteps:
    """Canonical commands for plan operations."""

    plan_number: int
    url: str

    @property
    def view(self) -> str:
        return self.url

    @property
    def dispatch(self) -> str:
        return f"erk pr dispatch {self.plan_number}"

    @property
    def checkout(self) -> str:
        return f"erk br co --for-plan {self.plan_number}"

    @property
    def checkout_new_slot(self) -> str:
        return f"erk br co --new-slot --for-plan {self.plan_number}"

    @property
    def dispatch_slash_command(self) -> str:
        return f"/erk:pr-dispatch {self.plan_number}"

    @property
    def implement_current_wt(self) -> str:
        return f'source "$(erk br co --for-plan {self.plan_number} --script)" && erk implement'

    @property
    def implement_current_wt_dangerous(self) -> str:
        return f'source "$(erk br co --for-plan {self.plan_number} --script)" && erk implement -d'

    @property
    def implement_new_wt(self) -> str:
        return (
            f'source "$(erk br co --new-slot --for-plan {self.plan_number} --script)"'
            " && erk implement"
        )

    @property
    def implement_new_wt_dangerous(self) -> str:
        return (
            f'source "$(erk br co --new-slot --for-plan {self.plan_number} --script)"'
            " && erk implement -d"
        )


# Slash commands (static, don't need plan number)
DISPATCH_SLASH_COMMAND = "/erk:pr-dispatch"
CHECKOUT_SLASH_COMMAND = "/erk:prepare"


def format_plan_next_steps_plain(plan_number: int, *, url: str) -> str:
    """Format for CLI output (plain text)."""
    s = PlanNextSteps(plan_number=plan_number, url=url)
    return f"""Implement plan #{plan_number}:
  In current wt:    {s.implement_current_wt}
    (dangerously):  {s.implement_current_wt_dangerous}
  In new wt:        {s.implement_new_wt}
    (dangerously):  {s.implement_new_wt_dangerous}

Checkout plan #{plan_number}:
  In current wt:  {s.checkout}
  In new wt:      {s.checkout_new_slot}

Dispatch plan #{plan_number}:
  CLI command:    {s.dispatch}
  Slash command:  {s.dispatch_slash_command}"""


def format_next_steps_markdown(plan_number: int, *, url: str) -> str:
    """Format for PR body (markdown)."""
    s = PlanNextSteps(plan_number=plan_number, url=url)
    return f"""## Execution Commands

**Dispatch to Erk Queue:**
```bash
{s.dispatch}
```

---

### Local Execution

**Checkout plan branch:**
```bash
{s.checkout}
```"""
