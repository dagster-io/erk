#!/usr/bin/env python3
"""Generate render.yaml from render.yaml.jinja template.

This script reads the Jinja2 template and generates the final render.yaml file.
It should be run whenever the template is modified.
"""

import subprocess
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined


def generate_render_yaml() -> None:
    """Generate render.yaml from the Jinja2 template."""
    repo_root = Path(__file__).parent.parent
    template_path = repo_root / "render.yaml.jinja"
    output_path = repo_root / "render.yaml"

    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    # Set up Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(repo_root),
        undefined=StrictUndefined,  # Raise error on undefined variables
        trim_blocks=True,  # Remove first newline after block
        lstrip_blocks=True,  # Strip leading spaces before blocks
    )

    # Load and render template
    template = env.get_template("render.yaml.jinja")
    rendered = template.render()

    # Write output
    output_path.write_text(rendered, encoding="utf-8")
    print(f"Generated {output_path} from {template_path}")

    # Run prettier on the generated file
    # Try npx first (works in CI), then fall back to prettier in PATH
    for prettier_cmd in [["npx", "prettier"], ["prettier"]]:
        try:
            result = subprocess.run(
                [*prettier_cmd, "--write", str(output_path)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,  # Don't raise on non-zero exit
            )
            if result.returncode == 0:  # Prettier succeeded
                print(f"Formatted {output_path} with prettier")
                break
        except FileNotFoundError:
            continue  # Try next command
    else:
        # Neither command worked - skip prettier formatting
        print("Warning: prettier not found, skipping formatting")


if __name__ == "__main__":
    generate_render_yaml()
