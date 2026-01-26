# Learn Plan: Issue #6082 - Capabilities Reorganization

**Issue:** #6082 - Reorganize Capabilities into Type-Based Folder Structure
**Commit:** 85acc329409ba8c01c3c12511bd0ee995f7cffbb
**Status:** ✓ Implementation Complete and Working
**Session:** 20d335df-58d1-458b-a371-80ce3f79bb96 (remote implementation)
**Raw Materials:** https://gist.github.com/schrockn/9a1f95e33389796d936a3284bdfcac9a

---

## Executive Summary

The capabilities reorganization was successfully implemented on 2026-01-26. The codebase now separates **capability infrastructure** (stable, in `core/capabilities/`) from **capability implementations** (frequently changing, in `capabilities/<type>/`). All 18 capabilities have been moved from consolidated files to a type-based folder structure with one capability per file. The registry is fully updated, all tests pass, and no breaking API changes were introduced.

**Key Achievement:** Clear separation of concerns enables better discoverability, easier extension, and improved maintainability as the capability system grows.

---

## What Was Built

### New Folder Structure

The reorganization created a type-based hierarchy:

```
src/erk/capabilities/                    # NEW: Implementation package root
├── skills/                             # Group 1: Skill capabilities (2 implementations)
│   ├── dignified_python.py
│   └── fake_driven_testing.py
├── reminders/                          # Group 2: Reminder capabilities (4 implementations)
│   ├── devrun.py
│   ├── dignified_python.py
│   ├── explore_docs.py
│   └── tripwires.py
├── reviews/                            # Group 3: Review capabilities (3 implementations)
│   ├── dignified_code_simplifier.py
│   ├── dignified_python.py
│   └── tripwires.py
├── workflows/                          # Group 4: Workflow capabilities (2 implementations)
│   ├── erk_impl.py
│   └── learn.py
├── agents/                             # Group 5: Agent capabilities (1 implementation)
│   └── devrun.py
├── code_reviews_system.py              # Standalone: Complex custom behavior
├── erk_bash_permissions.py             # Standalone: File permission management
├── hooks.py                            # Standalone: Hook configuration
├── learned_docs.py                     # Standalone: Documentation management
├── ruff_format.py                      # Standalone: Formatter integration
└── statusline.py                       # Standalone: User-level capability

src/erk/core/capabilities/              # UNCHANGED: Infrastructure layer
├── base.py                             # ABC and type definitions
├── registry.py                         # Capability factory (imports updated)
├── detection.py                        # Performance-critical helpers
├── skill_capability.py                 # Base class for skill pattern
├── reminder_capability.py              # Base class for reminder pattern
└── review_capability.py                # Base class for review pattern
```

### Files Changed

- **Added:** 18 new implementation files + 5 type package `__init__.py` files
- **Deleted:** 11 old consolidated/moved files from `core/capabilities/`
- **Modified:** 7 files (registry, tests, documentation)

### Capabilities Implemented

**18 Total Capabilities** organized by type:

1. **Skills (2):** DignifiedPythonCapability, FakeDrivenTestingCapability
2. **Reminders (4):** Devrun, DignifiedPython, ExploreDocs, Tripwires
3. **Reviews (3):** DignifiedCodeSimplifier, DignifiedPython, Tripwires
4. **Workflows (2):** ErkImpl, Learn
5. **Agents (1):** Devrun
6. **Standalones (6):** Hooks, StatusLine, LearnedDocs, CodeReviewsSystem, RuffFormat, ErkBashPermissions

---

## Code Patterns Documented

### Pattern 1: Template-Based Capabilities

Three design patterns use abstract base classes to minimize boilerplate:

**SkillCapability Pattern:**
```python
class DignifiedPythonCapability(SkillCapability):
    @property
    def skill_name(self) -> str:
        return "dignified-python"

    @property
    def description(self) -> str:
        return "Python coding standards (LBYL, modern types, ABCs)"
```
- Subclass implements only 2 properties
- Base class provides: install(), uninstall(), is_installed(), managed_artifacts, scope
- Used for: Skills (2 implementations in `capabilities/skills/`)

