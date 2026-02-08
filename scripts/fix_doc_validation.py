#!/usr/bin/env python3
"""Fix validation errors in docs/learned frontmatter."""

from pathlib import Path
import re
import sys


def extract_frontmatter_and_body(content: str) -> tuple[str, str, str] | None:
    """Extract frontmatter and body from markdown content.

    Returns (before_fm, frontmatter, body) or None if no frontmatter found.
    """
    if not content.startswith('---'):
        return None

    parts = content.split('---', 2)
    if len(parts) < 3:
        return None

    return parts[0], parts[1], parts[2]


def fix_audit_result(frontmatter: str) -> str:
    """Replace audit_result: regenerated with audit_result: clean."""
    result = re.sub(
        r'^(\s*)audit_result:\s*regenerated\s*$',
        r'\1audit_result: clean',
        frontmatter,
        flags=re.MULTILINE
    )

    # Also fix any places where the audit_result got concatenated with following content
    result = re.sub(
        r'^(\s*)audit_result:\s*(clean|edited)([^\n])',
        r'\1audit_result: \2\n\3',
        result,
        flags=re.MULTILINE
    )

    return result


def infer_action_from_warning(warning: str) -> str:
    """Infer an action trigger from the warning text."""
    warning_lower = warning.lower()

    # Common patterns to extract action
    patterns = [
        # "Before X" or "When X" patterns
        (r'before ([^,\.]+)', r'\1'),
        (r'when ([^,\.]+)', r'\1'),
        # "Don't/Never X" patterns
        (r'(?:don\'t|never|avoid)\s+([^,\.]+)', r'\1'),
        # "Always X" patterns
        (r'always ([^,\.]+)', r'\1'),
        # "X is NOT Y" patterns - extract X
        (r'^([A-Z_]+)\s+is\s+NOT', r'using \1'),
        # "CRITICAL: ..." patterns - extract the core action
        (r'CRITICAL:\s*(?:Before\s+)?([^,\.]+)', r'\1'),
    ]

    for pattern, replacement in patterns:
        match = re.search(pattern, warning, re.IGNORECASE)
        if match:
            action = re.sub(pattern, replacement, match.group(0), flags=re.IGNORECASE)
            # Clean up the action text
            action = action.strip().strip('"').strip("'")
            # Truncate if too long
            if len(action) > 80:
                action = action[:77] + '...'
            return action

    # Default: use first 60 chars of warning as action
    action = warning[:60].strip()
    if len(warning) > 60:
        action += '...'
    return action


