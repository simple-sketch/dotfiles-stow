#!/usr/bin/env python3
"""Choose an open Sway window with wmenu."""

import json
import subprocess


def windows(node, workspace=""):
    if node.get("type") == "workspace":
        workspace = node.get("name", "")
    if node.get("app_id") or node.get("window"):
        title = " ".join((node.get("name") or "Untitled").split())
        yield f"{node['id']}: [{workspace}] {title}", node["id"]
    for child in node.get("nodes", []) + node.get("floating_nodes", []):
        yield from windows(child, workspace)


def main():
    tree = json.loads(subprocess.check_output(["swaymsg", "-r", "-t", "get_tree"]))
    choices = dict(windows(tree))
    if not choices:
        return
    result = subprocess.run(
        ["wmenu", "-i", "-p", "Windows", "-l", "12"],
        input="\n".join(choices) + "\n", text=True, capture_output=True,
    )
    selected = choices.get(result.stdout.rstrip("\n"))
    if result.returncode == 0 and selected is not None:
        subprocess.run(["swaymsg", "-q", f"[con_id={selected}] focus"], check=True)


if __name__ == "__main__":
    main()
