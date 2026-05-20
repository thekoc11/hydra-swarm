#!/bin/bash

# Configuration
WORKTREE_BASE=".hydra_experiments"
MAIN_BRANCH=$(git branch --show-current)

function show_help {
    echo "Usage:"
    echo "  ./hydra.sh new <name> [count] [\"prompt\"]"
    echo "     Example: ./hydra.sh new test 3 \"Refactor this logic\""
    echo "     Example: ./hydra.sh new simple-fix \"Just fix this\""
    echo "  ./hydra.sh pick <experiment-name>"
    echo "  ./hydra.sh clean"
}

function ensure_safety {
    if [ -f ".gitignore" ]; then
        if ! grep -q "$WORKTREE_BASE" .gitignore; then
            echo "" >> .gitignore
            echo "# Temporary Hydra Experiments" >> .gitignore
            echo "$WORKTREE_BASE/" >> .gitignore
        fi
    else
        echo "$WORKTREE_BASE/" > .gitignore
    fi
}

# --- SMART ENVIRONMENT DETECTOR ---
function select_python_env {
    echo "🔍 Scanning for Python environments..." >&2 
    options=()
    paths=()

    for folder in ".venv" "venv" "env" ".env"; do
        if [ -d "$folder" ]; then
            options+=("Local: $folder")
            paths+=("$(pwd)/$folder")
        fi
    done

    if [ -f "pyproject.toml" ] && command -v poetry &> /dev/null; then
        POETRY_PATH=$(poetry env info --path 2>/dev/null)
        if [ ! -z "$POETRY_PATH" ]; then
            options+=("Poetry: $(basename $POETRY_PATH)")
            paths+=("$POETRY_PATH")
        fi
    fi

    if [ ! -z "$CONDA_PREFIX" ]; then
        options+=("Conda (Active): $(basename $CONDA_PREFIX)")
        paths+=("$CONDA_PREFIX")
    fi

    options+=("Enter Custom Path")
    paths+=("MANUAL")

    if [ ${#options[@]} -eq 0 ]; then
        echo "⚠️  No obvious environments found." >&2
        SELECTED_PATH="MANUAL"
    else
        PS3="Select your Python environment (Type number): "
        select opt in "${options[@]}"; do
            if [[ -n "$opt" ]]; then
                INDEX=$(($REPLY-1))
                SELECTED_PATH="${paths[$INDEX]}"
                break
            else
                echo "Invalid selection. Try again." >&2
            fi
        done
    fi

    if [ "$SELECTED_PATH" == "MANUAL" ]; then
        read -p "🐍 Enter absolute path to env folder: " SELECTED_PATH
    fi
    echo "$SELECTED_PATH"
}

# --- CORE WORKER FUNCTION ---
function spawn_experiment {
    local INSTANCE_NAME="$1"
    local ENV_PATH="$2"
    local PROMPT_TEXT="$3"

    TARGET_DIR="$WORKTREE_BASE/$INSTANCE_NAME"
    BRANCH_NAME="exp/$INSTANCE_NAME"

    # Zombie Check
    if git show-ref --verify --quiet "refs/heads/$BRANCH_NAME"; then
        echo "⚠️  Branch '$BRANCH_NAME' already exists. Deleting it for a fresh start..."
        git branch -D "$BRANCH_NAME"
    fi

    echo "🧪 Spawning: $INSTANCE_NAME..."
    
    if ! git worktree add -b "$BRANCH_NAME" "$TARGET_DIR"; then
        echo "❌ Error: Failed to create worktree for $INSTANCE_NAME"
        return 1
    fi

    if [ -f ".env" ]; then
        cp .env "$TARGET_DIR/.env"
        echo "   ✅ .env cloned"
    fi

    ln -s "$ENV_PATH" "$TARGET_DIR/.venv"
    echo "   ✅ .venv linked"

    code "$TARGET_DIR"
}

# --- MAIN LOGIC ---

if [ "$1" == "new" ]; then
    BASE_NAME="$2"
    ARG3="$3" # Could be count OR prompt
    ARG4="$4" # Prompt (if ARG3 is count)

    if [ -z "$BASE_NAME" ]; then
        echo "❌ Error: Please provide an experiment name."
        exit 1
    fi

    # Argument Parsing Logic
    COUNT=1
    PROMPT=""

    if [[ "$ARG3" =~ ^[0-9]+$ ]]; then
        # If 3rd arg is a number, it's the count
        COUNT=$ARG3
        PROMPT=$ARG4
    else
        # If 3rd arg is text (or empty), it's the prompt
        PROMPT=$ARG3
    fi

    ensure_safety

    # Ask for Env ONCE
    ENV_PATH=$(select_python_env)

    if [ -z "$ENV_PATH" ] || [ ! -d "$ENV_PATH" ]; then
        echo "❌ Error: Invalid environment path selected."
        exit 1
    fi

    # Clipboard: Copy prompt ONCE
    if [ ! -z "$PROMPT" ]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo "$PROMPT" | pbcopy
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            if command -v xclip &> /dev/null; then
                echo "$PROMPT" | xclip -selection clipboard
            else
                echo "⚠️  Install xclip to enable clipboard support." >&2
            fi
        elif grep -q Microsoft /proc/version; then
            echo "$PROMPT" | clip.exe
        fi
        echo "📋 Prompt copied to clipboard!"
    fi

    # Loop to spawn experiments
    if [ "$COUNT" -gt 1 ]; then
        for (( i=1; i<=COUNT; i++ )); do
            spawn_experiment "${BASE_NAME}-${i}" "$ENV_PATH" "$PROMPT"
        done
    else
        spawn_experiment "$BASE_NAME" "$ENV_PATH" "$PROMPT"
    fi

elif [ "$1" == "pick" ]; then
    WINNER="$2"
    if [ -z "$WINNER" ]; then
        echo "❌ Error: Which experiment won?"
        exit 1
    fi

    EXPERIMENT_DIR="$WORKTREE_BASE/$WINNER"

    # Check for uncommitted changes in the experiment worktree
    if [ -d "$EXPERIMENT_DIR" ]; then
        if [[ -n $(git -C "$EXPERIMENT_DIR" status --porcelain) ]]; then
            echo "⚠️  Uncommitted changes detected in $WINNER."
            read -p "💾 Do you want to commit them automatically? [y/N] " response
            if [[ "$response" =~ ^[yY]$ ]]; then
                git -C "$EXPERIMENT_DIR" add .
                git -C "$EXPERIMENT_DIR" commit -m "Hydra: Auto-commit before pick"
                echo "✅ Changes committed."
            else
                echo "❌ Aborting. Please commit your changes in '$EXPERIMENT_DIR' manually."
                exit 1
            fi
        fi
    fi

    echo "🏆 Merging winner: $WINNER into $MAIN_BRANCH"
    if git merge "exp/$WINNER"; then
        echo "✅ Merge complete. Run './hydra.sh clean' to remove experiments."
    else
        echo "❌ Merge failed. Please resolve conflicts or check git status."
        exit 1
    fi

elif [ "$1" == "clean" ]; then
    echo "🧹 Cleaning up..."
    rm -rf "$WORKTREE_BASE"
    git worktree prune
    echo "✨ Workspace folders cleaned."

else
    show_help
fi