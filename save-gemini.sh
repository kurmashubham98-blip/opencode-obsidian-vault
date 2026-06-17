#!/usr/bin/env bash
# Run Gemini CLI, then automatically save the conversation to the Obsidian vault
DIR="$(cd "$(dirname "$0")" && pwd)"
gemini "$@"
python3 "$DIR/save-gemini.py"
