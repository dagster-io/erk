# Add "No Import Aliases" Rule to Dignified Python

## Change

Add a new rule to the **Import Organization** section of `.claude/skills/dignified-python/dignified-python-core.md` prohibiting import aliases (`import X as Y` / `from mod import X as Y`) unless there is an explicit, justified reason.

## File to Modify

- `.claude/skills/dignified-python/dignified-python-core.md` — Insert new subsection after the existing inline import rule, within the Import Organization section (around line 179).

## Rule Content

Add a "No Import Aliases" rule with:
- Statement: imports must use canonical names; `as` aliasing is prohibited by default
- Rationale: aliases obscure the canonical name, make grep-based discovery harder, and invite cargo-culting
- The only acceptable exceptions: resolving genuine name collisions between two different modules
- Example of wrong pattern: `from erk.helpers import require_issues as require_github_issues`
- Example of correct pattern: `from erk.helpers import require_issues`

## Note on Existing Re-Export Rule

The core doc already has a "No Re-Exports" section that mentions `import X as X` for plugin entry points. The new rule is complementary — re-exports use `as` for a different purpose (explicit re-export syntax). The new rule targets gratuitous renaming aliases.

## Verification

- Read the modified file to confirm the rule is clear and properly placed
- Grep the codebase for `as ` in import lines to see if there are other violations worth noting (informational only)