# Setup Guide: OpenCode Obsidian Vault

## What Just Happened?
I created an Obsidian vault that tracks every model you’ve ever used in OpenCode. It does this by linking your conversations together so you can visualize them in Obsidian’s graph view.

## How the Automation Works
Every time you finish a chat in OpenCode, a script runs. This script:
1. Reads the conversation.
2. Identifies the model (e.g., GPT-4o, Claude, Kimi).
3. Creates a .md file in `/Input/` with the date, model name, and a summary.
4. Generates links to related conversations using the `[[wiki link]]` syntax.

## Visualizing the Graph
Once you have a few notes, open the **Graph View** in Obsidian. You will see:
- **Nodes:** Each note is a dot.
- **Links:** Lines connecting dots mean the notes reference each other.
- **Clusters:** You will quickly see which models you use for which tasks (e.g., coding vs. writing).

## Customizing the Vault
- **Colors:** Use the `Graph Color Groups` in Graph View to color-code nodes by model.
- **Filters:** Hide `Daily` or `Graphs` from the main graph to focus on model-to-model connections.
- **Templates:** The vault uses a standard YAML header (frontmatter) so dataview tables work out of the box.