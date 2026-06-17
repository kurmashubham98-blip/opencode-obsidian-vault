#!/usr/bin/env python3
"""Save Gemini CLI conversations to the Obsidian vault."""

import json
import os
import time
from datetime import datetime
from pathlib import Path

VAULT = Path(__file__).parent.resolve()
INPUT_DIR = VAULT / "Input"
MODELS_DIR = VAULT / "Models"
INPUT_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

GEMINI_DIR = Path(os.path.expanduser("~/.gemini/tmp"))


def sanitize(s: str) -> str:
    s = "".join(c if c.isalnum() or c in " -_" else " " for c in s)
    return " ".join(s.split()).replace(" ", "-")


def get_project_name(logs_path: Path) -> str:
    return logs_path.parent.name


def get_all_sessions() -> list[dict]:
    sessions = []
    for logs_file in GEMINI_DIR.rglob("chats/*.jsonl"):
        try:
            with open(logs_file) as f:
                first_line = f.readline().strip()
                if not first_line:
                    continue
                meta = json.loads(first_line)
                sid = meta.get("sessionId", logs_file.stem)
                start = meta.get("startTime", "")
                kind = meta.get("kind", "main")
                if kind != "main":
                    continue
                project = logs_file.parent.parent.name
                sessions.append({
                    "id": sid,
                    "start": start,
                    "project": project,
                    "path": logs_file,
                })
        except (json.JSONDecodeError, OSError):
            continue
    return sessions


def parse_session(logs_file: Path) -> dict | None:
    try:
        with open(logs_file) as f:
            lines = f.readlines()
    except OSError:
        return None

    meta = json.loads(lines[0].strip()) if lines else {}
    messages = []
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("type") == "user":
            content = d.get("content", [])
            text = ""
            if isinstance(content, list) and content:
                text = content[0].get("text", "")
            elif isinstance(content, str):
                text = content
            if text:
                text = text[:5000]
            messages.append({"role": "user", "text": text, "ts": d.get("timestamp", "")})
        elif d.get("type") == "gemini" and d.get("content"):
            messages.append({
                "role": "gemini",
                "text": str(d.get("content", ""))[:10000],
                "model": d.get("model", "gemini"),
                "tokens": d.get("tokens", {}),
                "thoughts": d.get("thoughts", []),
                "toolCalls": d.get("toolCalls", []),
                "ts": d.get("timestamp", ""),
            })
        elif d.get("type") == "gemini" and d.get("toolCalls"):
            messages.append({
                "role": "gemini",
                "text": "",
                "model": d.get("model", "gemini"),
                "tokens": d.get("tokens", {}),
                "thoughts": d.get("thoughts", []),
                "toolCalls": d.get("toolCalls", []),
                "ts": d.get("timestamp", ""),
            })

    if not messages:
        return None

    project = logs_file.parent.parent.name
    start_ts = meta.get("startTime", messages[0].get("ts", ""))
    try:
        dt = datetime.fromisoformat(start_ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        dt = datetime.fromtimestamp(os.path.getmtime(logs_file))
    date_str = dt.strftime("%Y-%m-%d")
    time_str = dt.strftime("%H:%M")

    return {
        "session_id": meta.get("sessionId", logs_file.stem),
        "project": project,
        "messages": messages,
        "date": date_str,
        "time": time_str,
        "dt": dt,
        "file_path": logs_file,
    }


def save_session(session: dict):
    sid = session["session_id"]
    for f in INPUT_DIR.glob("*.md"):
        if f"session_id: {sid}" in f.read_text():
            return

    title = f"Gemini - {session['project']}"
    time_slug = session["time"].replace(":", "-")
    filename = f"{session['date']} - {sanitize(title)} {time_slug}.md"
    filepath = INPUT_DIR / filename

    lines = []
    lines.append("---\n")
    lines.append(f"tags: [chat, gemini]\n")
    lines.append(f"date: {session['date']}\n")
    lines.append(f"model: gemini\n")
    lines.append(f"provider: google\n")
    lines.append(f"session_id: {sid}\n")
    lines.append(f'project: {session["project"]}\n')
    lines.append(f'title: "{title}"\n')
    lines.append("---\n\n")
    lines.append(f"# {session['date']} — {title}\n\n")
    lines.append(f"**Model:** [[gemini]] | **Project:** {session['project']}\n\n---\n\n")

    for msg in session["messages"]:
        if msg["role"] == "user":
            lines.append("### 🧑 User\n\n")
            if msg.get("text"):
                lines.append(msg["text"] + "\n")
        elif msg["role"] == "gemini":
            lines.append("### 🤖 Gemini\n\n")
            if msg.get("thoughts"):
                lines.append("> **Thoughts:**\n")
                for t in msg["thoughts"]:
                    subj = t.get("subject", "")
                    desc = t.get("description", "")
                    if desc:
                        lines.append(f"> *{desc[:500]}*\n")
                lines.append("\n")
            if msg.get("text"):
                lines.append(msg["text"] + "\n")
            if msg.get("toolCalls"):
                for tc in msg["toolCalls"]:
                    name = tc.get("name", "tool")
                    args = tc.get("args", {})
                    lines.append(f"> **Tool:** `{name}`\n")
                    if args:
                        lines.append("> **Args:**\n> ```json\n")
                        for l in json.dumps(args, indent=2).split("\n"):
                            lines.append(f"> {l}\n")
                        lines.append("> ```\n")
                    results = tc.get("result", [])
                    if results:
                        for r in results:
                            fr = r.get("functionResponse", {})
                    resp = fr.get("response", "")
                    if resp:
                        lines.append(f"> **Result:**\n> ```\n{str(resp)[:1000]}\n> ```\n")
            lines.append("\n")
        lines.append("---\n")

    filepath.write_text("".join(lines))
    print(f"  ✅ Saved: {filename}", flush=True)

    model_file = MODELS_DIR / "gemini.md"
    if not model_file.exists():
        note = "---\ntags: [model, google]\nmodel_name: \"gemini\"\n---\n\n# Gemini\n\n> Provider: Google\n\n## Chats\n"
        model_file.write_text(note)
    existing = model_file.read_text()
    if f"[[{filename}]]" not in existing:
        with open(model_file, "a") as f:
            f.write(f"- [[{filename}]]\n")


def main():
    sessions = get_all_sessions()
    for s in sessions:
        parsed = parse_session(s["path"])
        if parsed:
            save_session(parsed)
    print(f"  Done. Checked {len(sessions)} sessions.", flush=True)


if __name__ == "__main__":
    import sys
    main()
