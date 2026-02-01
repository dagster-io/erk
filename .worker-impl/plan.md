# Plan: Replace Verbatim Source Code in Documentation with Source Pointers

## Problem

Documentation in `docs/learned/` contains verbatim copies of source code that will go stale when the source changes. These should be replaced with pointers to the canonical source files.

## Quantitative Audit Summary

- 303 files in `docs/learned/` contain code blocks
- Filtered by signals: `from erk` imports, `class`/`def` definitions, >40% code density
- **11 files flagged as worst offenders** (erk-imports + many defs + code-heavy)
- Deep inspection revealed a spectrum: some are truly verbatim, others are pedagogical patterns

## Classification

After deep inspection, files fall into three categories:

### Category A: Genuine Verbatim Copies (replace with pointers)

Code blocks that are direct copies of actual source, will go stale.

| File | What's copied | Source location |
|------|--------------|-----------------|
| `architecture/erk-architecture.md` | RealTime/FakeTime classes, ErkDashApp exit pattern, BranchManager properties | `gateway/time/{real,fake}.py`, `tui/app.py`, `gateway/branch_manager/abc.py` |
| `testing/testing.md` | FakeGit constructor, FakeGitHub dual-mapping, FakeShell, FakeGraphite constructors | `gateway/git/fake.py`, `gateway/github/fake.py`, `gateway/graphite/fake.py` |
| `architecture/discriminated-union-error-handling.md` | MergeResult/MergeError types, WorktreeAdded/WorktreeAddError, BranchCreated/BranchCreateError, PushResult/PushError | `gateway/github/types.py`, `gateway/git/worktree/types.py`, `gateway/git/branch_ops/types.py`, `gateway/git/remote_ops/types.py` |
| `testing/cli-testing.md` | `ErkContext.for_test()` full API signature (lines 59-82) | `erk_shared/context/context.py:193` |
| `architecture/claude-cli-progress.md` | `CommitMessageGenerator.generate()` method (~33 lines) | `src/erk/core/commit_message_generator.py:85-189` |
| `textual/widget-development.md` | `CommandOutputPanel` class | `src/erk/tui/widgets/command_output.py` |
| `testing/rebase-conflicts.md` | `erk_isolated_fs_env` context manager, `isolated_filesystem` pattern | `tests/test_utils/env_helpers.py:610-667` |
| `testing/exec-script-testing.md` | `build_docker_run_args` test, FakeBranchManager usage | `src/erk/cli/commands/docker_executor.py`, `gateway/branch_manager/fake.py` |

### Category B: Pedagogical Patterns (leave as-is)

Code that illustrates concepts using made-up examples (MyGateway, GtKit Protocol, GeneratedPlan). These don't correspond to real source files and serve a teaching purpose.

Files: `architecture/protocol-vs-abc.md`, `architecture/gateway-abc-implementation.md` (mostly patterns), `cli/dependency-injection-patterns.md` (mostly patterns), `planning/lifecycle.md` (YAML specs), `tui/command-palette.md` (Textual patterns), `architecture/commandresult-extension-pattern.md` (templates)

### Category C: Mixed (trim verbatim parts, keep patterns)

Files with both real source copies AND pedagogical patterns. Trim the verbatim parts, keep the patterns.

Files: `architecture/gateway-abc-implementation.md`, `hooks/erk.md`, `cli/dependency-injection-patterns.md`

## Approach

For each Category A block, replace the verbatim code with:

```markdown
<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/fake.py:60-100 -->
See `FakeGit` constructor in `packages/erk-shared/src/erk_shared/gateway/git/fake.py`.
```

**Rules:**
- Keep 1-3 line snippets showing the key insight (e.g., a method signature) if it aids readability
- Replace full class/method bodies (>5 lines of real source) with a pointer
- Use format: `See ClassName.method_name() in path/to/file.py:LINE`
- Add HTML comment with source path for agent discoverability
- Preserve any prose around the code block explaining the concept

## Execution Order

### Pass 1: Worst Offenders (8 files)

Process in order of severity (most code lines first):

1. **`architecture/erk-architecture.md`** (436 code lines, 28 defs)
   - Replace: RealTime/FakeTime, ErkDashApp, BranchManager verbatim blocks
   - Keep: MyGateway exemplar patterns (pedagogical)

2. **`testing/testing.md`** (419 code lines, 13 defs)
   - Replace: FakeGit, FakeGitHub, FakeShell, FakeGraphite constructor copies
   - Keep: Error injection pattern examples (pedagogical)

3. **`architecture/discriminated-union-error-handling.md`** (401 code lines, 25 defs)
   - Replace: All real type definitions (MergeResult, WorktreeAdded, BranchCreated, PushResult, LandError)
   - Keep: Exec command template pattern (pedagogical skeleton)

4. **`testing/cli-testing.md`** (315 code lines, 15 defs)
   - Replace: `for_test()` full API signature
   - Keep: Pattern examples using fakes

5. **`testing/rebase-conflicts.md`** (262 code lines)
   - Replace: `erk_isolated_fs_env` verbatim copy
   - Keep: Old vs new API comparison (migration guidance)

6. **`testing/exec-script-testing.md`** (176 code lines, 15 defs)
   - Replace: `build_docker_run_args` test body, full test methods
   - Keep: Short pattern snippets

7. **`architecture/claude-cli-progress.md`** (141 code lines)
   - Replace: `CommitMessageGenerator.generate()` full method body

8. **`textual/widget-development.md`** (146 code lines)
   - Replace: `CommandOutputPanel` class copy

### Pass 2: Long Tail (3 files with mixed content)

9. **`architecture/gateway-abc-implementation.md`** - Trim verbatim worktree/GitHub composition blocks, keep pattern templates
10. **`hooks/erk.md`** - Add source pointers for `@project_scoped` and `is_in_managed_project()` API references
11. **`cli/dependency-injection-patterns.md`** - Fix stale reference to non-existent `ci_verify_autofix.py`, replace with real example or remove

## Verification

- After each file edit, confirm the doc still reads coherently (no dangling references)
- Verify that every source pointer path actually exists in the repo (`Glob` check)
- Run `make docs-check` or equivalent if available to verify doc integrity
- Spot-check 2-3 replaced blocks by reading the pointed-to source file to confirm the pointer is accurate