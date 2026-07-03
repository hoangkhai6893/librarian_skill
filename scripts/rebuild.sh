#!/usr/bin/env bash
# rebuild.sh — Full Agent Hub library rebuild pipeline
# Usage: bash scripts/rebuild.sh [--skip-import] [--verbose]
#
# Steps:
#   1. (Optional) Re-import skills via batch-import.sh  [skipped with --skip-import]
#   2. Build catalog.json from library/
#   3. Validate library integrity
#   4. Print summary

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$(dirname "$SCRIPT_DIR")"   # cd to agent-hub-index/

SKIP_IMPORT=false
VERBOSE=false
for arg in "$@"; do
    case "$arg" in
        --skip-import) SKIP_IMPORT=true ;;
        --verbose)     VERBOSE=true ;;
    esac
done

echo "=== Agent Hub Rebuild ==="
echo "  Root: $(pwd)"
echo "  Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# Step 1: Import (optional)
if [ "$SKIP_IMPORT" = false ] && [ -f "scripts/batch-import.sh" ]; then
    echo "Step 1: Importing skills (use --skip-import to skip)..."
    if [ "$VERBOSE" = true ]; then
        bash scripts/batch-import.sh --force
    else
        bash scripts/batch-import.sh --force 2>&1 | grep -E "^\[OK\]|^  Count:" || true
    fi
    echo ""
else
    echo "Step 1: Skipping import"
fi

# Step 2: Build catalog
echo "Step 2: Building catalog.json..."
python3 scripts/build-catalog.py
echo ""

# Step 3: Validate
echo "Step 3: Validating library..."
python3 scripts/validate.py
VALIDATE_EXIT=$?
echo ""

# Step 4: Summary
echo "=== Summary ==="
python3 -c "
import json
d = json.load(open('library/catalog.json'))
skills = sum(1 for e in d['entries'] if e['type'] == 'skill')
agents = sum(1 for e in d['entries'] if e['type'] == 'agent')
print(f'  Entries  : {d[\"totalEntries\"]} ({skills} skills, {agents} agents)')
print(f'  Collections: {len(d[\"collections\"])}')
print(f'  Stacks   : {len(d[\"stacks\"])}')
print(f'  Built at : {d[\"builtAt\"]}')
"

if [ $VALIDATE_EXIT -eq 0 ]; then
    echo "  Validation: PASS ✓"
    echo ""
    echo "[OK] Rebuild complete."
else
    echo "  Validation: FAIL ✗"
    echo ""
    echo "[ERROR] Validation failed. Check output above."
    exit 1
fi
