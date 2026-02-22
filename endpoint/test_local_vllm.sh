#!/bin/bash
# endpoint/test_local_vllm.sh

# Configuration
MODEL_DIR="$(pwd)/merged_model"
PORT=8080
# April 2024 image - newer than initial Gemma release, likely better tokenizer support
IMAGE="us-docker.pkg.dev/vertex-ai/vertex-vision-model-garden-dockers/pytorch-vllm-serve:public-image-20240414_0916_RC00"

echo "🚀 Starting local vLLM container..."
echo "Model directory: $MODEL_DIR"
echo "Port: $PORT"

# Check if merged_model exists
if [ ! -d "$MODEL_DIR" ]; then
    echo "❌ Error: $MODEL_DIR not found. Please run endpoint/merge_model.py first."
    exit 1
fi

# Run the container
# --ipc=host: Required for efficient shared memory
docker run --gpus all -it --rm \
    --ipc=host \
    --ulimit memlock=-1 \
    --ulimit stack=67108864 \
    -v "$MODEL_DIR":/model \
    -p $PORT:8080 \
    -e PORT=8080 \
    --name rollmind-vllm-test \
    "$IMAGE" \
    python3 -m vllm.entrypoints.api_server \
    --host=0.0.0.0 \
    --port=8080 \
    --model=/model \
    --max-model-len=1024 \
    --tensor-parallel-size=1
