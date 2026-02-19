# Plan: Update CHANGELOG.md Unreleased Section

## Context

38 commits have landed on master since the last CHANGELOG sync (as-of: `8442713b3`). This update brings the Unreleased section current through `f24b02de7`. The provided issue plan covers most entries but is missing several user-facing changes.

## Changes to CHANGELOG.md

**File:** `CHANGELOG.md`

### 1. Update the as-of marker (line 10)

```
<!-- as-of: 8442713b3 -->
```

→

```
<!-- as-of: f24b02de7 -->
```

### 2. Prepend new entries above existing entries in each category

**Major Changes** (prepend above line 14):

- Add draft PR plan backend: plans can now be stored as GitHub draft PRs instead of issues, with all workflows (plan-save, plan-implement, learn, CI) supporting both backends via environment-driven configuration (3351bd7, 2cba6a73, 8559caff, a76cab09, 60787e1f, 2d1a14ec, 7a5fde04, 0b41c581, 2db84a17, 24e699cf, f2654e91, 909d81ca, ca311d22, be00080c, b796427, fe30038, c814624, d9fdb99, b37158fd, 68410fd)
- Add objective dependency graph with `depends_on` support: roadmaps support explicit cross-phase dependencies, with a new "deps" column in Objectives dashboard and `--all-unblocked` dispatch for parallel node implementation (97e480be, aa36c19d, f9dde530, 1030f07f, 8ece7717)

**Added** (prepend above line 18):

- Add objective tracking to TUI land flow and plan detail screen (3634d19b)
- Add "codespace run objective plan" to objectives command palette in TUI (a0e73050)

**Changed** (prepend above line 25):

- Convert "Submit to Queue" and "Land PR" from modal dialogs to non-blocking toast pattern (5d185bcb, 873dc04b)
- Show real-time progress in TUI status bar during "Land PR" operation with diagnostic error messages (2cffffcb)
- Batch objective node updates into single atomic write for reliability (f24b02de)

**Fixed** (prepend above line 32):

- Fix submit pipeline error handling and add network timeout protection (406cb1ec)
- Fix misleading "PR rewritten" success message in `erk pr rewrite` (d13c56fa)
- Fix `erk prepare` to handle pre-existing branches with draft PR plan backend (ca311d22)

### 3. Commits intentionally omitted (internal/refactoring)

These are not user-facing and don't warrant changelog entries:

- b1a6bd13 Move inline imports to top-level (code cleanup)
- e80ddc0e Add regeneration instructions to reference.md (internal docs)
- 524c5f9a Remove plan title update method, refactor exec scripts (internal refactoring)
- 4228c098 Hoist objective update out of land-execute (internal refactoring)
- a7df4dad Update CHANGELOG.md (meta)

## Verification

- Read the updated CHANGELOG.md to confirm formatting matches existing entry style
- Confirm as-of marker points to `f24b02de7`
- Confirm no existing entries were modified or removed
- Confirm new entries are prepended above (not below) existing entries in each category
