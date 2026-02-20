# Step 1 Metrics Analysis Guide: Knowledge Extraction

This document outlines the standard procedure for evaluating the success of Step 1 (Knowledge Extraction) training runs for the Rollmind model.

## 0. Reporting Mandate

**Every analysis performed by the AI must be written to a dedicated markdown file in the project root.** 
*   **Filename Format:** `TRAINING_ANALYSIS_<STEP>_<RUN_NAME>.md` (e.g., `TRAINING_ANALYSIS_STEP1_v1.md`).
*   **Persistence:** Do not provide the analysis only in the chat; it must be saved to the filesystem for historical tracking.

## 1. The Core Paradox: Format Mismatch

In Step 1, we often see **Training Loss decreases** while **Validation Loss increases**.

*   **Why?** The Training set is usually "Raw Text Chunks," while the Validation set is "QA Pairs."
*   **Interpretation:** An increasing `eval_loss` in Step 1 does **not** necessarily mean overfitting. It usually means the model is specializing in the D&D writing style and moving away from the "generic" assistant style found in the QA validation set.

## 2. Primary Metric: `mean_token_accuracy`

This is your most reliable signal for knowledge absorption.

| Value | Status | Action |
| :--- | :--- | :--- |
| **< 50%** | **Weak** | Increase learning rate or LoRA rank. The model isn't "seeing" the patterns. |
| **60% - 75%** | **Good** | Standard range for a successful knowledge extraction on a 2B model. |
| **> 80%** | **Strong** | Excellent memorization. High risk of verbatim quoting (good for rules). |
| **> 95%** | **Overfit** | Model may lose conversational fluidity. Consider more weight decay. |

## 3. Selecting the Best Checkpoint

The "best" model for Rollmind is rarely the one with the lowest loss. Use this hierarchy:

1.  **The Knowledge Peak (Recommended):** The checkpoint with the **highest `mean_token_accuracy`**. This model has internalized the most rules and stylistic nuances.
2.  **The Inflection Point:** The step where accuracy begins to plateau (e.g., gaining < 1% over 20 steps). This is often the most efficient balance between learning and compute.
3.  **The Safety Checkpoint:** The checkpoint with the **lowest `eval_loss`**. Only use this if the "Knowledge Peak" version fails to converge or exhibits extreme hallucinations during Step 2.

## 4. Success Rubric: Is it ready for Step 2?

A run is cleared for Step 2 (Instruction Tuning) if it meets these criteria:

*   [ ] **Train Loss:** Has dropped significantly from the start (ideally < 1.5 for 2B models).
*   [ ] **Peak Accuracy:** `mean_token_accuracy` is at least **70%**.
*   [ ] **Trend Stability:** The accuracy curve shows a steady upward trend without massive erratic spikes.
*   [ ] **Grad Norm:** Remains stable (typically < 1.0). Spikes indicate unstable data or too high a learning rate.

## 5. Hyperparameter Optimization & Recommendations

When analyzing metrics, the AI **must always recommend** potentially better hyperparameters based on the run's performance, unless it is determined that the run is already near-optimal. Each recommendation must be rationalized by linking specific metric observations to the proposed change.

### Common Optimization Levers:

*   **Increase `lora_r` (LoRA Rank):** If accuracy plateaus early, the model may lack the "capacity" to store more knowledge. Moving from `r=16` to `r=32` or `r=64` can help.
*   **Adjust Learning Rate & Warmup:** If the loss curve is too jagged, decrease the LR slightly and increase `warmup_steps` to stabilize the early phase of learning.
*   **Extend Training:** If accuracy is still trending upward at the final step, increase the number of epochs. Knowledge extraction is often limited by "exposure time" to the text.
*   **Weight Decay:** To prevent verbatim "parrot" overfitting at very high accuracy (>90%), increase weight decay to encourage the model to learn general rules rather than specific strings.

## 6. Red Flags

*   **Stagnant Accuracy:** If accuracy stays flat for 50+ steps, the model has stopped learning. Increase LR or capacity.
*   **Zero Eval Accuracy:** Format mismatch in the validation file (check your prompt tags).
*   **Grad Norm Spikes:** Data contains "garbage" or noisy tokens that are confusing the model.
