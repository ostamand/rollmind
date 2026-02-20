# Training Analysis: Step 2 (baseline_r64)

## 1. Executive Summary
This run confirms a critical hypothesis: **Higher capacity ($r=64$) without Step 1 knowledge adapters does not solve the accuracy bottleneck.** While training accuracy reached a near-perfect **98.5%**, evaluation accuracy remained stalled at **69%**. This is a definitive signal of **overfitting to the synthetic QA patterns** rather than internalizing the D&D rules. The model has become excellent at "memorizing the test" but cannot generalize to the validation set without the underlying domain knowledge from Step 1.

## 2. Primary Metrics Analysis

| Metric | Result (at best step) | Target | Status |
| :--- | :--- | :--- | :--- |
| **Eval Loss** | 1.312 (Step 200) | Decreasing | **Pass (Early)** |
| **Eval Accuracy** | 69.1% (Step 500) | > 85% | **Stagnant** |
| **Train Accuracy** | 98.5% (Final) | - | **Overfit** |
| **Entropy** | 0.68 (Final) | Stable | **Warning** |

*   **The Overfitting Pivot:** Around Step 440 (start of Epoch 3), training accuracy shot up from 78% to 91%, while evaluation accuracy actually began to fluctuate and eventually decline slightly (69% down to 67.7%).
*   **Capacity Effect:** Doubling the rank to $r=64$ allowed the model to memorize the training set much more efficiently, but provided zero gain in validation performance compared to $r=32$.
*   **Entropy Drop:** Final entropy dropped to 0.68, suggesting the model is starting to exhibit "Mode Collapse," giving very certain but potentially wrong or repetitive answers.

## 3. Checkpoint Selection
*   **Selected Checkpoint:** **Step 200 (Epoch 0.93)** or **Step 400 (Epoch 1.86)**.
*   **Rationale:** The `eval_loss` reached its lowest point at Step 200 (1.312) and hovered there until Step 400. Beyond Step 400, the loss began a steady climb upward, indicating that the model's predictive power on unseen data was actively degrading.

## 4. Success Rubric
*   [x] **Convergence:** Yes, but very early.
*   [ ] **Instruction Adherence:** Failed. 69% is the "glass ceiling" for the base model on this specific D&D dataset.
*   [ ] **Rule Retention:** N/A (Baseline run).
*   [ ] **No Repetition:** Warning. Low entropy indicates potential for looping in long responses.

## 5. Hyperparameter Optimization & Recommendations

The bottleneck is no longer technical or capacity-related; it is **data-dependency related**.

| Recommendation | Suggested Change | Rationalization |
| :--- | :--- | :--- |
| **Re-run Step 1 ($r=64$)** | **Sequential Start** | The base Gemma model lacks the raw D&D facts to answer the validation set. We must provide the "D&D Brain" via Step 1 before instruction tuning. |
| **Reduce Step 2 Epochs** | **4.0 → 2.0** | The model begins overfitting significantly after the second exposure to the data. 2 epochs is the sweet spot for alignment. |
| **Lower Learning Rate** | **8e-5 → 4e-5** | For the sequential run, we want a "gentler" touch to avoid washing out the Step 1 knowledge. |
| **Early Stopping** | **Enable** | Set the trainer to stop if `eval_loss` doesn't improve for 2 consecutive evaluations. |

## 6. Final Verdict
**The Baseline path is exhausted.** $r=64$ is sufficient capacity, but it must be filled with domain knowledge. **Proceed to Step 1 Knowledge Extraction with $r=64$.**
