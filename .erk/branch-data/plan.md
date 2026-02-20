# Add Plan Backend Indicator to Statusline

## Context

The erk statusline currently shows git repo, worktree, branch, PR info, plan/objective numbers, CI checks, and model — but doesn't show which plan backend (`github` issue vs `draft_pr`) is active. Since this is controlled by the `ERK_PLAN_BACKEND` env var and affects how plans are stored, it's useful to see at a glance.

## Approach

Read `ERK_PLAN_BACKEND` env var (via `get_plan_backend()` from `erk_shared.plan_store`, already a dependency) and display it as a context label in the statusline.

**Display format:** `(be:issue)` or `(be:draft-pr)` — placed after the `|` separator, before the model indicator.

- `github` backend → displays as `(be:issue)`
- `draft_pr` backend → displays as `(be:draft-pr)`

**Placement in statusline:**

```
➜  (git:erk) (wt:root) (br:master) | (gh:#123 ...) (be:issue) │ (O)
                                                    ^^^^^^^^^^
```

## Files to Modify

1. **`packages/erk-statusline/src/erk_statusline/statusline.py`**
   - Import `get_plan_backend` from `erk_shared.plan_store`
   - In `main()`, call `get_plan_backend()` and map to display string
   - Add a `Token` for the backend label between the `build_gh_label` and model sections (~line 1256)

2. **`packages/erk-statusline/tests/test_statusline.py`**
   - Add test(s) for the backend label appearing in output

## Implementation Detail

In `main()`, after line 1189 (existing variable init block), add:

```python
from erk_shared.plan_store import get_plan_backend

backend_type = get_plan_backend()
backend_display = "draft-pr" if backend_type == "draft_pr" else "issue"
```

Then in the statusline assembly (~line 1238), add the backend token between the gh label and the model indicator:

```python
TokenSeq((Token("(be:"), Token(backend_display), Token(")")))
```

## Verification

- Run `make fast-ci` to verify tests and linting pass
- Manually verify by running `echo '{"workspace":{"current_dir":"/Users/schrockn/code/erk"},"model":{"display_name":"opus","id":"opus"},"session_id":"test"}' | uvx erk-statusline` and confirming `(be:issue)` appears
- Set `ERK_PLAN_BACKEND=draft_pr` and verify `(be:draft-pr)` appears
