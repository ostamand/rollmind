# GEMINI.md - RollMind Project Context

## Project Overview
**RollMind** is a high-fidelity pipeline for fine-tuning Large Language Models (specifically Google's **Gemma 3 12B** and **Gemma 1.1 7B**) on the **2024 D&D Player's Handbook**. The goal is to create a domain-expert assistant capable of character-aware reasoning and functional mechanical execution (dice rolls).

### Main Technologies
- **Language:** Python 3.12, TypeScript (Next.js)
- **Frameworks:** Hugging Face `transformers`, `peft` (LoRA), `trl` (SFTTrainer), `datasets`, `FastAPI`.
- **Hardware Optimization:** `bitsandbytes` (4-bit NF4 quantization), `accelerate`, `sdpa` (Flash Attention).
- **API Integration:** Vertex AI (Gemini 3 Flash Preview) for complex synthetic data generation.

### Architecture
The project follows a rigorous two-step fine-tuning workflow:
1.  **Step 1: Domain Adaptation:** Continued pre-training on 100% of the PHB 2024 text chunks (~3000 chars each) with preserved header context to ensure deep rule retention.
2.  **Step 2: Instruction Alignment:** Multi-task SFT on a stratified synthetic dataset including Contextual QA, Functional Rolls (`[ROLL]` tags), Gameplay Scenarios, and Domain-Specific Refusals.

## Building and Running

### Setup
```bash
pip install -r requirements.txt
huggingface-cli login
gcloud auth application-default login
```

### Data Pipeline
```bash
# 1. Semantic Chunking
python3 prepare/prepare_step1_data.py

# 2. Synthetic Generation (QA, Rolls, Scenarios, Refusals)
python3 prepare/generate_qa.py --project $PROJ
python3 prepare/generate_rolls.py --project $PROJ
python3 prepare/generate_scenarios.py --project $PROJ
python3 prepare/generate_roll_refusals.py --project $PROJ

# 3. Stratified Aggregation
python3 prepare/aggregate_step2_data.py
```

### Training
```bash
# Step 1: Domain Adaptation (e.g. 12B or 7B)
python3 train/step1/train_step1.py --config train/step1/config_step1_7b_r128.json

# Step 2: Instruction Alignment
python3 train/step2/train_step2.py --config train/step2/config_step2_7b_roll_test1.json
```

### The Web App (`app/`)
RollMind includes a full-stack Next.js + FastAPI application with:
-   **Streaming Inference:** Real-time token delivery.
-   **Character Context:** Dynamic injection of player stats into prompts.
-   **DiceRoller:** Intercepts `[ROLL]` tags for cryptographic, animated dice results.

```bash
./app/start.sh
```

## Development Conventions

### Data Format & Templating
- **Instruction Template:** Official Gemma template is used for all Step 2 data and inference.
- **Context Injection:** Character profiles are prepended to the user prompt:
  `Character Profile: [Class] [Level]. Stats: [Score] ([Mod])...`
- **Functional Tags:** Mechanical actions use the `[ROLL]XdY+Z[/ROLL]` format.

### Training Strategy: Stability & Accuracy
- **Fact Coverage:** Step 1 trains on 100% of rules to prevent knowledge gaps.
- **Completion-Only Loss:** Step 2 masks the user prompt during training to optimize only for assistant accuracy.
- **High-Rank LoRA:** Uses `r=64` or `r=128` to capture the technical nuance of D&D rules.

### Project Structure
- `prepare/`: Advanced data engineering and Vertex AI generation.
- `train/`: LoRA and Partial fine-tuning logic.
- `app/`: Web frontend and FastAPI backend.
- `hf_hub/`: Utilities for model card generation and Hub uploads.
- `results/`: Training logs and metrics analysis.
- `data/`: PHB source markdown, split chunks, and aggregated synthetic sets.
