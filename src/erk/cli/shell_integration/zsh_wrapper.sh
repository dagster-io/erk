# Erk shell integration for zsh
# This function wraps the erk CLI to provide seamless worktree switching

erk() {
  # Don't intercept if we're doing shell completion
  [ -n "$_ERK_COMPLETE" ] && { command erk "$@"; return; }

  local script_path exit_status
  script_path=$(ERK_SHELL=zsh command erk __shell "$@")
  exit_status=$?

  # Passthrough mode: run the original command directly
  [ "$script_path" = "__ERK_PASSTHROUGH__" ] && { command erk "$@"; return; }

  # Source the script file if it exists (even on non-zero exit)
  # Destructive commands output scripts BEFORE operations that might fail,
  # so the shell can navigate even if later steps error.
  if [ -n "$script_path" ] && [ -f "$script_path" ]; then
    source "$script_path"

    # Clean up unless ERK_KEEP_SCRIPTS is set
    if [ -z "$ERK_KEEP_SCRIPTS" ]; then
      rm -f "$script_path"
    fi

    # Preserve original command's exit code (not source's exit code)
    # so callers know if the underlying command failed
    return $exit_status
  fi

  # No script to source - propagate exit status
  return $exit_status
}
