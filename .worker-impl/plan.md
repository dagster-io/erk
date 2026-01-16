# Plan: Increase Land Action Timeout to 10 Minutes

## Summary

Increase the timeout for the "land" action in `erk dash` from 30 seconds to 10 minutes (600 seconds).

## Changes

### File: `src/erk/tui/screens/plan_detail_screen.py`

1. **Store timeout value for use in timeout message** (~line 396)
   - Add `self._stream_timeout_seconds = timeout` before setting the timer
   - This allows the timeout handler to display the correct value

2. **Update timeout message to use stored value** (line 487)
   - Change hardcoded `"30 seconds"` to use `self._stream_timeout_seconds`
   - Format as minutes if >= 60 seconds for readability

3. **Pass explicit timeout for land action** (lines 631-635)
   - Add `timeout=600.0` to the `run_streaming_command()` call for `land_pr`

## Verification

1. Run `erk dash -i` and trigger the land action on a PR
2. Confirm the command runs without timing out prematurely
3. (Optional) Test timeout message formatting by temporarily setting a short timeout