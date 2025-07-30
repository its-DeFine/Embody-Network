#!/bin/bash
# Full repository cleanup script
# Removes temporary files, caches, and test outputs

set -e

echo "🧹 AutoGen Platform Repository Cleanup"
echo "====================================="
echo

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Function to print status
print_status() {
    echo -e "${2}${1}${NC}"
}

# 1. Remove Python cache directories
print_status "Removing Python cache directories..." "$YELLOW"
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
print_status "✅ Python caches cleaned" "$GREEN"

# 2. Remove test result directories
print_status "Removing test result directories..." "$YELLOW"
rm -rf test-results-*/ 2>/dev/null || true
print_status "✅ Test results cleaned" "$GREEN"

# 3. Remove temporary JSON files
print_status "Removing temporary files..." "$YELLOW"
rm -f dual_mode_validation_*.json 2>/dev/null || true
print_status "✅ Temporary files cleaned" "$GREEN"

# 4. Clean log directories
print_status "Cleaning log directories..." "$YELLOW"
rm -rf logs/dual_mode_test_*/ 2>/dev/null || true
rm -rf logs/live_trading_*/ 2>/dev/null || true
# Keep the logs directory but remove contents
find logs -type f -delete 2>/dev/null || true
print_status "✅ Logs cleaned" "$GREEN"

# 5. Clean temporary reports
print_status "Cleaning temporary reports..." "$YELLOW"
rm -f onboarding_reports/*.json 2>/dev/null || true
rm -f prediction-market-agent/docker/fast-trading/ai-trading-bot/trading_results/*.json 2>/dev/null || true
print_status "✅ Temporary reports cleaned" "$GREEN"

# 6. Update .gitignore if needed
print_status "Checking .gitignore..." "$YELLOW"
if ! grep -q "control-board/node_modules" .gitignore 2>/dev/null; then
    echo "control-board/node_modules/" >> .gitignore
    print_status "✅ Added node_modules to .gitignore" "$GREEN"
else
    print_status "✅ .gitignore already contains node_modules" "$GREEN"
fi

# 7. Git operations (if in a git repo)
if [ -d .git ]; then
    print_status "Updating git tracking..." "$YELLOW"
    
    # Untrack docker-compose.override.yml if it's tracked
    if git ls-files --error-unmatch docker-compose.override.yml >/dev/null 2>&1; then
        git rm --cached docker-compose.override.yml 2>/dev/null || true
        print_status "✅ Untracked docker-compose.override.yml" "$GREEN"
    fi
    
    # Untrack node_modules if it's tracked
    if git ls-files --error-unmatch control-board/node_modules >/dev/null 2>&1; then
        git rm -r --cached control-board/node_modules 2>/dev/null || true
        print_status "✅ Untracked node_modules" "$GREEN"
    fi
fi

# 8. Docker cleanup (optional)
read -p "Do you want to clean Docker resources? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Cleaning Docker resources..." "$YELLOW"
    docker system prune -f 2>/dev/null || true
    print_status "✅ Docker resources cleaned" "$GREEN"
fi

# 9. Summary
echo
print_status "🎉 Cleanup Summary:" "$GREEN"
echo "  - Python caches removed"
echo "  - Test results removed"
echo "  - Temporary files removed"
echo "  - Logs cleaned"
echo "  - Reports cleaned"
echo "  - Git tracking updated"

# Show disk usage
echo
print_status "💾 Current repository size:" "$YELLOW"
du -sh . 2>/dev/null | awk '{print "  Total: " $1}'
du -sh control-board/node_modules 2>/dev/null | awk '{print "  Node modules: " $1}' || echo "  Node modules: Not found"

echo
print_status "✨ Repository cleanup complete!" "$GREEN"

# Remind about uncommitted files
if [ -d .git ]; then
    echo
    print_status "📝 Consider committing these files:" "$YELLOW"
    [ -f .github/workflows/ci-cd.yml ] && [ ! -f .git/index ] || git ls-files --others --exclude-standard | grep -E "(Makefile|pytest.ini|.github/workflows/ci-cd.yml)" || true
fi