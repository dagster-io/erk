#!/usr/bin/env python3
"""Remove tripwires sections from frontmatter."""

import sys
from pathlib import Path


def remove_tripwires(content: str) -> str:
    """Remove tripwires section from frontmatter."""
    lines = content.split("\n")
    in_frontmatter = False
    in_tripwires = False
    result = []

    for line in lines:
        if line.strip() == "---":
            if not in_frontmatter:
                in_frontmatter = True
                result.append(line)
            else:
                # End of frontmatter
                in_frontmatter = False
                in_tripwires = False
                result.append(line)
        elif in_frontmatter and line.startswith("tripwires:"):
            in_tripwires = True
            # Don't add the tripwires: line
        elif in_tripwires:
            # Skip all tripwire content until we hit a non-indented line or end of frontmatter
            if line.startswith("  ") or line.startswith("\t") or line.strip() == "":
                # Skip this line (it's part of tripwires)
                continue
            else:
                # This is the start of a new frontmatter field
                in_tripwires = False
                result.append(line)
        else:
            result.append(line)

    return "\n".join(result)


def main():
    if len(sys.argv) < 2:
        print("Usage: python remove_tripwires.py <file1.md> [file2.md ...]")
        sys.exit(1)

    for file_path in sys.argv[1:]:
        path = Path(file_path)
        if not path.exists():
            print(f"File not found: {file_path}")
            continue

        try:
            content = path.read_text(encoding="utf-8")
            new_content = remove_tripwires(content)

            if content != new_content:
                path.write_text(new_content, encoding="utf-8")
                print(f"Removed tripwires from: {file_path}")
            else:
                print(f"No changes: {file_path}")

        except Exception as e:
            print(f"Error processing {file_path}: {e}")


if __name__ == "__main__":
    main()
