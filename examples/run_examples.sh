#!/usr/bin/env bash
# ============================================================================
# apcore-cli examples — run these from the project root directory
#
# Usage:
#   cd /path/to/apcore-cli-python
#   bash examples/run_examples.sh
# ============================================================================

set -e
export APCORE_EXTENSIONS_ROOT=examples/extensions

echo "============================================"
echo " apcore-cli Examples (macOS/Linux)"
echo "============================================"
echo ""

# --- Discovery ---
echo "1. List all modules:"
echo "   \$ apcore-cli list --format json"
python -m apcore_cli list --format json
echo ""

echo "2. Filter by tag:"
echo "   \$ apcore-cli list --tag math --format json"
python -m apcore_cli list --tag math --format json
echo ""

echo "3. Describe a module:"
echo "   \$ apcore-cli describe math.add --format json"
python -m apcore_cli describe math.add --format json
echo ""

# --- Execution ---
echo "4. Execute math.add with CLI flags:"
echo "   \$ apcore-cli math.add --a 42 --b 58"
python -m apcore_cli math.add --a 42 --b 58
echo ""

echo "5. Execute math.multiply:"
echo "   \$ apcore-cli math.multiply --a 6 --b 7"
python -m apcore_cli math.multiply --a 6 --b 7
echo ""

echo "6. Execute text.upper:"
echo "   \$ apcore-cli text.upper --text 'hello apcore'"
python -m apcore_cli text.upper --text 'hello apcore'
echo ""

echo "7. Execute text.reverse:"
echo "   \$ apcore-cli text.reverse --text 'apcore-cli'"
python -m apcore_cli text.reverse --text 'apcore-cli'
echo ""

echo "8. Execute text.wordcount:"
echo "   \$ apcore-cli text.wordcount --text 'hello world from apcore'"
python -m apcore_cli text.wordcount --text 'hello world from apcore'
echo ""

# --- STDIN Piping ---
echo "9. Pipe JSON via STDIN:"
echo "   \$ echo '{\"a\": 100, \"b\": 200}' | apcore-cli math.add --input -"
echo '{"a": 100, "b": 200}' | python -m apcore_cli math.add --input -
echo ""

echo "10. CLI flag overrides STDIN:"
echo "   \$ echo '{\"a\": 1, \"b\": 2}' | apcore-cli math.add --input - --a 999"
echo '{"a": 1, "b": 2}' | python -m apcore_cli math.add --input - --a 999
echo ""

# --- System modules ---
echo "11. Get system info:"
echo "   \$ apcore-cli sysutil.info"
python -m apcore_cli sysutil.info
echo ""

echo "12. Read environment variable:"
echo "   \$ apcore-cli sysutil.env --name HOME"
python -m apcore_cli sysutil.env --name HOME
echo ""

echo "13. Check disk usage:"
echo "   \$ apcore-cli sysutil.disk --path /"
python -m apcore_cli sysutil.disk --path /
echo ""

# --- Chaining (Unix pipes) ---
echo "14. Chain modules — add result piped to text.wordcount:"
echo "   \$ apcore-cli math.add --a 5 --b 10 | python -c \"...\""
RESULT=$(python -m apcore_cli math.add --a 5 --b 10)
echo "   math.add returned: $RESULT"
MSG=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'The sum is {d[\"sum\"]}')")
echo "   Parsed: $MSG"
echo ""

# --- Shell completion ---
echo "15. Generate bash completion:"
echo "   \$ apcore-cli completion bash | head -5"
python -m apcore_cli completion bash | head -5
echo "   ..."
echo ""

# --- Help ---
echo "16. Module help (auto-generated from schema):"
echo "   \$ apcore-cli math.add --help"
python -m apcore_cli math.add --help
echo ""

echo "============================================"
echo " All examples completed successfully!"
echo "============================================"
