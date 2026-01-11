# Plan: Add Capability System Documentation

## Objective

Add implementation-focused documentation for capability patterns discovered in the shell-integration session. The existing `capability-system.md` provides API reference but lacks concrete implementation patterns.

## Source Information

- Sessions analyzed: `fafcc5c5`, `5128cd7a` (shell-integration implementation)
- Raw materials: https://gist.github.com/schrockn/c9a1beb1e90a9ed091beb50622b372fc

## Documentation Items

### 1. Create `docs/learned/architecture/capability-patterns.md` (Category B - Teaching Gap)

**Priority**: High - fills the main gap between API reference and real implementations

**Content outline**:

1. **Quick Decision Tree**: Which capability type to create?
   - Skill-based → use `SkillCapability` base class
   - User-level settings → inject gateways for testability
   - Project artifacts → define in `artifacts` property

2. **SkillCapability Pattern** (from `skills.py`)
   - Minimal implementation: just `skill_name` + `description`
   - Example: `DignifiedPythonCapability`

3. **User-Level Capability Pattern** (from `shell_integration.py`, `statusline.py`)
   - Scope = "user", operates outside repo
   - Gateway injection for testability (Shell, Console, ClaudeInstallation)
   - Pattern: `shell=None` in constructor means "use real in production"

4. **Settings Modification Pattern** (from `hooks.py`, `statusline.py`)
   - Read → validate → modify → write
   - Handle shared files (multiple capabilities may modify same file)

5. **Dependency Injection for Testing**
   - Constructor takes optional gateway parameters
   - Default to real implementations when None
   - Enables FakeShell/FakeConsole in tests

### 2. Update `docs/learned/index.md` (Category B)

**Priority**: Medium - routing entry for new doc

Add entry under architecture section:
```
- `architecture/capability-patterns.md` - Read when: creating new capabilities, need implementation examples beyond API reference
```

### 3. Update `docs/learned/glossary.md` (Category B)

**Priority**: Low - clarify existing entry

Update "Capability" glossary entry to distinguish:
- Capability (the system) vs Capability Marker (the feature flag)

## Files to Modify

| File | Action |
|------|--------|
| `docs/learned/architecture/capability-patterns.md` | Create |
| `docs/learned/index.md` | Update routing table |
| `docs/learned/glossary.md` | Update capability entry |

## Reference Files (read for content)

- `src/erk/core/capabilities/base.py` - ABC definition
- `src/erk/core/capabilities/skills.py` - SkillCapability base class
- `src/erk/core/capabilities/shell_integration.py` - User-level example with gateway injection
- `src/erk/core/capabilities/statusline.py` - User-level settings modification
- `tests/unit/core/test_capabilities.py` - Testing patterns with fakes

## Verification

1. Run `erk docs validate` to ensure frontmatter is valid
2. Check that new doc appears in index with correct routing
3. Verify no broken links with `make md-check`