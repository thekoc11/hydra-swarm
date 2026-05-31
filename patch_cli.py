import sys
from pathlib import Path

content = Path("src/hydra_swarm/cli.py").read_text()

# Flaw 14: --skills to -s
content = content.replace('"--skills", skill', '"-s", skill')

# Flaw 10: Inconsistent pointer (use resolve() for both)
content = content.replace(
    'pointer.write_text(str(lifecycle_path) + "\\n")',
    'pointer.write_text(str(lifecycle_path.resolve()) + "\\n")'
)

# Flaw 2: Sanitize goal
old_stub = """def _write_lifecycle_stub(goal: str, experiments_dir: Path) -> Path:
    \"\"\"Create a lifecycle stub file and return its path.\"\"\"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    lifecycle_path = experiments_dir / f"hydra_lifecycle_{timestamp}.md"
    lifecycle_path.write_text(
        f"# Hydra Run — {timestamp}\\n\\n"
        f"## Goal\\n{goal}\\n\\n"
    )
    return lifecycle_path"""

new_stub = """def _write_lifecycle_stub(goal: str, experiments_dir: Path) -> Path:
    \"\"\"Create a lifecycle stub file and return its path.\"\"\"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    lifecycle_path = experiments_dir / f"hydra_lifecycle_{timestamp}.md"
    
    # Sanitize goal to prevent lifecycle injection attacks (Fix 2)
    safe_goal = goal.replace("\\n##", "\\n#").replace("[HYDRA", "(HYDRA").replace("[BLUEPRINT", "(BLUEPRINT").replace("[ADVERSARY", "(ADVERSARY").replace("[DEFENDER", "(DEFENDER").replace("[BUILDER", "(BUILDER")
    
    lifecycle_path.write_text(
        f"# Hydra Run — {timestamp}\\n\\n"
        f"## Goal\\n{safe_goal}\\n\\n"
    )
    return lifecycle_path"""
content = content.replace(old_stub, new_stub)

# Flaw 6: ensure_skills silent no-op
old_skills = """    skills_src = _pkg_dir() / "skills"
    if not skills_src.exists():
        return"""
new_skills = """    skills_src = _pkg_dir() / "skills"
    if not skills_src.exists():
        print("Warning: Source skills directory not found. Package may be corrupted.", file=sys.stderr)
        return"""
content = content.replace(old_skills, new_skills)

# Flaw 4: _detect_phase misroute
old_detect = """def _detect_phase(lifecycle_text: str) -> str:
    \"\"\"Detect which phase to resume from based on completion tags (no LLM needed).\"\"\"
    if "[HYDRA: CONVERGED]" not in lifecycle_text:
        return "hydra-architect"
    # Knowledge secured means everything is done — librarian for re-compounding
    if "[HYDRA KNOWLEDGE: SECURED]" in lifecycle_text:
        return "hydra-librarian"
    if "[BLUEPRINT: COMPLETE]" not in lifecycle_text:
        return "hydra-proceed"
    if "[DEFENDER: COMPLETE]" in lifecycle_text:
        return "hydra-librarian"
    return "hydra-proceed"  # pipeline in progress"""

new_detect = """def _detect_phase(lifecycle_text: str) -> str:
    \"\"\"Detect which phase to resume from based on completion tags (no LLM needed).\"\"\"
    if "[HYDRA: CONVERGED]" not in lifecycle_text:
        return "hydra-architect"
    # Knowledge secured means everything is done — librarian for re-compounding
    if "[HYDRA KNOWLEDGE: SECURED]" in lifecycle_text:
        return "hydra-librarian"
        
    # Check if research-only pipeline (no [impl] in architect contract)
    architect_section = lifecycle_text.split("## Architect", 1)[-1] if "## Architect" in lifecycle_text else ""
    if "[impl]" not in architect_section:
        return "hydra-librarian"
        
    if "[BLUEPRINT: COMPLETE]" not in lifecycle_text:
        return "hydra-proceed"
    if "[DEFENDER: COMPLETE]" in lifecycle_text:
        return "hydra-librarian"
    return "hydra-proceed"  # pipeline in progress"""
content = content.replace(old_detect, new_detect)

# Flaw 5: Legacy --agent validation
old_agent = """    if "--agent" in argv:
        idx = argv.index("--agent")
        agent_name = argv[idx + 1] if idx + 1 < len(argv) else ""
        # Remaining args after --agent <name> are the goal"""
new_agent = """    if "--agent" in argv:
        idx = argv.index("--agent")
        agent_name = argv[idx + 1] if idx + 1 < len(argv) else ""
        if not agent_name or agent_name.startswith("-"):
            sys.exit("Error: --agent requires a valid agent name")
        # Remaining args after --agent <name> are the goal"""
content = content.replace(old_agent, new_agent)

# Flaw 7: No timeout on _launch_hermes
old_launch = """    subprocess.run([hermes, "chat", "-s", skill])"""
new_launch = """    try:
        subprocess.run([hermes, "chat", "-s", skill], timeout=3600)
    except subprocess.TimeoutExpired:
        print("\\nError: Hermes session timed out after 3600 seconds.", file=sys.stderr)
        sys.exit(1)"""
content = content.replace(old_launch, new_launch)

Path("src/hydra_swarm/cli.py").write_text(content)
print("cli.py patched")
