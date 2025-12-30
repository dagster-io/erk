# Erk shell integration for fish
# This function wraps the erk CLI to provide seamless worktree switching

# Helper to invoke erk with proper version
function _erk_cmd
    # Allow override for local dev
    if set -q ERK_INVOKE
        $ERK_INVOKE $argv
        return
    end

    # Read version from repo
    set -l repo_root (git rev-parse --show-toplevel 2>/dev/null)
    set -l version ""

    if test -n "$repo_root" -a -f "$repo_root/.erk/pinned-uvx-erk-version"
        set version (string trim (cat "$repo_root/.erk/pinned-uvx-erk-version"))
    end

    if test -n "$version"
        uvx "erk@$version" $argv
    else
        # Fallback to uvx erk (latest) if no version file or outside repo
        uvx erk $argv
    end
end

function erk
    # Don't intercept if we're doing shell completion
    if set -q _ERK_COMPLETE
        _erk_cmd $argv
        return
    end

    set -l script_path (env ERK_SHELL=fish _erk_cmd __shell $argv)
    set -l exit_status $status

    # Passthrough mode
    if test "$script_path" = "__ERK_PASSTHROUGH__"
        _erk_cmd $argv
        return
    end

    # Source the script file if it exists, regardless of exit code.
    # This matches Python handler logic: use script even if command had errors.
    # The script contains important state changes (like cd to target dir).
    if test -n "$script_path" -a -f "$script_path"
        source "$script_path"
        set -l source_exit $status

        # Clean up unless ERK_KEEP_SCRIPTS is set
        if not set -q ERK_KEEP_SCRIPTS
            rm -f "$script_path"
        end

        return $source_exit
    end

    # Only return exit_status if no script was provided
    if test $exit_status -ne 0
        return $exit_status
    end
end
