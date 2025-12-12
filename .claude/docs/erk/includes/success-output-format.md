# Success Output Format

After creating the issue, output this exact format:

```markdown
✅ GitHub issue created: #<number>
<issue-url>

Next steps:

View Issue: gh issue view <number> --web
Interactive Execution: erk implement <number>
Dangerous Interactive Execution: erk implement <number> --dangerous
Yolo One Shot: erk implement <number> --yolo

---

{"issue_number": <number>, "issue_url": "<url>", "status": "created"}
```

**Verify your output includes:**

- ✅ Issue number and URL on first line
- ✅ "Next steps:" header
- ✅ Four commands with actual issue number (not placeholder)
- ✅ JSON metadata with issue_number, issue_url, and status
- ❌ NO placeholders like <number> or <url> in final output
