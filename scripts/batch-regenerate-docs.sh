#!/usr/bin/env bash
set -euo pipefail

# Batch Regenerate and Audit Recently Created Docs
#
# Discovers docs created in the last 2 weeks, regenerates each against
# current content quality standards, then audits with /local:audit-doc.
#
# Usage:
#   ./scripts/batch-regenerate-docs.sh                           # sequential, opus model
#   ./scripts/batch-regenerate-docs.sh --model sonnet            # use sonnet
#   ./scripts/batch-regenerate-docs.sh --dry-run                 # list docs only
#   ./scripts/batch-regenerate-docs.sh --limit 5                 # first 5 docs
#   ./scripts/batch-regenerate-docs.sh --resume-after docs/learned/architecture/fail-open-patterns.md

# --- Defaults ---
MODEL="opus"
DRY_RUN=false
LIMIT=0
RESUME_AFTER=""
TIMEOUT=300

# --- Parse arguments ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        --model)
            MODEL="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --limit)
            LIMIT="$2"
            shift 2
            ;;
        --resume-after)
            RESUME_AFTER="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1" >&2
            echo "Usage: $0 [--model MODEL] [--dry-run] [--limit N] [--resume-after PATH] [--timeout SECS]" >&2
            exit 1
            ;;
    esac
done

# --- Discover docs ---
echo "Discovering docs created in the last 2 weeks..."

DOCS=$(git log --since="2 weeks ago" --diff-filter=A --name-only --pretty=format: -- docs/learned/ \
    | grep -v '^$' \
    | grep '\.md$' \
    | grep -v 'index\.md$' \
    | grep -v 'tripwires\.md$' \
    | grep -v 'tripwires-index\.md$' \
    | sort -u)

# Filter to docs that still exist on disk
EXISTING_DOCS=()
while IFS= read -r doc; do
    if [[ -f "$doc" ]]; then
        EXISTING_DOCS+=("$doc")
    fi
done <<< "$DOCS"

