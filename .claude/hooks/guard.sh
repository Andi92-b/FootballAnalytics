#!/bin/bash
# Blocks destructive commands. Exit 0 = approved. Exit 2 + message = blocked.
INPUT="${CLAUDE_TOOL_INPUT:-}"

if echo "$INPUT" | grep -qE 'rm -rf|DROP TABLE|DELETE FROM|git push --force|git reset --hard'; then
  echo "BLOCKED: Destructive command requires explicit operator confirmation."
  exit 2
fi

# Block writes outside the project root
ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -n "$ROOT" ] && echo "$INPUT" | grep -qE '> /|tee /|cp .* /|mv .* /'; then
  if ! echo "$INPUT" | grep -q "$ROOT"; then
    echo "BLOCKED: Write outside project root requires explicit confirmation."
    exit 2
  fi
fi

exit 0
