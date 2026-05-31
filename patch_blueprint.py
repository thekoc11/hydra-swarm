from pathlib import Path
content = Path("src/hydra_swarm/agents/blueprint.md").read_text()
old = "When done: append to the lifecycle file:"
new = "When done: because you have `edit: allow`, append your roadmap directly to the lifecycle file:"
content = content.replace(old, new)
Path("src/hydra_swarm/agents/blueprint.md").write_text(content)
print("blueprint patched")
