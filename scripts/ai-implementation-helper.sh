#!/usr/bin/env bash
#
# AI Implementation Helper
# Developer CLI tool for working with the AI Implementation System

set -euo pipefail

REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Usage information
usage() {
    cat <<EOF
AI Implementation Helper

Usage:
  $0 <command> [options]

Commands:
  list                 List all available plan files
  validate <plan>      Validate plan file structure
  trigger <plan>       Trigger AI implementation workflow
  trigger-quick <plan> Trigger quick implementation (no validation)
  status               Check status of recent workflow runs
  help                 Show this help message

Examples:
  $0 list
  $0 validate feature-auth-plan.md
  $0 trigger feature-auth-plan.md
  $0 trigger-quick prototype-plan.md
  $0 status

Requirements:
  - gh (GitHub CLI) must be installed and authenticated
  - Repository must have AI Implementation workflows configured
EOF
}

# Check if gh CLI is installed
check_gh_cli() {
    if ! command -v gh &> /dev/null; then
        echo -e "${RED}Error: GitHub CLI (gh) is not installed${NC}"
        echo "Install from: https://cli.github.com/"
        exit 1
    fi

    if ! gh auth status &> /dev/null; then
        echo -e "${RED}Error: GitHub CLI is not authenticated${NC}"
        echo "Run: gh auth login"
        exit 1
    fi
}

# List all plan files
list_plans() {
    echo -e "${CYAN}Available plan files:${NC}"
    echo ""

    plans=$(find . -maxdepth 1 -name "*-plan.md" -type f | sort)

    if [ -z "$plans" ]; then
        echo -e "${YELLOW}No plan files found in repository root${NC}"
        echo "Plan files should match pattern: *-plan.md"
        return
    fi

    for plan in $plans; do
        plan_file=$(basename "$plan")

        # Check if enriched
        if grep -q "enriched_by_persist_plan: true" "$plan" 2>/dev/null; then
            enriched="${GREEN}✓ enriched${NC}"
        else
            enriched="${YELLOW}⚠ not enriched${NC}"
        fi

        # Extract objective if available
        objective=$(grep -E "^##? (Objective|Goal)" "$plan" -A 1 | tail -n 1 | sed 's/^[[:space:]]*//' || echo "")

        echo -e "  ${BLUE}$plan_file${NC} ($enriched)"
        if [ -n "$objective" ]; then
            echo -e "    ${objective:0:80}..."
        fi
        echo ""
    done
}

# Validate plan file structure
validate_plan() {
    local plan_file="$1"

    if [ ! -f "$plan_file" ]; then
        echo -e "${RED}Error: Plan file '$plan_file' not found${NC}"
        exit 1
    fi

    echo -e "${CYAN}Validating plan: $plan_file${NC}"
    echo ""

    local errors=0

    # Check for enrichment marker
    if grep -q "enriched_by_persist_plan: true" "$plan_file"; then
        echo -e "${GREEN}✓${NC} Plan is enriched by /erk:persist-plan"
    else
        echo -e "${YELLOW}⚠${NC} Plan may not be enriched (missing enriched_by_persist_plan marker)"
        echo "  Run /erk:persist-plan to enrich the plan with context"
    fi

    # Check for required sections
    if grep -q -E "## Implementation (Steps|Phases)" "$plan_file"; then
        echo -e "${GREEN}✓${NC} Has Implementation Steps/Phases section"
    else
        echo -e "${RED}✗${NC} Missing Implementation Steps/Phases section"
        errors=$((errors + 1))
    fi

    if grep -q "## Objective" "$plan_file" || grep -q "## Goal" "$plan_file"; then
        echo -e "${GREEN}✓${NC} Has Objective/Goal section"
    else
        echo -e "${YELLOW}⚠${NC} Missing Objective/Goal section (recommended)"
    fi

    if grep -q "## Context" "$plan_file"; then
        echo -e "${GREEN}✓${NC} Has Context section"
    else
        echo -e "${YELLOW}⚠${NC} Missing Context section (recommended for enriched plans)"
    fi

    echo ""
    if [ $errors -eq 0 ]; then
        echo -e "${GREEN}✓ Plan validation passed${NC}"
        return 0
    else
        echo -e "${RED}✗ Plan validation failed with $errors error(s)${NC}"
        return 1
    fi
}

