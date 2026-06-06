#!/usr/bin/env bash
# Run OpenCode, then automatically save the session to the Obsidian vault
DIR="$(cd "$(dirname "$0")" && pwd)"
opencode "$@"
python3 "$DIR/save-session.py" --force
