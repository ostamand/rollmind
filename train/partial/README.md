# Partial Fine-Tuning (Top-Layer Unfreezing)

This directory contains scripts for **Partial Fine-Tuning** on 24GB VRAM GPUs. Unlike LoRA, which adds adapters, this method unfreezes the actual weights of the top transformer layers and the LM head, allowing for a deeper "re-wiring" of the model's domain knowledge.

## Why Partial Fine-Tuning?
- **Better Domain Knowledge:** Updating the actual weights of the final layers can lead to more stable rule retrieval than LoRA.
- **Instruction Adherence:** Unfreezing the `lm_head` helps the model better align its conversational style with the instruction format.
- **VRAM Optimized:** By using `adamw_8bit` and freezing the backbone, we can fit a 7B model training into 24GB.

## Memory Requirements (7B Model)
- **Base Model (Frozen BF16):** ~14 GB
- **Top 4 Layers (Unfrozen):** ~6 GB (Weights + Gradients + 8-bit Optimizer States)
- **Total:** **~20-21 GB VRAM** (Leaving 3GB for activations and KV cache).

**Warning:** Unfreezing the embeddings (`embed_tokens`) on Gemma-7b adds roughly **6GB** of overhead. If you unfreeze embeddings, you must reduce the number of unfrozen layers (e.g., `--num-layers 2`) to avoid Out-Of-Memory (OOM) errors.

## Usage

### Step 1: Domain Adaptation (Rule Learning)
Trains on the 100% rules corpus using the last 4 layers.
```bash
python3 step1/train_partial_step1.py 
    --config step1/config_partial_step1.json 
    --num-layers 4
```

### Step 2: Instruction Tuning (Alignment)
Aligns the model to the conversational assistant format using the weights from Step 1.
```bash
python3 step2/train_partial_step2.py 
    --config step2/config_partial_step2.json 
    --num-layers 4
```

## Arguments
- `--config`: Path to the JSON configuration file.
- `--num-layers`: (Default: 4) The number of transformer blocks to unfreeze, starting from the last layer.
- `--unfreeze-embeddings`: (Flag) If present, unfreezes the `embed_tokens` layer. Use with caution.

## Configuration Details
- **Learning Rate:** Typically lower than LoRA (e.g., `2e-5` for Step 1, `1e-5` for Step 2).
- **Optimizer:** Hardcoded to `adamw_8bit` to save VRAM.
- **Weight Decay:** Higher decay (e.g., `0.05`) in Step 2 helps prevent forgetting the Step 1 knowledge.
