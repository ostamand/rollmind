# Training Analysis: Step 2 (test5_7b_r64)

## 1. Executive Summary
The `test5_7b_r64` run (Gemma-7b-it) demonstrates successful instruction alignment but highlights a clear boundary for generalization. The model achieved its lowest evaluation loss at the end of the first epoch (Step 550), after which it began to overfit the training set during the second epoch. 

**Key takeaway:** One epoch of instruction tuning is likely sufficient for this dataset/configuration, as the second epoch led to a decrease in entropy and an increase in validation loss.

## 2. Metric Breakdown

| Metric | Value | Step / Epoch | Interpretation |
| :--- | :--- | :--- | :--- |
| **Best Eval Loss** | **1.3356** | Step 550 (Epoch 1.0) | Optimal balance of alignment and knowledge. |
| **Peak Eval Accuracy**| **64.83%** | Step 950 (Epoch 1.69) | High accuracy, but at the cost of higher loss. |
| **Final Train Loss** | 0.9160 | Step 1120 (Epoch 2.0) | Significant drop from ~1.5 (Epoch 1). |
| **Eval Entropy** | 1.18 - 1.50 | - | Sharp drop in Epoch 2 suggests reduced output variety. |

## 3. Analysis vs. Mandates

### The Overfitting Signal (Alignment Phase)
As per the `METRICS_ANALYSIS_STEP2.md` mandate, we look for the divergence between training and validation loss.
*   **Epoch 1 (Steps 1-560):** Both `train_loss` and `eval_loss` decreased steadily. `eval_loss` reached its minimum of **1.335** at Step 550.
*   **Epoch 2 (Steps 560-1122):** `train_loss` dropped sharply (from 1.27 to 0.91), while `eval_loss` rose to **1.37** and stayed between 1.36-1.37. This is a classic signal of overfitting to the specific phrasing of the QA pairs.

### Primary Metrics: Loss & Generalization
*   **Eval Accuracy:** Peaked at **64.8%** at Step 950. While improved over previous runs, it remains below the 85% target. This suggests that while the model is learning the *content*, the specific *token-level prediction* of long D&D rule explanations is challenging.
*   **Entropy:** Entropy dropped from **1.50** (Step 550) to **1.18** (Step 1100). This indicates the model is becoming "robotic" and more certain of specific (potentially memorized) answers in the second epoch.

## 4. Success Rubric Assessment
*   [x] **Convergence:** `eval_loss` reached a clear minimum at the end of Epoch 1.
*   [ ] **Peak Accuracy:** 64.8% (Below the 85% goal).
*   [x] **Instruction Adherence:** Qualitatively, the model follows the Gemma template correctly.
*   [x] **No Repetition:** No catastrophic mode collapse observed, though entropy reduction is a warning sign.

**Verdict:** **SUCCESSFUL ALIGNMENT.** The model is well-aligned to the instruction format. The Step 550 checkpoint is the best candidate for deployment.

## 5. Checkpoint Recommendation
*   **Primary Choice: Step 550.** This is the "Sweet Spot". It has the absolute lowest `eval_loss` (1.335) and the highest `eval_entropy` (1.50), meaning it retains the most conversational flexibility while having the best generalization.
*   **Comparison:** Checkpoints after Step 550 show higher accuracy but higher loss, indicating they are likely "guessing" the exact tokens of the training set rather than understanding the rules better.

## 6. Hyperparameter Recommendations

1.  **Reduce Epoch Count:** Set `num_train_epochs` to **1.0** or **1.25**. The second epoch provided no generalization benefit and likely degraded the model's creative "D&D flavor."
2.  **Learning Rate:** The current `4e-5` is effective for the first epoch. If continuing for multiple epochs, consider a steeper `cosine` decay or a lower starting rate (e.g., `2e-5`).
3.  **Increase Dropout:** To combat the overfitting seen in Epoch 2, increase `lora_dropout` from **0.05** back to **0.1** if multiple epochs are required.
4.  **LoRA Rank:** To push accuracy higher without overfitting, consider `lora_r=128`. The 7B model has enough capacity to benefit from a higher rank for complex rule-following.
