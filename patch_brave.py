import sys
from pathlib import Path

content = Path("src/hydra_swarm/skills/hydra-architect/scripts/brave_search.py").read_text()

# Flaw 8: Remove auto-loading .env from global scope
content = content.replace("load_dotenv()", "")

# Flaw 11: Validate max 3 goggles
old_goggles = 'parser.add_argument("--goggles", nargs="*", default=[], help="Goggle URLs to rerank results")'
new_goggles = 'parser.add_argument("--goggles", nargs="*", default=[], help="Goggle URLs to rerank results")'
content = content.replace(old_goggles, new_goggles)  # unchanged here

# Find the main execution block where parse_args happens
main_block_old = """    args = parser.parse_args()"""
main_block_new = """    args = parser.parse_args()
    
    # Flaw 8: Load .env at execution time, not import time
    load_dotenv()
    
    # Flaw 11: Validate max 3 goggles
    if len(args.goggles) > 3:
        parser.error("Brave Search API allows a maximum of 3 goggles per query.")"""
content = content.replace(main_block_old, main_block_new)

Path("src/hydra_swarm/skills/hydra-architect/scripts/brave_search.py").write_text(content)
print("brave patched")
