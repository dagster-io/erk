---
erk:
  kit: erk
---

# Create GitHub Issue

Create the issue using the kit CLI command:

```bash
# Write plan content to temp file
tmpfile=$(mktemp)
cat > "$tmpfile" << 'EOF'
$PLAN_CONTENT
EOF

# Create issue from file (command accepts raw content despite name)
issue_url=$(erk exec create-enriched-plan-from-context --plan-file "$tmpfile")
exit_code=$?

# Clean up temp file
rm "$tmpfile"

# Check for errors
if [ $exit_code -ne 0 ]; then
    echo "❌ Error: Failed to create GitHub issue" >&2
    exit 1
fi
```

**Note:** The `create-enriched-plan-from-context` command accepts raw content. Despite the name suggesting enrichment, it creates issues from any markdown content.

**Extract issue number from URL:**

Parse the issue number from the returned URL (e.g., `https://github.com/org/repo/issues/123` → `123`)

**If issue creation fails:**

```
❌ Error: Failed to create GitHub issue

Details: [specific error from kit CLI command]

Suggested action:
  1. Verify GitHub CLI (gh) is installed and authenticated
  2. Check repository has issues enabled
  3. Verify network connectivity
  4. Check gh auth status
```
