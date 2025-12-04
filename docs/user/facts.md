# Erk Facts

Scratchpad for facts to be organized into proper documentation later.

---

## Branch Naming Convention

**Format:** `PPPP-DESC-MM-DD-HHMM`

**Example:** `1904-gt-pr-prep-prepare-branch-12-02-0106`

**Components:**

- `PPPP` - Plan/issue number for quick reference
- `DESC` - Shorthand description so you don't have to memorize numbers
- `MM-DD-HHMM` - Timestamp for uniqueness on each queue submission

**Rationale:**

- Minute-level granularity is sufficient; collisions are rare in practice
- If collision occurs, a number suffix is added automatically

---

## GitHub Planning Feature Flag

**Config key:** `github_planning`

**Default:** `true` (enabled)

**Toggle:**

```bash
erk config set github_planning false  # disable
erk config set github_planning true   # enable
```

**What it controls:**

When enabled, erk modifies Claude Code's plan mode behavior:

- Injects session IDs into prompts for tracking
- Prompts to save plans to GitHub issues when exiting plan mode

When disabled, plan mode behaves normally without erk's GitHub integration hooks. Use this if you want standard Claude Code plan mode without the GitHub workflow.
