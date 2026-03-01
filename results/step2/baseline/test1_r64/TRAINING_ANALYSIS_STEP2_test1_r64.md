# Training Analysis: Step 2 (test1_r64 - Sequential)

## 1. Executive Summary
This run is a **technical success but an accuracy failure**. By loading the Step 1 Knowledge Adapters ($r=64$) before instruction tuning, we achieved better alignment and a slightly higher evaluation accuracy (**71.3%**) compared to the baseline without adapters (**69.1%**). The model is extremely stable, with training and evaluation losses nearly converging (1.01 vs 1.16). However, we are still significantly below the **85% accuracy target**, suggesting that while the "brain" is bigger, the model is still struggling to bridge the gap between raw knowledge and precise instruction following for D&D rules.

## 2. Primary Metrics Analysis

| Metric | Result (at best step) | Target | Status |
| :--- | :--- | :--- | :--- |
| **Eval Loss** | 1.161 (Step 200/430) | Decreasing | **Pass** |
| **Eval Accuracy** | 71.3% (Step 400) | > 85% | **Weak** |
| **Train Accuracy** | 84.3% (Step 310) | - | **Good** |
| **Entropy** | 1.20 (Final) | Stable | **Pass** |

*   **Knowledge Transfer:** The starting accuracy at Step 10 was **57.4%**, whereas the baseline without adapters started at **48.4%**. This confirms that the Step 1 knowledge was successfully loaded and provided a better starting point.
*   **The 70% Ceiling:** Despite the $r=64$ capacity and the prior knowledge, the model is hitting a plateau at ~71% accuracy. This indicates that the current instruction tuning data might be the limiting factor, or the model needs more intensive alignment.

## 3. Checkpoint Selection
*   **Selected Checkpoint:** **Step 400 (Epoch 1.86)**
*   **Rationale:** This checkpoint achieved the peak evaluation accuracy of **71.33%**. While Step 430 had a marginally lower `eval_loss`, the accuracy began to dip slightly, suggesting the start of overfitting to the specific phrasing of the training QA pairs.

## 4. Success Rubric
*   [x] **Convergence:** Yes. Eval loss reached a stable minimum.
*   [ ] **Instruction Adherence:** Moderate. 71% is functional but will likely hallucinate complex mechanics.
*   [x] **Rule Retention:** Pass. The improvement over the baseline proves the model is utilizing Step 1 knowledge.
*   [x] **No Repetition:** Pass. Entropy is very healthy at 1.20.

## 5. Hyperparameter Optimization & Recommendations

The model is stable and generalizing well, but it isn't "sharp" enough.

| Recommendation | Suggested Change | Rationalization |
| :--- | :--- | :--- |
| **Increase LR for Step 2** | **5e-5 → 1e-4** | The convergence is very slow and stable. A more aggressive learning rate during Step 2 might help the model "re-wire" its Step 1 knowledge more effectively into the instruction format. |
| **Increase Training Duration** | **2.0 → 3.0 Epochs** | Since we are only at 82% training accuracy, the model hasn't even fully "learned" the training set yet. Giving it one more epoch with a higher LR should push validation accuracy higher. |
| **Increase lora_alpha** | **128 → 256** | Doubling the alpha relative to the rank ($4 	imes r$) makes the adapters more "influential" over the base model's weights, which can help with complex rule adherence. |
| **Reduce lora_dropout** | **0.1 → 0.05** | The model is currently *underfitting* (Train Acc 82% vs Eval Acc 71%). Reducing dropout will allow it to fit the training data more tightly, which should pull the evaluation accuracy up. |

## 6. Final Verdict
The sequential pipeline is the correct approach. We have successfully integrated domain knowledge, but we are being too "gentle" during the alignment phase. **Re-run Step 2 with higher LR and lower dropout.**
