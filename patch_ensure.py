from pathlib import Path

content = Path("src/hydra_swarm/cli.py").read_text()

# Patch ensure_agents (Flaw 3 + Flaw 9)
old_agents = """def ensure_agents(target: Path) -> None:
    \"\"\"Copy OpenCode agent configs from package to target .opencode/agents/.\"\"\"
    agents_src = _pkg_dir() / "agents"
    agents_dst = target / ".opencode" / "agents"
    agents_dst.mkdir(parents=True, exist_ok=True)
    for src in agents_src.glob("*.md"):
        shutil.copy2(src, agents_dst / src.name)"""

new_agents = """def ensure_agents(target: Path) -> None:
    \"\"\"Copy OpenCode agent configs from package to target .opencode/agents/.\"\"\"
    agents_src = _pkg_dir() / "agents"
    agents_dst = target / ".opencode" / "agents"
    agents_dst.mkdir(parents=True, exist_ok=True)
    valid_agents = {"blueprint.md", "builder.md", "adversary.md", "defender.md"}
    for src in agents_src.glob("*.md"):
        if src.name in valid_agents:
            dst = agents_dst / src.name
            if not dst.exists():
                shutil.copy2(src, dst)"""
content = content.replace(old_agents, new_agents)

# Patch ensure_skills (Flaw 3 + Flaw 14 Fix O(2n))
# Wait, Flaw 14 (LOW) says: ensure_skills has two separate rglob loops doing the same work.
old_skills = """    # Copy to Hermes global skills dir (for auto-discovery)
    hermes_skills = Path.home() / ".hermes" / "skills"
    hermes_skills.mkdir(parents=True, exist_ok=True)
    for src in skills_src.rglob("*"):
        if src.is_file():
            rel = src.relative_to(skills_src)
            dst = hermes_skills / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    # Also copy to project skills/ for portability/reference
    skills_dst = target / "skills"
    skills_dst.mkdir(parents=True, exist_ok=True)
    for src in skills_src.rglob("*"):
        if src.is_file():
            rel = src.relative_to(skills_src)
            dst = skills_dst / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)"""

new_skills = """    # Copy to Hermes global skills dir and project skills/ in one pass (Fix O(2n))
    hermes_skills = Path.home() / ".hermes" / "skills"
    skills_dst = target / "skills"
    
    for src in skills_src.rglob("*"):
        if src.is_file():
            rel = src.relative_to(skills_src)
            
            dst_global = hermes_skills / rel
            dst_global.parent.mkdir(parents=True, exist_ok=True)
            if not dst_global.exists():
                shutil.copy2(src, dst_global)
                
            dst_local = skills_dst / rel
            dst_local.parent.mkdir(parents=True, exist_ok=True)
            if not dst_local.exists():
                shutil.copy2(src, dst_local)"""
content = content.replace(old_skills, new_skills)

Path("src/hydra_swarm/cli.py").write_text(content)
print("ensure patched")