**ReminderCapability Pattern:**
```python
class DevrunReminderCapability(ReminderCapability):
    @property
    def reminder_name(self) -> str:
        return "devrun"

    @property
    def description(self) -> str:
        return "Remind agent to use devrun for CI tool commands"
```
- Manages state in `.erk/state.toml`
- Marked as optional (required=False)
- Used for: Reminders (4 implementations in `capabilities/reminders/`)

**ReviewCapability Pattern:**
```python
class DignifiedPythonReviewDefCapability(ReviewCapability):
    @property
    def review_name(self) -> str:
        return "dignified-python"

    @property
    def description(self) -> str:
        return "Dignified Python style code review"
```
- Installs `.claude/reviews/*.md` files
- Preflight checks for code-reviews-system dependency
- Used for: Reviews (3 implementations in `capabilities/reviews/`)

### Pattern 2: Standalone Complex Capabilities

Capabilities with unique behavior don't fit template patterns:

- **HooksCapability** - Manages Claude settings.json hooks configuration
- **StatuslineCapability** - User-level scope (installed in home directory)
- **LearnedDocsCapability** - Complex docs directory management
- **CodeReviewsSystemCapability** - GitHub Actions workflow infrastructure
- **RuffFormatCapability** - Development tool integration
- **ErkBashPermissionsCapability** - Bash script permission management

### Pattern 3: Registry as Single Source of Truth

```python
@cache
def _all_capabilities() -> tuple[Capability, ...]:
    return (
        LearnedDocsCapability(),
        DignifiedPythonCapability(),         # From skills/
        FakeDrivenTestingCapability(),       # From skills/
        # ... 16 more capabilities
        TripwiresReminderCapability(),       # From reminders/
    )
```

Key features:
- Explicit registration (no auto-discovery)
- `@cache` ensures O(1) lookups and single instance
- All capability queries route through: `get_capability()`, `list_capabilities()`, `is_capability_managed()`
- New capabilities added by: (1) Define file, (2) Import in registry, (3) Add to tuple

### Pattern 4: One File Per Capability

**Before:** Multiple capabilities in one file
```
src/erk/core/capabilities/skills.py
├── DignifiedPythonCapability
└── FakeDrivenTestingCapability
```

**After:** Individual files for each capability
```
src/erk/capabilities/skills/
├── dignified_python.py      → DignifiedPythonCapability
└── fake_driven_testing.py   → FakeDrivenTestingCapability
```

Benefits:
- **Discoverability:** File name matches capability name
- **Modularity:** Each file is small and focused
- **Growth:** Easy to add new capabilities (just create new file)
- **Dependencies:** Clear what each file imports/depends on

---

## Import Path Changes

### New Import Pattern

**Before:** Consolidated imports from core
```python
from erk.core.capabilities.skills import DignifiedPythonCapability
from erk.core.capabilities.reminders import DevrunReminderCapability
```

**After:** Type-specific imports
```python
from erk.capabilities.skills.dignified_python import DignifiedPythonCapability
from erk.capabilities.reminders.devrun import DevrunReminderCapability
```

**Pattern:** `from erk.capabilities.<type>.<name> import <ClassName>`

### Infrastructure Imports (Unchanged)

These remain in `core/` because they're stable infrastructure:
```python
from erk.core.capabilities.base import Capability, CapabilityResult
from erk.core.capabilities.registry import get_capability, list_capabilities
from erk.core.capabilities.skill_capability import SkillCapability
from erk.core.capabilities.reminder_capability import ReminderCapability
```

### Registry Updates (20 lines changed)

- `src/erk/core/capabilities/registry.py:5-24` - Import all 18 capabilities from new locations
- `src/erk/artifacts/sync.py` - HooksCapability import updated
- `tests/unit/core/test_capabilities.py` - All 18 imports updated

---

## Architectural Improvements

### 1. Clear Separation of Concerns

