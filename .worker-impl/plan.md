# Extraction Plan: Workflow Config File Loading

## Objective

Document the workflow configuration file pattern for repo-scoped dispatch-time configuration.

## Source Information

- **Implementation Session**: 3a63c598-dda0-4487-b0af-3fcdecabcde3
- **Plan Issue**: #2741

## Documentation Items

### Item 1: Glossary Entry for Workflow Config

**Type**: Category B (Teaching Gap)
**Location**: docs/agent/glossary.md
**Action**: Add entry
**Priority**: Low

**Content**:

```markdown
### workflow config

A TOML configuration file at `.erk/workflows/<workflow-name>.toml` that provides repo-specific parameters passed to GitHub Actions workflows at dispatch time. The filename matches the workflow file (without `.yml` extension). All values are converted to strings before being passed as workflow inputs.

Example: `.erk/workflows/dispatch-erk-queue-git.toml`

```toml
kit_names = "erk,gt,devrun"
model_name = "claude-sonnet-4-5-20250929"
package_install_script = ""
```

See also: [queue-setup](/docs/user/queue-setup.md#workflow-configuration)
```

### Item 2: Reference in erk skill

**Type**: Category B (Teaching Gap)
**Location**: .claude/skills/erk/erk.md (or routing)
**Action**: Consider adding reference
**Priority**: Low

**Content**: The erk skill could reference workflow config as part of the `erk submit` workflow, noting that repos can customize dispatch inputs via `.erk/workflows/` TOML files.

## Notes

This was a straightforward feature implementation. The main user-facing documentation was added directly to `docs/user/queue-setup.md` as part of the implementation. The extraction items above are minor additions for completeness.