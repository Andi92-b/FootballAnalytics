#!/bin/bash
# Fires on every user message. Signals the first message of a new session.
MARKER="/tmp/FOOTBALL_session_started_$$"
if [ ! -f "$MARKER" ]; then
  touch "$MARKER"
  echo "FOOTBALL_SESSION_START: New Football session. CLAUDE.md loaded. Read skill capabilities: fields before executing any task."
fi
