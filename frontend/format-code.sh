#!/bin/bash

# Frontend Code Formatting Script
# Automatically format all frontend code files

set -e

echo "🎨 Formatting Frontend Code..."
echo "=============================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to frontend directory
cd "$(dirname "$0")"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 Installing dependencies...${NC}"
    npm install
    echo ""
fi

# Run Prettier
echo "🎨 Running Prettier formatter..."
npm run format
echo -e "${GREEN}✅ Code formatting complete!${NC}"
echo ""

# Run ESLint auto-fix
echo "🔧 Running ESLint auto-fix..."
npm run lint:fix
echo -e "${GREEN}✅ ESLint auto-fix complete!${NC}"
echo ""

echo "=============================="
echo -e "${GREEN}✨ All code has been formatted!${NC}"
echo ""
echo "📝 Summary of formatting:"
echo "  - Prettier: Applied consistent code style"
echo "  - ESLint: Fixed auto-fixable issues"
echo ""
echo -e "${YELLOW}💡 Tip: Run './check-quality.sh' to verify all checks pass${NC}"