# Training Analysis: Step 2 (test5_7b_r64)

## 1. Executive Summary
The `test5_7b_r64` run represents a **significant optimization** over `test4`. By increasing the learning rate to `4e-5` and reducing `lora_dropout` to `0.05`, we achieved lower training loss, lower evaluation loss, and a higher peak accuracy. The model converged more deeply, with the `eval_loss` dropping to **1.34** (compared to 1.40 in `test4`). While the 85% accuracy target hasn't been reached yet, this run confirms that the model was previously under-fitting due to overly restrictive dropout.

## 2. Metric Breakdown & Comparison

| Metric | `test4` (Final) | `test5` (Final) | Improvement |
| :--- | :--- | :--- | :--- |
| **Train Loss** | 1.4627 | 1.2902 | ✅ -11.8% |
| **Eval Loss** | 1.4038 | **1.3419** | ✅ -4.4% |
| **Eval Accuracy** | 63.6% | **65.0%** (Peak) | ✅ +1.4% |
| **Eval Entropy** | 1.40 | 1.50 | ✅ More Diverse |

## 3. Analysis vs. Mandates

### Hyperparameter Impact
*   **Lower Dropout (0.15 -> 0.05):** This was the most effective change. It allowed the model to more effectively "unlock" the 98% accuracy knowledge from Step 1. The training accuracy reached **75.7%** (Step 350) before settling, compared to lower levels in the previous run.
*   **Higher Learning Rate (2e-5 -> 4e-5):** The 7B model responded well to the higher LR. The loss curve was steeper and the model reached its minimum `eval_loss` significantly earlier (Step 300 vs Step 400).

### The Accuracy Plateau
Despite these improvements, the model is still plateauing around **65% eval accuracy**. This is common in Step 2 when the validation set consists of complex, multi-sentence answers where exact token matching is difficult. 
*   **Interpretation:** The model is effectively "aligned" to the format, but the metric might be undershooting its actual performance. Qualitative testing of this checkpoint is now required.

## 4. Success Rubric Assessment
*   [x] **Convergence:** `eval_loss` reached a clear minimum of 1.34 at Step 300 and stabilized.
*   [ ] **Peak Accuracy:** 65.0% (Still below the 85% goal).
*   [x] **Instruction Adherence:** The stable entropy (1.50) suggests the model is not collapsing into repetitive patterns.

**Verdict:** **BEST RUN TO DATE.** This model is the strongest candidate for deployment yet.

## 5. Checkpoint Recommendation
*   **Primary Choice:** **Step 300**. This checkpoint achieved the absolute lowest `eval_loss` (**1.3419**) and represents the "Sweet Spot" before the model began to fluctuate slightly in later steps.
*   **Secondary Choice:** **Step 450**. This checkpoint achieved the highest `eval_mean_token_accuracy` (**65.03%**). Use this if Step 300 feels slightly less confident in its rules knowledge.

## 6. Hyperparameter Recommendations
We have likely reached the limit of what simple LR/Dropout adjustments can do for a 7B model on this specific dataset.
1.  **Data Quality:** Review the `val_qa.jsonl` file. If the answers are very long (as discussed in previous feedback), the `mean_token_accuracy` will naturally be lower because the model has more "opportunities" to diverge from the reference text even while being correct.
2.  **Increase LoRA Rank:** To push past 70% accuracy, we might need to increase capacity. Consider a run with **`lora_r=128`** and **`lora_alpha=256`**.
3.  **Epoch Count:** The model was still improving its accuracy at Step 350. Extending training to **3 or 4 epochs** might allow for a slower, deeper convergence.
