#!/bin/bash

# Frontend Code Quality Check Script
# Run all quality checks for the frontend codebase

set -e

echo "🔍 Running Frontend Code Quality Checks..."
echo "========================================="

# Colors for output
RED='\033[0;31m'
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

# Run Prettier check
echo "🎨 Checking code formatting with Prettier..."
if npm run format:check; then
    echo -e "${GREEN}✅ Code formatting check passed!${NC}"
else
    echo -e "${RED}❌ Code formatting issues found!${NC}"
    echo -e "${YELLOW}   Run 'npm run format' to fix formatting issues${NC}"
    exit 1
fi
echo ""

# Run ESLint
echo "🔍 Running ESLint..."
if npm run lint; then
    echo -e "${GREEN}✅ ESLint check passed!${NC}"
else
    echo -e "${RED}❌ ESLint issues found!${NC}"
    echo -e "${YELLOW}   Run 'npm run lint:fix' to fix auto-fixable issues${NC}"
    exit 1
fi
echo ""

# Check for console.log statements (warning only)
echo "🔍 Checking for console.log statements..."
CONSOLE_COUNT=$(grep -r "console\.log" --include="*.js" --exclude-dir=node_modules . | wc -l | tr -d ' ')
if [ "$CONSOLE_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Found $CONSOLE_COUNT console.log statement(s)${NC}"
    echo "   Consider removing or replacing with proper logging"
else
    echo -e "${GREEN}✅ No console.log statements found${NC}"
fi
echo ""

# Check file sizes
echo "📏 Checking file sizes..."
LARGE_FILES=$(find . -name "*.js" -o -name "*.css" -not -path "./node_modules/*" -size +100k)
if [ -n "$LARGE_FILES" ]; then
    echo -e "${YELLOW}⚠️  Large files detected (>100KB):${NC}"
    echo "$LARGE_FILES"
    echo "   Consider splitting or minifying these files"
else
    echo -e "${GREEN}✅ All files are reasonable size${NC}"
fi
echo ""

echo "========================================="
echo -e "${GREEN}✨ All quality checks completed successfully!${NC}"