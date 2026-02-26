# Add .erk/impl-context/ to .gitignore

## Context
Commit d1ce4bfe0 added only `.erk/impl-context/plan-ref.json` to `.gitignore`, but the entire `.erk/impl-context/` directory should be ignored since it contains ephemeral local artifacts.

## Change
In `.gitignore`, replace `.erk/impl-context/plan-ref.json` with `.erk/impl-context/` to ignore the whole directory.

## Verification
Run `git status` to confirm no impl-context files show as tracked/untracked.
