#!/bin/bash
set -eou pipefail

# ==============================================================================
# HYDRA SWARM FRAMEWORK - ORCHESTRATOR
# ==============================================================================

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() { echo -e "${BLUE}[HYDRA]${NC} $1"; }
log_success() { echo -e "${GREEN}[HYDRA SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[HYDRA WARN]${NC} $1"; }
log_err() { echo -e "${RED}[HYDRA ERROR]${NC} $1"; }

# 1. Dependency Check
# ------------------------------------------------------------------------------
for cmd in opencode jq git awk; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        log_err "'$cmd' is required but not installed."
        exit 1
    fi
done

# 2. Environment Initialization
# ------------------------------------------------------------------------------
mkdir -p .hydra_experiments
if [ -d .git ] && [ -f .git/info/exclude ]; then
    if ! grep -q "^.hydra_experiments/" .git/info/exclude; then
        echo ".hydra_experiments/" >> .git/info/exclude
        log "Added .hydra_experiments/ to .git/info/exclude"
    fi
fi

# 3. Phase 0: Socratic Architect (Interactive Crucible)
# ------------------------------------------------------------------------------
RUN_ARCHITECT=true

if [ -f "Master_Plan.md" ] && [ -f "swarm_contract.json" ]; then
    log_warn "Master_Plan.md and swarm_contract.json already exist."
    echo -n "Do you want to (s)kip the Crucible and use existing files, or (r)e-run the Architect? [s/r]: "
    read -r SKIP_CHOICE
    if [[ "$SKIP_CHOICE" =~ ^[Ss]$ ]]; then
        RUN_ARCHITECT=false
        log "Skipping Socratic Architect. Using existing Master_Plan.md and swarm_contract.json."
    fi
fi

if [ "$RUN_ARCHITECT" = true ]; then
    log "Initiating Socratic Architect..."
    echo -n "Enter your initial application goal (The Naive Request): "
    read -r USER_GOAL
    
    # Prepend the user goal to the system prompt dynamically so the TUI sees it
    cp architect.md .hydra_experiments/architect_injected.md
    echo -e "\n\n## USER'S INITIAL GOAL\n$USER_GOAL\n\nPlease begin the interrogation based on the goal above." >> .hydra_experiments/architect_injected.md

    log "Launching interactive Socratic Architect... (Type CONVERGE when the plan is finalized)"
    opencode --prompt .hydra_experiments/architect_injected.md
    
    # Cleanup the injected prompt
    rm -f .hydra_experiments/architect_injected.md
    
    # If the interactive session closed but files still don't exist, we must fail.
    if [ ! -f "Master_Plan.md" ] || [ ! -f "swarm_contract.json" ]; then
        log_err "Architect did not save Master_Plan.md and swarm_contract.json."
        log_err "Please ensure you instruct it to write the files to disk using the 'write' tool after CONVERGE."
        exit 1
    fi
fi

BASE_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# 4. Main Framework Loop (The Engine)
# ------------------------------------------------------------------------------
ITERATION=1
while true; do
    log "=== STARTING SWARM ITERATION $ITERATION ==="
    
    NUM_AGENTS=$(jq '.agents | length' swarm_contract.json)
    log "Spawning $NUM_AGENTS headless agents..."

    # Phase 1: Spawning the Swarm
    for i in $(seq 0 $((NUM_AGENTS - 1))); do
        AGENT_NAME=$(jq -r ".agents[$i].name" swarm_contract.json)
        AGENT_PROMPT=$(jq -r ".agents[$i].prompt" swarm_contract.json)
        WORKTREE_PATH=".hydra_experiments/$AGENT_NAME"
        BRANCH_NAME="hydra/$AGENT_NAME"

        # Cleanup lingering worktrees from previous iterations
        if [ -d "$WORKTREE_PATH" ]; then
            git worktree remove --force "$WORKTREE_PATH" >/dev/null 2>&1 || true
            git branch -D "$BRANCH_NAME" >/dev/null 2>&1 || true
        fi

        log "Creating isolated Git worktree for $AGENT_NAME..."
        git worktree add -b "$BRANCH_NAME" "$WORKTREE_PATH" "$BASE_BRANCH" > /dev/null 2>&1

        log "Launching Agent: $AGENT_NAME in background..."
        
        # When --dir is used, relative paths for --prompt and the prompt text are evaluated from the new dir
        # So we use absolute path for the prompt file
        PROMPT_FILE="$(pwd)/headless_agent.md"
        MASTER_PLAN="$(pwd)/Master_Plan.md"
        
        opencode run \
            --dangerously-skip-permissions \
            --dir "$WORKTREE_PATH" \
            "$(cat "$PROMPT_FILE")

---
Read $MASTER_PLAN and execute strategy: $AGENT_PROMPT" \
            > ".hydra_experiments/${AGENT_NAME}.log" 2>&1 &
    done

    log "Waiting for all Swarm Agents to complete the 5-State Machine..."
    wait
    log_success "All agents have completed execution."

    # Phase 2: The Tribunal Prep (The Bailiff)
    log "Summoning the Evaluator (The Bailiff)..."
    opencode run \
        --dangerously-skip-permissions \
        "$(cat "$(pwd)/evaluator_agent.md")

