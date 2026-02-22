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