"""Issue and planned PR next steps formatting - single source of truth."""

from dataclasses import dataclass


@dataclass(frozen=True)
class IssueNextSteps:
    """Canonical commands for issue operations."""

    plan_number: int
    url: str

    @property
    def view(self) -> str:
        return self.url

    @property
    def checkout(self) -> str:
        return f"erk br co --for-plan {self.plan_number}"

    @property
    def dispatch(self) -> str:
        return f"erk pr dispatch {self.plan_number}"

    @property
    def checkout_new_slot(self) -> str:
        return f"erk br co --new-slot --for-plan {self.plan_number}"

    @property
    def implement_new_br(self) -> str:
        return f'source "$(erk br co --for-plan {self.plan_number} --script)" && erk implement'

    @property
    def implement_new_br_dangerous(self) -> str:
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


@dataclass(frozen=True)
class PlannedPRNextSteps:
    """Canonical commands for planned PR operations."""

    pr_number: int
    branch_name: str
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
    def implement_new_br(self) -> str:
        return f'source "$(erk br co --for-plan {self.pr_number} --script)" && erk implement'

    @property
    def implement_new_br_dangerous(self) -> str:
        return f'source "$(erk br co --for-plan {self.pr_number} --script)" && erk implement -d'

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


# Slash commands (static, don't need issue number)
DISPATCH_SLASH_COMMAND = "/erk:pr-dispatch"
CHECKOUT_SLASH_COMMAND = "/erk:prepare"


def format_next_steps_plain(plan_number: int, *, url: str) -> str:
    """Format for CLI output (plain text)."""
    s = IssueNextSteps(plan_number, url=url)
    return f"""Implement plan #{plan_number}:
  In new br:        {s.implement_new_br}
    (dangerously):  {s.implement_new_br_dangerous}
  In new wt:        {s.implement_new_wt}
    (dangerously):  {s.implement_new_wt_dangerous}

Checkout plan #{plan_number}:
  In new br:  {s.checkout}
  In new wt:  {s.checkout_new_slot}

Dispatch to queue: {s.dispatch}"""


def format_planned_pr_next_steps_plain(pr_number: int, *, branch_name: str, url: str) -> str:
    """Format for CLI output (plain text) for planned PR plans."""
    s = PlannedPRNextSteps(pr_number=pr_number, branch_name=branch_name, url=url)
    return f"""Implement plan #{pr_number}:
  In new br:        {s.implement_new_br}
    (dangerously):  {s.implement_new_br_dangerous}
  In new wt:        {s.implement_new_wt}
    (dangerously):  {s.implement_new_wt_dangerous}

Checkout plan #{pr_number}:
  In new br:  {s.checkout}
  In new wt:  {s.checkout_new_slot}

Dispatch to queue: {s.dispatch}"""


def format_next_steps_markdown(plan_number: int, *, url: str) -> str:
    """Format for issue body (markdown)."""
    s = IssueNextSteps(plan_number, url=url)
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
