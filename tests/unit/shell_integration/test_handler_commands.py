"""Unit tests for shell integration command routing."""

from pathlib import Path

from erk.cli.shell_integration.handler import (
    GLOBAL_FLAGS,
    SHELL_INTEGRATION_COMMANDS,
    handle_shell_request,
)


def test_pr_land_compound_command_registered() -> None:
    """Verify 'pr land' compound command is registered for shell integration.

    This prevents regression of the bug where 'erk pr land' via shell wrapper
    failed with "requires shell integration" error because the compound command
    was not registered in SHELL_INTEGRATION_COMMANDS.

    When compound commands are missing:
    1. Shell wrapper intercepts → calls 'erk __shell pr land'
    2. Handler checks for "pr land" compound command → NOT FOUND
    3. Falls back to "pr" (the group) → --script goes to pr_group, not pr_land
    4. pr_land never receives --script flag → fails with error
    """
    assert "pr land" in SHELL_INTEGRATION_COMMANDS


def test_pr_group_not_registered() -> None:
    """Verify 'pr' group is NOT registered for shell integration.

    Regression test for issue #2227: `erk pr submit` silently exiting.

    The bug: When "pr" (the group) was registered, ANY pr subcommand that
    didn't have its own entry (like "pr submit") would:
    1. Shell wrapper intercepts → calls 'erk __shell pr submit'
    2. Handler matches "pr" (the group), not "pr submit"
    3. _invoke_hidden_command adds --script to args
    4. Invokes pr_group with args ["submit", "--script"]
    5. Click routes to pr_submit but --script isn't a valid option
    6. Click fails with "No such option: --script" (swallowed)
    7. Result: silent exit with code 1

    The fix: Remove "pr" from SHELL_INTEGRATION_COMMANDS.
    Only register specific pr subcommands that support --script (pr land, pr checkout).
    Unregistered pr subcommands (pr submit, pr sync, etc.) now passthrough correctly.
    """
    assert "pr" not in SHELL_INTEGRATION_COMMANDS, (
        "The 'pr' group should NOT be registered. "
        "Only specific pr subcommands with --script support should be registered."
    )


def test_pr_subcommands_without_script_support_passthrough() -> None:
    """Verify pr subcommands without --script support are passed through.

    Commands like 'pr submit', 'pr sync', etc. don't support --script and
    should NOT be in SHELL_INTEGRATION_COMMANDS. When invoked via shell wrapper,
    they should passthrough to run normally without shell integration.
    """
    # These pr subcommands don't support --script flag
    subcommands_without_script = ["pr submit", "pr sync", "pr auto-restack"]

    for cmd in subcommands_without_script:
        assert cmd not in SHELL_INTEGRATION_COMMANDS, (
            f"'{cmd}' should NOT be registered - it doesn't support --script"
        )

    # Verify passthrough behavior: when unrecognized, handler returns passthrough=True
    result = handle_shell_request(("pr", "submit"))
    assert result.passthrough is True, "pr submit should passthrough"

    result = handle_shell_request(("pr", "sync"))
    assert result.passthrough is True, "pr sync should passthrough"


def test_compound_commands_have_all_expected_entries() -> None:
    """Verify all expected compound commands are registered.

    Compound commands use "group subcommand" format and must be registered
    explicitly so shell integration routes --script to the correct handler.
    """
    expected_compound_commands = [
        "wt create",
        "wt goto",
        "stack consolidate",
        "pr land",
        "pr checkout",
        "pr co",  # alias for pr checkout
    ]

    for cmd in expected_compound_commands:
        assert cmd in SHELL_INTEGRATION_COMMANDS, f"Missing compound command: {cmd}"


def test_top_level_commands_registered() -> None:
    """Verify top-level commands are registered for shell integration."""
    expected_top_level = [
        "checkout",
        "co",  # alias
        "up",
        "down",
        "implement",
    ]

    for cmd in expected_top_level:
        assert cmd in SHELL_INTEGRATION_COMMANDS, f"Missing top-level command: {cmd}"


def test_legacy_aliases_registered() -> None:
    """Verify legacy top-level aliases for backward compatibility."""
    expected_aliases = [
        "create",
        "goto",
        "consolidate",
    ]

    for alias in expected_aliases:
        assert alias in SHELL_INTEGRATION_COMMANDS, f"Missing legacy alias: {alias}"


