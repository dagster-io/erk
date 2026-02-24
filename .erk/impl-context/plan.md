# Convert address_remote from modal to toast (fire-and-forget)

## Context

The `address_remote` TUI action currently opens a `PlanDetailScreen` modal that streams the output of `erk launch pr-address --pr <N> --no-wait`. Since this is a fire-and-forget workflow dispatch (takes ~2-3 seconds, just checks PR status and dispatches a GitHub Actions workflow), the modal is unnecessary overhead. The user has to press Esc to dismiss it.

The `close_plan` action already uses the ideal pattern: immediate toast, background `@work(thread=True)`, success/error toast. We replicate that pattern for `address_remote`.

## Changes

### `src/erk/tui/app.py`

1. **Add `import subprocess`** to imports (line ~5 area)

2. **Replace `address_remote` handler** (lines 918-942) with toast pattern:
   ```python
   elif command_id == "address_remote":
       if row.pr_number:
           self.notify(f"Dispatching address for PR #{row.pr_number}...")
           self._address_remote_async(row.pr_number)
   ```

3. **Add `_address_remote_async` method** near `_close_plan_async` (after line 536):
   ```python
   @work(thread=True)
   def _address_remote_async(self, pr_number: int) -> None:
       """Dispatch address-remote workflow in background thread with toast."""
       try:
           result = subprocess.run(
               ["erk", "launch", "pr-address", "--pr", str(pr_number), "--no-wait"],
               capture_output=True,
               text=True,
               check=False,
               cwd=str(self._provider.repo_root),
           )
           if result.returncode == 0:
               self.call_from_thread(
                   self.notify, f"Dispatched address for PR #{pr_number}", timeout=3
               )
           else:
               error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
               self.call_from_thread(
                   self.notify,
                   f"Failed to dispatch address for PR #{pr_number}: {error_msg}",
                   severity="error",
                   timeout=5,
               )
       except Exception as e:
           self.call_from_thread(
               self.notify,
               f"Failed to dispatch address for PR #{pr_number}: {e}",
               severity="error",
               timeout=5,
           )
   ```

   Uses `subprocess.run(check=False)` with explicit return code checking - the approved LBYL pattern from `docs/learned/architecture/subprocess-wrappers.md` for optional/fire-and-forget operations.

## Files modified

- `src/erk/tui/app.py` - Replace modal handler with toast + background worker

## Verification

1. Run TUI tests: `make fast-ci` (via devrun agent)
2. Manual: `erk dash -i`, select a row with a PR, press Ctrl+P → 'a' → observe toast instead of modal
