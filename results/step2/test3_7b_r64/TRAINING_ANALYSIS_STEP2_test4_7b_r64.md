# Training Analysis: Step 2 (test4_7b_r64)

## 1. Executive Summary
The `test4_7b_r64` run (Instruction Tuning) shows **solid convergence** and a healthy alignment between training and validation loss. The model successfully transitioned from the raw knowledge learned in Step 1 to the conversational format. However, the peak evaluation accuracy of **63.6%** is lower than the Step 2 target (>85%), suggesting that while the model is learning to follow instructions, it may still be struggling with the specific complexity of the QA pairs or is being overly constrained by high dropout.

## 2. Metric Breakdown

| Metric | Initial (Step 10/50) | Peak / Final (Step 596) | Status |
| :--- | :--- | :--- | :--- |
| **Train Loss** | 3.4713 | 1.4627 | ✅ Converged |
| **Eval Loss** | 1.7502 (Step 50) | 1.4038 | ✅ Excellent |
| **Eval Accuracy** | 56.9% (Step 50) | 63.6% | ⚠️ Lower than target (>85%) |
| **Eval Entropy** | 1.86 (Step 50) | 1.40 | ✅ Stable |

## 3. Analysis vs. Mandates

### Loss Convergence
Both training loss and evaluation loss decreased steadily throughout the run. This is a positive sign of healthy alignment without immediate overfitting. The `eval_loss` reached its "Gold Standard" minimum of **1.4038** at Step 400 and maintained it until the end of the run (Step 596).

### Primary Metric: Accuracy & Entropy
*   **Accuracy (63.6%):** This is significantly lower than the recommended >85% for Step 2. Given that Step 1 accuracy was >95%, this suggests a disconnect. The model has the knowledge, but the instruction-tuning phase isn't yet "unlocking" it at a high enough confidence level to match the targets.
*   **Entropy (1.40):** The entropy remains healthy. There is no sign of "Mode Collapse" (where the model becomes a robotic parrot), which indicates the model retains its conversational variety.

## 4. Success Rubric Assessment
*   [x] **Convergence:** `eval_loss` reached a clear minimum and stabilized.
*   [ ] **Peak Accuracy:** 63.6% (Target: >85%). 
*   [x] **No Repetition:** Grad norms and entropy are stable, suggesting no catastrophic collapse.

**Verdict:** **SUCCESSFUL ALIGNMENT, BUT NEEDS OPTIMIZATION.** The model is functional and ready for testing, but likely hasn't reached its full potential.

## 5. Checkpoint Recommendation
*   **Primary Choice:** **Step 400**. This checkpoint reached the minimum `eval_loss` first. Continuing to Step 596 provided no significant benefit in loss or accuracy, so Step 400 is the most efficient and least likely to have over-specialized.

## 6. Hyperparameter Recommendations
The current run uses a high dropout (`0.15`) and a conservative learning rate (`2e-5`).
1.  **Reduce `lora_dropout`:** Move from `0.15` to **`0.05`**. The low accuracy despite high Step 1 performance suggests the model is being "prevented" from utilizing its learned weights too strictly.
2.  **Increase Learning Rate:** Try **`4e-5`**. The 7B model has significant capacity; the current LR might be too gentle to shift the high-accuracy Step 1 weights into the new instruction format effectively.
3.  **Increase `lora_alpha`:** Current alpha is `128` (2x rank). Consider keeping this ratio but ensuring the model has enough "signal" to override its pre-trained tendencies.
