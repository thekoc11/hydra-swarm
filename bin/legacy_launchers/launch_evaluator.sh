#!/bin/bash

# ==============================================================================
# Hydra Swarm Framework - Evaluator Agent Prompt Multiplexer
# ==============================================================================

SESSION_NAME="evaluator_builder"
TMP_DIR="/tmp/hydra_prompts"
mkdir -p "$TMP_DIR"

# Ensure we have the latest context of the other prompts to feed to the evaluator builder
ARCHITECT_CTX=$(cat architect.md 2>/dev/null || echo "architect.md not found")
HEADLESS_CTX=$(cat headless_agent.md 2>/dev/null || echo "headless_agent.md not found")
JUDGE_CTX=$(cat llm_judge.md 2>/dev/null || echo "llm_judge.md not found")

# 1. Safely write the prompt to a temporary file
# ------------------------------------------------------------------------------

cat << EOF > "$TMP_DIR/evaluator_prompt.txt"
I am building an autonomous AI swarm framework called Hydra Swarm. I need you to help me write a system prompt file called 'evaluator_agent.md'. 

This prompt will turn an LLM into the 'Supreme Judge Agent'. It will be run via 'opencode run --prompt evaluator_agent.md' to evaluate the work of headless agents.

Here is the exact ecosystem you are integrating with:

--- BEGIN architect.md ---
${ARCHITECT_CTX}
--- END architect.md ---

--- BEGIN headless_agent.md ---
${HEADLESS_CTX}
--- END headless_agent.md ---

--- BEGIN llm_judge.md ---
${JUDGE_CTX}
--- END llm_judge.md ---

CRITICAL REQUIREMENTS FOR THE PROMPT YOU WRITE:
1. **Role:** It is the autonomous supreme judge of the Hydra Swarm. It has full access to 'bash', 'read', and 'glob' tools.
2. **Phase 1 (Objective Execution):** It must 'read' \`swarm_contract.json\`. If \`evaluation_protocol.objective_command\` exists, it must independently traverse into every \`.hydra_experiments/<agent_name>\` worktree and use its 'bash' tool to run that command. Any agent that returns a non-zero exit code is immediately disqualified.
3. **Phase 2 (Subjective Evaluation):** If \`evaluation_protocol.subjective_judge_prompt\` exists, it must use the 'read' tool to natively analyze the code diffs of ONLY the agents that survived Phase 1. It must evaluate them according to the rules in \`llm_judge.md\`.
4. **The Output Mandate:** It must conclude its run by writing exactly ONE raw JSON object to standard output, formatted as: 
   \`{"status": "SUCCESS" | "FAILED", "winner": "<agent_name>" | "NONE", "diagnosis": "<Detailed reasoning for the winner, or detailed root-cause analysis if all failed so hydra.sh can backtrack>"}\`

Please ask me questions to refine this agentic paradigm, and then draft 'evaluator_agent.md'.
EOF

# 2. Setup Tmux Session
# ------------------------------------------------------------------------------

tmux has-session -t "$SESSION_NAME" 2>/dev/null && tmux kill-session -t "$SESSION_NAME"
tmux new-session -d -s "$SESSION_NAME"

# We don't need to split panes, just use the single main window
# ------------------------------------------------------------------------------

tmux send-keys -t "$SESSION_NAME" "opencode --prompt \"\$(cat $TMP_DIR/evaluator_prompt.txt)\"" C-m

echo "✅ Tmux session '$SESSION_NAME' successfully created."
echo "➡️  Run 'tmux attach-session -t $SESSION_NAME' to interact with the Evaluator Prompt Engineer."
