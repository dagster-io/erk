# Plan: Fix `erk pr submit` producing zero output on timeout

## Context

When `erk pr submit` is called and `gt submit` hangs (e.g., after retracking a branch with 53 commits), the entire process gets killed by the Bash tool's 120-second timeout. **All output is lost** — not even the initial `🚀 Submitting PR...` message appears. This happens because:

1. `gt submit` runs with `stdout=sys.stdout` (inherits Python's stdout pipe)
2. `gt submit` has its own 120-second timeout, competing with the Bash tool's 120-second timeout
3. When the process is killed externally, Python's pipe buffers are lost — even though Click calls `flush()`, the kernel pipe buffer contents may not reach the reader

The user sees `(No output)` and `(timeout 2m)`, which gives zero diagnostic information.

## Root Cause

In `submit_stack()` (`packages/erk-shared/src/erk_shared/gateway/graphite/real.py:310`):
```python
subprocess.run(
    cmd,
    stdout=DEVNULL if quiet else sys.stdout,  # ← gt gets Python's stdout fd
    stderr=subprocess.PIPE,                    # ← stderr captured
    timeout=120,                               # ← same as Bash tool timeout
)
```

When `gt submit` hangs and both timeouts fire near-simultaneously, the process is killed before any output reaches the Bash tool reader.

## Approach

**Capture gt submit output instead of passing stdout through.** This ensures Python controls when output is written to the pipe, and Click's earlier messages aren't lost.

### Step 1: Change `submit_stack()` to capture stdout

**File:** `packages/erk-shared/src/erk_shared/gateway/graphite/real.py` (lines 289-331)

- Change `stdout=sys.stdout` to `stdout=subprocess.PIPE`
- After subprocess completes, print captured stdout via `user_output()`
- On timeout, the captured output is still available via `e.stdout` and should be printed before raising
- Reduce timeout from 120s to 90s to leave headroom before the Bash tool's 120s timeout

```python
result = subprocess.run(
    cmd,
    cwd=repo_root,
    timeout=90,
    stdout=subprocess.PIPE if not quiet else DEVNULL,
    stderr=subprocess.PIPE,
    text=True,
    check=True,
)
if not quiet and result.stdout:
    user_output(result.stdout, nl=False)
if not quiet and result.stderr:
    user_output(result.stderr, nl=False)
```

Update timeout handler to print partial output:
```python
except subprocess.TimeoutExpired as e:
    if not quiet and e.stdout:
        user_output(e.stdout, nl=False)
    raise RuntimeError(
        "gt submit timed out after 90 seconds. Check network connectivity and try again."
    ) from e
except subprocess.CalledProcessError as e:
    if not quiet and e.stdout:
        user_output(e.stdout, nl=False)
    raise RuntimeError(
        f"gt submit failed (exit code {e.returncode}): {e.stderr or ''}"
    ) from e
```

### Step 2: Add explicit flush before subprocess calls in the pipeline

**File:** `src/erk/cli/commands/pr/submit_pipeline.py` (line 241)

Add `sys.stdout.flush()` before `ctx.graphite.submit_stack()` calls (lines 242 and 640) to ensure Click's status messages reach the pipe reader before entering a long subprocess:

```python
sys.stdout.flush()
ctx.graphite.submit_stack(...)
```

### Step 3: Update the `quiet` parameter threading

**File:** `src/erk/cli/commands/pr/submit_pipeline.py` (line 246)

Change `quiet=False` to `quiet=state.quiet` so the quiet flag is properly respected:

```python
ctx.graphite.submit_stack(
    state.repo_root,
    publish=True,
    restack=False,
    quiet=state.quiet,  # was: quiet=False
    force=effective_force,
)
```

Same fix at line 640-646 for the `enhance_with_graphite` step.

## Files to modify

1. `packages/erk-shared/src/erk_shared/gateway/graphite/real.py` — capture stdout, reduce timeout, print partial output on error
2. `src/erk/cli/commands/pr/submit_pipeline.py` — add flushes, fix quiet threading

## Verification

1. Run `erk pr submit --skip-description` on a branch that will hit gt submit
2. Verify the `🚀 Submitting PR...` and `Phase 1:` messages appear immediately
3. If gt submit takes time, verify the output from gt appears after completion (not interleaved)
4. Test timeout scenario: verify partial gt output + error message appear, not zero output
5. Run existing submit tests to confirm no regressions
