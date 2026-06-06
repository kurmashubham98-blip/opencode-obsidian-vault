#!/usr/bin/env python3
"""Export latest OpenCode session to Obsidian vault as a markdown note."""

import json
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


def run_opencode(*args: str) -> str:
    result = subprocess.run(
        ["opencode", *args],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        print(f"opencode error: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout


def export_session(session_id: str) -> dict:
    tmpfile = Path(f"/tmp/opencode_export_{session_id}.json")
    try:
        result = subprocess.run(
            ["opencode", "export", session_id],
            capture_output=False, text=True, timeout=120,
            stdout=open(tmpfile, "w"),
        )
        if result.returncode != 0:
            print(f"opencode export error: {result.stderr}", file=sys.stderr)
            sys.exit(1)
        with open(tmpfile) as f:
            return json.load(f)
    finally:
        if tmpfile.exists():
            tmpfile.unlink()


def sanitize_filename(s: str) -> str:
    s = "".join(c if c.isalnum() or c in " -_" else " " for c in s)
    s = " ".join(s.split())
    return s.replace(" ", "-")


def build_markdown(data: dict) -> str:
    info = data["info"]
    title = info.get("title", "Untitled")
    model = info.get("model", {})
    model_name = model.get("id", "Unknown")
    if "/" in model_name:
        model_name = model_name.split("/")[-1]
    provider = model.get("providerID", "unknown")
    session_id = info["id"]
    ts_created = info["time"]["created"] / 1000
    created_dt = datetime.fromtimestamp(ts_created)
    date_str = created_dt.strftime("%Y-%m-%d")
    tokens_in = info.get("tokens", {}).get("input", 0)
    tokens_out = info.get("tokens", {}).get("output", 0)
    cost = info.get("cost", 0)

    lines = []
    lines.append("---")
    tag_model = model_name.replace("/", "-")
    lines.append(f'tags: [chat, {provider}, {tag_model}]')
    lines.append(f"date: {date_str}")
    lines.append(f"model: {model_name}")
    lines.append(f"provider: {provider}")
    lines.append(f"session_id: {session_id}")
    lines.append(f"tokens_input: {tokens_in}")
    lines.append(f"tokens_output: {tokens_out}")
    lines.append(f"cost: {cost}")
    lines.append(f'title: "{title}"')
    lines.append("---")
    lines.append("")
    lines.append(f"# {date_str} — {title}")
    lines.append("")
    lines.append(f"**Model:** [[{model_name}]] | **Provider:** {provider}")
    lines.append("")
    lines.append("---")
    lines.append("")

    messages = data.get("messages", [])
    user_models = {}

    for msg_num, msg in enumerate(messages, 1):
        msg_info = msg.get("info", {})
        role = msg_info.get("role", "unknown")

        if "model" in msg_info:
            m = msg_info["model"]
            mid = m.get("modelID", m.get("id", "unknown")).split("/")[-1]
            pid = m.get("providerID", "unknown")
            user_models[msg_num] = f"{pid}/{mid}"

        model_tag = user_models.get(msg_num, "")
        if role == "user":
            header = f"### 🧑 User — {model_tag}" if model_tag else "### 🧑 User"
        elif role == "assistant":
            header = "### 🤖 Assistant"
        elif role == "tool":
            header = "### 🔧 Tool"
        else:
            header = f"### {role.capitalize()}"

        lines.append(header)
        lines.append("")

        for part in msg.get("parts", []):
            ptype = part.get("type", "text")

            if ptype == "text":
                text = part.get("text", "")
                if text.strip():
                    lines.append(text)
                    lines.append("")

            elif ptype in ("tool_use", "tool_call"):
                tool_name = part.get("name", "tool")
                tool_input = part.get("input", {})
                lines.append(f"> **Tool:** `{tool_name}`")
                lines.append(">")
                if tool_input:
                    lines.append("> **Input:**")
                    lines.append("> ```json")
                    for tj_line in json.dumps(tool_input, indent=2).split("\n"):
                        lines.append(f"> {tj_line}")
                    lines.append("> ```")
                result = part.get("result", "")
                lines.append(">")
                lines.append(f"> **Result:**")
                lines.append("> ```")
                result_str = str(result)[:2000]
                for rl in result_str.split("\n"):
                    lines.append(f"> {rl}")
                lines.append("> ```")
                lines.append("")

            elif ptype == "tool_result":
                content = part.get("text") or part.get("content") or ""
                lines.append("```")
                lines.append(str(content)[:2000])
                lines.append("```")
                lines.append("")

            elif ptype == "file":
                fpath = part.get("path", "")
                fcontent = part.get("content", "")
                lines.append(f"> **File:** `{fpath}`")
                if fcontent:
                    lines.append(">")
                    lines.append("> ```")
                    for fl in str(fcontent)[:2000].split("\n"):
                        lines.append(f"> {fl}")
                    lines.append("> ```")
                lines.append("")

            else:
                lines.append(f"*[{ptype}]*")
                lines.append("```json")
                lines.append(json.dumps(part, indent=2)[:1000])
                lines.append("```")
                lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def main():
    session_list = run_opencode("session", "list")
    session_lines = session_list.strip().split("\n")
    if len(session_lines) < 3:
        print("No sessions found.")
        return

    force = "--force" in sys.argv
    now = time.time()
    latest_session_id = session_lines[2].split()[0]
    print(f"Exporting session: {latest_session_id}")

    data = export_session(latest_session_id)

    session_updated = data["info"]["time"]["updated"] / 1000
    if not force and now - session_updated > 300:
        print("Session too old (>5 min). Use --force to save anyway.")
        return

    info = data["info"]
    session_id = info["id"]
    title = info.get("title", "Untitled")
    model = info.get("model", {})
    model_name = model.get("id", "Unknown")
    if "/" in model_name:
        model_name = model_name.split("/")[-1]
    provider = model.get("providerID", "unknown")
    ts_created = info["time"]["created"] / 1000
    created_dt = datetime.fromtimestamp(ts_created)
    date_str = created_dt.strftime("%Y-%m-%d")

    clean_title = sanitize_filename(title)
    filename = f"{date_str} - {clean_title}.md"
    filepath = INPUT_DIR / filename

    if filepath.exists():
        existing_data = filepath.read_text()
        if f"session_id: {session_id}" in existing_data:
            print(f"⏭️ Already saved: {filepath}")
            return
    markdown = build_markdown(data)
    filepath.write_text(markdown)
    print(f"✅ Saved: {filepath}")

    model_file = MODELS_DIR / f"{model_name}.md"
    if not model_file.exists():
        model_note = f"""---
tags: [model, {provider}]
model_name: "{model_name}"
---

# {model_name}

> Provider: {provider}

## Chats
- [[{filename}]]
"""
        model_file.write_text(model_note)
        print(f"✅ Created model profile: {model_file}")
    else:
        existing = model_file.read_text()
        if f"[[{filename}]]" not in existing:
            new_link = f"\n- [[{filename}]]\n"
            model_file.write_text(existing + new_link)
            print(f"✅ Updated model profile: {model_file}")

    print(f"🎯 Done! Open vault in Obsidian and check Graph View.")


if __name__ == "__main__":
    main()
