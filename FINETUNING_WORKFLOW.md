# RollMind Fine-Tuning Workflow

This document outlines the professional two-step process used to transform Google's Gemma models into **RollMind**, a domain-expert D&D 2024 rules engine.

## 1. Strategy Overview

We use a two-step approach to maximize both rule retention and conversational utility:
1.  **Domain Adaptation (Continued Pre-training):** Training on 100% of the raw PHB markdown text to internalize the "Rules as Written" (RAW).
2.  **Instruction Alignment (SFT):** Training on a diverse, multi-task synthetic dataset to teach the model how to act as a character-aware assistant and use the `[ROLL]` tag system.

## 2. Step 1: Domain Adaptation (Rule Learning)

### Data Preparation (`prepare/prepare_step1_data.py`)
The 2024 Player's Handbook is processed into semantic chunks of ~3000 characters.
-   **Context Preservation:** Header hierarchies (#, ##, ###) are prepended to every chunk so the model never loses track of the current topic (e.g., knowing it's reading about "Grappled" within the "Conditions" section).
-   **Full Coverage:** We train on 100% of these chunks to ensure no rule is left behind.

### Training Configuration (`train/step1/`)
-   **Models:** Gemma 1.1 7B or Gemma 3 12B.
-   **LoRA Targets:** All linear modules (`q_proj`, `v_proj`, `gate_proj`, `up_proj`, etc.) for deep adaptation.
-   **Rank:** High rank (r=64 or r=128) used to capture the complexity of the ruleset.

## 3. Step 2: Instruction Alignment (The Assistant)

### Multi-Task Dataset (`prepare/aggregate_step2_data.py`)
We use a stratified mix of synthetic data generated via **Vertex AI (Gemini 3 Flash Preview)**:
-   **Contextual QA:** 5-7 QA pairs per PHB chunk, injected with randomized **Character Profiles**.
-   **Functional Rolls:** Dedicated examples of `[ROLL]` tags with upcasting and scaling logic.
-   **Table Scenarios:** Real-world gameplay situations like "Leveling Up" or "Multiclassing".
-   **Refusals:** Teaching the model to stay in its domain and decline impossible actions.

### Training Strategy (`train/step2/`)
-   **Adapter Loading:** We load the base model and apply the LoRA weights from Step 1 as the starting point.
-   **Completion-Only Loss:** We mask the user prompt so the model only learns to optimize the assistant's responses.
-   **Hyperparameters:** Lower learning rate (e.g., `4e-5`) and higher weight decay to maintain stability.

## 4. Hardware Optimization

-   **24GB VRAM:** Optimized for L4 or RTX 3090/4090 GPUs.
-   **QLoRA (4-bit):** Uses `bitsandbytes` NormalFloat4 quantization.
-   **Memory Management:** `gradient_checkpointing` and `adamw_8bit` optimizer are used to fit the 12B model comfortably.
-   **Flash Attention:** Uses `sdpa` implementation for faster processing.
