# OpenCode Obsidian Vault

Auto-save every OpenCode and Gemini CLI conversation into an Obsidian vault with full context — messages, tool calls, tokens, costs — and visualize everything in Obsidian's Graph View.

## How It Works

- **`watcher.py`** — background daemon that monitors both OpenCode and Gemini CLI sessions
- **`save-session.py`** — export an OpenCode session to the vault
- **`save-gemini.py`** — export Gemini CLI conversations to the vault
- Saves as clean markdown in `Input/` with frontmatter (model, provider, tokens)
- Creates/updates model profiles in `Models/`
- Everything uses `[[wikilinks]]` — Obsidian's Graph View shows connections

## Quick Start

```bash
git clone https://github.com/kurmashubham98-blip/opencode-obsidian-vault.git
cd opencode-obsidian-vault

# Open in Obsidian: File → Open Vault → Open folder as vault → select this folder

# Start the watcher (auto-saves both OpenCode and Gemini sessions)
python3 watcher.py
```

Or run manually:
```bash
python3 save-session.py          # save latest OpenCode session
python3 save-gemini.py           # save all Gemini CLI conversations
```

## Auto-Start with systemd (Linux)

```bash
cp opencode-vault-watcher.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now opencode-vault-watcher.service
```

## Privacy

**Zero network calls.** Everything stays on your machine.

## Requirements

- [OpenCode](https://opencode.ai)
- [Obsidian](https://obsidian.md)
- Python 3

## License

MIT
