#!/bin/bash
# Appends a JSON log line for every Bash tool call.
ROOT=$(git rev-parse --show-toplevel)
LOG_DIR="$ROOT/.claude/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/skills-$(date +%Y-%m-%d).log"
echo "{\"ts\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\", \"input\": $(echo "${CLAUDE_TOOL_INPUT:-{}}" | python3 -c 'import sys,json; d=sys.stdin.read(); print(json.dumps(d[:200]))' 2>/dev/null || echo '""')}" >> "$LOG_FILE"
