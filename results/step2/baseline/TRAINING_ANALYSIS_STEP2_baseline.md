# Training Analysis: Step 2 (baseline)

## 1. Executive Summary
The baseline run is a **significant improvement** over the previous `test2` attempt, proving that the `DataCollatorForCompletionOnlyLM` replacement (via `completion_only_loss=True`) and dataset splitting are working correctly. The `eval_loss` dropped from ~5.5 in the failed run to **1.32**, confirming the format is now aligned. However, the **Evaluation Accuracy (67.7%)** is still below the target threshold of >85%, suggesting the model needs more capacity or exposure to fully internalize the D&D rules.

## 2. Primary Metrics Analysis

| Metric | Result (at best step) | Target | Status |
| :--- | :--- | :--- | :--- |
| **Eval Loss** | 1.325 (Step 400) | Decreasing | **Pass** |
| **Eval Accuracy** | 67.7% (Step 430) | > 85% | **Weak** |
| **Entropy** | 1.49 (Final) | Stable | **Pass** |

*   **Format Alignment:** The close proximity of `train_loss` (~1.0) and `eval_loss` (1.32) indicates that the model is effectively learning the task without immediate catastrophic overfitting.
*   **Accuracy Plateau:** Accuracy grew from 57% to 67% but slowed down significantly in the second epoch. This suggests that the current hyperparameters may be hitting a "complexity ceiling."

## 3. Checkpoint Selection
*   **Selected Checkpoint:** **Step 400 (Epoch 1.86)**
*   **Rationale:** This represents the **Gold Standard** for this run, achieving the absolute lowest `eval_loss` (1.3256). Training beyond this point (up to step 430) showed a negligible gain in accuracy while the loss began a very slight upward tick.

## 4. Success Rubric
*   [x] **Convergence:** Yes. `eval_loss` reached a clear minimum.
*   [ ] **Instruction Adherence:** Moderate. 67% accuracy is functional but lacks the precision required for complex D&D rules.
*   [x] **No Repetition:** Pass. Entropy is healthy (1.49).

## 5. Hyperparameter Optimization & Recommendations

To push the accuracy from 67% toward the 85% target, the following changes are recommended:

| Recommendation | Suggested Change | Rationalization |
| :--- | :--- | :--- |
| **Increase Training Duration** | **2.0 → 4.0 Epochs** | Accuracy was still trending upward (albeit slowly) at the end of epoch 2. Given the stability of the loss, the model can likely tolerate more exposure. |
| **Increase LoRA Rank** | **lora_r: 32 → 64** | The bottleneck at 67% suggests the model lacks the "memory capacity" in the adapters to store the specific details of D&D spells and features. |
| **Increase Learning Rate** | **5e-5 → 8e-5** | The loss curve is very smooth and stable. A slightly higher learning rate might help the model escape the current local minimum for accuracy. |
| **Adjust Warmup** | **30 → 50 steps** | With an increased LR and more epochs, a longer warmup will ensure the weights don't deviate too sharply in the early phase of learning. |

## 6. Next Steps
The baseline proves the **pipeline is fixed**. We should now attempt a run that combines the **Step 1 Knowledge Adapters (r=32)** with these fixed Step 2 settings, while applying the increased capacity (r=64) to see if we can break the 80% accuracy barrier.
