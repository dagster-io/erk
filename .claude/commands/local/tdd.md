---
description: Enforce test-driven development with fake-driven architecture. Write failing test first, then implement.
argument-hint: <feature-description>
---

# Test-Driven Development Command

You are a TDD enforcement agent. Your role is to ensure strict Red-Green-Refactor workflow discipline while leveraging erk's fake-driven testing architecture.

**Core Principle**: You MUST NOT write implementation code until you have a failing test that demonstrates the need for that code.

## Phase 1: LOAD - Load Required Skills

Load the testing and Python skills:

1. Load the `fake-driven-testing` skill
2. Load the `dignified-python` skill

## Phase 2: UNDERSTAND - Analyze the Feature Request

Before writing any code, analyze the feature: `$ARGUMENTS`

Determine:

1. **Test Layer**: Where does this test belong?
   - **Layer 3 (Pure Unit)**: Zero dependencies, testing pure functions/utilities
   - **Layer 4 (Business Logic)**: Uses Fake\* classes for external dependencies

2. **Test Location**: Based on what you're testing:
   - `tests/unit/` - Pure unit tests or business logic with fakes
   - `tests/commands/` - CLI command tests
   - `tests/services/` - Service layer tests

3. **Existing Fakes**: Check `tests/fakes/` for available Fake\* classes:
   - `FakeGit`, `FakeGitHub`, `FakeGraphite`
   - `FakeConsole`, `FakeClaudeCode`
   - Others as needed

4. **Gateway Impact**: Does this feature require a new gateway method?
   - If YES: You must follow the gateway checklist (5-file implementation)
   - If NO: Proceed with business logic testing

Report your analysis before proceeding.

## Phase 3: RED - Write Failing Test First

**GATE**: You cannot proceed to Phase 4 until this test EXISTS and FAILS.

Write the test:

1. Create the test file if it doesn't exist
2. Write a test that describes the expected behavior
3. Use existing Fake\* classes from `tests/fakes/`
4. Use `tmp_path` fixture for any file operations (NEVER hardcoded paths)
5. Follow naming convention: `test_<behavior>_<condition>()`

Run the test via devrun agent:

```
Run pytest <test_file>::<test_function> and report results
```

**Verify the test FAILS**:

- If it passes immediately, the test is not TDD - you're testing existing behavior
- If it fails with the expected error (e.g., AttributeError, ImportError, AssertionError), proceed
- Document the failure message

## Phase 4: GREEN - Minimal Implementation

**GATE**: Only enter this phase after Phase 3 shows a failing test.

Write the MINIMUM code to make the test pass:

1. No extra features
2. No optimization
3. No "while I'm here" changes
4. Just enough to satisfy the test

Run the test via devrun agent:

```
Run pytest <test_file>::<test_function> and report results
```

**Verify the test PASSES**:

- If it passes, proceed to Phase 5
- If it fails, fix ONLY what's needed to pass

## Phase 5: REFACTOR - Improve While Green

With a passing test, you may now refactor:

1. Extract helper functions if needed
2. Improve variable names
3. Remove duplication
4. Add type hints if missing

**After each change**, run the test via devrun:

```
Run pytest <test_file>::<test_function> and report results
```

**Tests MUST stay green**. If any test fails, revert the refactor.

## Phase 6: EXPAND - Add Edge Cases

For each additional case, repeat the RED-GREEN-REFACTOR cycle:

Consider:

- Error conditions (invalid input, missing data)
- Boundary values (empty lists, max values)
- Edge cases specific to the feature

For each case:

1. **RED**: Write failing test for the edge case
2. **GREEN**: Minimal implementation to pass
3. **REFACTOR**: Clean up while green

## Phase 7: VERIFY - Final Checks

Run full CI verification via devrun agent:

```
Run make fast-ci and report results
```

Confirm:

- All new tests pass
- No regressions in existing tests
- Linting and type checking pass

## Gateway Checklist (If Needed)

If Phase 2 determined a new gateway method is needed, you must complete this BEFORE writing business logic tests:

1. **ABC** (`src/erk_shared/<gateway>/abc.py`): Add abstract method
2. **Real** (`src/erk_shared/<gateway>/real.py`): Implement real behavior
3. **Fake** (`tests/fakes/<gateway>.py`): Implement fake behavior
4. **DryRun** (`src/erk_shared/<gateway>/dry_run.py`): Implement dry-run behavior
5. **Printing** (`src/erk_shared/<gateway>/printing.py`): Implement printing wrapper

After all 5 implementations exist, proceed with business logic testing.

## Enforcement Rules

1. **No implementation before failing test** - Phase 3 MUST complete before Phase 4
2. **Test must actually fail** - A passing test on first run is not TDD
3. **Use existing fakes** - Don't create ad-hoc mocks; use Fake\* classes
4. **Minimal implementation** - Write just enough to pass, no more
5. **Always run via devrun** - Never run pytest/make directly

## Begin Now

Start by loading the required skills (Phase 1), then analyze the feature request (Phase 2). Report your analysis before writing any code.
