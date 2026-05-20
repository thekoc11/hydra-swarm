#!/bin/bash

# ==============================================================================
# Hydra Swarm Framework - Robust Parallel Prompt Multiplexer
# ==============================================================================

SESSION_NAME="hydra_builder"
TMP_DIR="/tmp/hydra_prompts"
mkdir -p "$TMP_DIR"

HYDRA_CONTEXT=$(cat hydra.sh 2>/dev/null || echo "Error: hydra.sh not found.")

# 1. Safely write the prompts to temporary files first
# ------------------------------------------------------------------------------

cat << EOF > "$TMP_DIR/architect_prompt.txt"
I am upgrading my bash tool, 'hydra.sh', into an autonomous AI swarm framework. I need you to help me write a system prompt file called 'architect.md'. 

This prompt will turn an LLM into the 'Socratic Architect'. It relies heavily on Andrej Karpathy's 'LLM Knowledge Base' philosophy: the Architect's job is to ruthlessly refine the user's intent into a rock-solid, explicit Knowledge Base (the Master Plan) that dumb, headless agents can later 'compile' into code.

CRITICAL REQUIREMENTS FOR THE PROMPT YOU WRITE:
1. It must mandate that the LLM assumes the user's initial query is extremely crude, naive, and technically flawed.
2. It must instruct the LLM to relentlessly interrogate the user (only 1-2 questions at a time) to expose edge cases and false assumptions before allowing any code to be written.
3. Once converged, it must output 'swarm_contract.json' (defining evaluation protocols and agent prompts) AND 'Master_Plan.md'.

Here is my current hydra.sh script so you understand the context:
\`\`\`bash
${HYDRA_CONTEXT}
\`\`\`

Please ask me questions to refine this behavior, and then draft 'architect.md'.
EOF

cat << EOF > "$TMP_DIR/headless_prompt.txt"
I am upgrading my bash tool, 'hydra.sh', into an autonomous AI swarm framework. I need you to help me write a system prompt file called 'headless_agent.md'. 

This file will be injected into headless agents. Following the 'LLM Knowledge Base' philosophy, these agents act as 'compilers'—they read the Master Plan and strictly translate it into code using a 5-State Machine.

CRITICAL REQUIREMENTS FOR THE PROMPT YOU WRITE:
1. It must enforce a strict 5-State Machine: State 1 (Blueprint), State 2 (Builder - happy path), State 3 (Adversary - drop tools, find flaws in own code), State 4 (Defender - fix flaws), State 5 (Self-Evaluator).
2. It must forbid skipping states.
3. It must require the agent to explicitly log transitions to stdout (e.g., '[STATE TRANSITION: 2 -> 3]').
4. It must instruct the agent to loop back to State 2 if State 5 fails.

Here is my current hydra.sh script so you understand the context:
\`\`\`bash
${HYDRA_CONTEXT}
\`\`\`

Please ask me questions to refine this logic, and then draft 'headless_agent.md'.
EOF

cat << EOF > "$TMP_DIR/judge_prompt.txt"
I am upgrading my bash tool, 'hydra.sh', into an autonomous AI swarm framework. I need you to help me write a system prompt file called 'llm_judge.md'. 
This file will evaluate competing agents on subjective tasks.

CRITICAL REQUIREMENTS FOR THE PROMPT YOU WRITE:
1. It must accept the original goal and the 'git diffs' of multiple competing agents.
2. It must evaluate based on Correctness, Robustness, and Elegance.
3. It MUST output exactly ONE winner. Ties are absolutely forbidden.
4. The final output must be a raw JSON string containing exactly two keys: 'winner' (the agent name) and 'reasoning'. No markdown code blocks.

Here is my current hydra.sh script for context:
\`\`\`bash
${HYDRA_CONTEXT}
\`\`\`

Please ask me questions to refine this evaluation rubric, and then draft 'llm_judge.md'.
EOF

cat << EOF > "$TMP_DIR/python_prompt.txt"
I am upgrading my bash tool, 'hydra.sh', into an autonomous AI swarm framework. I need you to help me write a Python script called 'swarm_evaluator.py'.

CRITICAL REQUIREMENTS FOR THE SCRIPT YOU WRITE:
1. It must read 'swarm_contract.json' in the current directory.
2. It must handle two types of evaluation protocols based on the contract: 'script' and 'llm_judge'.
3. If 'script': It iterates through '.hydra_experiments/<agent_name>' directories, runs a specified bash command (like pytest) using subprocess, and picks the fastest one that exits with code 0.
4. If 'llm_judge': It runs 'git diff HEAD' in each worktree, concatenates them, and uses subprocess to call 'opencode run' with 'llm_judge.md', returning the parsed JSON winner.
5. It must print ONLY the winning agent's name to stdout.

Here is the exact schema for the 'swarm_contract.json' file that your script will be parsing:
\`\`\`json
{
  "task_type": "objective | subjective",
  "evaluation_protocol": {
    "type": "script | llm_judge",
    "command": "<bash command to run if type is script, else null>",
    "judge_prompt": "<instructions for the llm judge if type is llm_judge, else null>"
  },
  "agents": [
    {
      "name": "exp-1-speed",
      "prompt": "Focus on execution speed."
    }
  ]
}
\`\`\`

Here is my current hydra.sh script:
\`\`\`bash
${HYDRA_CONTEXT}
\`\`\`

Please ask me questions to clarify the subprocess handling or edge cases, and then draft 'swarm_evaluator.py'.
EOF

# 2. Setup Tmux Session
# ------------------------------------------------------------------------------

tmux has-session -t "$SESSION_NAME" 2>/dev/null && tmux kill-session -t "$SESSION_NAME"
tmux new-session -d -s "$SESSION_NAME"

tmux split-window -h
tmux split-window -v
tmux select-pane -t 0
tmux split-window -v
tmux select-layout tiled

# 3. Launch Opencode safely using the generated prompt files
# ------------------------------------------------------------------------------

tmux send-keys -t "$SESSION_NAME:0.0" "opencode --prompt \"\$(cat $TMP_DIR/architect_prompt.txt)\"" C-m
tmux send-keys -t "$SESSION_NAME:0.1" "opencode --prompt \"\$(cat $TMP_DIR/headless_prompt.txt)\"" C-m
tmux send-keys -t "$SESSION_NAME:0.2" "opencode --prompt \"\$(cat $TMP_DIR/judge_prompt.txt)\"" C-m
tmux send-keys -t "$SESSION_NAME:0.3" "opencode --prompt \"\$(cat $TMP_DIR/python_prompt.txt)\"" C-m

echo "✅ Tmux session '$SESSION_NAME' successfully created."
