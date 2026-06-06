# OpenCode Obsidian Vault

Auto-save every OpenCode conversation into an Obsidian vault with full context — messages, tool calls, tokens, costs — and visualize everything in Obsidian's Graph View.

## How It Works

1. A **watcher** (`watcher.py`) monitors OpenCode sessions in the background
2. When a session ends, it exports the full conversation
3. Saves it as a clean markdown file in `Input/` with proper frontmatter
4. Creates/updates model profiles in `Models/`
5. Everything links with `[[wikilinks]]` — Obsidian's Graph View shows connections

## Quick Start

```bash
# 1. Clone anywhere
git clone https://github.com/kurmashubham98-blip/opencode-obsidian-vault.git

# 2. Open in Obsidian
#    File → Open Vault → Open folder as vault → select the cloned folder

# 3. Start the auto-save watcher
python3 watcher.py
```

Or use the alias (add to `~/.bashrc`):
```bash
alias oc='opencode; python3 /path/to/cloned/folder/save-session.py'
```

## systemd Auto-Start (Linux)

```bash
# Edit the .service file to point to your cloned path first
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
