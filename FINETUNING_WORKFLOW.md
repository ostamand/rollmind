# Gemma Fine-Tuning Workflow: D&D Manual

This document outlines a two-step process for fine-tuning a Gemma-it model (2b or 7b) on a 12GB GPU to accurately answer questions about a D&D manual.

## 1. Strategy Overview

We use a two-step approach to maximize accuracy:
1.  **Domain Adaptation (Continued Pre-training):** Train on raw markdown text to familiarize the model with D&D terminology and rules. No instruction template is used here.
2.  **Instruction Fine-Tuning (SFT):** Train on Question-Answer pairs using the official Gemma template to teach the model how to provide helpful, structured responses based on its new knowledge.

## 2. Environment Setup

Install the core Hugging Face libraries. We use `bitsandbytes` for 4-bit quantization (QLoRA) to fit the model in 12GB VRAM.

```bash
pip install -U transformers peft accelerate bitsandbytes datasets trl
```

## 3. Step 1: Domain Adaptation (Raw Text)

### Data Preparation
Chunk the markdown into logical sections.
*   **Format:** JSONL with a `"text"` field containing raw text.
*   **Chunk Size:** ~1024 tokens.
*   **Goal:** Next token prediction (learning the domain).

### Training Script Configuration
The model is loaded in 4-bit with `nf4` quantization. LoRA is applied to all linear modules for maximum parameter efficiency.

```python
model_id = "google/gemma-2b-it"

lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "o_proj", "k_proj", "v_proj", "gate_proj", "up_proj", "down_proj"],
    task_type="CAUSAL_LM",
)
```

## 4. Step 2: Instruction Fine-Tuning (Q&A)

### Data Preparation
Generate synthetic Q&A pairs and format them using the **Official Gemma Template**.
*   **Template:**
    ```
    <start_of_turn>user
    What is Armor Class?<end_of_turn>
    <start_of_turn>model
    Armor Class (AC) represents how hard it is for opponents to land a damaging blow on you...<end_of_turn>
    ```

### Training Strategy
1.  **Base:** Load `google/gemma-2b-it` and the LoRA adapters from Step 1.
2.  **Refinement:** Train on the Q&A dataset with a lower learning rate (e.g., `5e-5`).
3.  **Stability:** This step ensures the model retains its "Assistant" persona while utilizing the D&D knowledge.

## 5. Hardware Optimization (12GB VRAM)

*   **QLoRA (4-bit):** Essential for fitting the model and maintaining performance.
*   **Gradient Accumulation:** Use `gradient_accumulation_steps=8` with `batch_size=1` to simulate a larger effective batch size.
*   **Precision:** Use `bf16=True` if your GPU supports it (e.g., RTX 30/40 series), otherwise use `fp16=True`.
*   **Memory Efficiency:** Use `paged_adamw_32bit` optimizer to save VRAM.
