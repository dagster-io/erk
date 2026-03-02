# Make Python version configurable in erk-remote-setup action

## Context

The `erk-remote-setup` GitHub Action hardcodes `python-version: "3.13"` when calling `astral-sh/setup-uv@v5`. This fails when the action runs in repos with stricter Python constraints (e.g., the `internal` monorepo requires `<3.13`). The version needs to be configurable so each workflow/repo can specify what works for its dependency graph.

## Change

**File:** `.github/actions/erk-remote-setup/action.yml`

1. Add a `python-version` input with default `"3.12"`:
   ```yaml
   python-version:
     description: "Python version for uv"
     required: false
     default: "3.12"
   ```

2. Reference the input in the setup-uv step:
   ```yaml
   - uses: astral-sh/setup-uv@v5
     with:
       python-version: ${{ inputs.python-version }}
   ```

No workflow file changes needed — all 6 callers (one-shot, pr-rewrite, plan-implement, pr-rebase, pr-address, learn) will pick up the default `3.12` automatically. Any caller can override by passing `python-version: "3.11"` etc.

## Verification

Re-run any workflow that uses this action and confirm the `setup-uv` step resolves to Python 3.12 and succeeds.
