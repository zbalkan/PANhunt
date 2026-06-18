#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "Usage: $(basename "$0") <test|prod>"
    echo "  test  Upload to TestPyPI"
    echo "  prod  Upload to PyPI"
    exit 1
}

[[ $# -eq 1 ]] || usage
[[ "$1" == "test" || "$1" == "prod" ]] || usage

TARGET="$1"
VENV_DIR=".venv"
VENV_CREATED=false

if [[ ! -f "pyproject.toml" ]]; then
    echo "Error: run this script from the repository root." >&2
    exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    VENV_CREATED=true
fi

PYTHON="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

echo "Installing build dependencies..."
"$PIP" install --quiet --upgrade pip
"$PIP" install --quiet build twine

echo "Removing previous build artifacts..."
rm -rf dist/ build/
find . -maxdepth 3 \( -name "*.egg-info" -o -name "*.egg" \) -exec rm -rf {} +

echo "Building distribution..."
"$PYTHON" -m build

echo "Checking distribution..."
"$PYTHON" -m twine check dist/*

if [[ "$TARGET" == "test" ]]; then
    echo "Uploading to TestPyPI..."
    "$PYTHON" -m twine upload --repository testpypi dist/*
else
    echo "Uploading to PyPI..."
    "$PYTHON" -m twine upload dist/*
fi

if [[ "$VENV_CREATED" == true ]]; then
    echo "Removing virtual environment..."
    rm -rf "$VENV_DIR"
fi

echo "Done."