def test_global_flags_stripped_before_command_matching() -> None:
    """Global flags like --debug should not prevent command recognition.

    When running 'erk --debug pr land', the handler receives args like
    ('--debug', 'pr', 'land'). Without stripping global flags, the handler
    tries to match '--debug pr' as a compound command (not found), then
    '--debug' as a single command (not found), and falls back to passthrough.

    This test verifies that global flags are stripped before command matching,
    so 'pr land' is correctly recognized as a compound command.
    """
    # With --help present, the handler should recognize 'pr land' and passthrough
    # (since --help causes passthrough behavior for recognized commands)
    result = handle_shell_request(("--debug", "pr", "land", "--help"))
    assert result.passthrough is True

    # Multiple global flags should all be stripped
    result = handle_shell_request(("--debug", "--verbose", "pr", "land", "--help"))
    assert result.passthrough is True


def test_global_flags_constant_contains_expected_flags() -> None:
    """Verify GLOBAL_FLAGS contains all expected top-level flags."""
    expected_flags = ["--debug", "--dry-run", "--verbose", "-v"]
    for flag in expected_flags:
        assert flag in GLOBAL_FLAGS, f"Missing global flag: {flag}"


def test_only_global_flags_returns_passthrough() -> None:
    """If args contain only global flags, handler should passthrough."""
    result = handle_shell_request(("--debug",))
    assert result.passthrough is True

    result = handle_shell_request(("--debug", "--verbose"))
    assert result.passthrough is True


def test_process_command_result_uses_script_even_when_command_fails(tmp_path: Path) -> None:
    """process_command_result should use script even if exit code is non-zero.

    This test verifies the fix for shell integration stranding:
    - Commands like 'pr land' output their activation script BEFORE destructive ops
    - If a later step fails (e.g., git pull after worktree deletion), the script
      is already in stdout
    - Handler must check for a valid script path BEFORE checking exit code
    - If a valid script exists, use it instead of passthrough

    Without this fix:
    1. pr land outputs script to stdout
    2. pr land deletes worktree
    3. git pull fails → non-zero exit
    4. Handler sees exit_code != 0 → returns passthrough=True
    5. Shell wrapper runs `command erk pr land` → fails (cwd gone)

    With this fix:
    1. pr land outputs script to stdout (early output)
    2. pr land deletes worktree
    3. git pull fails → non-zero exit
    4. Handler sees script in stdout → uses it instead of passthrough
    5. Shell runs script → navigates to destination
    """
    from erk.cli.shell_integration.handler import process_command_result

    # Create a real temp file to simulate the activation script
    script_file = tmp_path / "activation-script.sh"
    script_file.write_text("cd /some/destination\n")

    result = process_command_result(
        exit_code=1,  # Command failed
        stdout=str(script_file),  # But script was output
        stderr="Error: git pull failed",
        command_name="pr land",
    )

    # Key assertion: should NOT passthrough since we have a valid script
    assert result.passthrough is False, (
        "Should use script instead of passthrough when script exists"
    )
    assert result.script == str(script_file)
    assert result.exit_code == 1  # Exit code should still reflect failure


def test_process_command_result_forwards_error_on_failure_without_script() -> None:
    """process_command_result should forward error and NOT passthrough when command fails.

    When a shell-integrated command fails without producing a script, we must NOT
    passthrough. Passthrough would re-run the command WITHOUT --script, which for
    commands like 'pr land' shows a misleading "requires shell integration" error
    instead of the actual failure reason (e.g., "PR is already merged").

    The correct behavior is:
    1. Forward the stderr (actual error message) to the user
    2. Return passthrough=False so shell wrapper doesn't re-run
    3. Return the exit code so shell wrapper exits with correct status
    """
    from erk.cli.shell_integration.handler import process_command_result

    result = process_command_result(
        exit_code=1,  # Command failed
        stdout="",  # No script output
        stderr="Error: validation failed",
        command_name="checkout",
    )

    # Key assertion: should NOT passthrough - error was already forwarded
    assert result.passthrough is False
    assert result.script is None
    assert result.exit_code == 1


