# Training Analysis: Step 2 (test2_7b_r64)

## 1. Executive Summary
This run evaluated the **Gemma 7B** model with an expanded instruction dataset ("more data") to improve generalization. While the model reached a higher peak evaluation accuracy (**74.5%** vs **72.3%** in test1), it did so at the cost of higher loss. The model achieved its optimal balance of conversational fluidness and accuracy at **Step 450**, just before a massive overfitting spike at the 1-epoch mark.

## 2. Primary Metrics Analysis

| Metric | Result (at best step) | Status | Interpretation |
| :--- | :--- | :--- | :--- |
| **Eval Loss** | 1.029 (Step 450) | **Good** | Slightly higher than test1 (0.994), likely due to increased data complexity. |
| **Eval Accuracy** | 72.01% (Step 450) | **Good** | Stable alignment; peaked at 74.5% later, but with significantly worse loss. |
| **Train Loss** | 0.940 (Step 450) | **Healthy** | Loss was still decreasing smoothly until the "overfitting cliff" at Step 470. |
| **Entropy** | 1.50 (Stable) | **Excellent** | Consistent with test1; the model shows no signs of mode collapse. |

### The "Overfitting Cliff" (Step 470):
*   **Observation:** At Step 470 (exactly 1.006 epochs), the `train_loss` dropped from 0.93 to **0.74** in a single window, and eventually down to **0.10**. Simultaneously, `eval_loss` exploded from 1.02 to **1.35+**.
*   **Conclusion:** The model has completely memorized the expanded training set by the end of the first epoch. Any training beyond Step 460 is actively damaging the model's ability to generalize to new D&D questions.

## 3. Selecting the Best Checkpoint
*   **Selected Checkpoint:** **checkpoint-450**
*   **Rationale:** This is the **Absolute Minimum Eval Loss** checkpoint. It provides the best compromise between rule accuracy and natural language generation. While Step 1050 had higher accuracy (74.5%), the loss of 1.36 indicates the model is becoming "brittle" and likely to hallucinate specific training patterns in production.

## 4. Success Rubric: Is it ready for Deployment?
*   [x] **Convergence:** `eval_loss` reached its minimum at Step 450.
*   [x] **Instruction Adherence:** High accuracy and stable entropy confirm template mastery.
*   [x] **Rule Retention:** The high starting accuracy (72% at Step 450) indicates it is successfully leveraging Step 1 knowledge.
*   [x] **No Repetition:** Entropy remains in the healthy 1.5 range.

**Verdict:** **Ready for Inference.** Use **checkpoint-450**. This run confirms that "more data" requires more careful epoch management.

## 5. Hyperparameter Optimization & Recommendations

The persistence of the `5e-5` learning rate in this run, combined with the higher minimum loss compared to test1, strongly suggests we are "overshooting" the global minimum.

| Recommendation | Suggested Change | Rationalization |
| :--- | :--- | :--- |
| **Lower Learning Rate** | **5e-5 → 2e-5** | With the larger dataset, we need a finer "brush" to find the global minimum without triggering the aggressive overfitting seen at Step 470. |
| **Hard Epoch Limit** | **1.0 Epochs** | The data is very clear: 1.0 epochs is the absolute ceiling. Future runs should use `num_train_epochs: 1.0` to avoid wasting compute on overfitting. |
| **Increase LoRA Dropout**| **0.10 → 0.15** | To counter the aggressive memorization of the larger dataset, slightly higher dropout will force the model to learn more robust features. |

## 6. Red Flags
*   **Catastrophic Overfitting:** The speed at which the model dropped to 0.10 train loss while eval loss skyrocketed suggests the dataset might contain high-repetition patterns or that the model capacity (7B) is very high relative to the unique information density of the QA pairs.
