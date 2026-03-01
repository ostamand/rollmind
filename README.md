# Gemma D&D Manual Fine-Tuning

This project provides a simple, structured workflow for fine-tuning a Gemma model (2b or 7b) on a D&D Player's Handbook.

## 🚀 Fast VM Setup (24GB VRAM)

For high-performance training on VMs with a 24GB GPU, use the automated setup script. This script handles GitHub authentication, repository cloning, and dependency installation:

```bash
# 1. Download and run the setup script
curl -fsSL -o setup_vm.sh https://raw.githubusercontent.com/<your-username>/rollmind/main/setup_vm.sh
chmod +x setup_vm.sh
./setup_vm.sh

# 2. Activate the environment
source venv/bin/activate
```

### Authentication Summary
- **GitHub CLI (gh):** Required to clone and push to your private repository.
- **Hugging Face:** Required to download gated Gemma weights.
- **Google Cloud (gcloud):** Required to sync data from GCS and generate synthetic QA.

---

## 1. Setup (Manual)

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Authentication
**Hugging Face:** Gemma is a gated model. Log in to download weights:
```bash
huggingface-cli login
```

**Google Cloud (Vertex AI):** Required for Q&A generation in Step 2:
```bash
gcloud auth application-default login
```

### Sync Data from GCS
If you are training on a remote VM (e.g., Lambda Labs, RunPod, or local server), you can download your pre-prepared data from a private GCS bucket.

```bash
# Using Application Default Credentials (ADC)
python3 download_data.py --bucket your-bucket-name --prefix data/ --out ./data
```

## 2. Step 1: Data Preparation

Process raw markdown files into semantic chunks. This script produces `train_chunks.jsonl`, `val_chunks.jsonl`, and `full_chunks.jsonl` (the entire corpus).

```bash
python3 prepare/prepare_step1_data.py
```

## 3. Step 2: Q&A Generation (Instruction Data)

We use two methods to generate high-quality synthetic Question-Answer pairs from the D&D manual.

### Method A: General QA Generation
Generates a broad set of Q&A pairs from every chunk of the manual.
```bash
python3 prepare/generate_qa.py --project your-project-id
```

### Method B: Scenario-Based Generation (Recommended)
Generates targeted, high-level Q&A pairs based on specific player personas (e.g., Leveling Up, Combat, Social Skills).

```bash
python3 prepare/generate_scenarios.py --project your-project-id
```

### Method C: Roll-Specific Data Generation
Generates training data for a D&D assistant that can output dice rolls using a custom `[ROLL]XdY+Z[/ROLL]` tag, including refusals for impossible actions.

```bash
# 1. Generate successful roll examples
python3 prepare/generate_rolls.py --project your-project-id

# 2. Generate roll-specific refusals (e.g., Level 8 spell at level 1)
python3 prepare/generate_roll_refusals.py --project your-project-id
```

## 4. Step 3: Continued Pre-training (Domain Adaptation)

Train the model on the full text of the manual (`full_chunks.jsonl`) to ensure 100% rule coverage.

**For 24GB GPUs (High Throughput):**
```bash
python3 train/step1/train_step1.py --config train/step1/config_step1_7b_24gb.json
```

**For 12GB GPUs (Low Memory):**
```bash
python3 train/step1/train_step1.py --config train/step1/config_step1.json --low-mem
```

## 5. Step 4: Instruction Fine-Tuning

Fine-tune the domain-adapted model on the synthetic Q&A pairs.

**For 24GB GPUs (High Throughput):**
```bash
python3 train/step2/train_step2.py --config train/step2/config_step2_7b_24gb.json
```

**For 12GB GPUs (Low Memory):**
```bash
python3 train/step2/train_step2.py --config train/step2/config_step2.json --low-mem
```

## 6. Evaluation

Calculate the Average Loss and Perplexity of a model on the validation set.

### Baseline (Original Gemma)
```bash
python3 eval/evaluate_model.py \
    --model_id google/gemma-7b-it \
    --dataset_path data/step2/val_qa.jsonl
```

### Domain Adapted (After Step 2)
```bash
python3 eval/evaluate_model.py \
    --model_id google/gemma-7b-it \
    --adapter_path ./out/step2/test1_7b_r64 \
    --dataset_path data/step2/val_qa.jsonl
```

## 7. Inference

Use the `inference.py` script to chat with your model.

### Chat with Fine-Tuned Model (LoRA)
```bash
python3 inference.py \
    --model_id google/gemma-7b-it \
    --adapter_path ./out/step2/test1_7b_r64/checkpoint-250 \
    --prompt "What is the hit point roll dice for a priest"
```

## 8. Deployment (Vertex AI)

To deploy the fine-tuned model as a scalable API on Vertex AI:

### A. Merge LoRA Weights
Before deployment, merge the LoRA adapter back into the base model weights.
```bash
python3 endpoint/merge_model.py \
    --model_id google/gemma-7b-it \
    --adapter_path ./out/step2/test1_7b_r64/checkpoint-250 \
    --output_dir ./merged_model
```

### B. Deploy to Vertex AI Endpoint
This script uploads the merged model to GCS (if not already present), registers it in the Vertex AI Model Registry, and deploys it to an L4 GPU endpoint.

**Important:** Vertex AI does not support the `global` location for model deployment. Ensure your location is set to a specific region (e.g., `us-east4`).

```bash
python3 endpoint/deploy.py \
    --gcs_path gs://ostamand/rollmind/models/rollmind-v1 \
    --name rollmind-v1 \
    --local_model_dir ./merged_model \
    --location us-east4
```

**Note:** If the model weights are already in your GCS bucket, you can skip the upload step using:
```bash
python3 endpoint/deploy.py --gcs_path gs://ostamand/rollmind/models/rollmind-v1 --skip-upload --location us-east4
```

### C. Toggling Costs (On/Off)
To avoid 24/7 GPU costs, you can "turn off" the endpoint when not in use. This undeploys the model but keeps the endpoint and model configuration intact.

```bash
# Turn OFF (Stop GPU billing)
python3 endpoint/toggle_endpoint.py off --name rollmind-v1

# Turn ON (Redeploy and resume)
python3 endpoint/toggle_endpoint.py on --name rollmind-v1
```

### D. Cleanup
To permanently remove the endpoint and model:
```bash
python3 endpoint/cleanup.py --endpoint_id <YOUR_ENDPOINT_ID>
```

## Project Structure
- `data/`: Raw markdown and generated JSONL datasets.
- `prepare/`: Scripts for data processing, splitting, and QA generation.
- `train/`: Fine-tuning scripts and JSON configurations for both steps.
- `eval/`: Evaluation scripts for measuring performance.
- `endpoint/`: Deployment automation for Vertex AI (merging, uploading, and hosting).
- `app/`: Source code for the web interface and API proxy.
- `out/`: Trained model adapters, metrics, and checkpoints.


## 9. Current Best

```bash
python3 inference.py --prompt "What weapons can a Fighter use" --adapter_path ./out/step2/test1_7b_r64/checkpoint-250 --model_id 'google/gemma-7b-it'
```

## References
- [Gemma Prompt Structure Documentation](https://ai.google.dev/gemma/docs/core/prompt-structure)