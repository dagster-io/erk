#!/bin/bash
# Check if .venv exists but VIRTUAL_ENV is not set to the correct path

if [ -d ".venv" ]; then
    expected_venv="$(cd .venv && pwd)"
    if [ "$VIRTUAL_ENV" != "$expected_venv" ]; then
        echo "Warning: Virtual environment .venv exists but is not activated. Run: source .venv/bin/activate"
    fi
fi
