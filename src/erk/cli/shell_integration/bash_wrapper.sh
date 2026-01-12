# Erk shell integration for bash
# This function wraps the erk CLI to provide seamless worktree switching

erk() {
  # Don't intercept if we're doing shell completion
  [ -n "$_ERK_COMPLETE" ] && { uvx erk-bootstrap "$@"; return; }

  local script_path exit_status
  script_path=$(ERK_SHELL=bash uvx erk-bootstrap __shell "$@")
  exit_status=$?

  # Passthrough mode: run the original command directly
  [ "$script_path" = "__ERK_PASSTHROUGH__" ] && { uvx erk-bootstrap "$@"; return; }

  # Source the script file if it exists, regardless of exit code.
  # This matches Python handler logic: use script even if command had errors.
  # The script contains important state changes (like cd to target dir).
  if [ -n "$script_path" ] && [ -f "$script_path" ]; then
    source "$script_path"
    local source_exit=$?

    # Clean up unless ERK_KEEP_SCRIPTS is set
    if [ -z "$ERK_KEEP_SCRIPTS" ]; then
      rm -f "$script_path"
    fi

    return $source_exit
  fi

  # Only return exit_status if no script was provided
  [ $exit_status -ne 0 ] && return $exit_status
}