TOTAL=${#EXISTING_DOCS[@]}
echo "Found $TOTAL docs (after filtering deleted/renamed)"

# --- Handle resume-after ---
if [[ -n "$RESUME_AFTER" ]]; then
    SKIP=true
    FILTERED=()
    for doc in "${EXISTING_DOCS[@]}"; do
        if [[ "$SKIP" == true ]]; then
            if [[ "$doc" == "$RESUME_AFTER" ]]; then
                SKIP=false
            fi
            continue
        fi
        FILTERED+=("$doc")
    done
    EXISTING_DOCS=("${FILTERED[@]}")
    echo "Resuming after $RESUME_AFTER: ${#EXISTING_DOCS[@]} docs remaining"
fi

# --- Handle limit ---
if [[ "$LIMIT" -gt 0 ]] && [[ "$LIMIT" -lt ${#EXISTING_DOCS[@]} ]]; then
    EXISTING_DOCS=("${EXISTING_DOCS[@]:0:$LIMIT}")
    echo "Limited to $LIMIT docs"
fi

# --- Dry run ---
if [[ "$DRY_RUN" == true ]]; then
    echo ""
    echo "Dry run: listing ${#EXISTING_DOCS[@]} docs that would be processed:"
    echo ""
    for doc in "${EXISTING_DOCS[@]}"; do
        echo "  $doc"
    done
    echo ""
    echo "Total: ${#EXISTING_DOCS[@]} docs"
    exit 0
fi

# --- Create log directory ---
LOG_DIR="logs/batch-regen-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$LOG_DIR"
echo "Log directory: $LOG_DIR"

# --- Regeneration prompt ---
REGEN_PROMPT_TEMPLATE='You are regenerating a learned doc to meet current content quality standards.

## Instructions

1. Read the content quality standards from .claude/skills/learned-docs/learned-docs-core.md
2. Read the document at: DOC_PATH_PLACEHOLDER
3. Extract all source code file references from the document (file paths, imports, function names)
4. Read every referenced source file to understand the actual code
5. Completely rewrite the document following the quality standards:
   - Only cross-cutting insights (not single-artifact knowledge)
   - Explain WHY, not WHAT — the code already shows the what
   - One Code Rule: no reproduced source code except: data formats, third-party API patterns, anti-patterns marked WRONG, and I/O examples
   - Use source pointers (see docs/learned/documentation/source-pointers.md for format) instead of code blocks
   - Keep: decision tables, anti-patterns with explanations, cross-cutting patterns, historical context, tripwires
   - Remove: import paths, function signatures, docstring paraphrases, file listings
6. Preserve the frontmatter structure (title, read_when, tripwires) — improve their quality if needed but keep the same fields
7. Save the rewritten document to the same path

Do NOT change the document'\''s topic or scope. Regenerate it in-place with higher quality content.'

# --- Main loop ---
PROCESSED=0
SUCCEEDED=0
FAILED=0
FAILED_DOCS=()
START_TIME=$(date +%s)

set +e  # Continue on individual failures

for doc in "${EXISTING_DOCS[@]}"; do
    PROCESSED=$((PROCESSED + 1))
    SANITIZED=$(echo "$doc" | tr '/' '-')
    echo ""
    echo "[$PROCESSED/${#EXISTING_DOCS[@]}] Processing: $doc"

    # Step 1: Regenerate
    REGEN_PROMPT="${REGEN_PROMPT_TEMPLATE//DOC_PATH_PLACEHOLDER/$doc}"
    REGEN_LOG="$LOG_DIR/${SANITIZED}-regen.log"

    echo "  Regenerating..."
    DOC_START=$(date +%s)

    timeout "$TIMEOUT" claude --print \
        --dangerously-skip-permissions \
        --model "$MODEL" \
        "$REGEN_PROMPT" \
        > "$REGEN_LOG" 2>&1
    REGEN_EXIT=$?

    if [[ $REGEN_EXIT -ne 0 ]]; then
        echo "  FAILED (regeneration exit code: $REGEN_EXIT)"
        FAILED=$((FAILED + 1))
        FAILED_DOCS+=("$doc (regen)")
        DOC_END=$(date +%s)
        echo "$doc | FAILED (regen) | $((DOC_END - DOC_START))s" >> "$LOG_DIR/summary.log"
        continue
    fi

    # Step 2: Audit
    AUDIT_LOG="$LOG_DIR/${SANITIZED}-audit.log"

    echo "  Auditing..."
    timeout "$TIMEOUT" claude --print \
        --dangerously-skip-permissions \
        --model "$MODEL" \
        "/local:audit-doc $doc --auto-apply" \
        > "$AUDIT_LOG" 2>&1
    AUDIT_EXIT=$?

    DOC_END=$(date +%s)
    DOC_ELAPSED=$((DOC_END - DOC_START))

    if [[ $AUDIT_EXIT -ne 0 ]]; then
        echo "  FAILED (audit exit code: $AUDIT_EXIT)"
        FAILED=$((FAILED + 1))
        FAILED_DOCS+=("$doc (audit)")
        echo "$doc | FAILED (audit) | ${DOC_ELAPSED}s" >> "$LOG_DIR/summary.log"
        continue
    fi

    echo "  OK (${DOC_ELAPSED}s)"
    SUCCEEDED=$((SUCCEEDED + 1))
    echo "$doc | OK | ${DOC_ELAPSED}s" >> "$LOG_DIR/summary.log"
done

set -e

# --- Summary ---
END_TIME=$(date +%s)
TOTAL_ELAPSED=$((END_TIME - START_TIME))

echo ""
echo "=========================================="
echo "Batch Regeneration Complete"
echo "=========================================="
echo "Total docs:  ${#EXISTING_DOCS[@]}"
echo "Succeeded:   $SUCCEEDED"
echo "Failed:      $FAILED"
echo "Elapsed:     ${TOTAL_ELAPSED}s"
echo "Logs:        $LOG_DIR/"
echo "=========================================="

if [[ ${#FAILED_DOCS[@]} -gt 0 ]]; then
    echo ""
    echo "Failed docs (retry manually):"
    for fd in "${FAILED_DOCS[@]}"; do
        echo "  $fd"
    done
fi
