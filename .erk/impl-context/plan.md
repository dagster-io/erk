# Fix: Pass claude CLI prompts via stdin to avoid ARG_MAX

## Context

CI failed on `ci-update-pr-body` with `OSError: [Errno 7] Argument list too long: 'claude'`. The prompt (containing a large PR diff up to 1MB via `MAX_DIFF_CHARS`) is passed as a CLI argument, exceeding Linux's `ARG_MAX` (~2MB including env vars). This is the same class of bug documented in `docs/learned/ci/github-cli-comment-patterns.md` for `gh` CLI.

## Fix

Pass the prompt via stdin (`input=` parameter to `subprocess.run`) instead of as a positional CLI argument. The `claude --print` CLI reads from stdin when no positional prompt is provided.

### File: `src/erk/core/prompt_executor.py`

**1. `execute_prompt` (line 565)** — Remove `cmd.append(prompt)`, add `input=prompt` to `subprocess.run`. Already has `text=True` so no other changes needed.

**2. `execute_prompt_passthrough` (line 633)** — Remove `cmd.append(prompt)`, replace `stdin=subprocess.DEVNULL` with `input=prompt`, add `text=True`. Using `input=` pipes the prompt then closes stdin, which preserves the same "no interactive input" guarantee as `DEVNULL`.

### Out of scope: `src/erk/core/codex_prompt_executor.py`

Same vulnerability exists but Codex wasn't the failing path and its `build_codex_exec_args` is a pure function that returns args — changing it requires modifying callers too. Separate PR.

### No test changes needed

`FakePromptExecutor` tracks prompts via the method parameter, not by inspecting CLI args. Tests assert on `executor.prompt_calls[0].prompt` which is the string passed to the method, unaffected by how it reaches the subprocess.

## Verification

1. Run unit tests for prompt executor: `pytest tests/unit/core/test_prompt_executor.py`
2. Run tests for ci_update_pr_body: `pytest tests/unit/cli/commands/exec/scripts/test_ci_update_pr_body.py`
3. Run `ty` and `ruff` checks
