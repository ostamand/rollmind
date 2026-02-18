# Gemma D&D Manual Fine-Tuning

This project provides a simple, structured workflow for fine-tuning a Gemma model (2b or 7b) on a D&D Player's Handbook using a 12GB GPU. 

## 1. Setup

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Hugging Face Authentication
Gemma is a gated model. Ensure you have accepted the license on Hugging Face and log in via the CLI:
```bash
huggingface-cli login
```

## 2. Step 1: Data Preparation (Domain Adaptation)

Process raw markdown files into semantic chunks with header context and pre-split them into training and validation sets.

```bash
# Default (3000 chars per chunk)
python3 prepare/prepare_step1_data.py

# Custom chunk size
python3 prepare/prepare_step1_data.py --max_chars 4000
```
**Output:** `data/train_chunks.jsonl` and `data/val_chunks.jsonl`.

## 3. Step 2: Continued Pre-training

Train the model on the raw text chunks to learn D&D terminology and rules.

```bash
python3 train/step1/train_step1.py --config train/step1/config_step1.json
```
**Output:** Trained LoRA adapters in `out/step1`.

## 4. Step 3: Q&A Generation (Instruction Tuning Data)

To make the model an "assistant," we generate synthetic Question-Answer pairs from our training chunks using the Gemini API.

```bash
python3 prepare/generate_qa.py --api_key YOUR_GEMINI_API_KEY
```
**Output:** `data/train_qa.jsonl` formatted as User/Assistant turns.

## 5. Step 4: Instruction Fine-Tuning

Train the model using the generated Q&A pairs to improve its ability to answer user queries.

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
    --dataset_path data/step1/val_chunks.jsonl
```

### Domain Adapted (After Step 2)
```bash
python3 eval/evaluate_model.py \
    --model_id google/gemma-2b-it \
    --adapter_path ./out/step1 \
    --dataset_path data/step1/val_chunks.jsonl
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
    --adapter_path ./out/step1/checkpoint-100 \
    --prompt "What is the hit point roll dice for a priest" \
    --no_template
```

## Project Structure
- `data/`: Raw markdown and generated JSONL datasets.
- `prepare/`: Scripts for data processing, splitting, and QA generation.
- `train/`: Fine-tuning scripts and JSON configurations for both steps.
- `eval/`: Evaluation scripts for measuring performance.
- `out/`: Trained model adapters and checkpoints.

## References
- [Gemma Prompt Structure Documentation](https://ai.google.dev/gemma/docs/core/prompt-structure)