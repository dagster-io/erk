"""Prompts for the learn feature."""

# Prompt for converting a batch of JSONL session entries to XML
BATCH_TO_XML_PROMPT = """Convert these JSONL session entries to XML elements.

For each entry, output ONE of:
- <user>MESSAGE</user>
- <assistant>MESSAGE</assistant>
- <tool_use name="NAME">SUMMARY</tool_use>
- <tool_result tool="NAME">SUMMARY</tool_result>
- (skip if not meaningful - e.g., queue operations, metadata-only entries)

Guidelines:
- Keep summaries concise (< 200 chars for tool results)
- Preserve errors and warnings verbatim
- For tool_use, include the tool name and a brief description of what it does
- For tool_result, summarize the key outcome
- Skip entries that are purely system/queue metadata

Entries:
{batch_content}

Output only XML elements, no wrapper or explanation."""

# Prompt for synthesizing documentation gaps from a session
LEARN_SYNTHESIS_PROMPT = """Analyze this implementation session and identify documentation gaps.

Focus on actionable documentation improvements:

1. **Information Hunts**: What required extensive exploration to find?
2. **Repeated Explanations**: What concepts were explained multiple times?
3. **Trial and Error**: What patterns were discovered through debugging?
4. **Missing Context**: What background knowledge was assumed but not documented?

Skip:
- What was built (that's for Phase 2 - teaching gaps)
- General observations about code quality
- Implementation details that are self-documenting

For each gap found, provide:
- What doc is missing/incomplete
- Where it should live (file path or doc section)
- What it should contain (specific content suggestions)

Session content:
{session_xml}

Branch: {branch_name}
PR: #{pr_number}

Output format: Bulleted list of specific documentation improvements."""
