#!/usr/bin/env python3
"""Fix tripwires format in frontmatter from string list to object list."""

import re
import sys
import json
from pathlib import Path


def fix_tripwires_format(content: str) -> str:
    """Convert tripwires from string format to action/warning object format.

    Converts:
        tripwires:
          - Some tripwire text
          - Another tripwire

    To:
        tripwires:
          - action: "performing the action described in the tripwire"
            warning: "Some tripwire text"
          - action: "performing the action described in the tripwire"
            warning: "Another tripwire"
    """
    # Pattern to match tripwires section with string items
    pattern = r'(tripwires:\s*\n)((?:\s*-\s*[^\n]+\n?)+)'

    def replace_tripwires(match):
        header = match.group(1)
        items_section = match.group(2)

        # Extract individual tripwire items
        item_pattern = r'\s*-\s*([^\n]+)'
        items = re.findall(item_pattern, items_section)

        if not items:
            return match.group(0)

        # Check if already in new format (contains "action:" or "warning:")
        if any("action:" in item or "warning:" in item for item in items):
            return match.group(0)

        # Convert to new format
        new_items = []
        for item in items:
            # Extract action from the warning text (heuristic)
            item = item.strip()
            if item.startswith('"') and item.endswith('"'):
                item = item[1:-1]

            # Try to extract action from common patterns
            if " — " in item:
                # Format: "Never do X — explanation"
                action_part, warning_part = item.split(" — ", 1)
                if action_part.lower().startswith("never "):
                    action = action_part.lower().replace("never ", "").strip()
                elif action_part.lower().startswith("always "):
                    action = action_part.lower().replace("always ", "").strip()
                elif action_part.lower().startswith("prefer "):
                    action = action_part.lower().replace("prefer ", "preferring ").strip()
                elif action_part.lower().startswith("avoid "):
                    action = action_part.lower().replace("avoid ", "avoiding ").strip()
                elif action_part.lower().startswith("use "):
                    action = action_part.lower().replace("use ", "using ").strip()
                else:
                    # Extract meaningful action phrase
                    action = action_part.strip().lower()
                warning = item
            elif item.lower().startswith("never "):
                # "Never do X"
                action = item.lower().replace("never ", "").strip()
                if " when " in action:
                    action = action.split(" when ")[0].strip()
                if " if " in action:
                    action = action.split(" if ")[0].strip()
                warning = item
            elif item.lower().startswith("always "):
                action = item.lower().replace("always ", "").strip()
                warning = item
            elif item.lower().startswith("prefer "):
                action = item.lower().replace("prefer ", "preferring ").strip()
                warning = item
            elif item.lower().startswith("avoid "):
                action = item.lower().replace("avoid ", "avoiding ").strip()
                warning = item
            elif item.lower().startswith("use "):
                action = item.lower().replace("use ", "using ").strip()
                warning = item
            else:
                # Generic fallback - try to extract first meaningful phrase
                words = item.split()
                if len(words) > 5:
                    action = " ".join(words[:5]).lower()
                else:
                    action = "performing actions related to this tripwire"
                warning = item

            # Clean up action
            action = action.strip()

            # Format as YAML object with proper escaping
            # Use JSON encoding to properly escape the strings, then convert to YAML format
            action_escaped = json.dumps(action)
            warning_escaped = json.dumps(warning)
            new_items.append(f'  - action: {action_escaped}\n    warning: {warning_escaped}')

        return header + "\n".join(new_items) + "\n"

    return re.sub(pattern, replace_tripwires, content, flags=re.MULTILINE)


def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_tripwires.py <file1.md> [file2.md ...]")
        sys.exit(1)

    for file_path in sys.argv[1:]:
        path = Path(file_path)
        if not path.exists():
            print(f"File not found: {file_path}")
            continue

        try:
            content = path.read_text(encoding="utf-8")
            new_content = fix_tripwires_format(content)

            if content != new_content:
                path.write_text(new_content, encoding="utf-8")
                print(f"Fixed: {file_path}")
            else:
                print(f"No changes: {file_path}")

        except Exception as e:
            print(f"Error processing {file_path}: {e}")


if __name__ == "__main__":
    main()
