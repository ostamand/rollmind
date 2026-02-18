# GEMINI.md - Rollmind Project Context

## Project Overview
**Rollmind** is a specialized pipeline for fine-tuning Large Language Models (specifically Google's Gemma-2b-it) on D&D Player's Handbook documentation. The goal is to create a domain-specific assistant capable of understanding and answering questions based on the 2024 D&D rules.

### Main Technologies
- **Language:** Python
- **Frameworks:** Hugging Face `transformers`, `peft` (LoRA), `trl` (SFTTrainer), `datasets`.
- **Hardware Optimization:** `bitsandbytes` (4-bit quantization), `accelerate`.
- **API Integration:** Vertex AI SDK (Gemini 3 Flash Preview) for synthetic data generation.

### Architecture
The project follows a multi-step fine-tuning workflow:
1.  **Data Preparation:** Chunking markdown files into semantic units.
2.  **Step 1 (Domain Adaptation):** Continued pre-training on raw text chunks to learn terminology.
3.  **Instruction Data Generation:** Using Vertex AI to create Q&A pairs from all Step 1 chunks.
4.  **Step 2 (Instruction Tuning):** Fine-tuning the domain-adapted model on synthetic Q&A pairs.
5.  **Evaluation & Inference:** Measuring perplexity and interactive testing.

## Building and Running

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Login to Hugging Face (Gemma is gated)
huggingface-cli login

# Login to Google Cloud ADC (Required for Vertex AI)
gcloud auth application-default login
```

### Data Pipeline
```bash
# 1. Chunking Markdown
python3 prepare/prepare_step1_data.py

# 2. Generating Q&A (Requires Vertex AI setup)
# Processes all files in data/step1/ and splits into data/step2/train_qa.jsonl and val_qa.jsonl
python3 prepare/generate_qa.py
```

### Training
```bash
# Step 1: Domain Adaptation
python3 train/step1/train_step1.py --config train/step1/config_step1.json

# Step 2: Instruction Fine-tuning
python3 train/step2/train_step2.py --config train/step2/config_step2.json
```

### Evaluation & Inference
```bash
# Evaluate Perplexity
python3 eval/evaluate_model.py --model_id google/gemma-2b-it --adapter_path ./out/step2 --dataset_path data/step2/val_qa.jsonl

# Interactive Inference
python3 inference.py \
    --model_id google/gemma-2b-it \
    --adapter_path ./out/step2 \
    --prompt "What is the hit point roll dice for a priest"
```

## Development Conventions

### Data Format
- **Raw Chunks:** JSONL files with a single `"text"` field. Used in **Step 1** for domain adaptation. No instruction template is applied here to allow the model to focus purely on learning domain knowledge (D&D rules) via Next Token Prediction.
- **Instruction Data:** JSONL files with a single `"text"` field formatted using the official Gemma instruction template. Used in **Step 2** to teach the model how to act as an assistant using the knowledge gained in Step 1.
  ```
  <start_of_turn>user
  <question><end_of_turn>
  <start_of_turn>model
  <answer><end_of_turn>
  ```

### Model Configuration
- **Quantization:** 4-bit NormalFloat (NF4) with double quantization is used by default to fit training on 12GB VRAM GPUs.
- **LoRA:** Targeting all linear modules (`q_proj`, `v_proj`, etc.) for maximum effectiveness.
- **Precision:** Uses `bf16` if supported by hardware, otherwise falls back to `fp16`.

### Documentation
- **README Updates:** It is critical to keep `README.md` updated whenever changes are made that impact the project's usage or workflow. 
- **Content:** `README.md` should provide a high-level summary of how to use all available scripts and clearly outline the end-to-end training, evaluation, and inference flow.

### Project Structure
- `prepare/`: Data engineering and synthetic data generation.
- `train/`: Training logic and step-specific configurations.
- `eval/`: Metrics and validation logic.
- `data/`: Source markdown, intermediate chunks, and final training datasets.
- `out/`: Checkpoints and saved LoRA adapters.