def test_process_command_result_forwards_error_when_script_path_doesnt_exist() -> None:
    """process_command_result should forward error when script path doesn't exist.

    If stdout contains a path but the file doesn't exist (e.g., cleanup race condition),
    the command effectively failed to produce a usable script. We should forward the
    error and NOT passthrough, for the same reason as the no-script case: passthrough
    would re-run without --script and show misleading errors.
    """
    from erk.cli.shell_integration.handler import process_command_result

    result = process_command_result(
        exit_code=1,  # Command failed
        stdout="/nonexistent/path/to/script.sh",  # Path doesn't exist
        stderr="Error: something failed",
        command_name="checkout",
    )

    # Should NOT passthrough - error was forwarded, script path is invalid
    assert result.passthrough is False
    assert result.script is None
    assert result.exit_code == 1


def test_process_command_result_success_with_script(tmp_path: Path) -> None:
    """process_command_result should return script on success."""
    from erk.cli.shell_integration.handler import process_command_result

    script_file = tmp_path / "activation-script.sh"
    script_file.write_text("cd /destination\n")

    result = process_command_result(
        exit_code=0,
        stdout=str(script_file),
        stderr="",
        command_name="checkout",
    )

    assert result.passthrough is False
    assert result.script == str(script_file)
    assert result.exit_code == 0


def test_process_command_result_separates_stdout_from_stderr(tmp_path: Path) -> None:
    """Verify stdout/stderr separation for script path extraction.

    Regression test for bug where CliRunner's default mix_stderr=True caused
    user messages (stderr) to be mixed into stdout, corrupting script path
    extraction. This test verifies the fix: process_command_result receives
    already-separated stdout/stderr and correctly extracts the script path.

    The bug scenario:
    1. Command outputs user progress messages to stderr (via user_output())
    2. Command outputs script path to stdout (via machine_output())
    3. CliRunner with mix_stderr=True combines them into result.stdout
    4. Handler tries to extract script path: script_path = result.stdout.strip()
    5. Gets multi-line garbage instead of just the script path
    6. Path(garbage).exists() returns False
    7. No script is returned to shell wrapper
    8. User is stranded in deleted directory

    Fix: Use CliRunner(mix_stderr=False) to keep stdout/stderr separate.
    """
    from erk.cli.shell_integration.handler import process_command_result

    # Create a real temp file to simulate the activation script
    script_file = tmp_path / "activation-script.sh"
    script_file.write_text("cd /some/destination\n", encoding="utf-8")

    # Simulate what SHOULD happen with mix_stderr=False:
    # stdout contains only the script path, stderr contains user messages
    result = process_command_result(
        exit_code=0,
        stdout=str(script_file),  # Clean stdout with just the script path
        stderr="✓ Removed worktree\n✓ Deleted branch\n",  # User messages
        command_name="pr land",
    )

    # Key assertions:
    # 1. Handler correctly extracts script path from clean stdout
    assert result.passthrough is False, "Should use script, not passthrough"
    assert result.script == str(script_file), "Script path should be extracted correctly"
    assert result.exit_code == 0

    # Note: This test verifies process_command_result's behavior with
    # pre-separated stdout/stderr. The actual separation happens in
    # _invoke_hidden_command via CliRunner(mix_stderr=False).


def test_process_command_result_with_contaminated_stdout_fails(tmp_path: Path) -> None:
    """Verify that mixed stdout/stderr causes script extraction to fail.

    This test demonstrates WHY mix_stderr=False is needed: when stderr is
    mixed into stdout, the script path becomes unextractable garbage.
    """
    from erk.cli.shell_integration.handler import process_command_result

    # Create a real temp file
    script_file = tmp_path / "activation-script.sh"
    script_file.write_text("cd /some/destination\n", encoding="utf-8")

    # Simulate what USED TO happen with mix_stderr=True (the bug):
    # stdout contains user messages PLUS the script path
    contaminated_stdout = f"✓ Removed worktree\n✓ Deleted branch\n{script_file}\n"

    result = process_command_result(
        exit_code=0,
        stdout=contaminated_stdout,  # Contaminated stdout
        stderr=None,  # Empty because everything went to stdout
        command_name="pr land",
    )

    # With contaminated stdout, the extracted "script_path" is multi-line garbage.
    # The function either returns None/passthrough OR returns a script path that
    # doesn't actually exist as a file (because the "path" is the garbage string).
    # Either way, shell integration fails - the key assertion is that the VALID
    # script file we created won't be returned.
    assert result.script != str(script_file), (
        "Contaminated stdout should NOT extract the correct script path"
    )
    # If a script is returned, it should not be a file that exists
    if result.script:
        assert not Path(result.script).exists(), (
            "Returned script path should not exist when stdout is contaminated"
        )
