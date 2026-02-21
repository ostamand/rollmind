#!/bin/bash
# endpoint/test_local_vllm.sh

# 1. Configuration
# Use absolute path to ensure Docker mount works
MODEL_DIR="$(pwd)/merged_model"
PORT=8080
IMAGE="us-docker.pkg.dev/vertex-ai/vertex-vision-model-garden-dockers/pytorch-vllm-serve:latest"

echo "🚀 Starting local vLLM container..."
echo "Model directory: $MODEL_DIR"
echo "Port: $PORT"

# Check if merged_model exists
if [ ! -d "$MODEL_DIR" ]; then
    echo "❌ Error: $MODEL_DIR not found. Please run endpoint/merge_model.py first."
    exit 1
fi

# Run the container
# --gpus all: Required to use the GPU
# -v $MODEL_DIR:/model: Mount the local merged model into the container
# -p $PORT:8080: Map host port to container port
docker run --gpus all -it --rm \
    -v "$MODEL_DIR":/model \
    -p $PORT:8080 \
    --name rollmind-vllm-test \
    "$IMAGE" \
    --host=0.0.0.0 \
    --port=8080 \
    --model=/model \
    --max-model-len=1024 \
    --tensor-parallel-size=1
