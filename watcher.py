#!/usr/bin/env python3
"""Background watcher: auto-saves OpenCode sessions to Obsidian vault.

Runs as a systemd user service. Detects new/changed sessions by polling
`opencode session list` and saves them to the Obsidian vault.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

VAULT = Path(__file__).parent.resolve()
INPUT_DIR = VAULT / "Input"
MODELS_DIR = VAULT / "Models"
INPUT_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = VAULT / ".watcher_state.json"


def run_opencode(*args: str) -> str:
    result = subprocess.run(
        ["opencode", *args],
        capture_output=True, text=True, timeout=30,
    )
    return result.stdout if result.returncode == 0 else ""


def get_latest_session() -> dict | None:
    out = run_opencode("session", "list")
    lines = out.strip().split("\n")
    if len(lines) < 3:
        return None
    parts = lines[2].split(None, 2)
    if len(parts) < 2:
        return None
    return {"id": parts[0], "title": parts[1] if len(parts) > 1 else "", "raw": lines[2]}


def already_saved(session_id: str) -> bool:
    for f in INPUT_DIR.glob("*.md"):
        if f"session_id: {session_id}" in f.read_text():
            return True
    return False


def export_and_save(session_id: str):
    if already_saved(session_id):
        return

    tmpfile = Path(f"/tmp/opencode_watch_{session_id}.json")
    try:
        result = subprocess.run(
            ["opencode", "export", session_id],
            capture_output=False, text=True, timeout=120,
            stdout=open(tmpfile, "w"), stderr=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            return
        with open(tmpfile) as f:
            data = json.load(f)
    except Exception:
        return
    finally:
        if tmpfile.exists():
            tmpfile.unlink()

    info = data["info"]
    title = info.get("title", "Untitled")
    model = info.get("model", {})
    model_name = model.get("id", "Unknown")
    if "/" in model_name:
        model_name = model_name.split("/")[-1]
    provider = model.get("providerID", "unknown")
    ts = info["time"]["created"] / 1000
    dt = datetime.fromtimestamp(ts)
    date_str = dt.strftime("%Y-%m-%d")

    clean = "".join(c if c.isalnum() or c in " -_" else " " for c in title)
    clean = " ".join(clean.split()).replace(" ", "-")
    filename = f"{date_str} - {clean}.md"
    filepath = INPUT_DIR / filename

    if filepath.exists() and f"session_id: {session_id}" in filepath.read_text():
        return

    lines = []
    tag_model = model_name.replace("/", "-")
    lines.append("---\n")
    lines.append(f"tags: [chat, {provider}, {tag_model}]\n")
    lines.append(f"date: {date_str}\n")
    lines.append(f"model: {model_name}\n")
    lines.append(f"provider: {provider}\n")
    lines.append(f"session_id: {session_id}\n")
    lines.append(f'title: "{title}"\n')
    lines.append("---\n\n")
    lines.append(f"# {date_str} — {title}\n\n")
    lines.append(f"**Model:** [[{model_name}]] | **Provider:** {provider}\n\n---\n\n")

    for msg in data.get("messages", []):
        role = msg.get("info", {}).get("role", "unknown")
        lines.append(f"### {'🧑 User' if role == 'user' else '🤖 Assistant' if role == 'assistant' else '🔧 Tool' if role == 'tool' else role.capitalize()}\n\n")
        for part in msg.get("parts", []):
            ptype = part.get("type", "text")
            if ptype == "text":
                text = part.get("text", "")
                if text.strip():
                    lines.append(text + "\n")
            elif ptype in ("tool_use", "tool_call"):
                ti = part.get("input", {})
                res = part.get("result", "")
                lines.append(f"> **Tool:** `{part.get('name', 'tool')}`\n")
                if ti:
                    lines.append("> **Input:**\n> ```json\n")
                    for l in json.dumps(ti, indent=2).split("\n"):
                        lines.append(f"> {l}\n")
                    lines.append("> ```\n")
                if res:
                    lines.append("> **Result:**\n> ```\n")
                    for l in str(res)[:2000].split("\n"):
                        lines.append(f"> {l}\n")
                    lines.append("> ```\n")
            elif ptype == "tool_result":
                c = part.get("text") or part.get("content") or ""
                lines.append("```\n" + str(c)[:2000] + "\n```\n")
            elif ptype == "file":
                fc = part.get("content", "")
                lines.append(f"> **File:** `{part.get('path', '')}`\n")
                if fc:
                    lines.append("> ```\n")
                    for l in str(fc)[:2000].split("\n"):
                        lines.append(f"> {l}\n")
                    lines.append("> ```\n")
            else:
                lines.append(f"*[{ptype}]*\n```json\n{json.dumps(part, indent=2)[:1000]}\n```\n")
        lines.append("---\n")

    filepath.write_text("".join(lines))
    print(f"  ✅ Saved: {filename}", flush=True)

    mfile = MODELS_DIR / f"{model_name}.md"
    if not mfile.exists():
        note = f"---\ntags: [model, {provider}]\nmodel_name: \"{model_name}\"\n---\n\n# {model_name}\n\n> Provider: {provider}\n\n## Chats\n- [[{filename}]]\n"
        mfile.write_text(note)
        print(f"  ✅ Created model: {model_name}", flush=True)
    elif f"[[{filename}]]" not in mfile.read_text():
        with open(mfile, "a") as f:
            f.write(f"\n- [[{filename}]]\n")


def main():
    state = {"last_id": "", "saved_ids": set()}
    if STATE_FILE.exists():
        try:
            d = json.loads(STATE_FILE.read_text())
            state["last_id"] = d.get("last_id", "")
            state["saved_ids"] = set(d.get("saved_ids", []))
        except Exception:
            pass

    print("👀 OpenCode vault watcher started", flush=True)
    print(f"   Vault: {VAULT}", flush=True)
    cooldown_until = 0

    while True:
        try:
            latest = get_latest_session()
            if latest:
                sid = latest["id"]
                # If session changed and it's not saved yet
                if sid != state["last_id"]:
                    print(f"  Detected session change: {sid[:20]}...", flush=True)
                    state["last_id"] = sid
                    cooldown_until = time.time() + 30  # wait 30s for session to finish

                # Save after cooldown if not already saved
                if sid not in state["saved_ids"] and time.time() > cooldown_until:
                    print(f"  Saving session: {sid[:20]}...", flush=True)
                    export_and_save(sid)
                    state["saved_ids"].add(sid)
                    STATE_FILE.write_text(json.dumps({
                        "last_id": state["last_id"],
                        "saved_ids": list(state["saved_ids"]),
                    }))

            time.sleep(10)
        except KeyboardInterrupt:
            print("\n👋 Watcher stopped.", flush=True)
            break
        except Exception as e:
            print(f"  ⚠️ {e}", flush=True)
            time.sleep(30)


if __name__ == "__main__":
    main()
