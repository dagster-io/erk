#!/usr/bin/env python3
"""
Update Slack bot icon using the apps.hosted.icon API endpoint.

Usage:
    python update_slack_bot_icon.py --app-id A12345 --icon icon.png --token xoxb-...
"""

import argparse
import sys
from pathlib import Path

import requests
from PIL import Image


def resize_icon(image_path: Path) -> bytes:
    """Resize image to 512x512 pixels as required by Slack."""
    with Image.open(image_path) as img:
        # Convert to RGB if necessary (e.g., RGBA -> RGB)
        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(
                img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None
            )
            img = background

        # Resize to 512x512
        img_resized = img.resize((512, 512), Image.Resampling.LANCZOS)

        # Save to bytes
        from io import BytesIO

        output = BytesIO()
        img_resized.save(output, format="PNG")
        return output.getvalue()


def update_bot_icon(app_id: str, icon_path: Path, token: str) -> dict:
    """
    Update Slack bot icon using the apps.hosted.icon API endpoint.

    Args:
        app_id: Slack app ID (e.g., A12345)
        icon_path: Path to icon file
        token: Slack config token (from tooling.tokens.rotate)

    Returns:
        API response dict
    """
    if not icon_path.exists():
        raise FileNotFoundError(f"Icon file not found: {icon_path}")

    # Resize icon to 512x512
    icon_bytes = resize_icon(icon_path)

    # Prepare multipart form data
    files = {"file": ("icon.png", icon_bytes, "image/png")}
    data = {"app_id": app_id}

    # Make API request
    response = requests.post(
        "https://slack.com/api/apps.hosted.icon",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data=data,
        timeout=30,
    )

    result = response.json()

    if not result.get("ok"):
        raise RuntimeError(
            f"Icon upload failed: {result.get('error', 'Unknown error')}"
        )

    return result


def main():
    parser = argparse.ArgumentParser(description="Update Slack bot icon")
    parser.add_argument("--app-id", required=True, help="Slack app ID (e.g., A12345)")
    parser.add_argument("--icon", required=True, type=Path, help="Path to icon file")
    parser.add_argument("--token", required=True, help="Slack config token")

    args = parser.parse_args()

    try:
        result = update_bot_icon(args.app_id, args.icon, args.token)
        print(f"✅ Icon updated successfully: {result}")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
