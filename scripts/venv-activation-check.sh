#!/bin/bash
# Check if .venv exists but VIRTUAL_ENV is not set to the correct path
# Blocks session start (exit 2) if venv is not activated

if [ -d ".venv" ]; then
    expected_venv="$(cd .venv && pwd)"
    if [ "$VIRTUAL_ENV" != "$expected_venv" ]; then
        echo "❌ Virtual environment .venv exists but is not activated."
        echo ""
        echo "Activate with:  ! source .venv/bin/activate"
        exit 2  # Block session start
    fi
fi