def fix_tripwires(frontmatter: str) -> str:
    """Convert string tripwires to proper object format with action/warning.

    Also converts trigger/action format to action/warning format.
    """
    lines = frontmatter.split('\n')
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if we're at a tripwires section
        if line.strip().startswith('tripwires:'):
            result.append(line)
            i += 1

            # Process tripwire items
            while i < len(lines):
                line = lines[i]

                # Check if we've left the tripwires section
                if line and not line.startswith(' ') and not line.startswith('\t'):
                    break

                # Check if this is a string tripwire (list item without action:/warning:/trigger:)
                match = re.match(r'^(\s*)-\s+(.+)$', line)
                if match:
                    indent = match.group(1)
                    content = match.group(2)

                    # Check if it's already in object format with action:/warning:
                    if content.startswith('action:') or content.startswith('warning:'):
                        result.append(line)
                        i += 1
                        continue

                    # Check if it uses trigger: instead of action:
                    if content.startswith('trigger:'):
                        # This is trigger/action format - need to convert
                        # Collect the multi-line object
                        obj_lines = [line]
                        j = i + 1
                        while j < len(lines):
                            next_line = lines[j]
                            if re.match(r'^\s+(trigger|action|warning|score):', next_line):
                                obj_lines.append(next_line)
                                j += 1
                            elif next_line.strip() and not next_line.startswith(' ') and not next_line.startswith('\t'):
                                break
                            elif not next_line.strip():
                                j += 1
                            else:
                                j += 1

                        # Parse the object
                        trigger_val = None
                        action_val = None

                        for obj_line in obj_lines:
                            if 'trigger:' in obj_line:
                                trigger_val = obj_line.split('trigger:', 1)[1].strip()
                            elif 'action:' in obj_line:
                                action_val = obj_line.split('action:', 1)[1].strip()

                        # Convert trigger to action, action to warning
                        if trigger_val and action_val:
                            result.append(f'{indent}- action: {trigger_val}')
                            result.append(f'{indent}  warning: {action_val}')
                        elif trigger_val:
                            # Only trigger, no action - use trigger as action
                            result.append(f'{indent}- action: {trigger_val}')
                            result.append(f'{indent}  warning: "See documentation"')

                        # Skip the lines we processed
                        i = j
                        continue

                    # Check if next lines have action:/warning:/trigger: (multi-line object)
                    if i + 1 < len(lines):
                        next_line = lines[i + 1]
                        if re.match(r'^\s+(action|warning):', next_line):
                            # Already in correct format, just on multiple lines
                            result.append(line)
                            i += 1
                            continue
                        elif re.match(r'^\s+trigger:', next_line):
                            # Has trigger: field - will be handled on next iteration
                            result.append(line)
                            i += 1
                            continue

                    # This is a simple string tripwire - convert to object format
                    # Remove quotes if present
                    content = content.strip('"').strip("'")

                    # Infer action from warning content
                    action = infer_action_from_warning(content)

                    # Create object format
                    result.append(f'{indent}- action: "{action}"')
                    result.append(f'{indent}  warning: "{content}"')
                    i += 1
                    continue

                # Keep the line as-is
                result.append(line)
                i += 1
            continue

        # Not in tripwires section, keep line as-is
        result.append(line)
        i += 1

    return '\n'.join(result)


def fix_file(file_path: Path, dry_run: bool = False) -> tuple[bool, str]:
    """Fix validation errors in a single file.

    Returns (changed, message).
    """
    try:
        content = file_path.read_text()
        result = extract_frontmatter_and_body(content)

        if not result:
            return False, "No frontmatter"

        before_fm, frontmatter, body = result
        original_fm = frontmatter

        # Apply fixes
        frontmatter = fix_audit_result(frontmatter)
        frontmatter = fix_tripwires(frontmatter)

        if frontmatter == original_fm:
            return False, "No changes needed"

        if not dry_run:
            new_content = f"{before_fm}---{frontmatter}---{body}"
            file_path.write_text(new_content)
            return True, "Fixed"
        else:
            return True, "Would fix (dry run)"

    except Exception as e:
        return False, f"Error: {e}"


def main():
    docs_dir = Path('docs/learned')

    if not docs_dir.exists():
        print(f"Error: {docs_dir} not found", file=sys.stderr)
        sys.exit(1)

    dry_run = '--dry-run' in sys.argv

    if dry_run:
        print("DRY RUN MODE - no files will be modified\n")

    files_to_fix = sorted(docs_dir.rglob('*.md'))

    changed = []
    unchanged = []
    errors = []

    for file_path in files_to_fix:
        was_changed, message = fix_file(file_path, dry_run=dry_run)

        if "Error:" in message:
            errors.append((file_path, message))
        elif was_changed:
            changed.append((file_path, message))
        else:
            unchanged.append((file_path, message))

    # Print results
    if changed:
        print(f"\n{'Would fix' if dry_run else 'Fixed'} {len(changed)} files:")
        for path, msg in changed[:20]:  # Show first 20
            print(f"  {path.relative_to('docs/learned')}: {msg}")
        if len(changed) > 20:
            print(f"  ... and {len(changed) - 20} more")

    if errors:
        print(f"\nErrors in {len(errors)} files:")
        for path, msg in errors:
            print(f"  {path.relative_to('docs/learned')}: {msg}")

    print(f"\nSummary:")
    print(f"  Changed: {len(changed)}")
    print(f"  Unchanged: {len(unchanged)}")
    print(f"  Errors: {len(errors)}")

    if dry_run and changed:
        print("\nRun without --dry-run to apply changes")

    return 0 if not errors else 1


if __name__ == '__main__':
    sys.exit(main())
