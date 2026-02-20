# Gemma D&D Manual Fine-Tuning

This project provides a simple, structured workflow for fine-tuning a Gemma model (2b or 7b) on a D&D Player's Handbook using a 12GB GPU. 

## 1. Setup

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

**1. Authentication for External VMs:**
- Go to the [GCP Console](https://console.cloud.google.com/iam-admin/serviceaccounts).
- Create a Service Account (or use an existing one) with the `Storage Object Viewer` role.
- Generate a **JSON Key**, download it, and upload it to your VM (e.g., as `key.json`).

**2. Run the Sync Script:**
```bash
# Using an explicit service account key (Required for non-GCP VMs)
python3 download_data.py --bucket your-bucket-name --prefix data/ --out ./data --creds key.json
```

## 2. Step 1: Data Preparation

Process raw markdown files into semantic chunks. This script produces `train_chunks.jsonl`, `val_chunks.jsonl`, and `full_chunks.jsonl` (the entire corpus).

```bash
python3 prepare/prepare_step1_data.py
```

## 3. Step 2: Q&A Generation (Instruction Data)

We use two methods to generate high-quality synthetic Question-Answer pairs from the D&D manual. This data is used in Step 4 to teach the model how to respond to users.

### Method A: General QA Generation
Generates a broad set of Q&A pairs from every chunk of the manual.
```bash
python3 prepare/generate_qa.py --project your-project-id
```
**Output:** `data/step2/train_qa.jsonl`

### Method B: Scenario-Based Generation (Recommended)
Generates targeted, high-level Q&A pairs based on specific player personas (e.g., Leveling Up, Combat, Social Skills). This creates more natural conversational data.

**Features:**
- **Modular:** Each scenario is saved to its own file in `data/step2/scenarios/`.
- **Resumable:** Automatically skips already-generated batches.
- **Targeted:** You can run a single scenario to expand its coverage.

```bash
# Generate all scenarios (50 pairs each)
python3 prepare/generate_scenarios.py --project your-project-id

# Generate a specific scenario only
python3 prepare/generate_scenarios.py --project your-project-id --scenario "Multiclassing" --total_per_scenario 100
```

**Note on Resuming:** Both scripts track progress. If interrupted, simply run them again to pick up where you left off.

## 4. Step 3: Continued Pre-training (Domain Adaptation)

Train the model on the full text of the manual (`full_chunks.jsonl`) to ensure 100% rule coverage. We use the Q&A validation set to ensure the model doesn't "forget" how to be an assistant.

```bash
python3 train/step1/train_step1.py --config train/step1/config_step1.json
```
**Output:** Trained LoRA adapters in `out/step1`.

## 5. Step 4: Instruction Fine-Tuning

Fine-tune the domain-adapted model on the synthetic Q&A pairs to sharpen its assistant capabilities.

```bash
python3 train/step2/train_step2.py --config train/step2/config_step2.json
```
**Output:** Final LoRA adapters in `out/step2`.

## 6. Evaluation

Calculate the Average Loss and Perplexity of a model on the validation set.

### Baseline (Original Gemma)
```bash
python3 eval/evaluate_model.py \
    --model_id google/gemma-2b-it \
    --dataset_path data/step2/val_qa.jsonl
```

### Domain Adapted (After Step 2)
```bash
python3 eval/evaluate_model.py \
    --model_id google/gemma-2b-it \
    --adapter_path ./out/step1/full_adaptation \
    --dataset_path data/step2/val_qa.jsonl
```

## 7. Inference

Use the `inference.py` script to chat with your model.

### Chat with Base Model
```bash
python3 inference.py --prompt "What are the core traits of a Fighter?"
```

### Chat with Fine-Tuned Model (LoRA)
```bash
python3 inference.py \
    --model_id google/gemma-2b-it \
    --adapter_path ./out/step2 \
    --prompt "What is the hit point roll dice for a priest"
```

## Project Structure
- `data/`: Raw markdown and generated JSONL datasets.
- `prepare/`: Scripts for data processing, splitting, and QA generation.
- `train/`: Fine-tuning scripts and JSON configurations for both steps.
- `eval/`: Evaluation scripts for measuring performance.
- `out/`: Trained model adapters, metrics, and checkpoints.


## 8. Current Best

```bash
python3 inference.py --prompt "What weapons can a Fighter use" --adapter_path ./out/step2/test1_7b_r64/checkpoint-250 --model_id 'google/gemma-7b-it'
```

## References
- [Gemma Prompt Structure Documentation](https://ai.google.dev/gemma/docs/core/prompt-structure)