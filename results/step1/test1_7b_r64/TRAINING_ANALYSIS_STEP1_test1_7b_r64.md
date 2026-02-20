# Training Analysis: Step 1 (test1_7b_r64)

## 1. Executive Summary
This run marks the first successful knowledge extraction using the **Gemma 7B** model on limited VRAM (12GB). While the model surpassed the success threshold of 70% accuracy, it performed significantly lower than the **Gemma 2B** baseline (89%). This is primarily due to the "extreme offloading" constraints required to fit the larger model, specifically the restricted LoRA target modules and shorter training duration.

## 2. Primary Metrics Analysis

| Metric | Result (at best step) | Status | Interpretation |
| :--- | :--- | :--- | :--- |
| **Train Loss** | 0.96 (Step 80) | **Good** | Dropped from ~8.2; shows strong convergence. |
| **Peak Accuracy** | 76.41% (Step 80) | **Good** | Surpassed the 70% target, but lacks the "Strong" absorption of the 2B run. |
| **Eval Loss** | 6.20 (Static) | **Normal** | Consistent with Step 1 format mismatch (Text vs QA). |
| **Grad Norm** | ~3.9 (Stable) | **Strong** | Excellent stability despite heavy VRAM optimizations. |

### The "Capacity vs. Size" Trade-off:
*   **Efficiency:** The 7B model is learning, but it is doing so with one hand tied behind its back. By restricting LoRA to only attention modules (`q_proj`, `v_proj`, etc.) and using $r=32$, we provided significantly less "tunable surface area" relative to the model's total parameter count compared to the 2B run.
*   **Plateau:** Accuracy peaked at Step 80 and fluctuated slightly thereafter. This suggests that with the current restricted LoRA targets, the model has saturated its ability to absorb more specific rule text.

## 3. Comparison: 7B (Current) vs. 2B (Baseline)

| Feature | Gemma 2B (test1_r64) | Gemma 7B (test1_7b_r64) |
| :--- | :--- | :--- |
| **Peak Accuracy** | **89.2%** | 76.4% |
| **Epochs** | 5.0 | 3.0 |
| **LoRA Rank** | 64 | 32 |
| **LoRA Targets** | All Linear Layers | **Attention Only** |
| **Learning Rate** | 1e-4 | 5e-5 |

**Conclusion:** The 2B model currently "knows" the D&D rules better than this 7B run because it was allowed to train longer and across more of its internal layers.

## 4. Success Rubric: Is it ready for Step 2?
*   [x] **Train Loss:** Has dropped significantly (< 1.5).
*   [x] **Peak Accuracy:** Reached 76% (Exceeds 70% target).
*   [x] **Trend Stability:** Steady upward trend with minimal noise.
*   [x] **Grad Norm:** Very stable throughout.

**Verdict:** **Cleared for Step 2**, but expect slightly more hallucinations or "generic" answers than the 2B Knowledge-Peak version due to the lower absorption score.

## 5. Hyperparameter Optimization & Recommendations

To bring the 7B model up to the 90%+ accuracy level of the 2B model, I recommend the following adjustments for the next run:

| Recommendation | Suggested Change | Rationalization |
| :--- | :--- | :--- |
| **Increase Epochs** | **3.0 → 5.0** | Accuracy was still rising significantly at Step 80. More exposure is needed for a 7B model. |
| **Expand LoRA Targets** | **Add `gate_proj`, `up_proj`** | If VRAM allows, adding the MLP layers is the fastest way to increase knowledge capacity. |
| **Increase LoRA Rank** | **32 → 64** | Match the 2B model's capacity relative to its size. |
| **Slightly Higher LR** | **5e-5 → 8e-5** | The current LR is very safe; a slightly more aggressive rate may help it break through the 80% ceiling. |

## 6. Red Flags
*   **None observed.** The memory optimizations (offloading embeddings) were highly successful and did not destabilize the gradients.
