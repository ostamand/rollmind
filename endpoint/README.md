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

## Step 2: Deploy to Vertex AI
The `deploy.py` script handles the end-to-end process: uploading weights to GCS, registering the model, and provisioning a GPU node (NVIDIA L4).

### Option A: Upload and Deploy (Fresh Model)
This will upload your local merged model to GCS and create a new endpoint (or update an existing one with the same name).

```bash
python3 endpoint/deploy.py \
    --local_path ./merged_model \
    --gcs_path gs://ostamand/rollmind/models/rollmind-v1 \
    --name rollmind-v1 \
    --location us-east4
```

### Option B: Skip Upload (Already in GCS)
If you've already uploaded the artifacts to GCS and just want to register/deploy the model:
```bash
python3 endpoint/deploy.py \
    --gcs_path gs://ostamand/rollmind/models/rollmind-v1 \
    --skip-upload \
    --name rollmind-v1 \
    --location us-east4
```

### Option C: Update Existing Endpoint
The script automatically detects if an endpoint with the same `--name` already exists. If it does:
1. It deploys the new model version to the existing endpoint.
2. Once the new version is healthy, it **automatically undeploys** the old version to save costs.

*Note: Deployment takes 5-15 minutes.*

## Step 3: Test the Endpoint
Once the deployment finishes, it will print an **Endpoint ID**. Use it to test:
```bash
python3 endpoint/test_endpoint.py \
    --endpoint_id 1234567890 \
    --prompt "What is the hit point die for a Cleric?" \
    --location us-east4
```

## Step 4: Manage Costs (Toggle ON/OFF)
To avoid 24/7 GPU billing without deleting your endpoint configuration, you can "toggle" the model deployment. This is much faster than a full redeploy and keeps your Resource Names persistent.

```bash
# Turn OFF (Stop GPU billing immediately)
python3 endpoint/toggle_endpoint.py off --name rollmind-gemma-7b_endpoint

# Turn ON (Redeploy the latest version)
# If your model name is different from your endpoint name, use --model_name
python3 endpoint/toggle_endpoint.py on \
    --name rollmind-gemma-7b_endpoint \
    --model_name rollmind-gemma-7b
```

## Step 5: Cleanup (Permanent)
To permanently remove the endpoint and model from Vertex AI:
```bash
python3 endpoint/cleanup.py --location us-east4 --endpoint_id 1234567890 
```

---

## Technical Details
- **Container:** Uses the official Vertex Vision `pytorch-vllm-serve` container.
- **Hardware:** Deploys to `g2-standard-12` with 1x `NVIDIA_L4` GPU (24GB VRAM).
- **Model Parameters:** Configured with `--max-model-len=1024` and `--tensor-parallel-size=1`.
- **Region Support:** Ensure your `--location` matches a region where `G2` instances are available (e.g., `us-east4`, `us-central1`).
