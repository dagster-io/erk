#!/bin/bash
# Entrypoint for erk installation testing container
#
# Commands:
#   shell            - Interactive shell for manual exploration
#   fresh            - Test fresh install scenario on existing repo
#   upgrade          - Test upgrade scenario (install old version, then upgrade)
#   repo <name>      - Test with specific repo fixture (e.g., dagster-compass)
#   list-repos       - List available repo fixtures

set -e

ERK_SOURCE="/home/testuser/erk-source"
TEST_REPO="/home/testuser/test-repo"
FIXTURES_DIR="/home/testuser/fixtures"

# List available repo fixtures
list_repo_fixtures() {
    echo "Available repo fixtures:"
    if [ -d "$FIXTURES_DIR/repos" ]; then
        for repo in "$FIXTURES_DIR/repos"/*/; do
            if [ -d "$repo" ]; then
                repo_name=$(basename "$repo")
                echo "  - $repo_name"
            fi
        done
    else
        echo "  (none)"
    fi
}

# Setup test repo with generic config
setup_test_repo() {
    local fixture_name="${1:-current}"
    echo "Setting up test repository with fixture: $fixture_name"

    rm -rf "$TEST_REPO"
    mkdir -p "$TEST_REPO"
    cd "$TEST_REPO"

    git init
    git config user.email "test@example.com"
    git config user.name "Test User"

    # Copy config fixtures based on type
    if [ -d "$FIXTURES_DIR/repos/$fixture_name" ]; then
        # Repo-specific fixture
        echo "Using repo fixture: $fixture_name"
        if [ -d "$FIXTURES_DIR/repos/$fixture_name/.erk" ]; then
            cp -r "$FIXTURES_DIR/repos/$fixture_name/.erk" .
        fi
        if [ -d "$FIXTURES_DIR/repos/$fixture_name/.claude" ]; then
            cp -r "$FIXTURES_DIR/repos/$fixture_name/.claude" .
        fi
    elif [ -d "$FIXTURES_DIR/configs/$fixture_name" ]; then
        # Generic config fixture
        echo "Using config fixture: $fixture_name"
        cp -r "$FIXTURES_DIR/configs/$fixture_name/.erk" .
    else
        echo "ERROR: Fixture not found: $fixture_name"
        echo ""
        echo "Available config fixtures in $FIXTURES_DIR/configs/:"
        ls -1 "$FIXTURES_DIR/configs/" 2>/dev/null || echo "  (none)"
        echo ""
        echo "Available repo fixtures in $FIXTURES_DIR/repos/:"
        ls -1 "$FIXTURES_DIR/repos/" 2>/dev/null || echo "  (none)"
        exit 1
    fi

    # Create a dummy file and commit
    echo "# Test Project" > README.md
    git add .
    git commit -m "Initial commit"

    echo "Test repository created at $TEST_REPO"
}

# Setup test repo mimicking a specific repository
setup_repo_fixture() {
    local repo_name="$1"
    if [ -z "$repo_name" ]; then
        echo "ERROR: Repo name required"
        list_repo_fixtures
        exit 1
    fi

    setup_test_repo "$repo_name"
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

run_erk_tests() {
    echo ""
    echo "=== Running erk commands ==="
    echo ""

    echo "--- erk --help ---"
    erk --help || true
    echo ""

    echo "--- erk doctor ---"
    erk doctor || true
    echo ""

    echo "--- erk wt list ---"
    erk wt list || true
    echo ""

    # Check for version requirements
    if [ -f ".erk/required-erk-uv-tool-version" ]; then
        echo "--- Version check ---"
        required_version=$(cat .erk/required-erk-uv-tool-version)
        echo "Required erk version: $required_version"
        echo "Installed version: $(erk --version 2>/dev/null || echo 'unknown')"
        echo ""
    fi
}

case "${1:-shell}" in
    shell)
        echo "=== erk Installation Test Environment ==="
        echo ""
        echo "Source mounted at: $ERK_SOURCE"
        echo ""
        echo "Quick start:"
        echo "  1. Install erk: uv tool install -e $ERK_SOURCE"
        echo "  2. Create test repo: setup_test_repo [fixture_name]"
        echo "  3. Test commands in $TEST_REPO"
        echo ""
        echo "Helper functions available in shell:"
        echo "  setup_test_repo [name]  - Create test repo (default: current)"
        echo "  setup_repo_fixture name - Create test repo from repo fixture"
        echo "  install_erk             - Install erk from mounted source"
        echo "  list_repo_fixtures      - List available repo fixtures"
        echo ""
        list_repo_fixtures
        echo ""

        # Export functions for interactive use
        export -f setup_test_repo
        export -f setup_repo_fixture
        export -f install_erk_from_source
        export -f list_repo_fixtures
        export -f run_erk_tests
        export ERK_SOURCE TEST_REPO FIXTURES_DIR

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
        run_erk_tests

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
        run_erk_tests

        echo "=== Upgrade test complete ==="
        echo "Drop to shell for manual exploration..."
        exec /bin/bash
        ;;

    repo)
        REPO_NAME="${2:-}"
        if [ -z "$REPO_NAME" ]; then
            echo "Usage: $0 repo <repo-name>"
            echo ""
            list_repo_fixtures
            exit 1
        fi

        echo "=== Repo-Specific Test: $REPO_NAME ==="
        echo "Testing: Install erk on repo configured like $REPO_NAME"
        echo ""

        setup_repo_fixture "$REPO_NAME"
        install_erk_from_source

        cd "$TEST_REPO"
        run_erk_tests

        echo "=== Repo test complete: $REPO_NAME ==="
        echo "Drop to shell for manual exploration..."
        exec /bin/bash
        ;;

    list-repos)
        list_repo_fixtures
        ;;

    *)
        echo "Usage: $0 {shell|fresh|upgrade|repo <name>|list-repos}"
        echo ""
        echo "Commands:"
        echo "  shell            - Interactive shell for manual exploration"
        echo "  fresh            - Test fresh install scenario"
        echo "  upgrade          - Test upgrade scenario"
        echo "  repo <name>      - Test with specific repo fixture"
        echo "  list-repos       - List available repo fixtures"
        echo ""
        list_repo_fixtures
        exit 1
        ;;
esac
