#!/bin/bash
# Ensure jq and tmux are installed
if ! command -v jq >/dev/null 2>&1 || ! command -v tmux >/dev/null 2>&1; then
    echo "Error: 'jq' and 'tmux' are required."
    exit 1
fi
if [ ! -f "swarm_contract.json" ]; then
    echo "Error: swarm_contract.json not found. Start hydra_oc_swarm.sh first so the contract is generated."
    exit 1
fi
SESSION_NAME="hydra_swarm_logs"
# Kill the session if it already exists from a previous run
tmux kill-session -t "$SESSION_NAME" 2>/dev/null
# Extract the list of agent names from the contract
AGENTS=$(jq -r '.agents[].name' swarm_contract.json)
if [ -z "$AGENTS" ]; then
    echo "Error: No agents found in swarm_contract.json"
    exit 1
fi
# Convert agent list to an array
LOG_FILES=()
for agent in $AGENTS; do
    LOG_FILES+=(".hydra_experiments/${agent}.log")
done

# Add Evaluator and Judge logs
LOG_FILES+=(".hydra_experiments/evaluator_output.txt")
LOG_FILES+=(".hydra_experiments/judge_output.txt")

echo "Starting Tmux session to monitor ${#LOG_FILES[@]} agents/processes..."

# We use tail -F (capital F) so it waits patiently if the log file hasn't been created yet!
# Create the first pane
tmux new-session -d -s "$SESSION_NAME" "echo 'Watching ${LOG_FILES[0]}...' && tail -F ${LOG_FILES[0]}"
# Loop through the remaining agents and split the window
for ((i=1; i<${#LOG_FILES[@]}; i++)); do
    tmux split-window -t "$SESSION_NAME" "echo 'Watching ${LOG_FILES[$i]}...' && tail -F ${LOG_FILES[$i]}"
    # Re-balance the panes evenly after every split
    tmux select-layout -t "$SESSION_NAME" tiled
done
# Finally, attach to the session
echo "Attaching to tmux session..."
tmux attach-session -t "$SESSION_NAME"
