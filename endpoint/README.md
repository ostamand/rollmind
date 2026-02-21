# Vertex AI Deployment Scripts

This directory contains the tools needed to move your RollMind model from local development to a production-ready Vertex AI Endpoint.

## ⚠️ Warning: Cost
Vertex AI Endpoints for custom LLMs require at least one GPU running 24/7. This costs approximately **$0.90 - $1.00 per hour** ($700/month). Always run `cleanup.py` when you are finished testing to stop billing.

---

## Step 1: Merge Weights
High-performance serving containers (like vLLM) work best with merged weights.
```bash
python3 endpoint/merge_model.py \
    --model_id google/gemma-7b-it \
    --adapter_path ./out/step2/test1_7b_r64/checkpoint-250 \
    --output_dir ./merged_model
```

---

## 🧪 Local Testing (Recommended)
Before spending 15 minutes deploying to GCP, verify your merged model locally.

### 1. Verify Weights (Lightweight)
Test if the merged model still understands D&D rules:
```bash
python3 inference.py \
    --model_id ./merged_model \
    --prompt "What is a Wizard?"
```

### 2. Verify Serving Container (Docker)
Test the exact container image Vertex AI will use (requires GPU and Docker).
```bash
# Terminal 1: Start the container
./endpoint/test_local_vllm.sh

# Terminal 2: Send a test request
python3 endpoint/test_local_vllm_request.py --prompt "Tell me about Fighters."
```

---

## Step 2: Deploy to Vertex AI
This script uploads the weights to GCS, registers the model, and provisions a GPU node (NVIDIA L4).
```bash
python3 endpoint/deploy.py \
    --bucket ostamand/rollmind \
    --local_model_dir ./merged_model \
    --name rollmind-v1 \
    --location us-east4
```
*Note: Deployment takes 5-15 minutes.*

## Step 3: Test the Endpoint
Once the deployment finishes, it will print an **Endpoint ID**. Use it to test:
```bash
python3 endpoint/test_endpoint.py 
    --endpoint_id 1234567890 
    --prompt "What is the hit point die for a Cleric?"
```

## Step 4: Cleanup (Stop Billing)
To stop paying for the GPU, you must undeploy the model and delete the endpoint.
```bash
python3 endpoint/cleanup.py --endpoint_id 1234567890
```

---

## Technical Details
- **Container:** Uses the official Vertex Vision vLLM serving container.
- **Hardware:** Deploys to `g2-standard-4` with 1x `NVIDIA_L4` GPU (24GB VRAM).
- **Region:** Default is `us-east4`.
