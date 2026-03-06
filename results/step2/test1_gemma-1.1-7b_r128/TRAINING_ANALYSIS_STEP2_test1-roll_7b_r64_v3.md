# Training Analysis: Step 2 Instruction Tuning (test1-roll_7b_r64) - v3

## 1. Executive Summary
This run successfully aligned the model to the D&D instruction format, reaching a peak generalization performance at **Step 900**. Beyond this point, the model entered a phase of rapid overfitting characterized by a sharp drop in training loss and a corresponding rise in evaluation loss.

## 2. Metric Trends

### Loss Convergence
- **Initial Eval Loss:** 1.3715 (Step 100)
- **Best Eval Loss:** 1.0523 (Step 900)
- **Final Eval Loss:** 1.0523 (Step 1391 - Best model re-evaluation)
- **Overfitting Signal:** Evaluation loss increased from **1.0523** (Step 900) to **1.1117** (Step 1100), despite training loss falling below 0.65.

### Accuracy & Entropy
- **Eval Token Accuracy:** Peaked at **70.35%** at the optimal checkpoint.
- **Training Token Accuracy:** Spiked from ~71% to ~81% at Step 940, confirming the onset of memorization.
- **Entropy:** Decreased from **1.80** to **0.91**. The final entropy is quite low, suggesting the model may be prone to repetitive or "canned" responses if trained further.

## 3. Checkpoint Evaluation

| Checkpoint | Eval Loss | Action |
| :--- | :--- | :--- |
| Step 500 | 1.1419 | Underfitted |
| **Step 900** | **1.0523** | **Optimal - Use for Deployment** |
| Step 1100 | 1.1117 | Overfitted |

## 4. Hyperparameter Recommendations

- **Max Steps/Epochs:** Reduce to **900 steps** or **1.0 epoch**. The extra 491 steps contributed to overfitting without improving generalization.
- **Regularization:** Increase `lora_dropout` from current value to **0.1** to slow down the memorization of training samples.
- **Learning Rate:** The current peak of 4e-05 is effective for rapid alignment but could be lowered to **2e-05** to find a finer local minimum for `eval_loss`.

## 5. Conclusion
**Status: SUCCESS (Conditional).** 
The run produced a high-quality adapter at Step 900. The divergence in later steps is a standard overfitting profile for SFT on specialized datasets. The Step 900 adapter is recommended for integration into the inference pipeline.
