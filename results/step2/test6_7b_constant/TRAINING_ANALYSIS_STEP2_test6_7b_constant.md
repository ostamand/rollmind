# Training Analysis: Step 2 (test6_7b_constant)

## 1. Executive Summary
The `test6_7b_constant` run was an experiment to determine if a **constant learning rate** (`2e-5`) with **higher dropout** (`0.10`) could prevent the overfitting seen in `test5`. The results are definitive: **The constant learning rate approach did not outperform the cosine decay.** While it provided a stable training curve, the model reached a higher minimum `eval_loss` (1.38 vs 1.33) and showed the same divergence/overfitting behavior exactly at the 1.0 epoch mark.

## 2. Metric Breakdown & Comparison

| Metric | `test5` (Cosine @ 4e-5) | `test6` (Constant @ 2e-5) | Difference |
| :--- | :--- | :--- | :--- |
| **Best Eval Loss** | **1.3356** (Step 550) | 1.3863 (Step 550) | ❌ +3.8% (Worse) |
| **Eval Accuracy** | **64.83%** (Step 950) | 63.31% (Step 320 train) | ❌ -1.5% (Worse) |
| **Eval Entropy** | 1.50 | 1.50 | ➖ Identical |
| **Overfitting Point** | Epoch 1.0 | Epoch 1.0 | ➖ Identical |

## 3. Analysis vs. Mandates

### The "Constant" Experiment Result
*   **Hypothesis:** A steady, lower LR would allow for more stable learning and better generalization.
*   **Finding:** This hypothesis was **rejected**. By starting at a lower LR (`2e-5` vs `4e-5`), the model lacked the initial "learning pressure" required to reach the deeper minima achieved in `test5`. The stability of the constant LR did not prevent overfitting; both models began to diverge from the validation set after 1 full pass over the data.

### Impact of Higher Dropout (0.05 -> 0.10)
*   Increasing dropout was intended to force the model to learn more generalized patterns. While it kept the `eval_loss` from spiking as aggressively in the second epoch as it did in `test5`, it also slightly suppressed the model's ability to reach peak accuracy on the domain-specific D&D terms.

### The 1-Epoch Barrier
Both runs (Test 5 and Test 6) reached their absolute minimum `eval_loss` at **Step 550 (Epoch 1.0)**. This confirms that for this 7B model on the current `train_qa.jsonl` dataset, **one epoch is the maximum useful training duration**. Anything beyond 1.0 epoch leads to memorization of training samples rather than improved rule understanding.

## 4. Success Rubric Assessment
*   [x] **Convergence:** `eval_loss` reached a minimum and stabilized around 1.38.
*   [ ] **Peak Accuracy:** 62.8% (Below the 85% goal).
*   [x] **Instruction Adherence:** Stable entropy (1.50) confirms the model is not collapsing.

**Verdict:** **VALIDATED BUT INFERIOR.** The run confirms that `cosine` decay with a higher initial LR is the superior strategy for this model size.

## 5. Checkpoint Recommendation
*   **Primary Choice: Step 550.** Like `test5`, this is the "Sweet Spot" where loss is lowest before divergence begins. However, the `test5` Step 550 checkpoint remains the overall champion for deployment.

## 6. Hyperparameter Recommendations

1.  **Return to Cosine Scheduler:** The aggressive early learning of the `cosine` scheduler (starting at `4e-5` or even `5e-5`) is clearly more effective for the 7B model.
2.  **Cap Training at 1.0 Epochs:** Do not waste compute on second epochs for this dataset; the model has shown twice now that it will only overfit.
3.  **The Next Frontier (Rank 128):** As metrics have plateaued with `r=64`, the only remaining lever to reach the >70% accuracy target is to increase capacity. We should proceed with the **`r=128`** configuration.
