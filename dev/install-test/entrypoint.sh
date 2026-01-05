#!/bin/bash
# Entrypoint for erk installation testing container
#
# Commands:
#   shell   - Interactive shell for manual exploration
#   fresh   - Test fresh install scenario on existing repo
#   upgrade - Test upgrade scenario (install old version, then upgrade)

set -e

ERK_SOURCE="/home/testuser/erk-source"
TEST_REPO="/home/testuser/test-repo"

setup_test_repo() {
    # Create a test git repository with existing erk config
    echo "Setting up test repository..."

    mkdir -p "$TEST_REPO"
    cd "$TEST_REPO"

    git init
    git config user.email "test@example.com"
    git config user.name "Test User"

    # Copy current config fixtures
    cp -r /home/testuser/fixtures/configs/current/.erk .

    # Create a dummy file and commit
    echo "# Test Project" > README.md
    git add .
    git commit -m "Initial commit"

    echo "Test repository created at $TEST_REPO"
}

install_erk_from_source() {
    echo "Installing erk from source..."
    if [ ! -d "$ERK_SOURCE" ]; then
        echo "ERROR: erk source not mounted at $ERK_SOURCE"
        echo "Run with: docker run -v \$(pwd):/home/testuser/erk-source:ro ..."
        exit 1
    fi

    uv tool install -e "$ERK_SOURCE"
    echo "erk installed. Version: $(erk --version || echo 'version command not available')"
}

case "${1:-shell}" in
    shell)
        echo "=== erk Installation Test Environment ==="
        echo ""
        echo "Source mounted at: $ERK_SOURCE"
        echo ""
        echo "Quick start:"
        echo "  1. Install erk: uv tool install -e $ERK_SOURCE"
        echo "  2. Create test repo: setup_test_repo"
        echo "  3. Test commands in $TEST_REPO"
        echo ""
        echo "Helper functions available in shell:"
        echo "  setup_test_repo    - Create test repo with existing .erk config"
        echo "  install_erk        - Install erk from mounted source"
        echo ""

        # Export functions for interactive use
        export -f setup_test_repo
        export -f install_erk_from_source
        export ERK_SOURCE TEST_REPO

        # Alias for convenience
        echo "alias install_erk='install_erk_from_source'" >> ~/.bashrc

        exec /bin/bash
        ;;

    fresh)
        echo "=== Fresh Install Test ==="
        echo "Testing: Install erk on repo that already has .erk/ config"
        echo ""

        setup_test_repo
        install_erk_from_source

        cd "$TEST_REPO"
        echo ""
        echo "=== Running erk commands ==="
        echo ""

        echo "--- erk --help ---"
        erk --help || true
        echo ""

        echo "--- erk status ---"
        erk status || true
        echo ""

        echo "--- erk wt list ---"
        erk wt list || true
        echo ""

        echo "=== Fresh install test complete ==="
        echo "Drop to shell for manual exploration..."
        exec /bin/bash
        ;;

    upgrade)
        echo "=== Upgrade Test ==="
        echo "Testing: Upgrade erk on repo with older config format"
        echo ""
        echo "NOTE: Upgrade testing requires old erk versions on PyPI."
        echo "      For now, this is the same as 'fresh' test."
        echo "      Future: Install old version first, then upgrade."
        echo ""

        setup_test_repo
        install_erk_from_source

        cd "$TEST_REPO"
        echo ""
        echo "=== Running erk commands after upgrade ==="
        echo ""

        echo "--- erk status ---"
        erk status || true
        echo ""

        echo "=== Upgrade test complete ==="
        echo "Drop to shell for manual exploration..."
        exec /bin/bash
        ;;

    *)
        echo "Usage: $0 {shell|fresh|upgrade}"
        echo ""
        echo "Commands:"
        echo "  shell   - Interactive shell for manual exploration"
        echo "  fresh   - Test fresh install scenario"
        echo "  upgrade - Test upgrade scenario"
        exit 1
        ;;
esac
