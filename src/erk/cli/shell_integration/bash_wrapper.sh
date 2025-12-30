# Erk shell integration for bash
# This function wraps the erk CLI to provide seamless worktree switching

# Helper to invoke erk with proper version
_erk_cmd() {
    # Allow override for local dev
    if [[ -n "${ERK_INVOKE:-}" ]]; then
        ${ERK_INVOKE} "$@"
        return
    fi

    # Read version from repo
    local repo_root version
    repo_root=$(git rev-parse --show-toplevel 2>/dev/null)

    if [[ -n "$repo_root" && -f "$repo_root/.erk/pinned-uvx-erk-version" ]]; then
        version=$(cat "$repo_root/.erk/pinned-uvx-erk-version" | tr -d '[:space:]')
    fi

    if [[ -n "$version" ]]; then
        uvx "erk@${version}" "$@"
    else
        # Fallback to uvx erk (latest) if no version file or outside repo
        uvx erk "$@"
    fi
}

erk() {
  # Don't intercept if we're doing shell completion
  [ -n "$_ERK_COMPLETE" ] && { _erk_cmd "$@"; return; }

  local script_path exit_status
  script_path=$(ERK_SHELL=bash _erk_cmd __shell "$@")
  exit_status=$?

  # Passthrough mode: run the original command directly
  [ "$script_path" = "__ERK_PASSTHROUGH__" ] && { _erk_cmd "$@"; return; }

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
