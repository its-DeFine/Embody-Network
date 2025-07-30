#!/bin/bash
# Release preparation script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🚀 Preparing for release..."

# Check if we're on a clean working directory
if [[ -n $(git status -s) ]]; then
    echo -e "${RED}❌ Working directory is not clean. Please commit or stash changes.${NC}"
    exit 1
fi

# Get current version
CURRENT_VERSION=$(grep -E "version.*=" setup.py 2>/dev/null | grep -oE "[0-9]+\.[0-9]+\.[0-9]+" || echo "1.0.0")
echo "Current version: $CURRENT_VERSION"

# Prompt for new version
read -p "Enter new version (current: $CURRENT_VERSION): " NEW_VERSION
if [[ -z "$NEW_VERSION" ]]; then
    NEW_VERSION=$CURRENT_VERSION
fi

echo "📋 Release checklist:"

# Run tests
echo -e "${YELLOW}Running tests...${NC}"
make test || { echo -e "${RED}❌ Tests failed!${NC}"; exit 1; }
echo -e "${GREEN}✅ Tests passed${NC}"

# Run linting
echo -e "${YELLOW}Running linting...${NC}"
./scripts/lint.sh || { echo -e "${RED}❌ Linting failed!${NC}"; exit 1; }
echo -e "${GREEN}✅ Linting passed${NC}"

# Run security scan
echo -e "${YELLOW}Running security scan...${NC}"
./scripts/security_scan.sh || { echo -e "${RED}❌ Security issues found!${NC}"; exit 1; }
echo -e "${GREEN}✅ Security scan passed${NC}"

# Build Docker images
echo -e "${YELLOW}Building Docker images...${NC}"
make build || { echo -e "${RED}❌ Docker build failed!${NC}"; exit 1; }
echo -e "${GREEN}✅ Docker images built${NC}"

# Update version in files
echo -e "${YELLOW}Updating version to $NEW_VERSION...${NC}"
# Update version in Python files
find . -name "setup.py" -o -name "__version__.py" -o -name "_version.py" | while read -r file; do
    sed -i.bak "s/$CURRENT_VERSION/$NEW_VERSION/g" "$file"
    rm "${file}.bak"
done

# Update version in package.json files
find . -name "package.json" -type f | while read -r file; do
    sed -i.bak "s/\"version\": \".*\"/\"version\": \"$NEW_VERSION\"/g" "$file"
    rm "${file}.bak"
done

# Update documentation
echo -e "${YELLOW}Updating documentation...${NC}"
sed -i.bak "s/Version: .*/Version: $NEW_VERSION/" docs/INDEX.md
rm docs/INDEX.md.bak

# Generate changelog entry
echo -e "${YELLOW}Generating changelog entry...${NC}"
cat > RELEASE_NOTES_${NEW_VERSION}.md << EOF
# Release Notes - Version $NEW_VERSION

Release Date: $(date +%Y-%m-%d)

## Features
- [Add feature descriptions here]

## Bug Fixes
- [Add bug fix descriptions here]

## Breaking Changes
- [Add breaking changes here]

## Security Updates
- [Add security updates here]

## Documentation
- [Add documentation updates here]
EOF

echo -e "${GREEN}✅ Created RELEASE_NOTES_${NEW_VERSION}.md - Please edit before committing${NC}"

# Create git tag
echo -e "${YELLOW}Creating git tag v$NEW_VERSION...${NC}"
git add -A
git commit -m "chore: Release version $NEW_VERSION

- Update version numbers
- Add release notes
- Prepare for deployment"

git tag -a "v$NEW_VERSION" -m "Release version $NEW_VERSION"

echo -e "${GREEN}✅ Release preparation complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Review and edit RELEASE_NOTES_${NEW_VERSION}.md"
echo "2. Push changes: git push origin main --tags"
echo "3. Create GitHub release from tag v$NEW_VERSION"
echo "4. Deploy to production"