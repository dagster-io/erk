# Learn Plan: [Issue #6387] - Fix PR Comment Formatting in Conflict Workflow

## Summary

This learn plan captures documentation opportunities from implementing a fix for GitHub Actions PR comment formatting in the `pr-fix-conflicts.yml` workflow. The implementation addressed two related failures: escape sequences appearing literally in PR comments (malformed formatting), and an "Argument list too long" error when rebase output exceeded Linux kernel ARG_MAX limits (~2MB).

Three implementation sessions contributed insights: session e5da072c demonstrated clean implementation following a pre-written plan, session f871bb54 confirmed the pattern with minimal scope, and session 5d99bc36 discovered effective debugging approaches when PR validation failed unexpectedly.

## What Was Built

**Problem**: The conflict resolution workflow posted PR comments using inline command substitution:

```yaml
gh pr comment "$PR_NUMBER" --body "$(echo -e "$BODY")"
```

This pattern failed in two ways:

1. **Escape sequence loss**: The `echo -e` in command substitution didn't properly interpret `\n` as newlines, resulting in literal `\n` appearing in PR comments
2. **ARG_MAX overflow**: Large rebase output caused "Argument list too long" errors when the command line exceeded ~2MB

**Solution**: Replace inline `--body` with temp file + `--body-file`:

```yaml
TEMP_FILE=$(mktemp)
printf "%b\n" "$BODY" > "$TEMP_FILE"
gh pr comment "$PR_NUMBER" --body-file "$TEMP_FILE"
rm "$TEMP_FILE"
```

This pattern: (1) uses `printf "%b"` for reliable escape sequence interpretation (POSIX standard), (2) avoids command line length limits via file I/O, and (3) properly cleans up temporary resources.

## Why Documentation Matters

This fix addresses a subtle interaction between shell behavior, Linux kernel limits, and GitHub CLI conventions. The pattern is non-obvious for several reasons:

1. **Silent degradation**: Without the fix, PR comments render with literal `\n` characters - a visually confusing failure that doesn't produce error messages
2. **Context-dependent**: GitHub Actions uses dash/sh (not bash), so `echo -e` behaves differently than expected
3. **System-level limits**: ARG_MAX is rarely encountered in normal development but triggers on large CI outputs
4. **Tool-specific knowledge**: The `--body-file` flag is not prominently documented compared to `--body`

Future agents editing GitHub Actions workflows that post PR comments need this documented pattern to avoid repeating the same debugging cycle.

## Documentation Items

### HIGH Priority

#### 1. GitHub CLI PR Comment Patterns

