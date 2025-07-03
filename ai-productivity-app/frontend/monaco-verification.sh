#!/bin/bash

# Monaco Editor Verification Test Script
# This script runs the comprehensive verification checklist

echo "🔍 Starting Monaco Editor Verification..."
echo "════════════════════════════════════════════════════════════════"

# Change to frontend directory
cd /home/azureuser/opus2/ai-productivity-app/frontend

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print test results
print_result() {
    local test_name="$1"
    local result="$2"
    local details="$3"

    if [ "$result" = "PASS" ]; then
        echo -e "✅ $test_name: ${GREEN}PASS${NC} $details"
    elif [ "$result" = "FAIL" ]; then
        echo -e "❌ $test_name: ${RED}FAIL${NC} $details"
    else
        echo -e "⚠️  $test_name: ${YELLOW}WARN${NC} $details"
    fi
}

# Test 1: Check if Monaco Editor dependencies are properly installed
echo "1. 📦 Checking Monaco Dependencies..."
if npm list @monaco-editor/react > /dev/null 2>&1; then
    print_result "Monaco Dependencies" "PASS" "(@monaco-editor/react installed)"
else
    print_result "Monaco Dependencies" "FAIL" "(@monaco-editor/react missing)"
fi

# Test 2: Check if Monaco components exist
echo "2. 📁 Checking Monaco Components..."
if [ -f "src/components/editor/MonacoRoot.jsx" ]; then
    print_result "MonacoRoot Component" "PASS" "(file exists)"
else
    print_result "MonacoRoot Component" "FAIL" "(file missing)"
fi

if [ -f "src/hooks/useCodeEditor.js" ]; then
    print_result "useCodeEditor Hook" "PASS" "(file exists)"
else
    print_result "useCodeEditor Hook" "FAIL" "(file missing)"
fi

# Test 3: Check for proper error boundaries
echo "3. 🛡️  Checking Error Boundaries..."
if [ -f "src/components/editor/EditorErrorBoundary.jsx" ]; then
    print_result "Error Boundary" "PASS" "(file exists)"
else
    print_result "Error Boundary" "FAIL" "(file missing)"
fi

# Test 4: Check for mobile optimizations
echo "4. 📱 Checking Mobile Optimizations..."
if [ -f "src/components/editor/MobileCodeToolbar.jsx" ]; then
    print_result "Mobile Toolbar" "PASS" "(file exists)"
else
    print_result "Mobile Toolbar" "FAIL" "(file missing)"
fi

# Test 5: Check for proper imports in key files
echo "5. 🔗 Checking Import Integrity..."
if grep -q "MonacoRoot" src/pages/ProjectChatPage.jsx; then
    print_result "MonacoRoot Import" "PASS" "(imported in ProjectChatPage)"
else
    print_result "MonacoRoot Import" "FAIL" "(not imported in ProjectChatPage)"
fi

# Test 6: Check for proper panel configuration
echo "6. 🔧 Checking Panel Configuration..."
if grep -q "react-resizable-panels" src/components/chat/ChatLayout.jsx; then
    print_result "Resizable Panels" "PASS" "(configured in ChatLayout)"
else
    print_result "Resizable Panels" "FAIL" "(not configured in ChatLayout)"
fi

# Test 7: Check for localStorage handling
echo "7. 💾 Checking localStorage Handling..."
if grep -q "localStorage" src/components/chat/ChatLayout.jsx; then
    print_result "localStorage Integration" "PASS" "(localStorage handling found)"
else
    print_result "localStorage Integration" "FAIL" "(localStorage handling missing)"
fi

# Test 8: Check for proper cleanup in useCodeEditor
echo "8. 🧹 Checking Memory Management..."
if grep -q "dispose" src/hooks/useCodeEditor.js; then
    print_result "Memory Cleanup" "PASS" "(dispose calls found)"
else
    print_result "Memory Cleanup" "FAIL" "(dispose calls missing)"
fi

# Test 9: Check for performance optimizations
echo "9. ⚡ Checking Performance Optimizations..."
if grep -q "maxFileSize" src/components/editor/MonacoRoot.jsx; then
    print_result "File Size Limits" "PASS" "(maxFileSize handling found)"
else
    print_result "File Size Limits" "FAIL" "(maxFileSize handling missing)"
fi

# Test 10: Run ESLint on editor components
echo "10. 🔍 Running ESLint on Editor Components..."
if npm run lint -- --quiet src/components/editor/ > /dev/null 2>&1; then
    print_result "ESLint Editor" "PASS" "(no lint errors)"
else
    lint_errors=$(npm run lint -- src/components/editor/ 2>&1 | grep -c "error" || echo "0")
    print_result "ESLint Editor" "FAIL" "($lint_errors errors found)"
fi

# Test 11: Check TypeScript/JSX syntax
echo "11. 📝 Checking Syntax..."
if npm run build:check > /dev/null 2>&1; then
    print_result "Build Check" "PASS" "(syntax valid)"
else
    print_result "Build Check" "FAIL" "(syntax errors found)"
fi

# Test 12: Check for proper prop types
echo "12. 🏷️  Checking Prop Types..."
if grep -q "PropTypes" src/components/editor/MonacoRoot.jsx; then
    print_result "Prop Types" "PASS" "(PropTypes defined)"
else
    print_result "Prop Types" "WARN" "(PropTypes missing)"
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "🎯 To run the interactive browser verification:"
echo "1. Start the dev server: npm run dev"
echo "2. Open browser console and run:"
echo "   const verifier = new MonacoVerifier(); verifier.runAllTests();"
echo ""
echo "📊 For complete verification, ensure all tests pass before merging."
echo "════════════════════════════════════════════════════════════════"
