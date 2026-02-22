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


def _format_slot_options(
    *,
    on_trunk: bool,
    prepare: str,
    prepare_and_implement: str,
    prepare_new_slot: str,
    prepare_new_slot_and_implement: str,
    submit: str,
) -> str:
    """Format slot options block with trunk-aware ordering."""
    if on_trunk:
        return f"""OR exit Claude Code first, then run one of:

  New slot (recommended — you're on trunk):
    Local: {prepare_new_slot}
    Implement: {prepare_new_slot_and_implement}

  Same slot:
    Local: {prepare}
    Implement: {prepare_and_implement}

  Submit to Queue: {submit}"""
    return f"""OR exit Claude Code first, then run one of:

  Same slot (recommended — you're in a slot):
    Local: {prepare}
    Implement: {prepare_and_implement}

  New slot:
    Local: {prepare_new_slot}
    Implement: {prepare_new_slot_and_implement}

  Submit to Queue: {submit}"""


def format_next_steps_plain(issue_number: int, *, on_trunk: bool) -> str:
    """Format for CLI output (plain text)."""
    s = IssueNextSteps(issue_number)
    slot_block = _format_slot_options(
        on_trunk=on_trunk,
        prepare=s.prepare,
        prepare_and_implement=s.prepare_and_implement,
        prepare_new_slot=s.prepare_new_slot,
        prepare_new_slot_and_implement=s.prepare_new_slot_and_implement,
        submit=s.submit,
    )
    return f"""Next steps:

View Issue: {s.view}

In Claude Code:
  Submit to queue: {SUBMIT_SLASH_COMMAND}

{slot_block}"""


def format_draft_pr_next_steps_plain(pr_number: int, *, branch_name: str, on_trunk: bool) -> str:
    """Format for CLI output (plain text) for draft PR plans."""
    s = DraftPRNextSteps(pr_number=pr_number, branch_name=branch_name)
    slot_block = _format_slot_options(
        on_trunk=on_trunk,
        prepare=s.prepare,
        prepare_and_implement=s.prepare_and_implement,
        prepare_new_slot=s.prepare_new_slot,
        prepare_new_slot_and_implement=s.prepare_new_slot_and_implement,
        submit=s.submit,
    )
    return f"""Next steps:

View PR: {s.view}

In Claude Code:
  Submit to queue: {SUBMIT_SLASH_COMMAND}

{slot_block}"""


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
