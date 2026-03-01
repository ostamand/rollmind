# Training Analysis: Step 2 (optimized_r64 - Sequential)

## 1. Executive Summary
This run represents the **absolute limit of the Gemma-2B model** for this dataset. By loading the Step 1 Knowledge Adapters ($r=64$) and using an aggressive learning rate ($1e-4$), we pushed the training accuracy to a near-perfect **96.5%**. However, the evaluation accuracy hit a hard ceiling at **71.3%** and then began to decline. The massive gap between training success and validation performance is a definitive sign of **overfitting to the synthetic instruction patterns** rather than learning the logical application of the D&D rules.

## 2. Primary Metrics Analysis

| Metric | Result (at best step) | Target | Status |
| :--- | :--- | :--- | :--- |
| **Eval Loss** | 1.161 (Step 200) | Decreasing | **Pass** |
| **Eval Accuracy** | 71.3% (Step 400) | > 85% | **Fail (Ceiling)** |
| **Train Accuracy** | 96.5% (Step 620) | - | **Overfit** |
| **Entropy** | 0.77 (Final) | Stable | **Warning** |

*   **Intelligence Ceiling:** Despite Loading the Step 1 "Brain" and giving the model 3 epochs of training, the model cannot generalize past 71% accuracy. This suggests that the 2B parameter count lacks the reasoning depth to connect complex rules (e.g., combining a class feature with a specific spell requirement) in an instruction format.
*   **Overfitting Pivot:** After Step 400, training accuracy continued to rise while evaluation accuracy dropped from 71% to 69%. The model essentially stopped learning D&D rules and started "memorizing the noise" in the training set.

## 3. Checkpoint Selection
*   **Selected Checkpoint:** **Step 200 (Epoch 0.93)**.
*   **Rationale:** Although Step 400 had slightly higher accuracy, Step 200 achieved the **absolute minimum `eval_loss` (1.16)**. This version of the model is the best balance between the new instruction format and the underlying domain knowledge before the weights became too specialized to the training examples.

## 4. Success Rubric
*   [x] **Convergence:** Yes. Eval loss stabilized early.
*   [ ] **Instruction Adherence:** Failed. 71% is functional for simple queries but unreliable for rule-lawyering.
*   [x] **Rule Retention:** Pass. The model clearly knows more than the baseline, but can't "express" it under pressure.
*   [x] **No Repetition:** Pass. Entropy is still high enough to avoid looping.

## 5. Hyperparameter Optimization & Recommendations

We have exhausted the hyperparameter space for the 2B model. Further tweaks (more LR, less dropout) will only increase overfitting. 

| Recommendation | Suggested Change | Rationalization |
| :--- | :--- | :--- |
| **Switch to Gemma-7B** | **Model Upgrade** | The 2B model has hit its "IQ Limit." To break the 85% accuracy barrier, we need the increased logical depth and parameter count of the 7B (or 9B) version. |
| **Increase Dropout (7B)** | **lora_dropout: 0.1** | When moving to 7B, we must increase regularization to avoid the same overfitting patterns we saw here. |
| **Lower LR (7B)** | **5e-5** | A 7B model will converge much faster on knowledge; a gentler LR will preserve the pre-trained weights better. |

## 6. Final Verdict
**Gemma-2B is insufficient for a professional-grade D&D Assistant.** While it is an excellent "Rule Search" tool, it cannot handle the multi-step reasoning required for high-accuracy instruction following. **Proceed to Step 1 Knowledge Extraction with Gemma-7B.**
