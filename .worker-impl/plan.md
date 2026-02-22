_One-shot: plan content will be populated by one-shot workflow._

**Prompt:** For both erk down and erk up commands, add a -d alias for the --delete-current option.

This means:
- erk down -d should work as an alias for erk down --delete-current
- erk up -d should work as an alias for erk up --delete-current

Make this change in both the erk down and erk up Click command definitions.
