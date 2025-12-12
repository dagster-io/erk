**Next steps:**

View the plan:
gh issue view [issue_number] --web

Implement the plan:
erk implement [issue_number]

Implement and auto-submit PR (dangerous mode):
erk implement [issue_number] --dangerous

    Note: Calls Claude with --dangerously-skip-permissions to skip permission prompts.

Full automation mode (yolo - DANGEROUS):
erk implement [issue_number] --yolo

    ⚠️  WARNING: This is dangerous mode. Equivalent to --dangerous --submit --no-interactive.
    Automatically implements the plan, runs CI, and submits the PR without any prompts.

[OPTIONAL_COMMANDS]
