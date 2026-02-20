# Training Analysis: Step 1 (test2_7b_r64)

## 1. Executive Summary
This run is an **absolute triumph** for knowledge extraction. By increasing the capacity to **$r=64$** and adding **MLP targets** (`gate_proj`, `up_proj`), the 7B model was able to shatter the previous performance ceiling, reaching a peak `mean_token_accuracy` of **96.85%**. This officially moves the 7B project from "Good" to the **"Overfit/Perfect"** category, indicating near-total internalization of the provided D&D text.

## 2. Primary Metrics Analysis

| Metric | Result (at best step) | Status | Interpretation |
| :--- | :--- | :--- | :--- |
| **Train Loss** | 0.09 (Step 155) | **Exceptional** | Near-zero loss; effectively perfect convergence on the training set. |
| **Peak Accuracy** | 96.85% (Step 155) | **Overfit** | Surpassed the 95% threshold. Extremely high risk of verbatim "parrot" quoting. |
| **Eval Loss** | 6.26 (Final) | **Normal** | Followed the expected Step 1 curve: peaked at 7.3 before returning to baseline. |
| **Grad Norm** | ~1.3 (Stable) | **Strong** | Despite higher LR and capacity, training remained rock-solid. |

### The "Champion" Run:
*   **The Breakthrough:** Adding the MLP layers (`gate_proj`, `up_proj`) provided the necessary non-linear capacity for the model to store complex rules and tables.
*   **7B vs 2B:** This run now officially exceeds the 2B baseline (89%) in both raw accuracy and loss reduction, justifying the extra compute and VRAM complexity of the 7B model.

## 3. Selecting the Best Checkpoint
*   **Selected Checkpoint:** **Step 155 (Epoch 4.86)**
*   **Rationale:** This is the **Knowledge Peak**. It represents the absolute maximum of internalized information. While Step 160 showed a minor regression in accuracy (96.4%), Step 155 is the state-of-the-art for this dataset.

## 4. Success Rubric: Is it ready for Step 2?
*   [x] **Train Loss:** Has dropped to near zero (< 0.1).
*   [x] **Peak Accuracy:** 96.8% (Exceeds 70% target).
*   [x] **Trend Stability:** Exceptionally clean upward trajectory.
*   [x] **Grad Norm:** Stable.

**Verdict:** **Cleared for Step 2.** This is the strongest foundation for instruction tuning achieved so far.

## 5. Hyperparameter Optimization & Recommendations

The model has reached the point of diminishing returns for Step 1. Further training on this specific dataset is unnecessary.

| Recommendation | Suggested Change | Rationalization |
| :--- | :--- | :--- |
| **Increase Weight Decay** | **0.15 → 0.20** | Since accuracy is >95%, we need slightly more regularization to ensure the model learns *logic* rather than just *strings*. |
| **Increase LoRA Dropout** | **0.05 → 0.10** | For Step 2, we should increase dropout to prevent the model from being too rigid in its responses (avoiding "the textbook says exactly X" behavior). |

## 6. Red Flags
*   **Saturation:** The accuracy plateau between Steps 135 and 160 suggests we have squeezed every possible drop of information out of `full_chunks.jsonl`.
