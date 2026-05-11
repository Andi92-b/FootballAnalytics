#!/usr/bin/env python3
"""Runs at SessionEnd. Reads the skill log and prints a brief session summary."""
import os
from datetime import date

root = os.popen("git rev-parse --show-toplevel").read().strip()
log_file = f"{root}/.claude/logs/skills-{date.today()}.log"

if not os.path.exists(log_file):
    print("No skill activity logged today.")
    raise SystemExit(0)

with open(log_file) as f:
    lines = [l for l in f if l.strip()]

print(f"Session summary: {len(lines)} tool call(s) logged today.")
print(f"Log: {log_file}")