| Layer | Location | Purpose | Stability |
|-------|----------|---------|-----------|
| **Infrastructure** | `core/capabilities/` | Base classes, registry, detection | Stable (core team) |
| **Templates** | `core/capabilities/<type>_capability.py` | Pattern base classes | Stable (core team) |
| **Implementations** | `capabilities/<type>/<name>.py` | Concrete capabilities | Frequently changing (open for extension) |

### 2. Better Discoverability

Users can now:
- Find all skill capabilities in `capabilities/skills/`
- Add new reminders by creating file in `capabilities/reminders/`
- Understand capability type by folder location
- Prevent "junk drawer" effect in core/capabilities/

### 3. Reduced Core Complexity

- Removed 12 implementation files from `core/capabilities/`
- Core now contains only infrastructure: base classes, registry, detection
- Implementations in separate, organized package

### 4. Improved Extensibility

**Old approach:** To add capability, modify core/capabilities/reminders.py
**New approach:** Create new file `capabilities/reminders/my_reminder.py` + register in registry

Enables adding new capability types without modifying core infrastructure.

---

## Documentation Gaps Identified

### CRITICAL Gaps (Block New Contributors)

**1. Missing: Folder Organization/Structure Documentation**
- **Problem:** Docs explain HOW to add capabilities, but not WHERE or WHY
- **Impact:** New contributors confused about folder placement decisions
- **Solution:** Create `docs/learned/capabilities/folder-structure.md`
  - Explain type-based organization (skills/, reminders/, etc.)
  - Document decision criteria (when to use folders vs root-level)
  - Show directory tree with examples
  - Rationale: "2+ implementations → folder, 1 implementation → root-level"

**2. Missing: Type-Specific Capability Guides**
- **Problem:** Only reminder capability documented; other types unclear
- **Impact:** Contributors don't know how to add skills, workflows, agents, reviews
- **Solution:** Create type-specific guides:
  - `docs/learned/capabilities/adding-skills.md` - Skill pattern guide
  - `docs/learned/capabilities/adding-workflows.md` - Workflow pattern guide
  - `docs/learned/capabilities/adding-reviews.md` - Review pattern guide
  - `docs/learned/capabilities/adding-agents.md` - Agent pattern guide

**3. Missing: Migration/Planning Guide**
- **Problem:** Projects depending on erk have old import paths
- **Impact:** External users may break or have confusion
- **Solution:** Create `docs/learned/planning/capability-reorganization.md`
  - What changed and why
  - Before/after import paths
  - How the change affects downstream projects

### MODERATE Gaps (Improve Discoverability)

**4. Missing: Folder Placement Decision Criteria**
- Add explicit rules: when to use type folders vs root-level
- Include in folder-structure.md

**5. Minor: Update adding-new-capabilities.md**
- Fix line 76: Old reference "(`reminders.py` for reminders)" → "(`reminders/` for reminders)"
- This line is outdated but not contradictory

**6. Missing: Future Extensibility Guide**
- How to add NEW capability types beyond current 6
- Create `docs/learned/capabilities/adding-capability-types.md`
- Document: create base class → create type folder → register

---

## Related Documentation

### Existing Documentation (Already Complete)

| Document | Status | Notes |
|----------|--------|-------|
| `docs/learned/capabilities/adding-new-capabilities.md` | ✓ Updated | Reminder example updated to new import paths |
| `docs/learned/architecture/capability-system.md` | ✓ Complete | System architecture still valid |
| `docs/learned/architecture/workflow-capability-pattern.md` | ✓ Complete | Pattern guide still valid |

### New Documentation Needed (Priority Order)

1. **Immediate (HIGH):** Folder organization guide
2. **Immediate (HIGH):** Type-specific capability guides
3. **Soon (MEDIUM):** Migration/impact guide
4. **Soon (MEDIUM):** Future extensibility guide
5. **Nice-to-have (LOW):** Architecture benefits explanation

---

## Tripwire Candidates

One existing tripwire needs minor updating:

**Tripwire:** "Before using `is_reminder_installed()` in hook check"
- **Location:** `docs/learned/tripwires.md`
- **Current:** "Capability class MUST be defined in reminders.py"
- **New:** "Capability class MUST be defined in reminders/ folder"
- **Still Valid:** "AND registered in registry.py @cache tuple"

