# Step 2 Metrics Analysis Guide: Instruction Tuning

This document outlines the standard procedure for evaluating the success of Step 2 (Instruction Tuning/Alignment) training runs for the Rollmind model.

## 0. Reporting Mandate

**Every analysis performed by the AI must be written to a dedicated markdown file in the project root.** 
*   **Filename Format:** `TRAINING_ANALYSIS_<STEP>_<RUN_NAME>.md` (e.g., `TRAINING_ANALYSIS_STEP2_v1.md`).
*   **Persistence:** Do not provide the analysis only in the chat; it must be saved to the filesystem for historical tracking.

## 1. The Alignment Phase: Loss Convergence

Unlike Step 1, in Step 2 both the Training and Validation sets use the same **Instruction/QA format**.

*   **Expected Behavior:** You should see **both Training Loss and Validation Loss decrease** simultaneously.
*   **The Overfitting Signal:** If `train_loss` continues to fall while `eval_loss` begins to rise, the model is **overfitting** to the specific phrasing of your training QA pairs and is losing its ability to generalize to new questions.

## 2. Primary Metrics: Loss & Generalization

| Metric | Target | Interpretation |
| :--- | :--- | :--- |
| **Eval Loss** | **Decreasing** | The most important metric in Step 2. Lower is almost always better. |
| **Eval Accuracy** | **> 85%** | Because the instruction format is highly structured, accuracy should be significantly higher than in Step 1. |
| **Entropy** | **Stable** | If entropy drops too low, the model is becoming "robotic" and predictable (Mode Collapse). |

## 3. Selecting the Best Checkpoint

In Step 2, our priority shifts from knowledge absorption to **conversational generalization**.

1.  **The Gold Standard (Lowest Eval Loss):** The checkpoint with the absolute lowest `eval_loss`. This version generalizes best to unseen player questions. **This is almost always the preferred checkpoint for production.**
2.  **The "Sweet Spot":** The point right before `eval_loss` starts to tick upward, even if `train_loss` is still falling.
3.  **The Knowledge-Instruction Balance:** If the model "forgets" specific D&D rules learned in Step 1, you may need to pick a slightly earlier checkpoint or increase the influence of the Step 1 weights.

## 4. Success Rubric: Is it ready for Deployment?

A run is considered successful and ready for inference if:

*   [ ] **Convergence:** `eval_loss` reached a clear minimum and stabilized.
*   [ ] **Instruction Adherence:** Qualitative testing shows the model follows the "System Prompt" and uses the correct Markdown formatting.
*   [ ] **Rule Retention:** The model can still explain D&D mechanics accurately (verifying Step 1 knowledge wasn't "washed out").
*   [ ] **No Repetition:** The model doesn't get stuck in loops (a sign of too much training or too high a LoRA rank).

## 5. Hyperparameter Optimization & Recommendations

When analyzing metrics, the AI **must always recommend** potentially better hyperparameters based on the run's performance, unless it is determined that the run is already near-optimal. Each recommendation must be rationalized by linking specific metric observations to the proposed change.

### Common Optimization Levers:

*   **Lower Learning Rate:** Step 2 requires a much "gentler" touch than Step 1. If loss is erratic, cut the LR in half.
*   **Increase Dropout:** If the model overfits (Eval loss goes up), increase `lora_dropout` (e.g., from 0.05 to 0.1) to force better generalization.
*   **Prompt Template Check:** Ensure the training data exactly matches the `inference.py` prompt template (e.g., `### Instruction:`, `### Response:`). Even a missing newline can ruin Step 2.
*   **Epoch Count:** Step 2 usually requires fewer epochs than Step 1 (often 2-3 is enough).

## 6. Red Flags

*   **Catastrophic Forgetting:** The model follows instructions perfectly but forgets D&D rules. (Solution: Reduce LR or use a higher Step 1 starting weight).
*   **Mode Collapse:** The model gives the same "canned" answer to different questions. (Solution: Increase entropy or decrease training intensity).
*   **Loss Spikes:** Often indicates a corrupted QA pair in the training data (e.g., an empty response or broken JSON).