---
Evaluate the swarm." \
        > .hydra_experiments/evaluator_output.txt 2>&1 || true

    # Extract JSON verdict from XML block
    awk '/<HYDRA_VERDICT>/{flag=1; next} /<\/HYDRA_VERDICT>/{flag=0} flag' .hydra_experiments/evaluator_output.txt > .hydra_experiments/verdict.json
    
    if [ ! -s .hydra_experiments/verdict.json ]; then
        log_err "Failed to parse JSON from Evaluator. Full output was:"
        cat .hydra_experiments/evaluator_output.txt
        exit 1
    fi

    STATUS=$(jq -r '.status' .hydra_experiments/verdict.json)
    WINNER=$(jq -r '.winner' .hydra_experiments/verdict.json)
    DIAGNOSIS=$(jq -r '.diagnosis' .hydra_experiments/verdict.json)
    
    # Phase 3: The Tribunal (The Judge)
    if [ "$STATUS" == "PENDING_JUDGE" ]; then
        log "Bailiff handoff received. Summoning the Judge..."
        if [ ! -f ".hydra_experiments/judge_input.txt" ]; then
            log_err "Bailiff returned PENDING_JUDGE but failed to create judge_input.txt."
            exit 1
        fi
        
        opencode run \
            --dangerously-skip-permissions \
            "$(cat "$(pwd)/llm_judge.md")

---
$(cat .hydra_experiments/judge_input.txt)" \
            > .hydra_experiments/judge_output.txt 2>&1 || true
            
        # Extract JSON verdict from XML block or fallback to markdown block
        if grep -q "<JUDGE_VERDICT>" .hydra_experiments/judge_output.txt; then
            awk '/<JUDGE_VERDICT>/{flag=1; next} /<\/JUDGE_VERDICT>/{flag=0} flag' .hydra_experiments/judge_output.txt > .hydra_experiments/judge_verdict.json
        else
            awk '/```json/{flag=1; next} /```/{flag=0} flag' .hydra_experiments/judge_output.txt > .hydra_experiments/judge_verdict.json
        fi
        
        if [ ! -s .hydra_experiments/judge_verdict.json ]; then
            log_err "Failed to parse JSON from Judge. Full output was:"
            cat .hydra_experiments/judge_output.txt
            exit 1
        fi
        
        STATUS="SUCCESS"
        WINNER=$(jq -r '.winner' .hydra_experiments/judge_verdict.json)
        DIAGNOSIS=$(jq -r '.reasoning' .hydra_experiments/judge_verdict.json)
        
        # If the Judge disqualified everyone
        if [ "$WINNER" == "NONE" ] || [ "$WINNER" == "null" ]; then
            STATUS="FAILED"
            WINNER="NONE"
        fi
    fi

    # Phase 4: The Verdict & Backtrack Circuit Breaker
    if [ "$WINNER" != "NONE" ] && [ "$WINNER" != "null" ]; then
        log_success "THE TRIBUNAL HAS DECLARED A WINNER!"
        log_success "Winner: $WINNER"
        echo -e "${GREEN}Diagnosis:${NC} $DIAGNOSIS"
        echo ""
        log "Cleaning up losing worktrees..."
        for i in $(seq 0 $((NUM_AGENTS - 1))); do
            AGENT_NAME=$(jq -r ".agents[$i].name" swarm_contract.json)
            if [ "$AGENT_NAME" != "$WINNER" ]; then
                git worktree remove --force ".hydra_experiments/$AGENT_NAME" 2>/dev/null || true
                git branch -D "hydra/$AGENT_NAME" 2>/dev/null || true
            fi
        done
        log_success "Hydra Swarm execution complete."
        log_success "You can inspect the winning code in '.hydra_experiments/$WINNER' or merge it via: 'git merge hydra/$WINNER'"
        break
    else
        log_warn "THE SWARM HAS FAILED."
        echo -e "${RED}Diagnosis:${NC} $DIAGNOSIS"
        
        log "Cleaning up failed worktrees..."
        for i in $(seq 0 $((NUM_AGENTS - 1))); do
            AGENT_NAME=$(jq -r ".agents[$i].name" swarm_contract.json)
            git worktree remove --force ".hydra_experiments/$AGENT_NAME" 2>/dev/null || true
            git branch -D "hydra/$AGENT_NAME" 2>/dev/null || true
        done

        log "Initiating Architect Backtrack Sequence..."
        
        opencode run \
            --dangerously-skip-permissions \
            "$(cat "$(pwd)/architect.md")

---
## BACKTRACK TRIGGERED
The swarm failed. Evaluator Diagnosis:
$DIAGNOSIS

Please update Master_Plan.md and swarm_contract.json to address these fundamental flaws. IMPORTANT MANDATE: You MUST use the 'write' tool to save the updated Master_Plan.md and swarm_contract.json files to disk before concluding." \
            > .hydra_experiments/backtrack.log 2>&1
            
        log_warn "Backtrack complete. Respawning Swarm with hardened Master Plan..."
        ((ITERATION++))
    fi
done