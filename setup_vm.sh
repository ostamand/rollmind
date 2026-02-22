#!/bin/bash
# setup_vm.sh - Fast environment setup for Rollmind on a 24GB GPU VM

set -e

echo "--- 1. Installing System Dependencies & GitHub CLI ---"
sudo apt-get update && sudo apt-get install -y git git-lfs python3-pip python3-venv curl
# Install GitHub CLI
if ! command -v gh &> /dev/null; then
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
    sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
    sudo apt update
    sudo apt install gh -y
fi

echo "--- 2. GitHub Authentication & Clone ---"
if ! gh auth status &> /dev/null; then
    echo "Please login to GitHub to clone the private repository:"
    gh auth login
fi

read -p "Enter the repository name (e.g., username/rollmind): " REPO_NAME
if [ ! -d "rollmind" ] && [ ! -z "$REPO_NAME" ]; then
    gh repo clone "$REPO_NAME" rollmind
    cd rollmind
fi

echo "--- 3. Setting up Python Virtual Environment ---"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Optional but highly recommended for 24GB+ GPUs (e.g., A10G, RTX 3090/4090)
echo "--- 3. Installing Performance Optimizations ---"
pip install flash-attn --no-build-isolation || echo "Flash Attention installation failed, continuing with SDPA..."

echo "--- 4. Authentication Check ---"
if ! command -v gcloud &> /dev/null; then
    echo "gcloud not found. Please install it if you need to download data from GCS."
else
    echo "Checking gcloud authentication..."
    gcloud auth application-default login --no-launch-browser
fi

echo "Hugging Face login (Required for Gemma):"
huggingface-cli login

echo "--- 5. Data Synchronization ---"
read -p "Enter GCS Bucket name (leave empty to skip): " BUCKET_NAME
if [ ! -z "$BUCKET_NAME" ]; then
    read -p "Enter GCS prefix (default: data/): " GCS_PREFIX
    GCS_PREFIX=${GCS_PREFIX:-data/}
    python3 download_data.py --bucket "$BUCKET_NAME" --prefix "$GCS_PREFIX" --out ./data
fi

echo "--- Setup Complete! ---"
echo "To start training, remember to activate the environment: source venv/bin/activate"
