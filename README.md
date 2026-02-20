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

## 2. Step 1: Data Preparation

Process raw markdown files into semantic chunks. This script produces `train_chunks.jsonl`, `val_chunks.jsonl`, and `full_chunks.jsonl` (the entire corpus).

```bash
python3 prepare/prepare_step1_data.py
```

## 3. Step 2: Q&A Generation (Instruction Data)

Generate synthetic Question-Answer pairs from all training chunks using Vertex AI Gemini. **We run this before training** so the Q&A pairs can be used to validate the model's behavior during the learning process.

```bash
# Set env vars or use --project/--location
python3 prepare/generate_qa.py
```
**Output:** `data/step2/train_qa.jsonl` and `data/step2/val_qa.jsonl`.

**Note on Resuming:** The script automatically tracks progress in `data/step2/raw_qa.jsonl`. If the process is interrupted, simply run the command again to resume from the last completed chunk.

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
python3 inference.py --prompt "What weapons can a Fighter use" --adapter_path ./out/step2/test2_r64/checkpoint-200
```

## References
- [Gemma Prompt Structure Documentation](https://ai.google.dev/gemma/docs/core/prompt-structure)