This tripwire is still fully applicable; only the file path reference needs updating from "reminders.py" to "reminders/".

---

## Risk Assessment

**Overall Risk:** LOW

- All changes are internal reorganization (no API changes)
- Tests fully cover new structure (1,692 test lines)
- No breaking changes for external consumers
- Registry provides stable interface
- Implementation uses consistent patterns

**Backwards Compatibility:** MAINTAINED
- Registry functions unchanged
- Capability behavior unchanged
- Only import paths changed (handled centrally in registry)

---

## Testing Status

- ✓ 1,692 test lines covering registry and capabilities
- ✓ All capability contracts tested
- ✓ All imports updated and passing
- ✓ No functionality changes, only reorganization

---

## Files with New Patterns Documented

| File | Pattern | Worth Documenting |
|------|---------|-------------------|
| `src/erk/capabilities/skills/dignified_python.py` | Minimal SkillCapability subclass | Yes - template pattern |
| `src/erk/capabilities/reminders/devrun.py` | Minimal ReminderCapability subclass | Yes - template pattern |
| `src/erk/capabilities/reviews/dignified_python.py` | Minimal ReviewCapability subclass | Yes - template pattern |
| `src/erk/capabilities/workflows/learn.py` | Custom Capability implementation | Yes - artifact installation pattern |
| `src/erk/capabilities/hooks.py` | Complex standalone capability | Yes - unique behavior pattern |
| `src/erk/core/capabilities/registry.py` | Registry factory with @cache | Yes - single source of truth pattern |

---

## Implementation Notes

### What Went Well

1. **Clean separation:** Infrastructure clearly separate from implementations
2. **Systematic approach:** Type-based organization is consistent and predictable
3. **Zero API breakage:** Registry provides stable interface; only internal locations changed
4. **Scalability:** Structure enables adding new capability types without core changes

### Design Decisions with Rationale

1. **New package at `erk.capabilities`** (not `erk.core.capabilities`)
   - Signals implementation layer, not infrastructure
   - Clear distinction from core infrastructure

2. **Type-based folder structure**
   - Organizes 18 capabilities for discoverability
   - Enables future growth without cluttering core

3. **Explicit registry** (not auto-discovery)
   - Single source of truth
   - Easier debugging
   - Better control over initialization order

4. **One file per capability**
   - Reduces cognitive load per file
   - Makes file-to-capability mapping obvious
   - Simpler to add/remove capabilities

---

## Conclusion

The capabilities reorganization successfully separates stable infrastructure from growing implementations. The codebase is now positioned for:

- **Better maintainability:** Clear separation of concerns
- **Easier extension:** Type-based organization makes adding capabilities obvious
- **Improved discoverability:** File structure reflects capability taxonomy
- **Future growth:** New capability types can be added without core changes

**Main deliverable:** Production-ready code with comprehensive test coverage.

**Remaining work:** Documentation improvements to help future contributors understand and extend the new structure.

---

## Documentation Recommendations Summary

### To Create (Priority)

| Priority | Document | Purpose |
|----------|----------|---------|
| HIGH | `docs/learned/capabilities/folder-structure.md` | Explain type-based organization |
| HIGH | `docs/learned/capabilities/adding-skills.md` | Skill-specific guide |
| HIGH | `docs/learned/capabilities/adding-workflows.md` | Workflow-specific guide |
| HIGH | `docs/learned/capabilities/adding-reviews.md` | Review-specific guide |
| MEDIUM | `docs/learned/planning/capability-reorganization.md` | Migration guide |
| MEDIUM | `docs/learned/capabilities/adding-capability-types.md` | Future extensibility |

### To Update (Priority)

| Document | Change | Severity |
|----------|--------|----------|
| `docs/learned/capabilities/adding-new-capabilities.md` | Line 76: "reminders.py" → "reminders/" | Low |
| `docs/learned/tripwires.md` | "reminders.py" → "reminders/" | Low |

**Total documentation items:** 8 new/updates needed for complete coverage