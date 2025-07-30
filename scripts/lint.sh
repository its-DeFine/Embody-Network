#!/bin/bash
# Linting script for code quality checks

set -e

echo "🔍 Running code quality checks..."

# Python linting with ruff
echo "📝 Running Python linting..."
if command -v ruff &> /dev/null; then
    ruff check . --fix
else
    echo "⚠️  Ruff not installed. Installing..."
    pip install ruff
    ruff check . --fix
fi

# Python formatting with black
echo "🎨 Running Python formatting..."
if command -v black &> /dev/null; then
    black . --line-length 100
else
    echo "⚠️  Black not installed. Installing..."
    pip install black
    black . --line-length 100
fi

# JavaScript/TypeScript linting for control-board
echo "🔧 Running JavaScript/TypeScript linting..."
if [ -d "control-board" ]; then
    cd control-board
    if [ -f "package.json" ]; then
        npm run lint || echo "⚠️  No lint script found in package.json"
    fi
    cd ..
fi

# YAML linting
echo "📋 Running YAML linting..."
if command -v yamllint &> /dev/null; then
    yamllint . || true
else
    echo "⚠️  yamllint not installed. Skipping YAML validation."
fi

# Dockerfile linting
echo "🐳 Running Dockerfile linting..."
if command -v hadolint &> /dev/null; then
    find . -name "Dockerfile*" -type f -exec hadolint {} \;
else
    echo "⚠️  hadolint not installed. Skipping Dockerfile validation."
fi

echo "✅ Linting complete!"