# Trigger AI implementation workflow
trigger_workflow() {
    local plan_file="$1"
    local workflow="$2"
    local validation_level="${3:-full}"

    check_gh_cli

    if [ ! -f "$plan_file" ]; then
        echo -e "${RED}Error: Plan file '$plan_file' not found${NC}"
        exit 1
    fi

    # Validate plan first
    echo -e "${CYAN}Pre-flight validation...${NC}"
    if ! validate_plan "$plan_file"; then
        echo ""
        echo -e "${YELLOW}Plan validation failed. Continue anyway? (y/N)${NC}"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo "Aborted"
            exit 0
        fi
    fi

    echo ""
    echo -e "${CYAN}Triggering workflow: $workflow${NC}"
    echo -e "  Plan: ${BLUE}$plan_file${NC}"
    echo -e "  Validation: ${validation_level}"
    echo ""

    # Trigger workflow
    if [ "$workflow" = "ai-implement.yml" ]; then
        gh workflow run "$workflow" \
            -f plan-file="$plan_file" \
            -f validation-level="$validation_level"
    else
        gh workflow run "$workflow" \
            -f plan-file="$plan_file"
    fi

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Workflow triggered successfully${NC}"
        echo ""
        echo "Monitor progress:"
        echo "  gh run list --workflow=$workflow"
        echo "  gh run watch"
        echo ""
        echo "Or view in browser:"
        gh repo view --web --branch main
    else
        echo -e "${RED}✗ Failed to trigger workflow${NC}"
        exit 1
    fi
}

# Check status of recent workflow runs
check_status() {
    check_gh_cli

    echo -e "${CYAN}Recent AI Implementation workflow runs:${NC}"
    echo ""

    gh run list \
        --workflow=ai-implement.yml \
        --workflow=ai-implement-quick.yml \
        --limit 10 \
        --json status,conclusion,displayTitle,createdAt,url \
        --template '{{range .}}{{tablerow .displayTitle (.status | color "yellow") (if .conclusion .conclusion "-" | color "green") (.createdAt | timeago) .url}}{{end}}'

    echo ""
    echo "View logs: gh run view <run-id> --log"
    echo "Watch latest: gh run watch"
}

# Main command dispatcher
main() {
    if [ $# -eq 0 ]; then
        usage
        exit 0
    fi

    local command="$1"
    shift

    case "$command" in
        list)
            list_plans
            ;;
        validate)
            if [ $# -lt 1 ]; then
                echo -e "${RED}Error: Missing plan file argument${NC}"
                echo "Usage: $0 validate <plan-file>"
                exit 1
            fi
            validate_plan "$1"
            ;;
        trigger)
            if [ $# -lt 1 ]; then
                echo -e "${RED}Error: Missing plan file argument${NC}"
                echo "Usage: $0 trigger <plan-file> [validation-level]"
                exit 1
            fi
            trigger_workflow "$1" "ai-implement.yml" "${2:-full}"
            ;;
        trigger-quick)
            if [ $# -lt 1 ]; then
                echo -e "${RED}Error: Missing plan file argument${NC}"
                echo "Usage: $0 trigger-quick <plan-file>"
                exit 1
            fi
            trigger_workflow "$1" "ai-implement-quick.yml" "none"
            ;;
        status)
            check_status
            ;;
        help|--help|-h)
            usage
            ;;
        *)
            echo -e "${RED}Error: Unknown command '$command'${NC}"
            echo ""
            usage
            exit 1
            ;;
    esac
}

main "$@"