**Location**: `docs/learned/ci/github-cli-comment-patterns.md` (NEW)
**Action**: CREATE
**Sources**: [Impl e5da072c] [Impl f871bb54] [Impl 5d99bc36] [PR #6388]

**Read When**:

- Posting formatted PR comments from GitHub Actions workflows
- Debugging escape sequences in `gh pr comment` commands
- Encountering "Argument list too long" errors
- Writing GitHub Actions steps that use `gh pr` commands with multi-line content

**Topics to Cover**:

- Inline `--body` vs `--body-file` comparison and when to use each
- Why command substitution + echo -e fails (shell interpretation depth, escape sequence loss)
- The complete pattern: `mktemp` -> `printf "%b"` -> `--body-file` -> `rm`
- System ARG_MAX limits (~2MB on Linux) and why they matter
- POSIX portability: why `printf "%b"` is preferred over `echo -e`
- Real before/after example from `pr-fix-conflicts.yml`
- Cross-reference to existing `github-actions-output-patterns.md` for related heredoc patterns

---

#### 2. Shell Argument Limits (ARG_MAX) Tripwire

**Location**: `docs/learned/ci/tripwires.md` (UPDATE)
**Action**: UPDATE - Add tripwire entry
**Sources**: [Impl e5da072c] [Impl f871bb54] [PR #6388]

**Tripwire Entry**:

- **Trigger**: Writing GitHub Actions workflow steps that pass large content to `gh` CLI commands (e.g., `gh pr comment --body "$VAR"`)
- **Warning**: Use `--body-file` or other file-based input to avoid Linux ARG_MAX limit (~2MB on command-line arguments). Large CI outputs like rebase logs can exceed this limit.
- **Score**: 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)

---

#### 3. Printf vs Echo -e Escape Sequence Handling Tripwire

**Location**: `docs/learned/ci/tripwires.md` (UPDATE)
**Action**: UPDATE - Add tripwire entry
**Sources**: [Impl e5da072c] [Impl f871bb54] [PR #6388]

**Tripwire Entry**:

- **Trigger**: Using escape sequences like `\n` in GitHub Actions workflows
- **Warning**: Use `printf "%b"` instead of `echo -e` for reliable escape sequence handling. GitHub Actions uses dash/sh (POSIX standard), not bash, so `echo -e` behavior differs from local development.
- **Score**: 5/10 (Non-obvious +2, Cross-cutting +2, External tool quirk +1)

---

#### 4. Multi-line Output Handling Context Clarification

**Location**: `docs/learned/ci/github-actions-output-patterns.md` (UPDATE)
**Action**: UPDATE - Add clarifying cross-reference
**Sources**: [Gap Analysis - Contradiction Resolution]

**What to Add**:
A note clarifying that heredoc patterns in this document apply specifically to `$GITHUB_OUTPUT` workflow step outputs (data flowing between steps). For `gh pr comment` and other GitHub CLI external commands, use `--body-file` with `printf` instead. Include cross-reference to the new `github-cli-comment-patterns.md` document.

---

### MEDIUM Priority

#### 5. PR Checkout Footer Validation Pattern

**Location**: `docs/learned/cli/pr-commands.md` or `docs/learned/erk/pr-submission-patterns.md` (NEW)
**Action**: CREATE
**Sources**: [Impl 5d99bc36]

**Read When**:

- Adding checkout footers to PR bodies
- Implementing PR-related features that involve validation
- Debugging `erk pr check` failures

**Topics to Cover**:

- The `erk pr check` command validates exact patterns, not semantic equivalents
- The specific requirement: `erk pr checkout <number>` format
- Why `erk wt from-pr <number>` fails validation despite being semantically equivalent
- Reference to validation code in `erk_shared.gateway.pr.submit.has_checkout_footer_for_pr()`
- Pattern for investigating validation failures: error message -> grep -> read source

---

#### 6. PR Body Validation Workflow (Iterate-Until-Valid Pattern)

**Location**: `docs/learned/planning/pr-submission-patterns.md` (NEW)
**Action**: CREATE
**Sources**: [Impl 5d99bc36]

**Read When**:

- Updating PR bodies to satisfy validation requirements
- Implementing PR-related features
- Debugging validation failures

**Topics to Cover**:

- The iterate-until-valid workflow: update PR body -> run `erk pr check` -> read error -> investigate source -> fix -> re-validate
- When to read validation source code vs. guessing at fixes
- Example from session 5d99bc36: discovering `has_checkout_footer_for_pr()` pattern requirement
- Two-phase PR update strategy: (1) update body with required fields, (2) validate and iterate

---

#### 7. GitHub Actions GITHUB_TOKEN Limitations Tripwire

**Location**: `docs/learned/ci/tripwires.md` (UPDATE)
**Action**: UPDATE - Add tripwire entry
**Sources**: [Impl e5da072c]

**Tripwire Entry**:

- **Trigger**: GitHub Actions workflow needs to perform operations like gist creation, or session uploads fail in CI
- **Warning**: GitHub Actions GITHUB_TOKEN has restricted scope by default. Check token capabilities or use personal access token (PAT) for elevated permissions like gist creation.
- **Score**: 3/10 (Non-obvious +2, External tool quirk +1)

---

### LOW Priority

#### 8. Source Code Investigation Pattern for Debugging

**Location**: `docs/learned/planning/debugging-patterns.md` (NEW)
**Action**: CREATE
**Sources**: [Impl 5d99bc36]

**Read When**:

- Debugging validation failures
- Encountering errors with unclear root causes
- Deciding whether to guess at fixes or investigate source

**Topics to Cover**:

- The debugging approach: error message -> grep codebase -> read source file -> understand validation logic -> apply fix
- Example: PR validation investigation from session 5d99bc36
- Why this approach is superior to trial-and-error
- When to apply: validation failures, non-obvious error messages, pattern requirements

---

#### 9. Temporary File Lifecycle Pattern in Shell

**Location**: `docs/learned/architecture/subprocess-wrappers.md` (UPDATE)
**Action**: UPDATE - Add pattern reference
**Sources**: [Impl e5da072c] [PR #6388]

**What to Add**:
Document the standard Unix pattern for temp files in CI context:

1. Create: `TEMP_FILE=$(mktemp)`
2. Write: `printf "%b\n" "$VAR" > "$TEMP_FILE"`
3. Use: Pass filename as flag argument `--body-file "$TEMP_FILE"`
4. Cleanup: `rm "$TEMP_FILE"`

Reference the real example from `pr-fix-conflicts.yml` and note that this pattern is especially important in CI where large content is common.

---

#### 10. Worktree .impl/ vs .worker-impl/ Cleanup Timing

**Location**: `docs/learned/planning/` (appropriate existing file) (UPDATE)
**Action**: UPDATE - Add clarification
**Sources**: [Impl e5da072c]

**What to Add**:
Clarify the distinction:

- `.worker-impl/`: CI automatically removes this after validation passes. This is the ephemeral working copy used during remote implementation.
- `.impl/`: Requires user review and manual deletion. This is the original plan that should be preserved until the user confirms completion.
- Clear sequence: CI passes -> remove `.worker-impl/` -> commit -> push

---

## Tripwire Insights

### ARG_MAX Shell Limits

The "Argument list too long" error is one of the more confusing failures an agent can encounter in CI. It occurs when the combined size of command-line arguments exceeds the Linux kernel's ARG_MAX limit (approximately 2MB on most systems). This limit is rarely hit in local development but commonly triggered in CI where outputs can be large - rebase logs, test output, build artifacts.

The error is non-obvious because: (1) it mentions "argument list" but the real culprit is variable expansion, (2) it fails silently in some contexts (wrong output instead of error), and (3) the fix requires understanding that file I/O bypasses the limit entirely.

When an agent sees this error, or when editing workflows that pass dynamic content to CLI tools, the pattern should immediately come to mind: write to temp file, use file-based input flag, cleanup. This applies beyond `gh` to any CLI tool accepting file-based input.

### Printf vs Echo -e Behavior

The distinction between `printf "%b"` and `echo -e` seems trivial but causes real failures in GitHub Actions. GitHub Actions uses dash (the Debian Almquist Shell), which is POSIX-compliant but not bash-compatible. The `echo -e` flag for interpreting escape sequences is a bash extension - it may work, may be ignored, or may behave unexpectedly in dash.

`printf "%b"` is the POSIX standard for interpreting backslash escape sequences. It works consistently across shells and should be the default choice in any CI environment where the shell is not explicitly bash.

The symptom of using `echo -e` incorrectly is subtle: escape sequences like `\n` appear literally in output instead of being interpreted as newlines. This creates malformed output without error messages.

### GitHub Actions Token Scopes

The GITHUB_TOKEN provided automatically in GitHub Actions has restricted permissions by default. Operations like gist creation require elevated scopes that the default token doesn't have. When implementing CI features that interact with GitHub beyond the current repository, check whether the operation is supported by the default token or requires a personal access token (PAT).

The symptom is typically an HTTP 403 error on the GitHub API call. The fix is either to use a PAT stored as a repository secret, or to work around the limitation (e.g., skip optional features like session upload in CI).

---

## Contradiction Resolutions

### Multi-line Content Handling Context

**Existing doc**: `docs/learned/ci/github-actions-output-patterns.md`
**Conflict**: Existing doc says "Use heredoc for multi-line content"; new insight says "Use `--body-file` for multi-line content"

**Resolution**: These are not contradictory - they apply to different contexts:

1. **Heredoc with `$GITHUB_OUTPUT`**: For passing data between workflow steps. The heredoc pattern with EOF delimiters is correct for writing to `$GITHUB_OUTPUT` because this is a special GitHub Actions mechanism for step-to-step data flow.

2. **`--body-file` for GitHub CLI commands**: For sending data to external tools like `gh pr comment`. The `--body-file` pattern is correct because the data leaves the workflow and goes to the GitHub API.

**Action**: Update `github-actions-output-patterns.md` with a clarifying note that distinguishes these two contexts, and cross-reference the new `github-cli-comment-patterns.md` document for the `gh` CLI pattern.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Escape Sequence Command Substitution

**What happened**: PR comments displayed literal `\n` characters instead of newlines
**Root cause**: Using `echo -e` inside command substitution `$(...)` in a non-bash shell (GitHub Actions uses dash)
**Prevention**: Use `printf "%b"` and file-based input instead of command substitution with escape sequences
**Recommendation**: TRIPWIRE - score 5, affects all workflows posting formatted content

### 2. ARG_MAX Overflow

**What happened**: "Argument list too long" error when rebase output was large
**Root cause**: Variable expansion in command arguments exceeded Linux kernel limit (~2MB)
**Prevention**: Use file-based input (`--body-file`, `--input-file`, etc.) for any dynamic content that could be large
**Recommendation**: TRIPWIRE - score 6, silent failure mode, cross-cutting impact

### 3. Semantic vs Syntactic Command Equivalence

**What happened**: `erk pr check` failed despite using semantically equivalent command `erk wt from-pr`
**Root cause**: Validation code uses regex pattern matching, not semantic interpretation
**Prevention**: Read validation source code to understand exact pattern requirements; don't assume equivalence
**Recommendation**: ADD_TO_DOC - useful debugging insight but not tripwire-worthy

### 4. GitHub Token Scope Limitations

**What happened**: Session upload failed with HTTP 403 in CI
**Root cause**: GITHUB_TOKEN lacks gist creation permissions by default
**Prevention**: Document token capabilities; use PAT for elevated operations
**Recommendation**: TRIPWIRE - score 3, borderline, affects optional CI features

---

## Action Summary

- **New Documentation**: 6 items to create
  - `docs/learned/ci/github-cli-comment-patterns.md`
  - `docs/learned/cli/pr-commands.md` or `docs/learned/erk/pr-submission-patterns.md`
  - `docs/learned/planning/pr-submission-patterns.md`
  - `docs/learned/planning/debugging-patterns.md`

- **Documentation Updates**: 4 items to update
  - `docs/learned/ci/tripwires.md` (add 3 tripwire entries)
  - `docs/learned/ci/github-actions-output-patterns.md` (add cross-reference)
  - `docs/learned/architecture/subprocess-wrappers.md` (add temp file pattern)
  - `docs/learned/planning/` appropriate file (add .impl vs .worker-impl clarification)

- **Tripwires to Add**: 3 items
  - ARG_MAX shell limits (score 6)
  - Printf vs echo -e (score 5)
  - GITHUB_TOKEN limitations (score 3, borderline)

- **Contradictions Resolved**: 1 (heredoc vs --body-file context clarification)

## Implementation Notes

- All items directly address production issues or prevent future errors
- Clear source attribution enables easy verification
- Tripwire scoring provides objective prioritization
- HIGH priority item (github-cli-comment-patterns.md) is the core deliverable
- Session 5d99bc36's debugging insights are valuable for future agents encountering validation failures
