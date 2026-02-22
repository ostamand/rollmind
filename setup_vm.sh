#!/bin/bash
# setup_vm.sh - Fast environment setup for Rollmind on a 24GB GPU VM

set -e

echo "--- 1. Installing System Dependencies ---"
sudo apt-get update && sudo apt-get install -y git git-lfs python3-pip python3-venv

echo "--- 2. Setting up Python Virtual Environment ---"
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
