---
completed_steps: 0
steps:
- completed: false
  text: '1. **Live feedback not working**: Status messages ("Getting current branch...",
    etc.) all appear at once after the operation completes instead of streaming in
    real-time'
- completed: false
  text: '2. **Missing extraction plan link**: The URL for the created extraction plan
    is not shown in the output'
- completed: false
  text: 1. Run `command erk <command> --script` as a subprocess
- completed: false
  text: 2. Let stderr pass through directly to terminal (live streaming)
- completed: false
  text: 3. Capture only stdout (for the activation script path)
- completed: false
  text: 1. **`src/erk/cli/shell_integration/handler.py`** - Replace CliRunner with
    subprocess.run for live stderr streaming
- completed: false
  text: 2. **`src/erk/core/shell.py`** - Improve JSON extraction from Claude output
- completed: false
  text: 3. **`tests/fakes/shell.py`** - Update FakeShell if interface changes
- completed: false
  text: 4. **`tests/unit/shell_integration/test_handler_commands.py`** - Update tests
    for new subprocess approach
- completed: false
  text: '1. Manual test: Run `erk pr land` and verify progress messages appear in
    real-time'
- completed: false
  text: '2. Manual test: Verify extraction plan URL appears in output'
- completed: false
  text: '3. Unit tests: Update handler tests to verify subprocess invocation'
- completed: false
  text: '4. Unit tests: Test JSON extraction with mixed output content'
total_steps: 13
---

# Progress Tracking

- [ ] 1. **Live feedback not working**: Status messages ("Getting current branch...", etc.) all appear at once after the operation completes instead of streaming in real-time
- [ ] 2. **Missing extraction plan link**: The URL for the created extraction plan is not shown in the output
- [ ] 1. Run `command erk <command> --script` as a subprocess
- [ ] 2. Let stderr pass through directly to terminal (live streaming)
- [ ] 3. Capture only stdout (for the activation script path)
- [ ] 1. **`src/erk/cli/shell_integration/handler.py`** - Replace CliRunner with subprocess.run for live stderr streaming
- [ ] 2. **`src/erk/core/shell.py`** - Improve JSON extraction from Claude output
- [ ] 3. **`tests/fakes/shell.py`** - Update FakeShell if interface changes
- [ ] 4. **`tests/unit/shell_integration/test_handler_commands.py`** - Update tests for new subprocess approach
- [ ] 1. Manual test: Run `erk pr land` and verify progress messages appear in real-time
- [ ] 2. Manual test: Verify extraction plan URL appears in output
- [ ] 3. Unit tests: Update handler tests to verify subprocess invocation
- [ ] 4. Unit tests: Test JSON extraction with mixed output content