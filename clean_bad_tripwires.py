#!/usr/bin/env python3
"""Clean up files with malformed tripwires."""

import sys
from pathlib import Path


def clean_bad_tripwires(content: str) -> str:
    """Remove malformed tripwires and fix truncated ones."""
    lines = content.split("\n")
    in_frontmatter = False
    in_tripwires = False
    result = []

    i = 0
    while i < len(lines):
        line = lines[i]

        if line.strip() == "---":
            if not in_frontmatter:
                in_frontmatter = True
            else:
                in_frontmatter = False
                in_tripwires = False
            result.append(line)
        elif in_frontmatter and line.startswith("tripwires:"):
            in_tripwires = True
            result.append(line)
        elif in_tripwires:
            # Check for problematic tripwires
            if (
                "performing actions related to this tripwire" in line
                and 'warning: "--"' in lines[i + 1]
                if i + 1 < len(lines)
                else False
            ):
                # Skip this bad tripwire and the next line
                i += 1
                continue
            elif line.strip().endswith("not"):
                # Handle truncated action - look for the full warning text
                if i + 1 < len(lines) and "warning:" in lines[i + 1]:
                    warning_line = lines[i + 1]
                    if "Interactive commands need" in warning_line:
                        result.append(
                            '  - action: "using run_ssh_command() for interactive commands"'
                        )
                        result.append(
                            '    warning: "Interactive commands need'
                            ' exec_ssh_interactive(), not run_ssh_command()"'
                        )
                        i += 1
                        continue
            elif line.strip().endswith("environment -"):
                # Handle truncated action
                if i + 1 < len(lines) and "warning:" in lines[i + 1]:
                    warning_line = lines[i + 1]
                    if "don't duplicate setup" in warning_line:
                        result.append(
                            '  - action: "duplicating environment setup'
                            ' when using build_codespace_ssh_command()"'
                        )
                        result.append(
                            '    warning: "build_codespace_ssh_command()'
                            " bootstraps the environment"
                            " - don't duplicate setup\""
                        )
                        i += 1
                        continue
            elif not line.startswith("  ") and not line.startswith("tripwires:"):
                # We've left the tripwires section
                in_tripwires = False
                result.append(line)
            else:
                result.append(line)
        else:
            result.append(line)

        i += 1

    return "\n".join(result)


def main():
    if len(sys.argv) < 2:
        print("Usage: python clean_bad_tripwires.py <file1.md> [file2.md ...]")
        sys.exit(1)

    for file_path in sys.argv[1:]:
        path = Path(file_path)
        if not path.exists():
            print(f"File not found: {file_path}")
            continue

        try:
            content = path.read_text(encoding="utf-8")
            new_content = clean_bad_tripwires(content)

            if content != new_content:
                path.write_text(new_content, encoding="utf-8")
                print(f"Cleaned: {file_path}")
            else:
                print(f"No changes: {file_path}")

        except Exception as e:
            print(f"Error processing {file_path}: {e}")


if __name__ == "__main__":
    main()
